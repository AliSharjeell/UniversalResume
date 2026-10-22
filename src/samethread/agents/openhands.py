"""OpenHands / All-Hands agent: ~/.openhands/sessions or openhands CLI."""
import json
import os
import shutil

from ..core import HOME, el, file_sig, iso_ms, lp, read_jsonl, text_of
from .base import Agent


def root():
    return os.environ.get('OPENHANDS_HOME') or os.path.join(HOME, '.openhands')


class OpenHands(Agent):
    key, name, aliases, binary, writable, copyable = 'openhands', 'OpenHands', ('all-hands', 'opendevin'), 'openhands', False, True

    def detect(self):
        return bool(shutil.which('openhands') or os.path.isdir(root()))

    def list(self, cfg):
        out = {}
        base = os.path.join(root(), 'sessions')
        if os.path.isdir(base):
            for entry in os.scandir(base):
                if entry.name.endswith(('.json', '.jsonl')):
                    sid = entry.name.rsplit('.', 1)[0]
                    st = entry.stat()
                    out['openhands:' + sid] = self.session(sid, path=entry.path, sig=f'{st.st_mtime_ns}:{st.st_size}',
                                                           updated=int(st.st_mtime * 1000))
        return out

    def read(self, s, cfg):
        path = s.get('path')
        if not path or not os.path.exists(path):
            return []
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
        return els

    def write(self, cp, cwd, msgs, title, ctx):
        """Native copy: the chat becomes an OpenHands session file OpenHands lists and resumes itself."""
        path, sid, seen = self.write_session_file(cp, cwd, msgs, title, root(), dirs=('sessions',))
        return {'id': sid, 'path': path, 'seen': seen, 'sig': file_sig(path)}

    def delete(self, cp):
        if cp.get('path') and os.path.exists(lp(cp['path'])):
            os.remove(lp(cp['path']))

    def resume_cmd(self, sid):
        return ['openhands', '--resume', sid]

    def seed_cmd(self, prompt):
        return ['openhands', '-t', prompt]
