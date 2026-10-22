"""OpenCode 1.x: SQLite opencode.db (session/message/part). Writes go through `opencode import`."""
import json
import os
import secrets
import shutil
import sqlite3
import string
import sys

from .. import hookkit
from ..core import HOME, HOP_DIR, HopError, el, fmt_call, fmt_result, now_ms, run_quiet, write_json
from .base import Agent

DB = os.environ.get('OPENCODE_DB_PATH') or os.path.join(HOME, '.local', 'share', 'opencode', 'opencode.db')
CONFIG_DIR = os.path.join(HOME, '.config', 'opencode')
PLUGIN = os.path.join(CONFIG_DIR, 'plugins', 'samethread.js')
SLUG = 'hop-'
B62 = string.digits + string.ascii_letters
_oid_last = [0, 0]


def oc_id(prefix, ts, desc=False):
    """Same layout as OpenCode's Identifier.create: 6 time bytes (hex) + 14 random base62 chars."""
    if ts != _oid_last[0]:
        _oid_last[0], _oid_last[1] = ts, 0
    _oid_last[1] += 1
    n = ts * 0x1000 + _oid_last[1]
    if desc:
        n = ~n
    hx = ''.join('%02x' % ((n >> (40 - 8 * i)) & 0xff) for i in range(6))
    return f'{prefix}_{hx}' + ''.join(secrets.choice(B62) for _ in range(14))


def connect(rw=False):
    if not os.path.exists(DB):
        return None
    return sqlite3.connect(f'file:{DB}?mode={"rw" if rw else "ro"}', uri=True, timeout=15)


def binary():
    if sys.platform == 'win32':
        p = shutil.which('opencode.cmd') or shutil.which('opencode.exe') or shutil.which('opencode')
    else:
        p = shutil.which('opencode')
    if not p:
        raise HopError('opencode not found on PATH')
    exe = os.path.join(os.path.dirname(p), 'node_modules', 'opencode-ai', 'bin', 'opencode.exe')
    return exe if os.path.exists(exe) else p


def sig(c, sid):
    upd = c.execute('select time_updated from session where id=?', (sid,)).fetchone()
    n, mx = c.execute('select count(*), max(time_updated) from part where session_id=?', (sid,)).fetchone()
    return f'{upd[0] if upd else 0}:{n}:{mx}'


