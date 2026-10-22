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


if __name__ == '__main__':
    unittest.main()
