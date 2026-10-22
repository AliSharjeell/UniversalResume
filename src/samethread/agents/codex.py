"""Codex CLI: $CODEX_HOME/sessions/YYYY/MM/DD/rollout-<time>-<uuid>.jsonl, titles in session_index.jsonl."""
import datetime as dt
import json
import os
import re
import shutil
import uuid

from .. import hookkit
from ..core import (HOME, HOP_ORIGIN, append_line, el, file_sig, fmt_call, fmt_result, iso_ms, lp, ms_iso, read_jsonl,
                    text_of, write_lines)
from .base import Agent

INJECTED = ('<environment_context', '<user_instructions', '# AGENTS.md', '<INSTRUCTIONS', '<skills_instructions',
            '<permissions', '<turn_aborted', '<subagent_notification', '<user_shell_command')
UUID_RE = re.compile(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.jsonl$')


def home():
    return os.environ.get('CODEX_HOME') or os.path.join(HOME, '.codex')


def names():
    """Latest thread name per session id (Codex's own /rename log)."""
    out = {}
    path = os.path.join(home(), 'session_index.jsonl')
    if os.path.exists(path):
        for d in read_jsonl(path):
            if d.get('id') and d.get('thread_name'):
                out[d['id']] = d['thread_name']
    return out


class Codex(Agent):
    key, name, binary, writable = 'codex', 'Codex', 'codex', True

    def detect(self):
        return os.path.isdir(home()) or super().detect()

    def list(self, cfg):
        root = os.path.join(home(), 'sessions')
        out, titles = {}, names()
        for d, _, files in os.walk(root):
            for f in files:
                m = UUID_RE.search(f)
                if f.startswith('rollout-') and m:
                    path = os.path.join(d, f)
                    st = os.stat(lp(path))
                    out['codex:' + m.group(1)] = self.session(m.group(1), path=path, title=titles.get(m.group(1)),
                                                              sig=f'{st.st_mtime_ns}:{st.st_size}',
                                                              updated=int(st.st_mtime * 1000))
        return out

    def read(self, s, cfg):
        els = []
        for i, d in enumerate(read_jsonl(s['path'])):
            t, p, ts = d.get('type'), d.get('payload') or {}, iso_ms(d.get('timestamp'))
            if t == 'session_meta':
                s.update(cwd=p.get('cwd'), is_hop=p.get('originator') == HOP_ORIGIN, automation=p.get('source') == 'exec',
                         version=p.get('cli_version'))
                continue
            if t == 'compacted' and p.get('message'):
                els.append(el(f'L{i}', 'user', p['message'], ts, 'summary'))
                continue
            if t != 'response_item':
                continue
            pid, pt = p.get('id') or f'L{i}', p.get('type')
            if pt == 'message':
                txt = text_of(p.get('content')).strip()
                if not txt:
                    continue
                if p.get('role') == 'user' and not txt.startswith(INJECTED):
                    els.append(el(pid, 'user', txt, ts))
                elif p.get('role') == 'assistant':
                    els.append(el(pid, 'assistant', txt, ts))
            elif pt in ('function_call', 'custom_tool_call'):
                els.append(el(pid, 'tool', fmt_call(p.get('name'), p.get('arguments') or p.get('input'), cfg), ts))
            elif pt in ('function_call_output', 'custom_tool_call_output'):
                out = p.get('output')
                if isinstance(out, dict):
                    out = out.get('content') or out.get('output')
                els.append(el(pid, 'tool', fmt_result(out, cfg), ts))
            elif pt == 'local_shell_call':
                els.append(el(pid, 'tool', fmt_call('shell', {'command': (p.get('action') or {}).get('command')}, cfg), ts))
        return els

    def defaults(self, ctx):
        """Provider (the resume picker filters by it) and CLI version, from the user's own setup."""
        if 'codex' not in ctx:
            provider, version = 'openai', '0.0.0'
            try:
                with open(os.path.join(home(), 'config.toml'), encoding='utf-8') as f:
                    top = f.read().split('\n[', 1)[0]
                m = re.search(r'^\s*model_provider\s*=\s*"([^"]+)"', top, re.M)
                provider = m.group(1) if m else provider
            except OSError:
                pass
            newest = max(self.list({}).values(), key=lambda s: s['updated'], default=None)
            if newest:
                meta = next(read_jsonl(newest['path']), {})
                version = (meta.get('payload') or {}).get('cli_version') or version
            ctx['codex'] = (provider, version)
        return ctx['codex']

    def write(self, cp, cwd, msgs, title, ctx):
        provider, version = self.defaults(ctx)
        sid = cp['id'] if cp else str(uuid.uuid4())
        first, last = msgs[0]['ts'], max(m['ts'] for m in msgs)
        if cp:
            path = cp['path']
        else:
            t = dt.datetime.fromtimestamp(first / 1000)
            path = os.path.join(home(), 'sessions', f'{t:%Y}', f'{t:%m}', f'{t:%d}', f'rollout-{t:%Y-%m-%dT%H-%M-%S}-{sid}.jsonl')
        lines = [{'timestamp': ms_iso(first), 'type': 'session_meta', 'payload': {
            'id': sid, 'timestamp': ms_iso(first), 'cwd': cwd, 'originator': HOP_ORIGIN, 'cli_version': version,
            'source': 'cli', 'model_provider': provider}}]
        turn = None

        def event(ts, payload):
            lines.append({'timestamp': ms_iso(ts), 'type': 'event_msg', 'payload': payload})

        def item(ts, role, kind, text):
            lines.append({'timestamp': ms_iso(ts), 'type': 'response_item', 'payload': {
                'type': 'message', 'role': role, 'content': [{'type': kind, 'text': text}]}})

        for m in msgs:
            if m['role'] == 'user' or turn is None:
                if turn:
                    event(m['ts'], {'type': 'task_complete', 'turn_id': turn})
                turn = str(uuid.uuid4())
                event(m['ts'], {'type': 'task_started', 'turn_id': turn})
            if m['role'] == 'user':
                event(m['ts'], {'type': 'user_message', 'message': m['text'], 'images': []})
                item(m['ts'], 'user', 'input_text', m['text'])
            else:
                event(m['ts'], {'type': 'agent_message', 'message': m['text']})
                item(m['ts'], 'assistant', 'output_text', m['text'])
        event(last, {'type': 'task_complete', 'turn_id': turn})
        write_lines(path, lines, last)
        append_line(os.path.join(home(), 'session_index.jsonl'), {'id': sid, 'thread_name': title, 'updated_at': ms_iso(last)})
        seen = [f'L{i}' for i, line in enumerate(lines) if line['type'] == 'response_item']
        return {'id': sid, 'path': path, 'seen': seen, 'sig': file_sig(path)}

    def retitle(self, cp, title):
        append_line(os.path.join(home(), 'session_index.jsonl'),
                    {'id': cp['id'], 'thread_name': title, 'updated_at': ms_iso(int(os.path.getmtime(lp(cp['path'])) * 1000))})
        return True

    def delete(self, cp):
        if os.path.exists(lp(cp['path'])):
            os.remove(lp(cp['path']))

    def resume_cmd(self, sid):
        return ['codex', 'resume', sid]

    def seed_cmd(self, prompt):
        return ['codex', prompt]

    # Codex runs hooks.json hooks only after the user reviews them, so hop uses the config-level
    # `notify` command instead: it fires after every turn and lives in the user's own config.toml.
    NOTIFY_MARK = '# samethread: sync chats after each Codex turn (managed by `hop install`)'

    def install(self, dry):
        path = os.path.join(home(), 'config.toml')
        text = open(path, encoding='utf-8').read() if os.path.exists(path) else ''
        if self.NOTIFY_MARK in text:
            return 'notify already installed'
        head = text.split('\n[', 1)[0]
        if re.search(r'^\s*notify\s*=', head, re.M):
            return 'skipped: config.toml already sets `notify` (Codex allows one); sync runs automatically on resume'
        line = json.dumps([hookkit.bare_python().replace('\\', '/'), '-m', 'samethread', 'hook'])
        if dry:
            print(f'  [dry-run] would add `notify` to {path}')
        else:
            os.makedirs(home(), exist_ok=True)
            if text and not os.path.exists(path + '.samethread.bak'):
                shutil.copy2(path, path + '.samethread.bak')
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(f'{self.NOTIFY_MARK}\nnotify = {line}\n' + text)
        return f'notify added ({path})'

    def uninstall(self, dry):
        path = os.path.join(home(), 'config.toml')
        text = open(path, encoding='utf-8').read() if os.path.exists(path) else ''
        new = re.sub(re.escape(self.NOTIFY_MARK) + r'\nnotify = .*\n', '', text)
        if new == text:
            return 'nothing to remove'
        if not dry:
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(new)
        return 'notify removed'
