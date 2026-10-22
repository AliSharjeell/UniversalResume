"""MiniMax Code (mcode): the real session lives in ~/.minimax/v2/sessions/<dated folder>/,
and the SQLite runtime store indexes it.

The folder holds manifest.json, messages.jsonl, user-message-locators.jsonl and
history-catalog.json; the runtime store holds one session row plus one row per message.
A native copy writes both, so `mcode --session <id>` opens a conversation that carries
the whole thread.
"""
import base64
import datetime as dt
import hashlib
import json
import os
import sqlite3
import uuid

from ..core import HOME, el, fmt_call, fmt_result, lp, now_ms, write_json, write_text
from .base import Agent

USAGE = {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0, 'totalTokens': 0,
         'cost': {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0, 'total': 0}}


def data_dir():
    return os.environ.get('MINIMAX_DATA_DIR') or os.environ.get('MAVIS_DATA_DIR') or os.path.join(HOME, '.minimax')


def db_path():
    return os.path.join(data_dir(), 'v2', 'sqlite', 'runtime-state.sqlite')


def sessions_root():
    return os.path.join(data_dir(), 'v2', 'sessions')


def new_session_id():
    return 'mvs_' + uuid.uuid4().hex


def history_rel_dir(sid, ts):
    """The dated folder name the runtime uses: <YYYY/MM/DD>/<HH-MM-SS-mmm>-session_<base64 sid>."""
    t = dt.datetime.fromtimestamp(ts / 1000)
    tail = base64.b64encode(sid.encode('utf-8')).decode('ascii')
    stamp = f'{t:%H}-{t:%M}-{t:%S}-{ts % 1000:03d}'
    return f'{t:%Y}/{t:%m}/{t:%d}/{stamp}-session_{tail}'


def message_id(role):
    raw = uuid.uuid4().bytes
    if role == 'user':
        return 'msg-user-v1-' + base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=')
    return 'msg-' + base64.urlsafe_b64encode(raw[:16]).decode('ascii').rstrip('=')


