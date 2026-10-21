"""Aider AI pair programmer: ~/.aider or .aider.chat.history.md."""
import json
import os
import re
import shutil

from ..core import HOME, el, iso_ms, text_of
from .base import Agent


def root():
    return os.environ.get('AIDER_HOME') or os.path.join(HOME, '.aider')


class Aider(Agent):
    key, name, aliases, binary, writable = 'aider', 'Aider', ('aider-chat',), 'aider', False

    def detect(self):
        return bool(shutil.which('aider') or os.path.isdir(root()))

    def list(self, cfg):
        out = {}
        base = os.path.join(root(), 'chats')
        if os.path.isdir(base):
            for entry in os.scandir(base):
                if entry.name.endswith(('.md', '.json')):
                    sid = entry.name.rsplit('.', 1)[0]
                    st = entry.stat()
                    out['aider:' + sid] = self.session(sid, path=entry.path, sig=f'{st.st_mtime_ns}:{st.st_size}',
                                                       updated=int(st.st_mtime * 1000))
        return out

    def read(self, s, cfg):
        path = s.get('path')
        if not path or not os.path.exists(path):
            return []
        els = []
        try:
            if path.endswith('.json'):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                msgs = data.get('messages') or data.get('history') or []
                for d in msgs:
                    role = d.get('role', 'user')
                    text = text_of(d.get('content') or d.get('text') or '')
                    if text and text.strip():
                        els.append(el(d.get('id') or str(len(els)), role, text.strip(), iso_ms(d.get('timestamp'))))
            elif path.endswith('.md'):
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                parts = re.split(r'\n(?=#{1,4}\s+)', content)
                for part in parts:
                    part = part.strip()
                    if not part:
                        continue
                    role = 'assistant' if part.startswith('> ') or 'assistant' in part[:20].lower() else 'user'
                    text = re.sub(r'^#{1,4}\s*', '', part).strip()
                    if text:
                        els.append(el(str(len(els)), role, text, 0))
        except Exception:
            pass
        return els

    def resume_cmd(self, sid):
        return ['aider', '--restore-chat-history']

    def seed_cmd(self, prompt):
        return ['aider', '--message', prompt]
