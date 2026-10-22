"""Grok Build / Grok CLI: ~/.grok/sessions/<escaped-workspace>/<session>/chat_history.jsonl.

Grok groups its sessions per workspace: the folder name is the escaped workspace path
(C%3A%5CAppsNew%5Cproject) and each session is a folder holding chat_history.jsonl.
"""
import os
import shutil
import urllib.parse

from ..core import HOME, el, file_sig, iso_ms, lp, read_jsonl, text_of, write_lines
from .base import Agent, new_id


def root():
    return os.environ.get('GROK_HOME') or os.path.join(HOME, '.grok')


def workspace_dir(cwd):
    """The folder name Grok uses for a workspace: the path, escaped."""
    return urllib.parse.quote(cwd or '', safe='')


def session_dir(cwd, sid):
    return os.path.join(root(), 'sessions', workspace_dir(cwd), sid)


class Grok(Agent):
    key, name, aliases, binary, writable, copyable = 'grok', 'Grok', ('grok-build', 'grok-cli', 'xai'), 'grok', False, True

    def _bin(self):
        return shutil.which('grok') or shutil.which('grok-build') or 'grok'

    def detect(self):
        return bool(shutil.which('grok') or shutil.which('grok-build') or os.path.isdir(root()))

    def list(self, cfg):
        out = {}
        base = os.path.join(root(), 'sessions')
        if not os.path.isdir(base):
            return out
        # Grok's real layout: sessions/<escaped-workspace>/<session id>/chat_history.jsonl
        for ws in os.scandir(base):
            if not ws.is_dir():
                continue
            for entry in os.scandir(ws.path):
                if not entry.is_dir():
                    continue
                path = os.path.join(entry.path, 'chat_history.jsonl')
                if not os.path.exists(path):
                    continue
                st = os.stat(lp(path))
                out['grok:' + entry.name] = self.session(entry.name, path=path,
                                                         cwd=urllib.parse.unquote(ws.name),
                                                         sig=f'{st.st_mtime_ns}:{st.st_size}',
                                                         updated=int(st.st_mtime * 1000))
        # Older builds kept a flat session file next to the workspace folders.
        for entry in os.scandir(base):
            if entry.is_file() and entry.name.endswith(('.json', '.jsonl')) and entry.name != 'prompt_history.jsonl':
                sid = entry.name.rsplit('.', 1)[0]
                st = entry.stat()
                out.setdefault('grok:' + sid, self.session(sid, path=entry.path,
                                                            sig=f'{st.st_mtime_ns}:{st.st_size}',
                                                            updated=int(st.st_mtime * 1000)))
        return out

    def read(self, s, cfg):
        path = s.get('path')
        if not path or not os.path.exists(path):
            return []
        els = []
        try:
            for d in read_jsonl(path):
                # Grok tags records by type, not role: user / assistant / tool_result / reasoning.
                t = d.get('type') or d.get('role')
                if t == 'user':
                    role = 'user'
                elif t == 'assistant':
                    role = 'assistant'
                elif t in ('tool_result', 'tool'):
                    role = 'tool'
                else:
                    continue
                text = text_of(d.get('content') or d.get('text') or '')
                if text and text.strip():
                    els.append(el(d.get('id') or str(len(els)), role, text.strip(), iso_ms(d.get('timestamp'))))
        except Exception:
            pass
        return els

    def write(self, cp, cwd, msgs, title, ctx):
        """Native copy: the chat becomes a Grok session the Grok CLI lists and resumes itself."""
        sid = cp['id'] if cp else new_id()
        out = session_dir(cwd, sid)
        os.makedirs(lp(out), exist_ok=True)
        path = os.path.join(out, 'chat_history.jsonl')
        records = []
        for m in msgs:
            if m['role'] == 'user':
                records.append({'type': 'user', 'content': [{'type': 'text', 'text': m['text']}]})
            else:
                records.append({'type': 'assistant', 'content': m['text']})
        write_lines(path, records, max((m['ts'] for m in msgs), default=0))
        # Grok's own reader numbers these records by position, so the ids are positional.
        return {'id': sid, 'path': path, 'seen': [str(i) for i in range(len(records))], 'sig': file_sig(path)}

    def delete(self, cp):
        path = cp.get('path')
        if path and os.path.exists(lp(path)):
            folder = os.path.dirname(path)
            os.remove(lp(path))
            if os.path.isdir(lp(folder)) and not os.listdir(lp(folder)):
                os.rmdir(lp(folder))

    def resume_cmd(self, sid):
        return [self._bin(), '--resume', sid]

    def seed_cmd(self, prompt):
        return [self._bin(), prompt]
