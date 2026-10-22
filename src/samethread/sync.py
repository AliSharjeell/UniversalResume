"""Threads (tool-neutral conversations) and the sync engine that keeps every agent's copy current."""
import os
import re
import subprocess
import sys
import time
import uuid
from collections import Counter

from .agents import AGENTS, NAMES, targets
from .core import (HANDOFF_DIR, HOME, INDEX_PATH, LOCK_PATH, PENDING_PATH, THREAD_DIR, HopError, clip, dedup, log,
                   now_ms, read_json, write_json)

_names = '|'.join(re.escape(n) for n in NAMES.values())
TAG_RE = re.compile(rf'\s*\((?:{_names})(?:\+(?:{_names}))*\)\s*$')
HANDOFF_RE = re.compile(r'\[hop-handoff:([0-9a-f]+)\]')


def load(s, cfg):
    if 'els' not in s:
        s['els'] = dedup(AGENTS[s['tool']].read(s, cfg))
    return s['els']


def new_thread(origin, base_title, cwd):
    return {'tid': uuid.uuid4().hex[:12], 'origin': origin, 'base_title': base_title, 'cwd': cwd,
            'created': now_ms(), 'updated': 0, 'head': origin, 'elements': [], 'copies': {}, 'suppressed': []}


def authors(th):
    seen = []
    for e in th['elements']:
        if e.get('author') and e['author'] not in seen:
            seen.append(e['author'])
    return seen


def tag(th):
    return '+'.join(NAMES.get(a, a) for a in authors(th))


def thread_title(th):
    return f"{th['base_title']} ({tag(th)})"


def clean_title(title, els):
    title = TAG_RE.sub('', (title or '').strip())
    if not title or title.startswith('New session - '):
        first = next((e['text'] for e in els if e['role'] == 'user' and e['kind'] == 'msg'), 'Untitled')
        title = first.strip().splitlines()[0] if first.strip() else 'Untitled'
    title = ' '.join(title.split())
    return title if len(title) <= 80 else title[:78].rsplit(' ', 1)[0].rstrip(',.;:') + '…'


def render(th, cfg):
    els = th['elements']
    start = max((i for i, e in enumerate(els) if e['kind'] == 'summary'), default=0)
    msgs = []
    for e in els[start:]:
        if e['kind'] == 'summary':
            role, text = 'user', '[Summary of earlier conversation]\n' + e['text']
        else:
            role, text = ('user' if e['role'] == 'user' else 'assistant'), e['text']
        if msgs and msgs[-1]['role'] == role:
            msgs[-1]['text'] += '\n\n' + text
        else:
            msgs.append({'role': role, 'text': text, 'ts': e['ts']})
    dropped, total = 0, sum(len(m['text']) for m in msgs)
    while total > cfg['max_chars'] and len(msgs) > 2:
        total -= len(msgs.pop(0)['text'])
        dropped += 1
    for m in msgs:
        m['text'] = clip(m['text'], cfg['max_chars'])
    note = (f'[hop] Conversation carried over from {tag(th)} ("{th["base_title"]}"). '
            'Tool calls from other agents appear as text: "▸ tool: input" then "⎿ result".')
    if dropped:
        note += f' {dropped} earlier messages were omitted to fit the context window.'
    if msgs and msgs[0]['role'] == 'user':
        msgs[0]['text'] = note + '\n\n' + msgs[0]['text']
    else:
        msgs.insert(0, {'role': 'user', 'text': note, 'ts': msgs[0]['ts'] if msgs else now_ms()})
    for m in msgs:
        m['ts'] = m['ts'] or now_ms()
    return msgs


