"""Shared plumbing: paths, config, logging, JSON and the tool-neutral transcript elements."""
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time

HOME = os.path.expanduser('~')
HOP_DIR = os.environ.get('HOP_HOME') or os.path.join(HOME, '.hop')
THREAD_DIR = os.path.join(HOP_DIR, 'threads')
HANDOFF_DIR = os.path.join(HOP_DIR, 'handoff')
INDEX_PATH = os.path.join(HOP_DIR, 'index.json')
CONFIG_PATH = os.path.join(HOP_DIR, 'config.json')
LOCK_PATH = os.path.join(HOP_DIR, 'sync.lock')
PENDING_PATH = os.path.join(HOP_DIR, 'sync.pending')
LOG_PATH = os.path.join(HOP_DIR, 'hop.log')

HOP_MODEL = 'hop-import'
HOP_ORIGIN = 'samethread'
NO_WINDOW = 0x08000000 if os.name == 'nt' else 0

DEFAULT_CONFIG = {
    'targets': 'auto',
    'max_age_days': 365,
    'min_user_messages': 1,
    'cc_entrypoints': ['cli'],
    'path_remap': {'C:\\Windows\\System32': '~'},
    'max_chars': 400000,
    'tool_output_chars': 1500,
    'tool_input_chars': 300,
    'oc_model': None,
}

settings = {'quiet': False}


class HopError(Exception):
    pass


def log(msg):
    line = f'{dt.datetime.now():%Y-%m-%d %H:%M:%S} {msg}'
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except OSError:
        pass
    if not settings['quiet']:
        print(msg, flush=True)


def lp(path):
    """Long-path-safe form of a path for file operations (Windows' 260-char limit)."""
    if os.name != 'nt':
        return path
    path = os.path.abspath(path)
    return path if path.startswith('\\\\?\\') or len(path) < 240 else '\\\\?\\' + path


def dumps(obj):
    """Compact JSON, byte-compatible with JSON.stringify (some agents grep their files for it)."""
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))


