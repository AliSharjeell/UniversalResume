"""Pi (pi-coding-agent): ~/.pi/agent/sessions/--<cwd>--/<time>_<id>.jsonl, an append-only entry tree."""
import datetime as dt
import os
import re
import uuid

from .. import hookkit
from ..core import (HOME, HOP_ORIGIN, append_line, el, file_sig, fmt_call, fmt_result, iso_ms, lp, ms_iso, read_jsonl,
                    text_of, write_lines)
from .base import Agent

USAGE = {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0, 'totalTokens': 0,
         'cost': {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0, 'total': 0}}


def agent_dir():
    return os.environ.get('PI_CODING_AGENT_DIR') or os.path.join(HOME, '.pi', 'agent')


def sessions_dir():
    return os.environ.get('PI_CODING_AGENT_SESSION_DIR') or os.path.join(agent_dir(), 'sessions')


def cwd_dir(cwd):
    return os.path.join(sessions_dir(), '--' + re.sub(r'[/\\:]', '-', re.sub(r'^[/\\]', '', cwd)) + '--')


def short_id():
    return uuid.uuid4().hex[:8]


class Pi(Agent):
    key, name, binary, writable = 'pi', 'Pi', 'pi', True

    def detect(self):
        return os.path.isdir(agent_dir()) or super().detect()

    def list(self, cfg):
        out, root = {}, sessions_dir()
        if not os.path.isdir(lp(root)):
            return out
        for d in os.scandir(lp(root)):
            if not d.is_dir():
                continue
            for f in os.scandir(d.path):
                if f.name.endswith('.jsonl') and '_' in f.name:
                    sid = f.name[:-6].split('_', 1)[1]
                    st = f.stat()
                    path = os.path.join(root, d.name, f.name)
                    out['pi:' + sid] = self.session(sid, path=path, sig=f'{st.st_mtime_ns}:{st.st_size}',
                                                    updated=int(st.st_mtime * 1000))
        return out

    def read(self, s, cfg):
        entries, leaf = {}, None
        for d in read_jsonl(s['path']):
            if d.get('type') == 'session':
                s['cwd'] = d.get('cwd')
                continue
            if d.get('id'):
                entries[d['id']] = d
                leaf = d['id']
            if d.get('type') == 'session_info' and d.get('name'):
                s['title'] = d['name']
        chain, u, guard = [], leaf, set()
        while u and u in entries and u not in guard:
            guard.add(u)
            chain.append(entries[u])
            u = entries[u].get('parentId')
        chain.reverse()
        els = []
        for e in chain:
            ts, eid = iso_ms(e.get('timestamp')), e['id']
            if e.get('type') == 'compaction' and e.get('summary'):
                els.append(el(eid, 'user', e['summary'], ts, 'summary'))
            if e.get('type') != 'message':
                continue
            m = e.get('message') or {}
            role, content = m.get('role'), m.get('content')
            if role == 'user':
                txt = text_of(content).strip()
                if txt:
                    els.append(el(eid, 'user', txt, ts))
            elif role == 'assistant':
                if m.get('provider') == HOP_ORIGIN:
                    s['is_hop'] = True
                for i, b in enumerate(content or []):
                    if b.get('type') == 'text' and (b.get('text') or '').strip():
                        els.append(el(f'{eid}#{i}', 'assistant', b['text'].strip(), ts))
                    elif b.get('type') == 'toolCall':
                        els.append(el(f'{eid}#{i}', 'tool', fmt_call(b.get('name'), b.get('arguments'), cfg), ts))
            elif role == 'toolResult':
                els.append(el(eid, 'tool', fmt_result(content, cfg), ts))
            elif role == 'bashExecution':
                els.append(el(eid, 'tool', fmt_call('bash', {'command': m.get('command')}, cfg) + '\n'
                              + fmt_result(m.get('output'), cfg), ts))
        return els

    def write(self, cp, cwd, msgs, title, ctx):
        sid = cp['id'] if cp else str(uuid.uuid4())
        first, last = msgs[0]['ts'], max(m['ts'] for m in msgs)
        if cp:
            path = cp['path']
        else:
            stamp = ms_iso(first).replace(':', '-').replace('.', '-')
            path = os.path.join(cwd_dir(cwd), f'{stamp}_{sid}.jsonl')
        lines, seen, parent = [{'type': 'session', 'version': 3, 'id': sid, 'timestamp': ms_iso(first), 'cwd': cwd}], [], None
        for m in msgs:
            eid = short_id()
            if m['role'] == 'user':
                msg = {'role': 'user', 'content': [{'type': 'text', 'text': m['text']}], 'timestamp': m['ts']}
                seen.append(eid)
            else:
                msg = {'role': 'assistant', 'content': [{'type': 'text', 'text': m['text']}], 'api': 'openai-completions',
                       'provider': HOP_ORIGIN, 'model': 'hop-import', 'usage': USAGE, 'stopReason': 'stop',
                       'timestamp': m['ts']}
                seen.append(f'{eid}#0')
            lines.append({'type': 'message', 'id': eid, 'parentId': parent, 'timestamp': ms_iso(m['ts']), 'message': msg})
            parent = eid
        lines.append({'type': 'session_info', 'id': short_id(), 'parentId': parent, 'timestamp': ms_iso(last), 'name': title})
        write_lines(path, lines, last)
        return {'id': sid, 'path': path, 'seen': seen, 'sig': file_sig(path)}

    def retitle(self, cp, title):
        last = None
        for d in read_jsonl(cp['path']):
            last = d.get('id') or last
        append_line(cp['path'], {'type': 'session_info', 'id': short_id(), 'parentId': last,
                                 'timestamp': ms_iso(int(dt.datetime.now().timestamp() * 1000)), 'name': title})
        return True

    def delete(self, cp):
        if os.path.exists(lp(cp['path'])):
            os.remove(lp(cp['path']))

    def resume_cmd(self, sid):
        return ['pi', '--session', sid]

    def seed_cmd(self, prompt):
        return ['pi', prompt]

    def install(self, dry):
        src = ('// SameThread: after each Pi turn, mirror chats into the other agent CLIs.\n'
               '// Installed by `hop install`; removed by `hop uninstall`.\n' + hookkit.js_kicker(
                   '\nexport default function (pi: any) {\n  pi.on("agent_end", async () => kick())\n'
                   '  pi.on("session_shutdown", async () => kick())\n}\n'))
        return 'extension ' + hookkit.write_file(os.path.join(agent_dir(), 'extensions', 'samethread.ts'), src, dry)

    def uninstall(self, dry):
        return 'extension ' + hookkit.remove_file(os.path.join(agent_dir(), 'extensions', 'samethread.ts'), dry)