class MiniMax(Agent):
    key, name, aliases, binary, writable, copyable = 'mmx', 'MiniMax', ('minimax', 'mcode', 'minimax-code'), 'mcode', False, True

    def detect(self):
        return os.path.exists(db_path()) or super().detect()

    def connect(self):
        return sqlite3.connect(f'file:{db_path()}?mode=ro', uri=True, timeout=15)

    def list(self, cfg):
        if not os.path.exists(db_path()):
            return {}
        c = self.connect()
        try:
            stats = {sid: (n, mx) for sid, n, mx in
                     c.execute('select session_id, count(*), max(id) from local_runtime_message_rows group by session_id')}
            out = {}
            for sid, cwd, title, upd in c.execute(
                    "select session_id, workspace_dir, title, updated_at_ms from local_runtime_sessions where "
                    "parent_session_id is null and archived = 0 and visibility = 'visible' "
                    "and session_kind = 'conversation'"):
                n, mx = stats.get(sid, (0, 0))
                out['mmx:' + sid] = self.session(sid, cwd=os.path.normpath(cwd or HOME), title=title,
                                                 sig=f'{upd}:{n}:{mx}', updated=upd or 0)
            return out
        finally:
            c.close()

    def read(self, s, cfg):
        c = self.connect()
        try:
            rows = c.execute('select msg_id, role, created_at_ms, data_json from local_runtime_message_rows '
                             'where session_id=? order by id', (s['id'],)).fetchall()
        finally:
            c.close()
        els = []
        for mid, role, ts, data in rows:
            try:
                d = json.loads(data)
            except ValueError:
                continue
            txt = d.get('msg_content')
            if isinstance(txt, list):
                txt = '\n'.join(p.get('text', '') for p in txt if isinstance(p, dict))
            txt = (txt or '').strip() if isinstance(txt, str) else ''
            if role == 'user' and txt:
                els.append(el(mid, 'user', txt, ts))
            elif role == 'assistant' and txt:
                els.append(el(mid, 'assistant', txt, ts))
            for i, tc in enumerate(d.get('tool_calls') or []):
                if isinstance(tc, dict):
                    els.append(el(f'{mid}#t{i}', 'tool', fmt_call(tc.get('name') or tc.get('tool_name'),
                                                                  tc.get('args') or tc.get('arguments'), cfg), ts))
            if role == 'tool' and (txt or d.get('output')):
                els.append(el(mid, 'tool', fmt_result(txt or d.get('output'), cfg), ts))
        return els

    def write(self, cp, cwd, msgs, title, ctx):
        """Native copy: the chat becomes a real MiniMax session the runtime opens itself."""
        if not os.path.exists(db_path()):
            raise RuntimeError(f'MiniMax runtime store not found at {db_path()}')
        sid = cp['id'] if cp else new_session_id()
        first = msgs[0]['ts'] if msgs else now_ms()
        last = max((m['ts'] for m in msgs), default=first)
        rel = history_rel_dir(sid, first)
        folder = os.path.join(sessions_root(), *rel.split('/'))
        os.makedirs(lp(folder), exist_ok=True)

        turn = str(uuid.uuid4())
        records, seen, locators = [], [], []
        offsets, pos = [], 0
        for m in msgs:
            mid = message_id(m['role'])
            if m['role'] == 'user':
                # The runtime requires a finite timestamp on every message, user ones included.
                message = {'role': 'user', 'content': [{'type': 'text', 'text': m['text']}], 'timestamp': m['ts']}
            else:
                message = {'role': 'assistant', 'content': [{'type': 'text', 'text': m['text']}],
                           'api': 'anthropic-messages', 'provider': 'minimax', 'model': 'MiniMax-M3.1-Flash',
                           'usage': USAGE, 'stopReason': 'stop', 'timestamp': m['ts'],
                           'responseId': uuid.uuid4().hex}
            records.append({'message_id': mid, 'turn_id': turn, 'message': message})
            offsets.append(pos)
            pos += len(json.dumps({'message_id': mid, 'turn_id': turn, 'message': message},
                                  ensure_ascii=False, separators=(',', ':')).encode('utf-8')) + 1
            seen.append(mid)

        body = ''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' for r in records)
        # The runtime hashes the records with sorted keys, not the file bytes.
        revision = 'sha256:' + hashlib.sha256(json.dumps(records, ensure_ascii=False, sort_keys=True,
                                                         separators=(',', ':')).encode('utf-8')).hexdigest()
        for i, m in enumerate(msgs):
            if m['role'] == 'user':
                locators.append({'schemaVersion': 1, 'messageId': records[i]['message_id'], 'generation': 0,
                                 'lineNumber': i + 1, 'byteOffset': offsets[i], 'artifactRevision': revision})

        write_text(os.path.join(folder, 'messages.jsonl'), body)
        write_text(os.path.join(folder, 'user-message-locators.jsonl'),
                   ''.join(json.dumps(l, ensure_ascii=False, separators=(',', ':')) + '\n' for l in locators))
        write_json(os.path.join(folder, 'history-catalog.json'), {
            'schemaVersion': 1, 'sessionId': sid, 'activeGeneration': 0, 'activeRevision': revision,
            'artifacts': [{'revision': revision, 'generation': 0, 'kind': 'active', 'fileName': 'messages.jsonl',
                           'byteLength': len(body.encode('utf-8')), 'messageCount': len(records)}]})
        write_json(os.path.join(folder, 'manifest.json'), {
            'schemaVersion': 1, 'sessionId': sid, 'createdAtMs': first, 'updatedAtMs': last,
            'source': 'local-runtime', 'layout': 'v2-final-dated-session',
            'paths': {'sessionDir': folder,
                      'ledger': os.path.join(folder, 'ledger.jsonl'),
                      'display': os.path.join(folder, 'display.jsonl'),
                      'snapshot': os.path.join(folder, 'snapshot.json'),
                      'reports': os.path.join(folder, 'reports'),
                      'messages': os.path.join(folder, 'messages.jsonl')}})
        self.copy_llm_call(folder)

        self.index(sid, cwd, title, first, last, rel, records, seen, revision)
        return {'id': sid, 'path': folder, 'seen': seen, 'sig': self.sig_of(sid)}

    def copy_llm_call(self, folder):
        """Carry over the runtime's own model settings so the session resumes the same way."""
        root = sessions_root()
        for base, dirs, files in os.walk(root):
            if 'llm-call.json' in files:
                try:
                    with open(os.path.join(base, 'llm-call.json'), encoding='utf-8') as f:
                        raw = f.read()
                except OSError:
                    continue
                write_text(os.path.join(folder, 'llm-call.json'), raw)
                return True
        return False

    def index(self, sid, cwd, title, first, last, rel, records, seen, revision):
        """Add the session and its messages to the runtime store."""
        c = sqlite3.connect(db_path(), timeout=30)
        c.row_factory = sqlite3.Row
        try:
            c.execute('pragma busy_timeout=30000')
            tpl = c.execute("select * from local_runtime_sessions where session_kind='conversation' "
                            "order by updated_at_ms desc limit 1").fetchone()
            extra = tpl['extra_data_json'] if tpl and tpl['extra_data_json'] else '{}'
            agent_name = (tpl['agent_name'] if tpl else None) or 'mavis'
            runtime = (tpl['runtime'] if tpl else None) or 'pi-agent'
            project_id = tpl['project_id'] if tpl else None
            record = {'sessionId': sid, 'agentName': agent_name, 'workspaceDir': cwd, 'runtime': runtime,
                      'sessionType': 'branch', 'archived': False, 'visibility': 'visible', 'status': 'idle',
                      'createdAtMs': first, 'updatedAtMs': last}
            c.execute(
                'insert or replace into local_runtime_sessions (session_id, record_json, updated_at_ms, '
                'columnar_version, agent_name, runtime, session_type, status, archived, visibility, session_kind, '
                'purpose, purpose_kind, workspace_dir, project_workspace_dir, is_default_workspace, title, '
                'created_at_ms, error_message, error_code, extra_data_json, project_id, history_relative_dir) '
                'values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (sid, json.dumps(record, ensure_ascii=False), last, 3, agent_name, runtime, 'branch', 'idle', 0,
                 'visible', 'conversation', None, '', cwd, cwd, 0, title, first, None, None, extra, project_id, rel))
            for i, r in enumerate(records):
                mid = r['message_id']
                msg = r['message']
                ts = msg.get('timestamp') or first
                data = {'msg_id': mid, 'role': msg['role'], 'msg_content': msg['content'][0]['text']}
                if msg['role'] != 'user':
                    data['turn_id'] = r['turn_id']
                    data['timestamp'] = ts
                    data['msg_type'] = 2
                c.execute('insert or replace into local_runtime_message_rows '
                          '(session_id, msg_id, role, turn_id, created_at_ms, data_json, source, source_context_json) '
                          'values (?,?,?,?,?,?,?,?)',
                          (sid, mid, msg['role'], r['turn_id'], ts,
                           json.dumps(data, ensure_ascii=False), 'api', None))
            # The runtime re-derives a session's history from these rows and compares it with
            # messages.jsonl. The migration checkpoint marks the file as the history of record.
            c.execute('insert or replace into local_runtime_pi_history_file_migrations '
                      '(session_id, migrated_at_ms, source, message_count, target_revision) values (?,?,?,?,?)',
                      (sid, last, 'sqlite-rows', len(records), revision))
            c.commit()
        finally:
            c.close()

    def sig_of(self, sid):
        c = self.connect()
        try:
            upd = c.execute('select updated_at_ms from local_runtime_sessions where session_id=?', (sid,)).fetchone()
            n, mx = c.execute('select count(*), max(id) from local_runtime_message_rows where session_id=?',
                              (sid,)).fetchone()
            return f'{upd[0] if upd else 0}:{n}:{mx}'
        finally:
            c.close()

    def delete(self, cp):
        sid = cp.get('id')
        if not sid:
            return
        try:
            c = sqlite3.connect(db_path(), timeout=30)
            try:
                c.execute('pragma busy_timeout=30000')
                c.execute('delete from local_runtime_message_rows where session_id=?', (sid,))
                c.execute('delete from local_runtime_sessions where session_id=?', (sid,))
                c.execute('delete from local_runtime_pi_history_file_migrations where session_id=?', (sid,))
                c.commit()
            finally:
                c.close()
        except Exception:
            pass
        path = cp.get('path')
        if path and os.path.isdir(lp(path)):
            try:
                import shutil
                shutil.rmtree(lp(path), ignore_errors=True)
            except Exception:
                pass

    def resume_cmd(self, sid):
        return ['mcode', '--session', sid]

    def seed_cmd(self, prompt):
        return ['mcode', prompt]

    def install(self, dry):
        # MiniMax Code does not load local hook plugins from the CLI yet, so there is no hook to add.
        # Its chats are picked up automatically whenever Universal Resume starts or syncs.
        return 'no hook support yet; synced automatically on resume'
