"""Antigravity CLI (agy): conversations live in ~/.gemini/antigravity-cli.

A conversation is a brain folder with the transcript log, a trajectory database under
conversations/, and a row in conversation_summaries. hop writes all three, so agy resumes
the copy itself instead of being seeded with a handoff prompt.
"""
import datetime as dt
import json
import os
import re
import shutil
import sqlite3
import urllib.parse
import uuid

from .. import hookkit
from ..core import HOME, el, file_sig, fmt_call, fmt_result, iso_ms, lp, read_jsonl, remap, write_text
from ..proto import decode, drop_field, encode, set_field, sub
from .base import Agent

ROOT = os.path.join(HOME, '.gemini', 'antigravity-cli')
HOOKS = os.path.join(HOME, '.gemini', 'config', 'hooks.json')
HDR_RE = re.compile(r'^(Created At|Completed At):.*\n?', re.M)

USER_STEP = 14        # step_type of a user message
PLANNER_STEP = 15     # step_type of an agent message
STEP_STATUS_DONE = 3

TRAJECTORY_SCHEMA = [
    'CREATE TABLE `trajectory_meta` (`trajectory_id` text,`cascade_id` text,`trajectory_type` integer,'
    '`source` integer,PRIMARY KEY (`trajectory_id`))',
    'CREATE TABLE `steps` (`idx` integer,`step_type` integer NOT NULL DEFAULT 0,`status` integer NOT NULL DEFAULT 0,'
    '`has_subtrajectory` numeric NOT NULL DEFAULT false,`metadata` blob,`error_details` blob,`permissions` blob,'
    '`task_details` blob,`render_info` blob,`step_payload` blob,`step_format` integer NOT NULL DEFAULT 0,'
    'PRIMARY KEY (`idx`))',
    'CREATE TABLE `gen_metadata` (`idx` integer,`data` blob,`size` integer NOT NULL DEFAULT 0,PRIMARY KEY (`idx`))',
    'CREATE TABLE `executor_metadata` (`idx` integer,`data` blob,PRIMARY KEY (`idx`))',
    'CREATE TABLE `parent_references` (`idx` integer,`data` blob,PRIMARY KEY (`idx`))',
    'CREATE TABLE `trajectory_metadata_blob` (`id` text DEFAULT "main",`data` blob,PRIMARY KEY (`id`))',
    'CREATE TABLE `battle_mode_infos` (`idx` integer,`data` blob,PRIMARY KEY (`idx`))',
]


def transcript(cid):
    base = os.path.join(ROOT, 'brain', cid, '.system_generated', 'logs')
    for name in ('transcript_full.jsonl', 'transcript.jsonl'):
        p = os.path.join(base, name)
        if os.path.exists(p):
            return p
    return None


def uri_to_path(u):
    p = urllib.parse.unquote(urllib.parse.urlparse(u).path)
    if re.match(r'^/[A-Za-z]:', p):
        p = p[1:]
    return os.path.normpath(p)


def workspace_uri(cwd):
    """How agy records a workspace: file:///<path>."""
    norm = (cwd or '').replace('\\', '/').rstrip('/')
    return 'file:///' + norm


def stamp(ms):
    t = dt.datetime.fromtimestamp((ms or 0) / 1000, dt.timezone.utc)
    return t.strftime('%Y-%m-%dT%H:%M:%SZ')


def db_stamp(ms):
    t = dt.datetime.fromtimestamp((ms or 0) / 1000, dt.timezone.utc)
    return t.strftime('%Y-%m-%d %H:%M:%S.%f000+00:00')


