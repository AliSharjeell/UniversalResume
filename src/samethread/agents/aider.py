"""Aider AI pair programmer: ~/.aider or .aider.chat.history.md."""
import os
import shutil

from ..core import HOME, el, iso_ms
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

    def resume_cmd(self, sid):
        return ['aider', '--restore-chat-history']

    def seed_cmd(self, prompt):
        return ['aider', '--message', prompt]
