"""What an agent adapter provides. Adding an agent means one subclass in this package."""
import os
import shutil
import uuid

from ..core import HopError, lp, write_json, write_lines


def new_id():
    """A time-ordered id where the runtime has one (uuid7), else a plain uuid4."""
    try:
        return str(uuid.uuid7())
    except AttributeError:
        return str(uuid.uuid4())


class Agent:
    key = ''          # short id used in state and on the command line
    name = ''         # tag shown in titles, e.g. "Claude"
    aliases = ()      # extra command-line names
    binary = ''       # executable name, for detection and resume
    writable = False  # can hop write a native, resumable session?
    copyable = False  # can hop create a native session on demand, for a single hop?

    @property
    def can_copy(self):
        """Native copy: hop writes the chat into this agent's own store and resumes it there.

        Agents whose store is a plain file can be copied into on demand even when they are not
        part of the background mirroring set (`writable`).
        """
        return self.copyable or self.writable

    def detect(self):
        """Is this agent installed / used on this machine?"""
        return bool(self.binary and shutil.which(self.binary))

    def list(self, cfg):
        """{'<key>:<id>': session} for every session, cheaply (no transcript parsing)."""
        return {}

    def read(self, s, cfg):
        """Transcript elements of session `s`. May fill s['title'], s['cwd'], s['is_hop'], s['automation']."""
        return []

    def write(self, cp, cwd, msgs, title, ctx):
        """Create (cp is None) or rewrite (cp = existing owned copy) a mirror. Returns id, seen, sig (+path)."""
        raise HopError(f'{self.name} sessions cannot be written')

    def write_session_file(self, cp, cwd, msgs, title, base_dir, sid=None, ext='json', dirs=('sessions',)):
        """Write the conversation as one of this agent's own session files.

        Shared by the agents whose stores are plain files: the conversation becomes a native,
        resumable session the agent lists and opens with its own resume command.

        Returns (path, sid, seen). `seen` holds the element ids the agent's own reader will
        report, so sync can diff the copy against the thread later.
        """
        sid = cp['id'] if cp else (sid or new_id())
        out = next((os.path.join(base_dir, d) for d in dirs if os.path.isdir(os.path.join(base_dir, d))), None)
        if out is None:
            out = os.path.join(base_dir, dirs[0])
            os.makedirs(lp(out), exist_ok=True)
        path = os.path.join(out, sid + '.' + ext)
        records, seen = [], []
        for i, m in enumerate(msgs):
            eid = f'm{i}'
            records.append({'id': eid, 'role': m['role'], 'content': m['text'], 'timestamp': m['ts']})
            seen.append(eid)
        first = msgs[0]['ts'] if msgs else 0
        last = max((m['ts'] for m in msgs), default=0)
        if ext == 'jsonl':
            write_lines(path, records, last)
        else:
            write_json(path, {'id': sid, 'title': title, 'cwd': cwd, 'createdAt': first, 'updatedAt': last,
                              'messages': records})
        return path, sid, seen

    def retitle(self, cp, title):
        return False

    def delete(self, cp):
        pass

    def resume_cmd(self, sid):
        return [self.binary, sid]

    def seed_cmd(self, prompt):
        """Start a new conversation that reads the transcript first."""
        if self.binary:
            return [self.binary, prompt]
        return None

    def install(self, dry):
        return None

    def uninstall(self, dry):
        return None

    def session(self, sid, **kw):
        return {'tool': self.key, 'id': sid, 'title': None, 'cwd': None, 'is_hop': False,
                'automation': False, **kw}
