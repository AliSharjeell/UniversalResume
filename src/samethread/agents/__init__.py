"""Registry of supported agents, in the order they appear in tags and listings."""
from .aider import Aider
from .antigravity import Antigravity
from .claude import Claude
from .codex import Codex
from .cursor import Cursor
from .deepseek import DeepSeek
from .grok import Grok
from .hermes import Hermes
from .kimi import Kimi
from .minimax import MiniMax
from .openclaw import OpenClaw
from .opencode import OpenCode
from .openhands import OpenHands
from .pi import Pi
from .qwen import Qwen

AGENTS = {a.key: a for a in (
    Claude(),
    Codex(),
    Cursor(),
    Antigravity(),
    Grok(),
    DeepSeek(),
    Hermes(),
    OpenClaw(),
    Aider(),
    OpenCode(),
    OpenHands(),
    Qwen(),
    Kimi(),
    MiniMax(),
    Pi(),
)}
NAMES = {k: a.name for k, a in AGENTS.items()}


def resolve(name):
    name = name.lower()
    for key, agent in AGENTS.items():
        if name in (key, agent.name.lower(), *agent.aliases):
            return key
    raise KeyError(name)


def targets(cfg):
    """Agents to write mirrors into: every writable agent that is installed, unless configured."""
    chosen = cfg.get('targets', 'auto')
    if chosen == 'auto':
        return [k for k, a in AGENTS.items() if a.writable and a.detect()]
    return [k for k in chosen if k in AGENTS and AGENTS[k].writable]
