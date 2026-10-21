"""Kimi Code 2.x: ~/.kimi-code/sessions/wd_<slug>_<hash>/session_<uuid>/{state.json, agents/main/wire.jsonl}."""
import hashlib
import json
import os
import re
import shutil
import uuid

from .. import hookkit
from ..core import (HOME, HopError, dumps, el, file_sig, fmt_call, fmt_result, iso_ms, lp, read_json,
                    read_jsonl, text_of, write_lines)
from .base import Agent

ROOT = os.path.join(HOME, '.kimi-code')
INDEX = os.path.join(ROOT, 'session_index.jsonl')
CONFIG = os.path.join(ROOT, 'config.toml')
BEGIN, END = '# >>> samethread (managed by `hop install`)', '# <<< samethread'


def fwd(p):
    return p.replace('\\', '/')


def wd_key(cwd):
    """Kimi's encodeWorkDirKey: folder-name slug + first 12 hex of sha256(forward-slash path)."""
    norm = fwd(cwd).rstrip('/')
    name = norm.split('/')[-1] or norm
    slug = re.sub(r'[^a-z0-9._-]+', '-', name.lower()).strip('-')[:40].strip('-')
    slug = 'workspace' if slug in ('', '.', '..') else slug
    return f'wd_{slug}_{hashlib.sha256(norm.encode()).hexdigest()[:12]}'


def index():
    out = {}
    if os.path.exists(INDEX):
        for d in read_jsonl(INDEX):
            if d.get('sessionId') and d.get('sessionDir'):
                out[d['sessionId']] = d
    return out


