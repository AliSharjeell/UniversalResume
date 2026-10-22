"""Native copies: hop writes the chat into an agent's own store, and the agent reads it back."""
import argparse
import json
import os
import shutil
import tempfile
import unittest

TMP = tempfile.mkdtemp(prefix='hop-native-')
os.environ.update(HOP_HOME=os.path.join(TMP, 'hop'), HOME=TMP, USERPROFILE=TMP)

from samethread import core  # noqa: E402
from samethread.agents import AGENTS  # noqa: E402
from samethread.agents import cursor, deepseek, grok, hermes, openclaw, openhands  # noqa: E402

CFG = dict(core.DEFAULT_CONFIG)
MSGS = [{'role': 'user', 'text': 'why is CI red?', 'ts': 1790000000000},
        {'role': 'assistant', 'text': 'looking into it', 'ts': 1790000001000}]


class FileStoreNativeCopy(unittest.TestCase):
    """Agents whose store is a plain session file: the copy must round-trip through their own reader."""

    CASES = [
        ('cursor', cursor, 'CURSOR_HOME'),
        ('deepseek', deepseek, 'DEEPSEEK_HOME'),
        ('hermes', hermes, 'HERMES_HOME'),
        ('openclaw', openclaw, 'OPENCLAW_HOME'),
        ('openhands', openhands, 'OPENHANDS_HOME'),
    ]

    def test_copy_round_trips_through_the_agents_own_reader(self):
        for key, mod, env in self.CASES:
            with self.subTest(agent=key):
                root = tempfile.mkdtemp(prefix=f'hop-{key}-')
                os.environ[env] = root
                agent = AGENTS[key]

                res = agent.write(None, os.getcwd(), MSGS, 'CI is red', {'cfg': CFG})
                self.assertTrue(res['id'])
                self.assertEqual(len(res['seen']), len(MSGS))

                sessions = agent.list(CFG)
                self.assertIn(f'{key}:{res["id"]}', sessions, 'the agent must list the copy')

                els = agent.read(sessions[f'{key}:{res["id"]}'], CFG)
                texts = [e['text'] for e in els]
                self.assertIn('why is CI red?', texts)
                self.assertIn('looking into it', texts)
                self.assertEqual(sorted(e['id'] for e in els), sorted(res['seen']))

    def test_copy_is_owned_so_hop_can_delete_it_again(self):
        for key, mod, env in self.CASES:
            with self.subTest(agent=key):
                root = tempfile.mkdtemp(prefix=f'hop-{key}-')
                os.environ[env] = root
                agent = AGENTS[key]
                res = agent.write(None, os.getcwd(), MSGS, 'CI is red', {'cfg': CFG})
                path = res['path']
                self.assertTrue(os.path.exists(path))
                agent.delete({'id': res['id'], 'path': path})
                self.assertFalse(os.path.exists(path))

    def test_every_agent_that_advertises_a_copy_can_actually_write_one(self):
        from samethread.agents.base import Agent
        for key, agent in AGENTS.items():
            if not agent.can_copy:
                continue
            with self.subTest(agent=key):
                self.assertNotEqual(type(agent).write, Agent.write,
                                    f'{key} claims it can copy but has no writer')


