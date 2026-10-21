"""DeepSeek Harness / CLI: ~/.deepseek/sessions or deepseek CLI."""
import json
import os
import shutil

from ..core import HOME, el, iso_ms, read_jsonl, text_of
from .base import Agent


def root():
    return os.environ.get('DEEPSEEK_HOME') or os.path.join(HOME, '.deepseek')


class DeepSeek(Agent):
    key, name, aliases, binary, writable = 'deepseek', 'DeepSeek', ('deepseek-harness', 'deepseek-cli', 'deepseek-coder'), 'deepseek', False

    def _bin(self):
        return shutil.which('deepseek') or shutil.which('deepseek-harness') or shutil.which('deepseek-coder') or 'deepseek'

    def detect(self):
        return bool(shutil.which('deepseek') or shutil.which('deepseek-harness') or os.path.isdir(root()))

    def list(self, cfg):
        out = {}
        for sub in ('sessions', 'chats'):
            base = os.path.join(root(), sub)
            if not os.path.isdir(base):
                continue
            for entry in os.scandir(base):
                if entry.name.endswith(('.json', '.jsonl')):
                    sid = entry.name.rsplit('.', 1)[0]
                    st = entry.stat()
                    out['deepseek:' + sid] = self.session(sid, path=entry.path, sig=f'{st.st_mtime_ns}:{st.st_size}',
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
                    role = d.get('role') or 'user'
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

    def resume_cmd(self, sid):
        return [self._bin(), '--resume', sid]

    def seed_cmd(self, prompt):
        return [self._bin(), prompt]