class Sync:
    def __init__(self, cfg, days=None, dry=False):
        self.cfg, self.dry = cfg, dry
        self.days = days or cfg['max_age_days']
        self.idx = read_json(INDEX_PATH, {})
        self.idx.setdefault('copies', {})
        self.idx.setdefault('skip', {})
        versions = self.idx.setdefault('versions', {})
        if self.idx.get('cc_version'):
            versions.setdefault('cc', self.idx.pop('cc_version'))
        self.ctx = {'cfg': cfg, **{f'{k}_version': v for k, v in versions.items()}}
        self.threads, self.dirty, self.touched = {}, set(), set()
        self.stats = Counter()

    def thread(self, tid):
        if tid not in self.threads:
            self.threads[tid] = read_json(os.path.join(THREAD_DIR, tid + '.json'), None)
        return self.threads[tid]

    def save(self, tid=None):
        if self.dry:
            return
        for t in ([tid] if tid else list(self.touched | self.dirty)):
            if self.threads.get(t):
                write_json(os.path.join(THREAD_DIR, t + '.json'), self.threads[t])
        write_json(INDEX_PATH, self.idx)
        try:
            os.utime(LOCK_PATH)
        except OSError:
            pass

    def load(self, s):
        els = load(s, self.cfg)
        if s.get('version'):
            self.idx['versions'][s['tool']] = s['version']
            self.ctx[f'{s["tool"]}_version'] = s['version']
        return els

    def run(self):
        self.sessions, self.listed = {}, set()
        for key, agent in AGENTS.items():
            try:
                self.sessions.update(agent.list(self.cfg))
                self.listed.add(key)
            except Exception as e:  # one broken store must not stop the others
                log(f'! could not list {agent.name} sessions: {e}')
        self.claim_handoffs()
        self.scan_copies()
        self.adopt_new()
        self.materialize()
        self.save()
        return self.stats

    def claim_handoffs(self):
        """Attach conversations started by `hop resume <read-only agent>` to the thread they continue."""
        path = os.path.join(HANDOFF_DIR, 'pending.json')
        pending = {t: ts for t, ts in read_json(path, {}).items() if now_ms() - ts < 86400000}
        if not pending:
            return
        for key, s in self.sessions.items():
            if not pending:
                break
            if AGENTS[s['tool']].writable or key in self.idx['copies'] or s['updated'] < min(pending.values()):
                continue
            els = self.load(s)
            first = next((e for e in els if e['role'] == 'user'), None)
            m = first and HANDOFF_RE.search(first['text'])
            th = m and self.thread(m.group(1))
            if not th:
                continue
            users = [i for i, e in enumerate(els) if e['role'] == 'user']
            cut = users[1] if len(users) > 1 else len(els)
            th['copies'][key] = {'owned': False, 'seen': [e['id'] for e in els[:cut]], 'sig': None,
                                 'upto': len(th['elements'])}
            self.idx['copies'][key] = th['tid']
            pending.pop(th['tid'], None)
            self.touched.add(th['tid'])
            log(f'= linked {AGENTS[s["tool"]].name} conversation to "{th["base_title"]}"')
        if not self.dry:
            write_json(path, pending)

    def scan_copies(self):
        grown = {}
        for key, tid in list(self.idx['copies'].items()):
            th = self.thread(tid)
            if not th or key not in th['copies']:
                self.idx['copies'].pop(key, None)
                continue
            cp, s = th['copies'][key], self.sessions.get(key)
            tool = key.split(':')[0]
            if s is None:
                if tool not in self.listed:
                    continue
                if cp.get('broken'):
                    del th['copies'][key]
                    self.idx['copies'].pop(key, None)
                    self.touched.add(tid)
                elif cp['owned']:
                    log(f'- {NAMES.get(tool, tool)} mirror was deleted, not recreating: "{th["base_title"]}"')
                    th['suppressed'].append(tool)
                    del th['copies'][key]
                    self.idx['copies'].pop(key, None)
                    self.touched.add(tid)
                continue
            if s['sig'] == cp.get('sig'):
                continue
            try:
                els = self.load(s)
            except Exception as e:
                log(f'! could not read {key}: {e}')
                continue
            known = set(cp['seen'])
            new = [e for e in els if e['id'] not in known]
            cp['sig'] = s['sig']
            self.touched.add(tid)
            if new:
                grown.setdefault(tid, []).append((key, new, s['updated']))

        for tid, items in grown.items():
            th = self.thread(tid)
            n = len(th['elements'])
            items.sort(key=lambda x: x[2])
            for key, new, upd in items:
                cp = th['copies'][key]
                tool = key.split(':')[0]
                if key != items[-1][0] or cp['upto'] < n:
                    self.fork(th, key, new, upd)
                    continue
                th['elements'] += [dict(e, author=tool) for e in new]
                cp['seen'] += [e['id'] for e in new]
                cp['upto'] = len(th['elements'])
                th['head'], th['updated'] = key, max(th['updated'], upd)
                self.dirty.add(tid)
                self.stats['continued'] += 1

    def fork(self, th, key, new, upd):
        cp = th['copies'].pop(key)
        tool = key.split(':')[0]
        nt = new_thread(key, th['base_title'] + ' [fork]', th['cwd'])
        nt['elements'] = [dict(e) for e in th['elements'][:cp['upto']]] + [dict(e, author=tool) for e in new]
        cp['seen'] += [e['id'] for e in new]
        cp['upto'] = len(nt['elements'])
        cp['owned'] = False
        nt['copies'][key], nt['updated'] = cp, upd
        self.threads[nt['tid']] = nt
        self.idx['copies'][key] = nt['tid']
        self.touched.add(th['tid'])
        self.dirty.add(nt['tid'])
        self.stats['forked'] += 1
        log(f'~ {NAMES.get(tool, tool)} copy diverged, split into its own chat: "{nt["base_title"]}"')

    def ineligible(self, s, els):
        if s.get('is_hop'):
            return 'hop mirror'
        if s.get('automation'):
            return 'automation run'
        if not els:
            return 'empty'
        return None

    def adopt_new(self):
        cutoff = now_ms() - self.days * 86400000
        for key, s in sorted(self.sessions.items(), key=lambda kv: kv[1]['updated']):
            if key in self.idx['copies'] or s['updated'] < cutoff:
                continue
            if self.idx['skip'].get(key) == s['sig']:
                continue
            try:
                els = self.load(s)
            except Exception as e:
                log(f'! could not read {key}: {e}')
                continue
            if self.ineligible(s, els):
                self.idx['skip'][key] = s['sig']
                continue
            self.idx['skip'].pop(key, None)
            th = new_thread(key, clean_title(s.get('title'), els), s.get('cwd') or HOME)
            th['elements'] = [dict(e, author=s['tool']) for e in els]
            th['copies'][key] = {'owned': False, 'seen': [e['id'] for e in els], 'sig': s['sig'], 'upto': len(els)}
            th['updated'] = s['updated']
            self.threads[th['tid']] = th
            self.idx['copies'][key] = th['tid']
            self.dirty.add(th['tid'])
            self.stats['new'] += 1

    def backfill(self, writable):
        """A newly installed agent gets every recent chat, not just the ones that change from now on."""
        known = set(self.idx.get('targets', ['cc', 'oc']))  # indexes from 0.1 predate this field
        if any(t not in known for t in writable):
            cutoff = now_ms() - self.days * 86400000
            for tid in set(self.idx['copies'].values()):
                th = self.thread(tid)
                if th and th['updated'] >= cutoff:
                    self.dirty.add(tid)
        if not self.dry:
            self.idx['targets'] = writable

    def materialize(self):
        for tid in self.idx.pop('retry', []):
            if self.thread(tid):
                self.dirty.add(tid)
        writable = targets(self.cfg)
        self.backfill(writable)
        for tid in sorted(self.dirty, key=lambda t: self.threads[t]['updated']):
            th = self.threads[tid]
            if th.get('forgotten') or {'cc', 'oc'} <= set(th['suppressed']):  # 0.1 marked forgotten chats this way
                continue
            n, title = len(th['elements']), thread_title(th)
            for tool in writable:
                agent = AGENTS[tool]
                if tool in th['suppressed']:
                    continue
                mine = {k: cp for k, cp in th['copies'].items() if k.startswith(tool + ':')}
                current = [(k, cp) for k, cp in mine.items() if cp['upto'] == n]
                if current:
                    for k, cp in current:
                        if cp['owned'] and cp.get('title') != title and not self.dry:
                            try:
                                if agent.retitle(cp, title):
                                    cp['title'] = title
                            except Exception as e:
                                log(f'! {agent.name} retitle failed for "{title}": {e}')
                    continue
                owned = next(((k, cp) for k, cp in mine.items() if cp['owned']), (None, None))
                verb = 'update' if owned[0] else 'create'
                if self.dry:
                    log(f'[dry-run] {verb} {agent.name}: {title}')
                    self.stats[verb] += 1
                    continue
                try:
                    res = agent.write(owned[1], th['cwd'], render(th, self.cfg), title, self.ctx)
                except Exception as e:
                    log(f'! {agent.name} {verb} failed for "{title}": {e}')
                    self.stats['failed'] += 1
                    if owned[1]:
                        owned[1]['broken'] = True  # an update may delete before rewriting; don't mistake it for user deletion
                    if not isinstance(e, HopError):
                        self.idx.setdefault('retry', []).append(tid)
                    continue
                key = f'{tool}:{res["id"]}'
                cp = th['copies'].setdefault(key, {'owned': True})
                cp.pop('broken', None)
                cp.update({k: v for k, v in res.items() if k != 'seen'}, seen=res['seen'], upto=n, title=title)
                self.idx['copies'][key] = tid
                self.stats[verb] += 1
                log(f'{"+" if verb == "create" else "~"} {agent.name}: {title}')
                self.save(tid)


