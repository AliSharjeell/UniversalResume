"""Claude Code: ~/.claude/projects/<cwd-slug>/<uuid>.jsonl, a parentUuid-linked record log."""
import os
import re
import time
import uuid

from .. import hookkit
from ..core import (HOME, HOP_MODEL, append_line, el, file_sig, fmt_call, fmt_result, iso_ms, lp, ms_iso, read_jsonl,
                    write_lines)
from .base import Agent

ROOT = os.path.join(HOME, '.claude')
PROJECTS = os.path.join(ROOT, 'projects')
SETTINGS = os.path.join(ROOT, 'settings.json')
NOISE_RE = re.compile(r'<(system-reminder|local-command-caveat|local-command-stdout|local-command-stderr)>.*?</\1>', re.S)


def slug(path):
    return re.sub(r'[^A-Za-z0-9]', '-', path)


def user_text(s):
    m = re.search(r'<command-name>(.*?)</command-name>', s, re.S)
    if m:
        a = re.search(r'<command-args>(.*?)</command-args>', s, re.S)
        return f'{m.group(1).strip()} {a.group(1).strip() if a else ""}'.strip()
    return NOISE_RE.sub('', s).strip()


def blocks_text(content):
    if isinstance(content, str):
        return content
    out = []
    for b in content or []:
        if isinstance(b, dict):
            if b.get('type') == 'text':
                out.append(b.get('text') or '')
            elif b.get('type') == 'image':
                out.append('[image]')
    return '\n'.join(out)