class Antigravity(Agent):
    key, name, aliases, binary, writable, copyable = 'agy', 'Agy', ('antigravity',), 'agy', False, True

    def detect(self):
        return os.path.isdir(ROOT) or super().detect()

    def list(self, cfg):
        db = os.path.join(ROOT, 'conversation_summaries.db')
        if not os.path.exists(db):
            return {}
        c = sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=15)
        try:
            rows = c.execute('select conversation_id, title, last_modified_time, workspace_uris, '
                             'parent_conversation_id, nesting_depth from conversation_summaries').fetchall()
        finally:
            c.close()
        out = {}
        for cid, title, modified, ws, parent, depth in rows:
            path = transcript(cid)
            if parent or depth or not path:
                continue
            try:
                uris = json.loads(ws or '[]')
            except ValueError:
                uris = [ws] if ws and ws.startswith('file://') else []
            file_mtime = int(os.path.getmtime(path) * 1000) if os.path.exists(path) else 0
            db_mtime = iso_ms(modified) if modified else 0
            updated_ts = max(db_mtime, file_mtime)
            out['agy:' + cid] = self.session(cid, path=path, title=title or None, sig=file_sig(path),
                                             cwd=remap(cfg, uri_to_path(uris[0]) if uris else HOME),
                                             updated=updated_ts)
        return out

    def read(self, s, cfg):
        els = []
        for d in read_jsonl(s['path']):
            st, idx, ts = d.get('type'), d.get('step_index'), iso_ms(d.get('created_at'))
            content = d.get('content') or ''
            if st == 'USER_INPUT':
                m = re.search(r'<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>', content, re.S)
                txt = m.group(1) if m else re.sub(r'<ADDITIONAL_METADATA>.*?</ADDITIONAL_METADATA>', '', content, flags=re.S)
                if d.get('media'):
                    txt += '\n[image]'
                if txt.strip():
                    els.append(el(idx, 'user', txt.strip(), ts))
            elif st == 'PLANNER_RESPONSE':
                if content.strip():
                    els.append(el(f'{idx}#0', 'assistant', content.strip(), ts))
                for i, tc in enumerate(d.get('tool_calls') or []):
                    els.append(el(f'{idx}#t{i}', 'tool', fmt_call(tc.get('name'), tc.get('args'), cfg), ts))
            elif st == 'CHECKPOINT':
                txt = re.sub(r'^\{\{ CHECKPOINT \d+ \}\}\s*', '', content).strip()
                if txt:
                    els.append(el(idx, 'user', txt, ts, 'summary'))
            elif d.get('source') == 'MODEL':
                els.append(el(idx, 'tool', fmt_result(HDR_RE.sub('', content).strip() or d.get('error'), cfg), ts))
        return els

    def write(self, cp, cwd, msgs, title, ctx):
        """Native copy: the chat becomes an Antigravity conversation agy resumes itself."""
        cid = cp['id'] if cp else str(uuid.uuid4())
        logs = os.path.join(ROOT, 'brain', cid, '.system_generated', 'logs')
        os.makedirs(lp(logs), exist_ok=True)
        steps, seen = [], []
        for m in msgs:
            idx = len(steps)
            if m['role'] == 'user':
                steps.append({'step_index': idx, 'source': 'USER_EXPLICIT', 'type': 'USER_INPUT',
                              'status': 'DONE', 'created_at': stamp(m['ts']),
                              'content': f'<USER_REQUEST>\n{m["text"]}\n</USER_REQUEST>'})
                seen.append(str(idx))
            else:
                steps.append({'step_index': idx, 'source': 'MODEL', 'type': 'PLANNER_RESPONSE',
                              'status': 'DONE', 'created_at': stamp(m['ts']), 'content': m['text']})
                seen.append(f'{idx}#0')
        body = ''.join(json.dumps(s, ensure_ascii=False) + '\n' for s in steps)
        for name in ('transcript_full.jsonl', 'transcript.jsonl'):
            write_text(os.path.join(logs, name), body)

        traj_id, meta_fields = self.write_trajectory(cid, msgs, cwd)
        self.write_summary(cid, cwd, steps, msgs, title, traj_id, meta_fields)
        path = transcript(cid)
        return {'id': cid, 'path': path, 'seen': seen, 'sig': file_sig(path)}

    def write_trajectory(self, cid, msgs, cwd):
        """The conversation database agy opens the trajectory from.

        The trajectory is what the agent's context is built from, so the chat has to be in
        there, not just in the transcript log. The step payloads are protobuf, so hop takes
        a real step of each kind from an existing conversation as the shape to copy and
        rewrites the message, the ids and the time.
        """
        path = os.path.join(ROOT, 'conversations', cid + '.db')
        os.makedirs(lp(os.path.dirname(path)), exist_ok=True)
        c = sqlite3.connect(path, timeout=20)
        try:
            for sql in TRAJECTORY_SCHEMA:
                c.execute(sql.replace('CREATE TABLE', 'CREATE TABLE IF NOT EXISTS'))
            c.execute('delete from steps')
            c.execute('delete from trajectory_meta')
            c.execute('delete from trajectory_metadata_blob')

            trajectory_id = str(uuid.uuid4())
            c.execute('insert into trajectory_meta (trajectory_id, cascade_id, trajectory_type, source) '
                      'values (?,?,?,?)', (trajectory_id, cid, 4, 17))

            ws_uri = workspace_uri(cwd)
            meta_fields = [
                [1, 2, encode([[1, 2, ws_uri.encode('utf-8')]])],
                [3, 2, str(uuid.uuid4()).encode('utf-8')],
                [6, 2, cid.encode('utf-8')],
                [7, 2, ws_uri.encode('utf-8')],
                [18, 2, b'default-cli-project'],
            ]
            c.execute('insert into trajectory_metadata_blob (id, data) values (?,?)',
                      ('main', encode(meta_fields)))

            user_tpl, planner_tpl = self.step_templates()
            if user_tpl and planner_tpl:
                for idx, m in enumerate(msgs):
                    is_user = m['role'] == 'user'
                    tpl = user_tpl if is_user else planner_tpl
                    res = self.rewrite_step(tpl, m['text'], m['ts'], cid, trajectory_id, cwd, is_user)
                    if res is None:
                        break
                    payload, meta_bytes = res
                    c.execute('insert into steps (idx, step_type, status, metadata, step_payload) values (?,?,?,?,?)',
                              (idx, USER_STEP if is_user else PLANNER_STEP, STEP_STATUS_DONE, meta_bytes, payload))
            c.commit()
            return trajectory_id, meta_fields
        finally:
            c.close()

    def step_templates(self):
        """A real user step and a real agent step to copy the shape of."""
        convs = os.path.join(ROOT, 'conversations')
        if not os.path.isdir(convs):
            return None, None
        user_tpl = planner_tpl = None
        for name in sorted(os.listdir(convs)):
            if not name.endswith('.db'):
                continue
            try:
                c = sqlite3.connect(f'file:{os.path.join(convs, name)}?mode=ro', uri=True, timeout=5)
                rows = c.execute('select step_type, step_payload from steps').fetchall()
                c.close()
            except Exception:
                continue
            for stype, payload in rows:
                if not payload:
                    continue
                if stype == USER_STEP and user_tpl is None:
                    user_tpl = bytes(payload)
                elif stype == PLANNER_STEP and planner_tpl is None:
                    planner_tpl = bytes(payload)
            if user_tpl and planner_tpl:
                break
        return user_tpl, planner_tpl

    def rewrite_step(self, template, text, ts, cid, trajectory_id, cwd, is_user):
        """Copy a real step and put this message, these ids and this time into it."""
        try:
            fields = decode(template)
            body_field = 19 if is_user else 20
            body = sub(fields, body_field)
            if not body:
                return None
            if is_user:
                set_field(body, 2, text.encode('utf-8'))
                set_field(body, 3, ('\nJ' + text).encode('utf-8'))
            else:
                set_field(body, 1, text.encode('utf-8'))
                set_field(body, 8, text.encode('utf-8'))
                body = drop_field(body, 7)  # a plain reply carries no tool calls
            place = sub(body, 12)
            if place:
                set_field(place, 12, workspace_uri(cwd).encode('utf-8'))
                set_field(body, 12, encode(place))
            set_field(fields, body_field, encode(body))

            meta = sub(fields, 5)
            meta_bytes = b''
            if meta:
                ident = sub(meta, 20)
                if ident:
                    set_field(ident, 1, trajectory_id.encode('utf-8'))
                    set_field(ident, 4, cid.encode('utf-8'))
                    set_field(meta, 20, encode(ident))
                when = sub(meta, 1)
                if when:
                    set_field(when, 1, int(ts // 1000), wire=0)
                    set_field(when, 2, int((ts % 1000) * 1_000_000), wire=0)
                    set_field(meta, 1, encode(when))
                meta_bytes = encode(meta)
                set_field(fields, 5, meta_bytes)
            return encode(fields), meta_bytes
        except Exception:
            return None

    def write_summary(self, cid, cwd, steps, msgs, title=None, trajectory_id=None, meta_fields=None):
        """The summary row that puts the conversation in agy's own list."""
        db = os.path.join(ROOT, 'conversation_summaries.db')
        if not os.path.exists(db):
            raise RuntimeError(f'Antigravity conversation store not found at {db}')
        last = max((m['ts'] for m in msgs), default=0)
        preview = next((m['text'] for m in msgs if m['role'] == 'user'), '')
        user_step = max((s['step_index'] for s in steps if s['type'] == 'USER_INPUT'), default=-1)
        ws_uri = workspace_uri(cwd)
        summary_title = title or preview.strip()[:120]

        raw_summary = None
        if trajectory_id and meta_fields:
            try:
                summary_fields = [
                    [1, 2, summary_title.encode('utf-8')],
                    [4, 2, trajectory_id.encode('utf-8')],
                    [9, 2, encode([[1, 2, ws_uri.encode('utf-8')]])],
                    [15, 2, summary_title.encode('utf-8')],
                    [17, 2, encode(meta_fields)],
                ]
                raw_summary = encode(summary_fields)
            except Exception:
                raw_summary = None

        c = sqlite3.connect(db, timeout=20)
        try:
            c.execute('pragma busy_timeout=20000')
            c.execute('insert or replace into conversation_summaries (conversation_id, title, preview, step_count, '
                      'last_modified_time, workspace_uris, status, source, project_id, agent_name, '
                      'parent_conversation_id, nesting_depth, last_user_input_time, last_user_input_step_index, '
                      'app_data_dir, raw_summary) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                      (cid, summary_title, preview.strip()[:120], len(steps), db_stamp(last),
                       json.dumps([ws_uri]), 'CASCADE_RUN_STATUS_IDLE', '', 'default-cli-project', '',
                       '', 0, db_stamp(last), user_step, 'antigravity-cli', raw_summary))
            c.commit()
        finally:
            c.close()

    def delete(self, cp):
        cid = cp.get('id')
        if not cid:
            return
        db = os.path.join(ROOT, 'conversation_summaries.db')
        if os.path.exists(db):
            try:
                c = sqlite3.connect(db, timeout=20)
                try:
                    c.execute('pragma busy_timeout=20000')
                    c.execute('delete from conversation_summaries where conversation_id=?', (cid,))
                    c.commit()
                finally:
                    c.close()
            except Exception:
                pass
        shutil.rmtree(lp(os.path.join(ROOT, 'brain', cid)), ignore_errors=True)
        conv = os.path.join(ROOT, 'conversations', cid + '.db')
        if os.path.exists(lp(conv)):
            os.remove(lp(conv))

    def resume_cmd(self, sid):
        return ['agy', '--conversation', sid]

    def seed_cmd(self, prompt):
        return ['agy', '-i', prompt]

    def install(self, dry):
        hooks = hookkit.load(HOOKS)
        # agy runs hooks through `cmd /c`, which mangles quotes, so the command stays unquoted.
        entry = {'Stop': [{'type': 'command', 'command': hookkit.command('\\', ' --json'), 'timeout': 15}]}
        if hooks.get('samethread') == entry:
            return 'hook already installed'
        hooks['samethread'] = entry
        hookkit.save(HOOKS, hooks, dry)
        return f'Stop hook added ({HOOKS})'

    def uninstall(self, dry):
        hooks = hookkit.load(HOOKS)
        if hooks.pop('samethread', None) is None:
            return 'nothing to remove'
        hookkit.save(HOOKS, hooks, dry)
        return 'Stop hook removed'