def read_json(path, default):
    try:
        with open(lp(path), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, data, indent=None):
    os.makedirs(lp(os.path.dirname(path)), exist_ok=True)
    tmp = path + '.tmp'
    with open(lp(tmp), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
    os.replace(lp(tmp), lp(path))


def read_jsonl(path):
    with open(lp(path), encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if isinstance(obj, dict):
                yield obj


def write_lines(path, lines, mtime_ms=None):
    """Atomically write JSONL records, then stamp the file with the chat's real last activity."""
    os.makedirs(lp(os.path.dirname(path)), exist_ok=True)
    tmp = path + '.hoptmp'
    with open(lp(tmp), 'w', encoding='utf-8', newline='\n') as f:
        f.write(''.join(dumps(line) + '\n' for line in lines))
    os.replace(lp(tmp), lp(path))
    if mtime_ms:
        os.utime(lp(path), (mtime_ms / 1000, mtime_ms / 1000))


def append_line(path, obj):
    with open(lp(path), 'a', encoding='utf-8', newline='\n') as f:
        f.write(dumps(obj) + '\n')


def file_sig(path):
    st = os.stat(lp(path))
    return f'{st.st_mtime_ns}:{st.st_size}'


def load_config():
    user = read_json(CONFIG_PATH, None)
    if user is None:
        write_json(CONFIG_PATH, DEFAULT_CONFIG, indent=2)
        user = {}
    if user.get('targets') == ['cc', 'oc']:  # the v0.1 default; newer versions detect installed agents
        user['targets'] = 'auto'
        write_json(CONFIG_PATH, {**DEFAULT_CONFIG, **user}, indent=2)
    if user.get('max_age_days') == 30:
        user['max_age_days'] = 365
        write_json(CONFIG_PATH, {**DEFAULT_CONFIG, **user}, indent=2)
    return {**DEFAULT_CONFIG, **user}


def now_ms():
    return int(time.time() * 1000)


def iso_ms(s):
    if not s:
        return 0
    if isinstance(s, (int, float)):
        return int(s if s > 10 ** 11 else s * 1000)
    s = str(s).strip().replace(' ', 'T').replace('Z', '+00:00')
    m = re.match(r'(.*?\.)(\d+)(.*)$', s)
    if m:
        s = m.group(1) + (m.group(2) + '000000')[:6] + m.group(3)
    try:
        return int(dt.datetime.fromisoformat(s).timestamp() * 1000)
    except ValueError:
        return 0


def ms_iso(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def ago(ms):
    s = max(0, (now_ms() - ms) // 1000)
    for unit, n in (('d', 86400), ('h', 3600), ('m', 60)):
        if s >= n:
            return f'{s // n}{unit} ago'
    return 'just now'


def clip(text, n):
    text = text or ''
    if len(text) <= n:
        return text
    head, tail = n * 2 // 3, n // 3
    return f'{text[:head]}\n... [{len(text) - n} chars cut] ...\n{text[-tail:]}'


def same_path(a, b):
    try:
        ra = os.path.realpath(os.path.normpath(a))
        rb = os.path.realpath(os.path.normpath(b))
    except Exception:
        ra = os.path.normpath(a)
        rb = os.path.normpath(b)
    if sys.platform in ('darwin', 'win32'):
        return ra.lower() == rb.lower()
    return os.path.normcase(ra) == os.path.normcase(rb)


def remap(cfg, path):
    for src, dst in (cfg.get('path_remap') or {}).items():
        if same_path(path, os.path.expanduser(src)):
            return os.path.expanduser(dst)
    return path


def el(id_, role, text, ts, kind='msg'):
    if id_ is None or str(id_).strip() == '' or str(id_).strip() == 'None':
        id_str = f'{role}:{ts}:{hash(text) & 0xffffffff:x}'
    else:
        id_str = str(id_)
    return {'id': id_str, 'role': role, 'text': text, 'ts': ts or 0, 'kind': kind}


def dedup(els):
    pos, out = {}, []
    for e in els:
        if e['id'] in pos:
            out[pos[e['id']]] = e
        else:
            pos[e['id']] = len(out)
            out.append(e)
    return out


def text_of(parts):
    """Text from the many 'content' shapes agents use: str, [{'text'}], [{'type':'text','text'}]."""
    if isinstance(parts, str):
        return parts
    out = []
    for p in parts or []:
        if isinstance(p, str):
            out.append(p)
        elif isinstance(p, dict) and not p.get('thought') and isinstance(p.get('text'), str):
            if p.get('type') in (None, 'text', 'input_text', 'output_text'):
                out.append(p['text'])
    return '\n'.join(out)


CALL_KEYS = ('command', 'CommandLine', 'cmd', 'file_path', 'filePath', 'AbsolutePath', 'TargetFile', 'path',
             'SearchPath', 'pattern', 'Query', 'query', 'Url', 'url', 'description', 'prompt')


def fmt_call(name, args, cfg):
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except ValueError:
            pass
    val = None
    if isinstance(args, dict):
        for k in CALL_KEYS:
            v = args.get(k)
            if isinstance(v, list) and v and all(isinstance(x, str) for x in v):
                v = ' '.join(v)
            if isinstance(v, str) and v.strip():
                val = v
                break
    if val is None:
        val = args if isinstance(args, str) else (json.dumps(args, ensure_ascii=False) if args else '')
    if len(val) > 1 and val[0] == val[-1] == '"':
        try:
            val = json.loads(val)
        except ValueError:
            pass
    return f'▸ {name}: {clip(str(val).strip(), cfg["tool_input_chars"])}'


def fmt_result(out, cfg):
    if not isinstance(out, str):
        out = text_of(out) if isinstance(out, list) else ('' if out is None else json.dumps(out, ensure_ascii=False))
    out = out.strip()
    return '  ⎿ ' + clip(out, cfg['tool_output_chars']) if out else '  ⎿ (no output)'


def run_quiet(args, cwd=None, timeout=180):
    env = dict(os.environ, HOP_SYNCING='1')
    shell = sys.platform == 'win32' and str(args[0]).lower().endswith(('.cmd', '.bat'))
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, encoding='utf-8',
                          errors='replace', timeout=timeout, creationflags=NO_WINDOW, shell=shell)