class Kimi(Agent):
    key, name, aliases, binary, writable = 'kimi', 'Kimi', ('kimi-code',), 'kimi', True

    def detect(self):
        return os.path.isdir(ROOT) or super().detect()

    def list(self, cfg):
        out = {}
        for sid, d in index().items():
            wire = os.path.join(d['sessionDir'], 'agents', 'main', 'wire.jsonl')
            state = read_json(os.path.join(d['sessionDir'], 'state.json'), None)
            if not state or state.get('archived') or not os.path.exists(lp(wire)):
                continue
            out['kimi:' + sid] = self.session(sid, path=wire, dir=d['sessionDir'], title=state.get('title'),
                                              cwd=os.path.normpath(state.get('cwd') or d.get('workDir') or HOME),
                                              is_hop=bool((state.get('custom') or {}).get('samethread')),
                                              sig=file_sig(wire), updated=iso_ms(state.get('updatedAt')) or 0)
        return out

    def read(self, s, cfg):
        els = []
        for r in read_jsonl(s['path']):
            t, ts = r.get('type'), r.get('time')
            if t == 'context.append_message':
                m = r.get('message') or {}
                txt = text_of(m.get('content') or '').strip()
                if not txt or (m.get('origin') or {}).get('kind', 'user') != 'user':
                    continue
                els.append(el(m.get('id') or f'm{ts}', 'user' if m.get('role') == 'user' else 'assistant', txt, ts))
            elif t == 'context.append_loop_event':
                e = r.get('event') or {}
                et = e.get('type')
                if et == 'content.part' and (e.get('part') or {}).get('type') == 'text':
                    txt = (e['part'].get('text') or '').strip()
                    if txt:
                        els.append(el(e.get('uuid'), 'assistant', txt, ts))
                elif et == 'tool.call':
                    els.append(el(e.get('uuid'), 'tool', fmt_call(e.get('name'), e.get('args'), cfg), ts))
                elif et == 'tool.result':
                    res = e.get('result') or {}
                    els.append(el(f'r:{e.get("toolCallId")}', 'tool',
                                  fmt_result(res.get('output') if isinstance(res, dict) else res, cfg), ts))
        return els

    def template(self, ctx):
        """Kimi only resumes a session whose agent profile is bound. hop reuses the newest real binding."""
        if 'kimi_bind' not in ctx:
            best = (0, None)
            for s in self.list({}).values():
                if s['is_hop']:
                    continue
                for r in read_jsonl(s['path']):
                    if r.get('type') == 'profile.bind' and r.get('time', 0) > best[0]:
                        best = (r['time'], r)
            ctx['kimi_bind'] = best[1]
        if not ctx['kimi_bind']:
            raise HopError('open Kimi Code once so hop can copy its agent profile')
        return ctx['kimi_bind']

    def write(self, cp, cwd, msgs, title, ctx):
        bind = self.template(ctx)
        sid = cp['id'] if cp else 'session_' + str(uuid.uuid4())
        sdir = cp['dir'] if cp else os.path.join(ROOT, 'sessions', wd_key(cwd), sid)
        agent_home = os.path.join(sdir, 'agents', 'main')
        first, last = msgs[0]['ts'], max(m['ts'] for m in msgs)
        lines = [{'type': 'metadata', 'protocol_version': '1.5', 'created_at': first},
                 {'type': 'runtime.set_binding', 'workspaceId': wd_key(cwd), 'runtimeId': 'local', 'agentId': 'main',
                  'time': first},
                 dict(bind, environmentDisclosure={'cwd': cwd}, time=first)]
        seen, turn, step = [], -1, 0
        for m in msgs:
            if m['role'] == 'user':
                turn, step = turn + 1, 0
                mid = 'msg_hop_' + uuid.uuid4().hex[:20]
                lines.append({'type': 'context.append_message', 'agentId': 'main', 'time': m['ts'], 'message': {
                    'role': 'user', 'content': [{'type': 'text', 'text': m['text']}], 'toolCalls': [],
                    'origin': {'kind': 'user'}, 'id': mid}})
                seen.append(mid)
                continue
            step += 1
            su, pu = str(uuid.uuid4()), str(uuid.uuid4())
            loop = {'turnId': str(max(turn, 0)), 'step': step}
            for ev in ({'type': 'step.begin', 'uuid': su, **loop},
                       {'type': 'content.part', 'uuid': pu, 'stepUuid': su, 'part': {'type': 'text', 'text': m['text']}, **loop},
                       {'type': 'step.end', 'uuid': su, 'finishReason': 'stop', **loop}):
                lines.append({'type': 'context.append_loop_event', 'agentId': 'main', 'event': ev, 'time': m['ts']})
            seen.append(pu)
        write_lines(os.path.join(agent_home, 'wire.jsonl'), lines, last)
        first_user = next((m['text'] for m in msgs if m['role'] == 'user'), '')
        state = {'id': sid, 'version': 2, 'cwd': fwd(cwd), 'archived': False,
                 'agents': {'main': {'homedir': fwd(agent_home), 'type': 'main'}}, 'custom': {'samethread': True},
                 'lastPrompt': first_user[:200], 'title': title, 'titleKind': 'custom', 'isCustomTitle': True,
                 'createdAt': first, 'updatedAt': last}
        with open(lp(os.path.join(sdir, 'state.json')), 'w', encoding='utf-8', newline='\n') as f:
            f.write(dumps(state))
        if not cp:
            with open(INDEX, 'a', encoding='utf-8', newline='\n') as f:
                f.write(dumps({'sessionId': sid, 'sessionDir': fwd(sdir), 'workDir': fwd(cwd)}) + '\n')
        wire = os.path.join(agent_home, 'wire.jsonl')
        return {'id': sid, 'path': wire, 'dir': sdir, 'seen': seen, 'sig': file_sig(wire)}

    def retitle(self, cp, title):
        path = os.path.join(cp['dir'], 'state.json')
        state = read_json(path, None)
        if not state:
            return False
        state.update(title=title, titleKind='custom', isCustomTitle=True)
        with open(lp(path), 'w', encoding='utf-8', newline='\n') as f:
            f.write(dumps(state))
        return True

    def delete(self, cp):
        shutil.rmtree(lp(cp['dir']), ignore_errors=True)
        if os.path.exists(INDEX):
            with open(INDEX, encoding='utf-8') as f:
                keep = [line for line in f if cp['id'] not in line]
            with open(INDEX, 'w', encoding='utf-8', newline='\n') as f:
                f.writelines(keep)

    def resume_cmd(self, sid):
        return ['kimi', '-S', sid]

    def seed_cmd(self, prompt):
        return ['kimi', prompt]

    def install(self, dry):
        text = open(CONFIG, encoding='utf-8').read() if os.path.exists(CONFIG) else ''
        if BEGIN in text:
            return 'hook already installed'
        block = f'\n{BEGIN}\n[[hooks]]\nevent = "Stop"\ncommand = {json.dumps(hookkit.command("/"))}\ntimeout = 30\n{END}\n'
        if dry:
            print(f'  [dry-run] would append a Stop hook to {CONFIG}')
        else:
            os.makedirs(ROOT, exist_ok=True)
            if text and not os.path.exists(CONFIG + '.samethread.bak'):
                shutil.copy2(CONFIG, CONFIG + '.samethread.bak')
            with open(CONFIG, 'a', encoding='utf-8', newline='\n') as f:
                f.write(block)
        return f'Stop hook added ({CONFIG})'

    def uninstall(self, dry):
        if not os.path.exists(CONFIG):
            return 'nothing to remove'
        text = open(CONFIG, encoding='utf-8').read()
        new = re.sub(r'\n?' + re.escape(BEGIN) + r'.*?' + re.escape(END) + r'\n?', '\n', text, flags=re.S)
        if new == text:
            return 'nothing to remove'
        if not dry:
            with open(CONFIG, 'w', encoding='utf-8', newline='\n') as f:
                f.write(new)
        return 'Stop hook removed'