def is_lock_stale(path):
    try:
        if time.time() - os.path.getmtime(path) > 600:
            return True
        with open(path, 'r') as f:
            content = f.read().strip()
        if content:
            pid = int(content)
            try:
                os.kill(pid, 0)
            except OSError:
                return True
        return False
    except (OSError, ValueError):
        return True


def locked_sync(cfg, days=None, dry=False):
    os.makedirs(os.path.dirname(LOCK_PATH), exist_ok=True)
    try:
        fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        if not is_lock_stale(LOCK_PATH):
            open(PENDING_PATH, 'w').close()
            log('sync already running; queued another pass')
            return None
        try:
            os.remove(LOCK_PATH)
        except OSError:
            pass
        return locked_sync(cfg, days, dry)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    total = Counter()
    try:
        while True:
            if os.path.exists(PENDING_PATH):
                os.remove(PENDING_PATH)
            total += Sync(cfg, days, dry).run()
            if dry or not os.path.exists(PENDING_PATH):
                break
    finally:
        try:
            os.remove(LOCK_PATH)
        except OSError:
            pass
    return total


def wait_lock(seconds=60):
    deadline = time.time() + seconds
    while True:
        try:
            fd = os.open(LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return True
        except FileExistsError:
            if is_lock_stale(LOCK_PATH):
                try:
                    os.remove(LOCK_PATH)
                    continue
                except OSError:
                    pass
            if time.time() > deadline:
                return False
            time.sleep(0.5)


def detach(argv):
    exe = sys.executable
    pyw = os.path.join(os.path.dirname(exe), 'pythonw.exe')
    if os.name == 'nt' and os.path.exists(pyw):
        exe = pyw
    flags = (0x00000008 | 0x00000200) if os.name == 'nt' else 0  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([exe, '-m', 'samethread'] + argv, cwd=HOME, creationflags=flags, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=os.name != 'nt')
