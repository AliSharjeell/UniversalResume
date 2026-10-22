"""Aider AI pair programmer: ~/.aider or .aider.chat.history.md."""
import json
import os
import re
import shutil

from ..core import HOME, el, file_sig, iso_ms, lp, text_of, write_text
from .base import Agent, new_id


def root():
    return os.environ.get('AIDER_HOME') or os.path.join(HOME, '.aider')


class Aider(Agent):
    key, name, aliases, binary, writable, copyable = 'aider', 'Aider', ('aider-chat',), 'aider', False, True

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
                    # The heading names the speaker; the rest of the heading line is not content.
                    head = re.match(r'^#{1,4}\s*(.*)$', part.split('\n', 1)[0])
                    label = (head.group(1).strip().lower() if head else '')
                    role = 'assistant' if label.startswith('assistant') else 'user'
                    body = re.sub(r'^#{1,4}\s*[^\n]*\n?', '', part, count=1).strip()
                    if body:
                        els.append(el(str(len(els)), role, body, 0))
        except Exception:
            pass
        return els

    def write(self, cp, cwd, msgs, title, ctx):
        """Native copy: the chat becomes an Aider chat history Aider restores itself.

        Aider restores with `--restore-chat-history`, which reads .aider.chat.history.md from
        the project folder, so the copy is written there as well as into Aider's own chat store.
        """
        sid = cp['id'] if cp else new_id()
        base = os.path.join(root(), 'chats')
        os.makedirs(lp(base), exist_ok=True)
        path = os.path.join(base, sid + '.md')
        body = []
        for m in msgs:
            who = 'User' if m['role'] == 'user' else 'Assistant'
            body.append(f'#### {who}\n\n{m["text"]}\n')
        text = '\n'.join(body)
        last = max((m['ts'] for m in msgs), default=0)
        write_text(path, text, last)
        try:
            write_text(os.path.join(cwd, '.aider.chat.history.md'), text, last)
        except OSError:
            pass
        return {'id': sid, 'path': path, 'seen': [str(i) for i in range(len(msgs))], 'sig': file_sig(path)}

    def delete(self, cp):
        if cp.get('path') and os.path.exists(lp(cp['path'])):
            os.remove(lp(cp['path']))

    def resume_cmd(self, sid):
        return ['aider', '--restore-chat-history']

    def seed_cmd(self, prompt):
        return ['aider', '--message', prompt]