class Claude(Agent):
    key, name, aliases, binary, writable = 'cc', 'Claude', ('claude', 'claude-code'), 'claude', True

    def detect(self):
        return os.path.isdir(ROOT) or super().detect()

    def list(self, cfg):
        out = {}
        if not os.path.isdir(PROJECTS):
            return out
        for d in os.scandir(PROJECTS):
            if not d.is_dir():
                continue
            for f in os.scandir(d.path):
                if f.name.endswith('.jsonl') and f.is_file():
                    st = f.stat()
                    out['cc:' + f.name[:-6]] = self.session(f.name[:-6], path=f.path, sig=f'{st.st_mtime_ns}:{st.st_size}',
                                                            updated=int(st.st_mtime * 1000))
        return out

    def read(self, s, cfg):
        recs, leaf = {}, None
        meta = {'cwd': None, 'entrypoint': None, 'version': None, 'agent': None, 'custom': None, 'ai': None}
        for r in read_jsonl(s['path']):
            t = r.get('type')
            if t == 'custom-title':
                meta['custom'] = r.get('customTitle')
            elif t == 'agent-name':
                meta['agent'] = r.get('agentName')
            elif t == 'ai-title':
                meta['ai'] = r.get('aiTitle')
            u = r.get('uuid')
            if u:
                recs[u] = r
            if t in ('user', 'assistant') and u and not r.get('isSidechain'):
                leaf = u
                meta['cwd'] = meta['cwd'] or r.get('cwd')
                meta['entrypoint'] = meta['entrypoint'] or r.get('entrypoint')
                meta['version'] = r.get('version') or meta['version']
                if t == 'assistant' and (r.get('message') or {}).get('model') == HOP_MODEL:
                    s['is_hop'] = True

        chain, u, guard = [], leaf, set()
        while u and u in recs and u not in guard:
            guard.add(u)
            chain.append(recs[u])
            u = recs[u].get('parentUuid') or recs[u].get('logicalParentUuid')
        chain.reverse()

        els = []
        for r in chain:
            t = r.get('type')
            if t not in ('user', 'assistant') or r.get('isMeta') or r.get('isApiErrorMessage'):
                continue
            u, ts = r['uuid'], iso_ms(r.get('timestamp'))
            content = (r.get('message') or {}).get('content')
            if t == 'user':
                if r.get('isCompactSummary'):
                    txt = blocks_text(content).strip()
                    if txt:
                        els.append(el(f'{u}#0', 'user', txt, ts, 'summary'))
                    continue
                blocks = [{'type': 'text', 'text': content}] if isinstance(content, str) else (content or [])
                for i, b in enumerate(blocks):
                    if not isinstance(b, dict):
                        continue
                    bt = b.get('type')
                    if bt == 'text':
                        txt = user_text(b.get('text') or '')
                        if txt.startswith('<task-notification>'):
                            els.append(el(f'{u}#{i}', 'tool', fmt_result(txt, cfg), ts))
                        elif txt:
                            els.append(el(f'{u}#{i}', 'user', txt, ts))
                    elif bt == 'tool_result':
                        els.append(el(f'{u}#{i}', 'tool', fmt_result(blocks_text(b.get('content')), cfg), ts))
                    elif bt == 'image':
                        els.append(el(f'{u}#{i}', 'user', '[image]', ts))
            else:
                if isinstance(content, str):
                    content = [{'type': 'text', 'text': content}]
                for i, b in enumerate(content or []):
                    if not isinstance(b, dict):
                        continue
                    if b.get('type') == 'text' and (b.get('text') or '').strip():
                        els.append(el(f'{u}#{i}', 'assistant', b['text'].strip(), ts))
                    elif b.get('type') == 'tool_use':
                        els.append(el(f'{u}#{i}', 'tool', fmt_call(b.get('name'), b.get('input'), cfg), ts))

        s.update(cwd=meta['cwd'] or HOME, version=meta['version'], title=meta['agent'] or meta['custom'] or meta['ai'],
                 automation=meta['entrypoint'] not in cfg['cc_entrypoints'])
        return els

    def write(self, cp, cwd, msgs, title, ctx):
        sid = cp['id'] if cp else str(uuid.uuid4())
        path = cp['path'] if cp else os.path.join(PROJECTS, slug(cwd), sid + '.jsonl')
        base = {'isSidechain': False, 'userType': 'external', 'entrypoint': 'cli', 'cwd': cwd, 'sessionId': sid,
                'version': ctx.get('cc_version') or '2.1.0'}
        lines, seen, parent = [], [], None
        for m in msgs:
            u = str(uuid.uuid4())
            r = dict(base, parentUuid=parent, type=m['role'], uuid=u, timestamp=ms_iso(m['ts']))
            if m['role'] == 'user':
                r['message'] = {'role': 'user', 'content': m['text']}
            else:
                r['message'] = {'id': 'msg_hop_' + uuid.uuid4().hex[:24], 'type': 'message', 'role': 'assistant',
                                'model': HOP_MODEL, 'content': [{'type': 'text', 'text': m['text']}],
                                'stop_reason': 'end_turn', 'stop_sequence': None,
                                'usage': {'input_tokens': 0, 'output_tokens': 0}}
            lines.append(r)
            seen.append(u + '#0')
            parent = u
        lines.append({'type': 'custom-title', 'customTitle': title, 'sessionId': sid})
        write_lines(path, lines, max(m['ts'] for m in msgs))
        return {'id': sid, 'path': path, 'seen': seen, 'sig': file_sig(path)}

    def retitle(self, cp, title):
        if time.time() - os.path.getmtime(lp(cp['path'])) < 30:
            return False
        append_line(cp['path'], {'type': 'custom-title', 'customTitle': title, 'sessionId': cp['id']})
        return True

    def delete(self, cp):
        if os.path.exists(lp(cp['path'])):
            os.remove(lp(cp['path']))

    def resume_cmd(self, sid):
        return ['claude', '--resume', sid]

    def seed_cmd(self, prompt):
        return ['claude', prompt]

    def install(self, dry):
        return hookkit.add_json_hooks(SETTINGS, ['Stop', 'SessionEnd'], dry)

    def uninstall(self, dry):
        return hookkit.remove_json_hooks(SETTINGS, dry)