class OpenCode(Agent):
    key, name, aliases, binary, writable = 'oc', 'OpenCode', ('opencode',), 'opencode', True

    def detect(self):
        return os.path.exists(DB) or super().detect()

    def list(self, cfg):
        c = connect()
        if not c:
            return {}
        try:
            stats = {sid: (n, mx) for sid, n, mx in
                     c.execute('select session_id, count(*), max(time_updated) from part group by session_id')}
            out = {}
            for sid, directory, title, slug, upd in c.execute(
                    'select id, directory, title, slug, time_updated from session '
                    'where parent_id is null and time_archived is null'):
                n, mx = stats.get(sid, (0, 0))
                out['oc:' + sid] = self.session(sid, cwd=os.path.normpath(directory), title=title,
                                                is_hop=(slug or '').startswith(SLUG), sig=f'{upd}:{n}:{mx}', updated=upd)
            return out
        finally:
            c.close()

    def read(self, s, cfg):
        c = connect()
        try:
            order, msgs, parts = [], {}, {}
            for mid, data in c.execute('select id, data from message where session_id=? order by time_created, id',
                                       (s['id'],)):
                msgs[mid] = json.loads(data)
                order.append(mid)
            for pid, mid, data in c.execute('select id, message_id, data from part where session_id=? order by id',
                                            (s['id'],)):
                parts.setdefault(mid, []).append((pid, json.loads(data)))
        finally:
            c.close()
        els = []
        for mid in order:
            m = msgs[mid]
            role = m.get('role')
            kind = 'summary' if role == 'assistant' and m.get('summary') else 'msg'
            mts = (m.get('time') or {}).get('created') or 0
            for pid, p in parts.get(mid, []):
                pt = p.get('type')
                ts = (p.get('time') or {}).get('start') or mts
                if pt == 'text':
                    txt = (p.get('text') or '').strip()
                    if txt and not p.get('synthetic') and not p.get('ignored'):
                        els.append(el(pid, 'user' if role == 'user' else 'assistant', txt, ts, kind))
                elif pt == 'tool':
                    st = p.get('state') or {}
                    if st.get('status') in ('pending', 'running'):
                        continue
                    out = st.get('output') if st.get('status') == 'completed' else st.get('error')
                    els.append(el(pid, 'tool', fmt_call(p.get('tool'), st.get('input'), cfg) + '\n' + fmt_result(out, cfg), ts))
                elif pt == 'file':
                    els.append(el(pid, 'user' if role == 'user' else 'tool',
                                  f'[file: {p.get("filename") or p.get("url") or "?"}]', ts))
        return els

    def model(self, cfg, ctx):
        if 'oc_model' not in ctx:
            if cfg.get('oc_model'):
                provider, _, model = cfg['oc_model'].partition('/')
                ctx['oc_model'] = {'providerID': provider, 'modelID': model, '_version': '1.0.0'}
            else:
                c = connect()
                try:
                    row = c.execute("select json_extract(data, '$.model') from message where "
                                    "json_extract(data, '$.role')='user' order by time_created desc limit 1").fetchone()
                    ver = c.execute('select version from session order by time_updated desc limit 1').fetchone()
                finally:
                    c.close()
                if not row or not row[0]:
                    raise HopError('no OpenCode model found; set "oc_model" in ~/.hop/config.json (provider/model)')
                m = json.loads(row[0])
                ctx['oc_model'] = {'providerID': m['providerID'], 'modelID': m['modelID'],
                                   '_version': ver[0] if ver else '1.0.0'}
        return ctx['oc_model']

    def write(self, cp, cwd, msgs, title, ctx):
        if not os.path.isdir(cwd):
            raise HopError(f'folder no longer exists: {cwd}')
        model = self.model(ctx['cfg'], ctx)
        first = msgs[0]['ts'] or now_ms()
        sid = cp['id'] if cp else oc_id('ses', first, desc=True)
        mdl = {'providerID': model['providerID'], 'modelID': model['modelID']}
        doc_msgs, seen, last, parent = [], [], 0, None
        for m in msgs:
            ts = max(m['ts'] or 0, last + 1)
            last = ts
            mid, pid = oc_id('msg', ts), oc_id('prt', ts)
            if m['role'] == 'user':
                info = {'id': mid, 'sessionID': sid, 'role': 'user', 'time': {'created': ts}, 'agent': 'build', 'model': mdl}
                parent = mid
            else:
                info = {'id': mid, 'sessionID': sid, 'role': 'assistant', 'parentID': parent, 'mode': 'build',
                        'agent': 'build', 'path': {'cwd': cwd, 'root': '/'}, 'cost': 0,
                        'tokens': {'input': 0, 'output': 0, 'reasoning': 0, 'cache': {'read': 0, 'write': 0}},
                        'modelID': mdl['modelID'], 'providerID': mdl['providerID'],
                        'time': {'created': ts, 'completed': ts}, 'finish': 'stop'}
            doc_msgs.append({'info': info, 'parts': [{'id': pid, 'sessionID': sid, 'messageID': mid, 'type': 'text',
                                                      'text': m['text']}]})
            seen.append(pid)
        doc = {'info': {'id': sid, 'slug': SLUG + sid[-8:].lower(), 'projectID': 'global', 'directory': cwd,
                        'title': title, 'version': model['_version'], 'time': {'created': first, 'updated': last}},
               'messages': doc_msgs}
        tmp = os.path.join(HOP_DIR, 'tmp', sid + '.json')
        write_json(tmp, doc)
        exe = binary()
        try:
            if cp:
                run_quiet([exe, 'session', 'delete', sid, '--pure'])
            r = run_quiet([exe, 'import', tmp, '--pure'], cwd=cwd)
            if 'Imported session' not in (r.stdout + r.stderr):
                raise HopError(f'opencode import failed: {(r.stderr or r.stdout).strip()[-300:]}')
        finally:
            os.remove(tmp)
        c = connect()
        if not c:
            raise HopError(f'OpenCode imported the chat, but its database is not at {DB}; set OPENCODE_DB_PATH')
        try:
            return {'id': sid, 'seen': seen, 'sig': sig(c, sid)}
        finally:
            c.close()

    def retitle(self, cp, title):
        c = connect(rw=True)
        try:
            c.execute('update session set title=? where id=?', (title, cp['id']))
            c.commit()
        finally:
            c.close()
        return True

    def delete(self, cp):
        run_quiet([binary(), 'session', 'delete', cp['id'], '--pure'])

    def resume_cmd(self, sid):
        return ['opencode', '-s', sid]

    def seed_cmd(self, prompt):
        return ['opencode', prompt]

    def install(self, dry):
        src = ('// SameThread: after each OpenCode turn, mirror chats into the other agent CLIs.\n'
               '// Installed by `hop install`; removed by `hop uninstall`.\n' + hookkit.js_kicker(
                   '\nexport const SameThread = async () => {\n  kick()\n  return {\n'
                   '    event: async ({ event }) => {\n      if (event.type === "session.idle") kick()\n    },\n  }\n}\n'))
        return 'plugin ' + hookkit.write_file(PLUGIN, src, dry)

    def uninstall(self, dry):
        return 'plugin ' + hookkit.remove_file(PLUGIN, dry)
