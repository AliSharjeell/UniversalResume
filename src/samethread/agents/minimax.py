"""MiniMax Code (mcode): read-only. Sessions live in ~/.minimax/v2/sqlite/runtime-state.sqlite.

Its store is a migration-managed SQLite schema with several linked tables, so hop reads it and
continues chats inside MiniMax by seeding a new session (`hop resume mmx`), like Antigravity.
"""
import json
import os
import sqlite3

from ..core import HOME, el, fmt_call, fmt_result
from .base import Agent


def data_dir():
    return os.environ.get('MINIMAX_DATA_DIR') or os.environ.get('MAVIS_DATA_DIR') or os.path.join(HOME, '.minimax')


def db_path():
    return os.path.join(data_dir(), 'v2', 'sqlite', 'runtime-state.sqlite')


class MiniMax(Agent):
    key, name, aliases, binary, writable = 'mmx', 'MiniMax', ('minimax', 'mcode', 'minimax-code'), 'mcode', False

    def detect(self):
        return os.path.exists(db_path()) or super().detect()

    def connect(self):
        return sqlite3.connect(f'file:{db_path()}?mode=ro', uri=True, timeout=15)

    def list(self, cfg):
        if not os.path.exists(db_path()):
            return {}
        c = self.connect()
        try:
            stats = {sid: (n, mx) for sid, n, mx in
                     c.execute('select session_id, count(*), max(id) from local_runtime_message_rows group by session_id')}
            out = {}
            for sid, cwd, title, upd in c.execute(
                    "select session_id, workspace_dir, title, updated_at_ms from local_runtime_sessions where "
                    "parent_session_id is null and archived = 0 and visibility = 'visible' "
                    "and session_kind = 'conversation'"):
                n, mx = stats.get(sid, (0, 0))
                out['mmx:' + sid] = self.session(sid, cwd=os.path.normpath(cwd or HOME), title=title,
                                                 sig=f'{upd}:{n}:{mx}', updated=upd or 0)
            return out
        finally:
            c.close()

    def read(self, s, cfg):
        c = self.connect()
        try:
            rows = c.execute('select msg_id, role, created_at_ms, data_json from local_runtime_message_rows '
                             'where session_id=? order by id', (s['id'],)).fetchall()
        finally:
            c.close()
        els = []
        for mid, role, ts, data in rows:
            try:
                d = json.loads(data)
            except ValueError:
                continue
            txt = d.get('msg_content')
            if isinstance(txt, list):
                txt = '\n'.join(p.get('text', '') for p in txt if isinstance(p, dict))
            txt = (txt or '').strip() if isinstance(txt, str) else ''
            if role == 'user' and txt:
                els.append(el(mid, 'user', txt, ts))
            elif role == 'assistant' and txt:
                els.append(el(mid, 'assistant', txt, ts))
            for i, tc in enumerate(d.get('tool_calls') or []):
                if isinstance(tc, dict):
                    els.append(el(f'{mid}#t{i}', 'tool', fmt_call(tc.get('name') or tc.get('tool_name'),
                                                                  tc.get('args') or tc.get('arguments'), cfg), ts))
            if role == 'tool' and (txt or d.get('output')):
                els.append(el(mid, 'tool', fmt_result(txt or d.get('output'), cfg), ts))
        return els

    def resume_cmd(self, sid):
        return ['mcode', '--session', sid]

    def seed_cmd(self, prompt):
        return ['mcode', prompt]

    def install(self, dry):
        # MiniMax Code does not load local hook plugins from the CLI yet, so there is no hook to add.
        # Its chats are picked up automatically whenever Universal Resume starts or syncs.
        return 'no hook support yet; synced automatically on resume'
