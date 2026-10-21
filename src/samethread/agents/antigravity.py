"""Antigravity CLI (agy): read-only. Conversations are runtime-owned protobuf; hop reads the transcript log."""
import json
import os
import re
import sqlite3
import urllib.parse

from .. import hookkit
from ..core import HOME, el, file_sig, fmt_call, fmt_result, iso_ms, read_jsonl, remap
from .base import Agent

ROOT = os.path.join(HOME, '.gemini', 'antigravity-cli')
HOOKS = os.path.join(HOME, '.gemini', 'config', 'hooks.json')
HDR_RE = re.compile(r'^(Created At|Completed At):.*\n?', re.M)


def transcript(cid):
    base = os.path.join(ROOT, 'brain', cid, '.system_generated', 'logs')
    for name in ('transcript_full.jsonl', 'transcript.jsonl'):
        p = os.path.join(base, name)
        if os.path.exists(p):
            return p
    return None


def uri_to_path(u):
    p = urllib.parse.unquote(urllib.parse.urlparse(u).path)
    if re.match(r'^/[A-Za-z]:', p):
        p = p[1:]
    return os.path.normpath(p)


class Antigravity(Agent):
    key, name, aliases, binary, writable = 'agy', 'Agy', ('antigravity',), 'agy', False

    def detect(self):
        return os.path.isdir(ROOT) or super().detect()

    def list(self, cfg):
        db = os.path.join(ROOT, 'conversation_summaries.db')
        if not os.path.exists(db):
            return {}
        c = sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=15)
        try:
            rows = c.execute('select conversation_id, title, last_modified_time, workspace_uris, '
                             'parent_conversation_id, nesting_depth from conversation_summaries').fetchall()
        finally:
            c.close()
        out = {}
        for cid, title, modified, ws, parent, depth in rows:
            path = transcript(cid)
            if parent or depth or not path:
                continue
            try:
                uris = json.loads(ws or '[]')
            except ValueError:
                uris = []
            file_mtime = int(os.path.getmtime(path) * 1000) if os.path.exists(path) else 0
            db_mtime = iso_ms(modified) if modified else 0
            updated_ts = max(db_mtime, file_mtime)
            out['agy:' + cid] = self.session(cid, path=path, title=title or None, sig=file_sig(path),
                                             cwd=remap(cfg, uri_to_path(uris[0]) if uris else HOME),
                                             updated=updated_ts)
        return out

    def read(self, s, cfg):
        els = []
        for d in read_jsonl(s['path']):
            st, idx, ts = d.get('type'), d.get('step_index'), iso_ms(d.get('created_at'))
            content = d.get('content') or ''
            if st == 'USER_INPUT':
                m = re.search(r'<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>', content, re.S)
                txt = m.group(1) if m else re.sub(r'<ADDITIONAL_METADATA>.*?</ADDITIONAL_METADATA>', '', content, flags=re.S)
                if d.get('media'):
                    txt += '\n[image]'
                if txt.strip():
                    els.append(el(idx, 'user', txt.strip(), ts))
            elif st == 'PLANNER_RESPONSE':
                if content.strip():
                    els.append(el(f'{idx}#0', 'assistant', content.strip(), ts))
                for i, tc in enumerate(d.get('tool_calls') or []):
                    els.append(el(f'{idx}#t{i}', 'tool', fmt_call(tc.get('name'), tc.get('args'), cfg), ts))
            elif st == 'CHECKPOINT':
                txt = re.sub(r'^\{\{ CHECKPOINT \d+ \}\}\s*', '', content).strip()
                if txt:
                    els.append(el(idx, 'user', txt, ts, 'summary'))
            elif d.get('source') == 'MODEL':
                els.append(el(idx, 'tool', fmt_result(HDR_RE.sub('', content).strip() or d.get('error'), cfg), ts))
        return els

    def resume_cmd(self, sid):
        return ['agy', '--conversation', sid]

    def seed_cmd(self, prompt):
        return ['agy', '-i', prompt]

    def install(self, dry):
        hooks = hookkit.load(HOOKS)
        # agy runs hooks through `cmd /c`, which mangles quotes, so the command stays unquoted.
        entry = {'Stop': [{'type': 'command', 'command': hookkit.command('\\', ' --json'), 'timeout': 15}]}
        if hooks.get('samethread') == entry:
            return 'hook already installed'
        hooks['samethread'] = entry
        hookkit.save(HOOKS, hooks, dry)
        return f'Stop hook added ({HOOKS})'

    def uninstall(self, dry):
        hooks = hookkit.load(HOOKS)
        if hooks.pop('samethread', None) is None:
            return 'nothing to remove'
        hookkit.save(HOOKS, hooks, dry)
        return 'Stop hook removed'