class GrokNativeCopy(unittest.TestCase):
    """Grok groups sessions per workspace, so the copy has to land in that layout."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='hop-grok-')
        os.environ['GROK_HOME'] = self.root

    def test_copy_lands_in_the_per_workspace_session_folder(self):
        agent = AGENTS['grok']
        cwd = r'C:\AppsNew\llm-maker'
        res = agent.write(None, cwd, MSGS, 'CI is red', {'cfg': CFG})

        expected = os.path.join(self.root, 'sessions', 'C%3A%5CAppsNew%5Cllm-maker', res['id'], 'chat_history.jsonl')
        self.assertEqual(res['path'], expected)
        self.assertTrue(os.path.exists(expected))

        sessions = agent.list(CFG)
        self.assertIn(f'grok:{res["id"]}', sessions)
        self.assertEqual(sessions[f'grok:{res["id"]}']['cwd'], cwd)

    def test_grok_records_are_read_back_with_the_right_roles(self):
        agent = AGENTS['grok']
        res = agent.write(None, os.getcwd(), MSGS, 'CI is red', {'cfg': CFG})
        sessions = agent.list(CFG)
        els = agent.read(sessions[f'grok:{res["id"]}'], CFG)
        self.assertEqual([e['role'] for e in els], ['user', 'assistant'])
        self.assertEqual([e['text'] for e in els], ['why is CI red?', 'looking into it'])
        self.assertEqual(sorted(e['id'] for e in els), sorted(res['seen']))


class AiderNativeCopy(unittest.TestCase):
    """Aider restores from a markdown chat history, so the copy is written in that shape."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='hop-aider-')
        os.environ['AIDER_HOME'] = self.root
        self.project = tempfile.mkdtemp(prefix='hop-project-')

    def test_copy_is_aider_chat_history_and_reads_back_cleanly(self):
        agent = AGENTS['aider']
        res = agent.write(None, self.project, MSGS, 'CI is red', {'cfg': CFG})

        self.assertTrue(res['path'].endswith('.md'))
        with open(res['path'], encoding='utf-8') as f:
            body = f.read()
        self.assertIn('#### User', body)
        self.assertIn('#### Assistant', body)

        sessions = agent.list(CFG)
        self.assertIn(f'aider:{res["id"]}', sessions)
        els = agent.read(sessions[f'aider:{res["id"]}'], CFG)
        self.assertEqual([e['role'] for e in els], ['user', 'assistant'])
        self.assertEqual([e['text'] for e in els], ['why is CI red?', 'looking into it'])

    def test_project_folder_gets_the_history_aider_restores(self):
        agent = AGENTS['aider']
        agent.write(None, self.project, MSGS, 'CI is red', {'cfg': CFG})
        self.assertTrue(os.path.exists(os.path.join(self.project, '.aider.chat.history.md')))


