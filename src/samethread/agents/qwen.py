"""Qwen Code: ~/.qwen/projects/<sanitized-cwd>/chats/<id>.jsonl, uuid/parentUuid records with Gemini-style parts."""
import os
import re
import uuid

from .. import hookkit
from ..core import HOME, HOP_MODEL, append_line, el, file_sig, fmt_call, fmt_result, iso_ms, lp, ms_iso, read_jsonl, write_lines
from .base import Agent


def root():
    return os.environ.get('QWEN_RUNTIME_DIR') or os.path.join(HOME, '.qwen')


def project_dir(cwd):
    return os.path.join(root(), 'projects', re.sub(r'[^a-zA-Z0-9]', '-', cwd.lower() if os.name == 'nt' else cwd), 'chats')


class Qwen(Agent):
    key, name, aliases, binary, writable = 'qwen', 'Qwen', ('qwen-code',), 'qwen', True

    def detect(self):
        return os.path.isdir(root()) or super().detect()

    def list(self, cfg):
        out, base = {}, os.path.join(root(), 'projects')
        if not os.path.isdir(lp(base)):
            return out
        for d in os.scandir(lp(base)):
            chats = os.path.join(d.path, 'chats')
            if not d.is_dir() or not os.path.isdir(chats):
                continue
            for f in os.scandir(chats):
                if f.name.endswith('.jsonl'):
                    st = f.stat()
                    path = os.path.join(base, d.name, 'chats', f.name)
                    out['qwen:' + f.name[:-6]] = self.session(f.name[:-6], path=path, sig=f'{st.st_mtime_ns}:{st.st_size}',
                                                              updated=int(st.st_mtime * 1000))
        return out

    def read(self, s, cfg):
        recs, leaf = {}, None
        for r in read_jsonl(s['path']):
            u = r.get('uuid')
            if not u:
                continue
            recs[u] = r
            s['cwd'] = s.get('cwd') or r.get('cwd')
            s['version'] = r.get('version') or s.get('version')
            if r.get('type') in ('user', 'assistant', 'tool_result'):
                leaf = u
            if r.get('subtype') == 'custom_title':
                s['title'] = (r.get('systemPayload') or {}).get('customTitle') or s.get('title')
            if r.get('type') == 'assistant' and r.get('model') == HOP_MODEL:
                s['is_hop'] = True
        chain, u, guard = [], leaf, set()
        while u and u in recs and u not in guard:
            guard.add(u)
            chain.append(recs[u])
            u = recs[u].get('parentUuid')
        chain.reverse()
        els = []
        for r in chain:
            t, u, ts = r.get('type'), r['uuid'], iso_ms(r.get('timestamp'))
            if t == 'system' and r.get('subtype') == 'chat_compression':
                summary = (r.get('systemPayload') or {}).get('summary')
                if summary:
                    els.append(el(u, 'user', summary, ts, 'summary'))
                continue
            if t not in ('user', 'assistant', 'tool_result') or r.get('subtype'):
                continue
            for i, p in enumerate((r.get('message') or {}).get('parts') or []):
                if not isinstance(p, dict) or p.get('thought'):
                    continue
                pid = f'{u}#{i}'
                if isinstance(p.get('text'), str) and p['text'].strip():
                    els.append(el(pid, 'assistant' if t == 'assistant' else 'user' if t == 'user' else 'tool',
                                  p['text'].strip(), ts))
                elif p.get('functionCall'):
                    fc = p['functionCall']
                    els.append(el(pid, 'tool', fmt_call(fc.get('name'), fc.get('args'), cfg), ts))
                elif p.get('functionResponse'):
                    resp = p['functionResponse'].get('response')
                    out = resp.get('output', resp) if isinstance(resp, dict) else resp
                    els.append(el(pid, 'tool', fmt_result(out, cfg), ts))
        return els

    def write(self, cp, cwd, msgs, title, ctx):
        sid = cp['id'] if cp else str(uuid.uuid4())
        path = cp['path'] if cp else os.path.join(project_dir(cwd), sid + '.jsonl')
        base = {'sessionId': sid, 'cwd': cwd, 'version': ctx.get('qwen_version') or '0.0.0'}
        lines, seen, parent = [], [], None
        for m in msgs:
            u = str(uuid.uuid4())
            if m['role'] == 'user':
                lines.append(dict(base, uuid=u, parentUuid=parent, timestamp=ms_iso(m['ts']), type='user',
                                  message={'role': 'user', 'parts': [{'text': m['text']}]}))
            else:
                lines.append(dict(base, uuid=u, parentUuid=parent, timestamp=ms_iso(m['ts']), type='assistant',
                                  model=HOP_MODEL, message={'role': 'model', 'parts': [{'text': m['text']}]}))
            seen.append(f'{u}#0')
            parent = u
        last = max(m['ts'] for m in msgs)
        lines.append(dict(base, uuid=str(uuid.uuid4()), parentUuid=parent, timestamp=ms_iso(last), type='system',
                          subtype='custom_title', systemPayload={'customTitle': title, 'titleSource': 'manual'}))
        write_lines(path, lines, last)
        return {'id': sid, 'path': path, 'seen': seen, 'sig': file_sig(path)}

    def retitle(self, cp, title):
        last = None
        for r in read_jsonl(cp['path']):
            last = r.get('uuid') or last
        append_line(cp['path'], {'uuid': str(uuid.uuid4()), 'parentUuid': last, 'sessionId': cp['id'],
                                 'timestamp': ms_iso(int(os.path.getmtime(lp(cp['path'])) * 1000)), 'type': 'system',
                                 'subtype': 'custom_title', 'systemPayload': {'customTitle': title, 'titleSource': 'manual'}})
        return True

    def delete(self, cp):
        if os.path.exists(lp(cp['path'])):
            os.remove(lp(cp['path']))

    def resume_cmd(self, sid):
        return ['qwen', '--resume', sid]

    def seed_cmd(self, prompt):
        return ['qwen', prompt]

    def install(self, dry):
        return hookkit.add_json_hooks(os.path.join(root(), 'settings.json'), ['Stop'], dry)

    def uninstall(self, dry):
        return hookkit.remove_json_hooks(os.path.join(root(), 'settings.json'), dry)
