"""What an agent adapter provides. Adding an agent means one subclass in this package."""
import shutil

from ..core import HopError


class Agent:
    key = ''          # short id used in state and on the command line
    name = ''         # tag shown in titles, e.g. "Claude"
    aliases = ()      # extra command-line names
    binary = ''       # executable name, for detection and resume
    writable = False  # can hop write a native, resumable session?

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
