"""Native copies: hop writes the chat into an agent's own store, and the agent reads it back."""
import json
import os
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
        for key, agent in AGENTS.items():
            if not agent.can_copy:
                continue
            with self.subTest(agent=key):
                self.assertNotEqual(type(agent).write, type(AGENTS['agy']).write,
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


if __name__ == '__main__':
    unittest.main()