class MiniMaxNativeCopy(unittest.TestCase):
    """MiniMax keeps the real session on disk and indexes it in the runtime store."""

    SESSIONS_SQL = """
    CREATE TABLE local_runtime_sessions (
      session_id TEXT PRIMARY KEY, record_json TEXT NOT NULL, updated_at_ms INTEGER NOT NULL,
      columnar_version INTEGER NOT NULL DEFAULT 0, agent_name TEXT, runtime TEXT, session_type TEXT,
      status TEXT, archived INTEGER NOT NULL DEFAULT 0, visibility TEXT NOT NULL DEFAULT 'visible',
      session_kind TEXT NOT NULL DEFAULT 'unknown', purpose TEXT, purpose_kind TEXT NOT NULL DEFAULT '',
      origin_cron_id TEXT, parent_session_id TEXT, workspace_dir TEXT, project_workspace_dir TEXT,
      is_default_workspace INTEGER NOT NULL DEFAULT 0, title TEXT, created_at_ms INTEGER,
      error_message TEXT, error_code INTEGER, extra_data_json TEXT NOT NULL DEFAULT '{}',
      project_id INTEGER, history_relative_dir TEXT)
    """
    MESSAGES_SQL = """
    CREATE TABLE local_runtime_message_rows (
      id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, msg_id TEXT NOT NULL, role TEXT,
      turn_id TEXT, created_at_ms INTEGER NOT NULL, data_json TEXT NOT NULL, source TEXT,
      source_context_json TEXT, UNIQUE(session_id, msg_id))
    """
    CHECKPOINT_SQL = """
    CREATE TABLE local_runtime_pi_history_file_migrations (
      session_id TEXT PRIMARY KEY, migrated_at_ms INTEGER NOT NULL, source TEXT NOT NULL,
      message_count INTEGER NOT NULL, target_revision TEXT NOT NULL)
    """

    def setUp(self):
        import sqlite3
        self.root = tempfile.mkdtemp(prefix='hop-mmx-')
        os.makedirs(os.path.join(self.root, 'v2', 'sqlite'), exist_ok=True)
        db = os.path.join(self.root, 'v2', 'sqlite', 'runtime-state.sqlite')
        c = sqlite3.connect(db)
        c.execute(self.SESSIONS_SQL)
        c.execute(self.MESSAGES_SQL)
        c.execute(self.CHECKPOINT_SQL)
        c.commit()
        c.close()
        os.environ['MINIMAX_DATA_DIR'] = self.root
        os.environ.pop('MAVIS_DATA_DIR', None)

    def test_copy_writes_a_session_folder_and_indexes_it(self):
        agent = AGENTS['mmx']
        res = agent.write(None, r'C:\AppsNew\project', MSGS, 'CI is red', {'cfg': CFG})

        folder = res['path']
        self.assertTrue(os.path.isdir(folder))
        for name in ('manifest.json', 'messages.jsonl', 'user-message-locators.jsonl', 'history-catalog.json'):
            self.assertTrue(os.path.exists(os.path.join(folder, name)), f'{name} is missing')

        sessions = agent.list(CFG)
        self.assertIn(f'mmx:{res["id"]}', sessions, 'the runtime must list the copy')
        self.assertEqual(sessions[f'mmx:{res["id"]}']['cwd'], r'C:\AppsNew\project')

    def test_copy_reads_back_through_the_runtime_store(self):
        agent = AGENTS['mmx']
        res = agent.write(None, r'C:\AppsNew\project', MSGS, 'CI is red', {'cfg': CFG})
        sessions = agent.list(CFG)
        els = agent.read(sessions[f'mmx:{res["id"]}'], CFG)
        self.assertEqual([e['role'] for e in els], ['user', 'assistant'])
        self.assertEqual([e['text'] for e in els], ['why is CI red?', 'looking into it'])
        self.assertEqual(sorted(e['id'] for e in els), sorted(res['seen']))

    def test_history_catalog_matches_the_messages_file(self):
        import hashlib
        agent = AGENTS['mmx']
        res = agent.write(None, r'C:\AppsNew\project', MSGS, 'CI is red', {'cfg': CFG})
        body = open(os.path.join(res['path'], 'messages.jsonl'), encoding='utf-8').read()
        catalog = json.load(open(os.path.join(res['path'], 'history-catalog.json'), encoding='utf-8'))
        records = [json.loads(l) for l in body.split('\n') if l.strip()]
        revision = 'sha256:' + hashlib.sha256(json.dumps(records, ensure_ascii=False, sort_keys=True,
                                                         separators=(',', ':')).encode('utf-8')).hexdigest()
        self.assertEqual(catalog['activeRevision'], revision)
        self.assertEqual(catalog['artifacts'][0]['byteLength'], len(body.encode('utf-8')))
        self.assertEqual(catalog['artifacts'][0]['messageCount'], len(records))

    def test_copy_records_the_history_migration_checkpoint(self):
        """Without the checkpoint the runtime re-derives the history and rejects the copy."""
        import sqlite3
        agent = AGENTS['mmx']
        res = agent.write(None, r'C:\AppsNew\project', MSGS, 'CI is red', {'cfg': CFG})
        c = sqlite3.connect(os.path.join(self.root, 'v2', 'sqlite', 'runtime-state.sqlite'))
        row = c.execute('select session_id, source, message_count, target_revision '
                        'from local_runtime_pi_history_file_migrations where session_id=?',
                        (res['id'],)).fetchone()
        c.close()
        self.assertIsNotNone(row, 'the runtime needs a migration checkpoint for a hand-written session')
        self.assertEqual(row[1], 'sqlite-rows')
        self.assertEqual(row[2], len(MSGS))
        self.assertTrue(row[3].startswith('sha256:'))

    def test_every_message_carries_a_timestamp(self):
        agent = AGENTS['mmx']
        res = agent.write(None, r'C:\AppsNew\project', MSGS, 'CI is red', {'cfg': CFG})
        with open(os.path.join(res['path'], 'messages.jsonl'), encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                msg = json.loads(line)['message']
                self.assertIsInstance(msg.get('timestamp'), (int, float), 'the runtime rejects a missing timestamp')


class AntigravityNativeCopy(unittest.TestCase):
    """Antigravity copies must write summaries, trajectory dbs, and support in-place updates."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='hop-agy-')
        from samethread.agents import antigravity
        self.saved_root = antigravity.ROOT
        antigravity.ROOT = self.tmp
        os.makedirs(os.path.join(self.tmp, 'conversations'), exist_ok=True)
        import sqlite3
        db = os.path.join(self.tmp, 'conversation_summaries.db')
        c = sqlite3.connect(db)
        c.execute('CREATE TABLE `conversation_summaries` (`conversation_id` text,`title` text NOT NULL DEFAULT "",'
                  '`preview` text NOT NULL DEFAULT "",`step_count` integer NOT NULL DEFAULT 0,`last_modified_time` datetime NOT NULL,'
                  '`workspace_uris` text NOT NULL,`status` text NOT NULL DEFAULT "",`source` text NOT NULL DEFAULT "",'
                  '`project_id` text NOT NULL DEFAULT "",`agent_name` text NOT NULL DEFAULT "",`parent_conversation_id` text NOT NULL DEFAULT "",'
                  '`nesting_depth` integer NOT NULL DEFAULT 0,`battle_id` text NOT NULL DEFAULT "",`winning_conversation_id` text NOT NULL DEFAULT "",'
                  '`not_fully_idle` numeric NOT NULL DEFAULT false,`killed` numeric NOT NULL DEFAULT false,`last_user_input_time` datetime NOT NULL,'
                  '`last_user_input_step_index` integer NOT NULL DEFAULT -1,`app_data_dir` text NOT NULL DEFAULT "", raw_summary BLOB, group_id TEXT NOT NULL DEFAULT "",'
                  'PRIMARY KEY (`conversation_id`))')
        c.commit()
        c.close()

    def tearDown(self):
        from samethread.agents import antigravity
        antigravity.ROOT = self.saved_root
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_write_and_update_native_copy(self):
        import sqlite3
        agent = AGENTS['agy']
        cwd = os.getcwd()
        res = agent.write(None, cwd, MSGS, 'CI is red', {'cfg': CFG})
        self.assertIsNotNone(res['id'])
        cid = res['id']

        # Check summary row
        db = os.path.join(self.tmp, 'conversation_summaries.db')
        c = sqlite3.connect(db)
        c.row_factory = sqlite3.Row
        row = c.execute('select * from conversation_summaries where conversation_id=?', (cid,)).fetchone()
        self.assertEqual(row['title'], 'CI is red')
        self.assertEqual(row['status'], 'CASCADE_RUN_STATUS_IDLE')
        uris = json.loads(row['workspace_uris'])
        self.assertIsInstance(uris, list)
        self.assertTrue(uris[0].startswith('file:///'))
        c.close()

        # Check trajectory db
        conv_db = os.path.join(self.tmp, 'conversations', cid + '.db')
        c = sqlite3.connect(conv_db)
        meta = c.execute('select * from trajectory_meta').fetchall()
        self.assertEqual(len(meta), 1)
        meta_blob = c.execute('select * from trajectory_metadata_blob').fetchall()
        self.assertEqual(len(meta_blob), 1)
        c.close()

        # Update existing copy
        more_msgs = MSGS + [{'role': 'user', 'text': 'another question', 'ts': 1790000002000}]
        res2 = agent.write(res, cwd, more_msgs, 'CI is red (Updated)', {'cfg': CFG})
        self.assertEqual(res2['id'], cid)

        c = sqlite3.connect(db)
        c.row_factory = sqlite3.Row
        row2 = c.execute('select * from conversation_summaries where conversation_id=?', (cid,)).fetchone()
        self.assertEqual(row2['title'], 'CI is red (Updated)')
        c.close()

        # Delete copy
        agent.delete(res2)
        c = sqlite3.connect(db)
        row3 = c.execute('select * from conversation_summaries where conversation_id=?', (cid,)).fetchone()
        self.assertIsNone(row3)
        c.close()
        self.assertFalse(os.path.exists(conv_db))


class HopResumeNativeCopy(unittest.TestCase):
    """A hop has to write the copy and then launch the agent's own resume command."""

    def setUp(self):
        from samethread import cli
        self.cli = cli
        self.dir = tempfile.mkdtemp(prefix='hop-resume-')
        self.saved = (cli.THREAD_DIR, cli.launch, cli.load_config)
        cli.THREAD_DIR = self.dir
        self.launched = []
        cli.launch = lambda cmd, cwd: self.launched.append((cmd, cwd))
        cli.load_config = lambda: dict(CFG)
        self.thread = {
            'tid': 'abcd1234abcd', 'base_title': 'CI is red', 'title': 'CI is red (Codex)',
            'cwd': os.getcwd(), 'origin': 'codex:1', 'updated': 1790000000000,
            'elements': [{'id': '0', 'role': 'user', 'text': 'why is CI red?', 'author': 'codex',
                          'kind': 'msg', 'ts': 1790000000000},
                         {'id': '1', 'role': 'assistant', 'text': 'looking into it', 'author': 'codex',
                          'kind': 'msg', 'ts': 1790000001000}],
            'copies': {}, 'suppressed': [],
        }
        with open(os.path.join(self.dir, self.thread['tid'] + '.json'), 'w', encoding='utf-8') as f:
            json.dump(self.thread, f)

    def tearDown(self):
        cli = self.cli
        cli.THREAD_DIR, cli.launch, cli.load_config = self.saved

    def test_resume_copies_natively_and_launches_the_native_resume_command(self):
        os.environ['CURSOR_HOME'] = tempfile.mkdtemp(prefix='hop-cursor-')
        args = argparse.Namespace(agent='cursor', query=None, all=False, handoff=False)
        try:
            self.cli.cmd_resume(args)
        except SystemExit:
            pass
        self.assertTrue(self.launched, 'the hop must launch the agent')
        cmd, cwd = self.launched[0]
        self.assertTrue(any('resume' in part for part in cmd), 'the hop must use the agent native resume command')
        self.assertEqual(cwd, os.getcwd())

        th = json.load(open(os.path.join(self.dir, self.thread['tid'] + '.json'), encoding='utf-8'))
        copies = [k for k in th['copies'] if k.startswith('cursor:')]
        self.assertEqual(len(copies), 1, 'the thread must record the native copy')
        sid = copies[0].split(':', 1)[1]
        self.assertEqual(cmd[-1], sid, 'the hop must resume the copy it just wrote')

        written = os.path.join(os.environ['CURSOR_HOME'], 'sessions', sid + '.json')
        self.assertTrue(os.path.exists(written), 'the copy must be a real session file')
        doc = json.load(open(written, encoding='utf-8'))
        self.assertEqual([m['role'] for m in doc['messages']], ['user', 'assistant'])

    def test_handoff_flag_skips_the_native_copy(self):
        os.environ['CURSOR_HOME'] = tempfile.mkdtemp(prefix='hop-cursor-')
        args = argparse.Namespace(agent='cursor', query=None, all=False, handoff=True)
        try:
            self.cli.cmd_resume(args)
        except SystemExit:
            pass
        self.assertTrue(self.launched)
        cmd, _ = self.launched[0]
        self.assertFalse(any('resume' in part for part in cmd),
                         'the handoff path must not use the native resume command')

        th = json.load(open(os.path.join(self.dir, self.thread['tid'] + '.json'), encoding='utf-8'))
        self.assertFalse([k for k in th['copies'] if k.startswith('cursor:')])

    def test_resume_updates_existing_copy_that_is_behind(self):
        os.environ['CURSOR_HOME'] = tempfile.mkdtemp(prefix='hop-cursor-')
        # First resume: creates the copy with 2 elements
        args = argparse.Namespace(agent='cursor', query=None, all=False, handoff=False)
        try:
            self.cli.cmd_resume(args)
        except SystemExit:
            pass
        self.assertEqual(len(self.launched), 1)

        # Thread gets a 3rd element from another agent
        th = json.load(open(os.path.join(self.dir, self.thread['tid'] + '.json'), encoding='utf-8'))
        th['elements'].append({'id': '2', 'role': 'user', 'text': 'new turn from codex',
                               'author': 'codex', 'kind': 'msg', 'ts': 1790000002000})
        with open(os.path.join(self.dir, self.thread['tid'] + '.json'), 'w', encoding='utf-8') as f:
            json.dump(th, f)

        # Second resume: copy was behind, must update it before launching
        self.launched.clear()
        try:
            self.cli.cmd_resume(args)
        except SystemExit:
            pass
        self.assertEqual(len(self.launched), 1)
        th2 = json.load(open(os.path.join(self.dir, self.thread['tid'] + '.json'), encoding='utf-8'))
        copies = [k for k in th2['copies'] if k.startswith('cursor:')]
        self.assertEqual(th2['copies'][copies[0]]['upto'], 3)
        sid = copies[0].split(':', 1)[1]
        written = os.path.join(os.environ['CURSOR_HOME'], 'sessions', sid + '.json')
        doc = json.load(open(written, encoding='utf-8'))
        self.assertEqual(len(doc['messages']), 3)


if __name__ == '__main__':
    unittest.main()
