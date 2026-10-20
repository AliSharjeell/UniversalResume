"""OpenHands / All-Hands agent: ~/.openhands/sessions or openhands CLI."""
import json
import os
import shutil

from ..core import HOME, el, iso_ms, read_jsonl
from .base import Agent


def root():
    return os.environ.get('OPENHANDS_HOME') or os.path.join(HOME, '.openhands')


class OpenHands(Agent):
    key, name, aliases, binary, writable = 'openhands', 'OpenHands', ('all-hands', 'opendevin'), 'openhands', False

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

    def resume_cmd(self, sid):
        return ['openhands', '--resume', sid]

    def seed_cmd(self, prompt):
        return ['openhands', prompt]
