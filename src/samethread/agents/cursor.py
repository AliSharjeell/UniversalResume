"""Cursor CLI / Agent: ~/.cursor/sessions and Cursor workspace composer storage."""
import glob
import json
import os
import shutil
import sqlite3
import urllib.parse

from ..core import HOME, el, file_sig, iso_ms, lp, read_jsonl, text_of
from .base import Agent


def root():
    return os.environ.get('CURSOR_HOME') or os.path.join(HOME, '.cursor')


def parse_uri(u):
    p = urllib.parse.unquote(urllib.parse.urlparse(u).path)
    if len(p) > 2 and p[0] == '/' and p[2] == ':':
        p = p[1:]
    return os.path.normpath(p)


class Cursor(Agent):
    key, name, aliases, binary, writable, copyable = 'cursor', 'Cursor', ('cursor-cli', 'cursor-agent', 'agent'), 'cursor-agent', False, True

    def _bin(self):
        return shutil.which('cursor-agent') or shutil.which('cursor') or 'cursor-agent'

    def detect(self):
        ws_dir = os.path.join(os.environ.get('APPDATA', ''), 'Cursor', 'User', 'workspaceStorage')
        return bool(shutil.which('cursor-agent') or shutil.which('cursor') or os.path.isdir(root()) or os.path.isdir(ws_dir))

    def list(self, cfg):
        out = {}
        # 1. File-based session stores
        for sub in ('sessions', 'chats'):
            base = os.path.join(root(), sub)
            if not os.path.isdir(base):
                continue
            for entry in os.scandir(base):
                if entry.name.endswith(('.json', '.jsonl')):
                    sid = entry.name.rsplit('.', 1)[0]
                    st = entry.stat()
                    out['cursor:' + sid] = self.session(sid, path=entry.path, sig=f'{st.st_mtime_ns}:{st.st_size}',
                                                        updated=int(st.st_mtime * 1000))

        # 2. Cursor workspaceStorage state.vscdb (Composers)
        ws_bases = []
        if os.name == 'nt' and os.environ.get('APPDATA'):
            ws_bases.append(os.path.join(os.environ['APPDATA'], 'Cursor', 'User', 'workspaceStorage'))
        ws_bases.append(os.path.expanduser('~/.config/Cursor/User/workspaceStorage'))
        ws_bases.append(os.path.expanduser('~/Library/Application Support/Cursor/User/workspaceStorage'))

        for base in ws_bases:
            if not os.path.isdir(base):
                continue
            for entry in os.scandir(base):
                if not entry.is_dir():
                    continue
                db_path = os.path.join(entry.path, 'state.vscdb')
                if not os.path.exists(db_path):
                    continue
                ws_file = os.path.join(entry.path, 'workspace.json')
                cwd = HOME
                if os.path.exists(ws_file):
                    try:
                        with open(ws_file, 'r', encoding='utf-8') as fp:
                            d = json.load(fp)
                            raw_u = d.get('folder') or d.get('workspace') or ''
                            if raw_u:
                                cwd = parse_uri(raw_u)
                    except Exception:
                        pass
                try:
                    c = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True, timeout=5)
                    try:
                        row = c.execute('select value from ItemTable where key = ?', ('composer.composerData',)).fetchone()
                        if row and row[0]:
                            data = json.loads(row[0])
                            for comp in data.get('allComposers', []):
                                cid = comp.get('composerId')
                                if cid:
                                    title = comp.get('name') or comp.get('text') or 'Cursor Composer'
                                    upd = comp.get('lastUpdatedAt') or comp.get('createdAt') or int(os.path.getmtime(db_path) * 1000)
                                    out['cursor:' + cid] = self.session(cid, cwd=cwd, title=title,
                                                                        sig=f'{db_path}:{upd}', updated=upd)
                    finally:
                        c.close()
                except Exception:
                    pass

        return out

    def read(self, s, cfg):
        path = s.get('path')
        if not path or not os.path.exists(path):
            return [el(s['id'], 'user', s.get('title') or 'Cursor session', s.get('updated', 0))]
        els = []
        try:
            if path.endswith('.jsonl'):
                for d in read_jsonl(path):
                    role = d.get('role') or ('user' if d.get('type') == 'user' else 'assistant')
                    text = text_of(d.get('content') or d.get('text') or '')
                    if text and text.strip():
                        els.append(el(d.get('id') or str(len(els)), role, text.strip(), iso_ms(d.get('timestamp'))))
            else:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                msgs = data.get('messages') or data.get('history') or []
                for d in msgs:
                    role = d.get('role', 'user')
                    text = text_of(d.get('content') or d.get('text') or '')
                    if text and text.strip():
                        els.append(el(d.get('id') or str(len(els)), role, text.strip(), iso_ms(d.get('timestamp'))))
        except Exception:
            pass
        return els or [el(s['id'], 'user', s.get('title') or 'Cursor session', s.get('updated', 0))]

    def write(self, cp, cwd, msgs, title, ctx):
        """Native copy: the chat becomes a Cursor session file Cursor lists and resumes itself."""
        path, sid, seen = self.write_session_file(cp, cwd, msgs, title, root(), dirs=('sessions', 'chats'))
        return {'id': sid, 'path': path, 'seen': seen, 'sig': file_sig(path)}

    def delete(self, cp):
        if cp.get('path') and os.path.exists(lp(cp['path'])):
            os.remove(lp(cp['path']))

    def resume_cmd(self, sid):
        b = self._bin()
        return [b, 'resume', sid] if 'cursor-agent' in b else [b, '--resume', sid]

    def seed_cmd(self, prompt):
        return [self._bin(), prompt]
