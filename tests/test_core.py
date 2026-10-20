import json
import os
import tempfile
import unittest

TMP = tempfile.mkdtemp(prefix='hop-test-')
os.environ.update(HOP_HOME=os.path.join(TMP, 'hop'), HOME=TMP, USERPROFILE=TMP, CODEX_HOME=os.path.join(TMP, '.codex'))

from samethread import core, sync  # noqa: E402
from samethread.agents import AGENTS, NAMES, resolve  # noqa: E402

CFG = dict(core.DEFAULT_CONFIG)


def thread(elements):
    th = sync.new_thread('agy:x', 'Auth refactor', os.getcwd())
    th['elements'] = elements
    return th


def e(id_, role, text, author='agy', kind='msg', ts=1790000000000):
    return dict(core.el(id_, role, text, ts, kind), author=author)


class Helpers(unittest.TestCase):
    def test_iso_ms_handles_every_timestamp_shape(self):
        self.assertEqual(core.iso_ms('2026-09-22T04:18:45Z'), 1790050725000)
        self.assertEqual(core.iso_ms('2026-09-23 05:42:48.2564+00:00'), core.iso_ms('2026-09-23T05:42:48.256400Z'))
        self.assertEqual(core.iso_ms(1790050725000), 1790050725000)
        self.assertEqual(core.iso_ms('garbage'), 0)

    def test_compact_json_matches_json_stringify(self):
        self.assertEqual(core.dumps({'subtype': 'custom_title', 'n': 1}), '{"subtype":"custom_title","n":1}')

    def test_titles_drop_old_tags_and_fall_back_to_first_prompt(self):
        self.assertEqual(sync.clean_title('Fix login (Agy+Qwen+Kimi)', []), 'Fix login')
        self.assertEqual(sync.clean_title('New session - 2026-09-23', [e('1', 'user', 'why is CI red?\nmore')]), 'why is CI red?')

    def test_fmt_call_prefers_the_meaningful_argument(self):
        self.assertEqual(core.fmt_call('Bash', {'command': 'ls -la', 'timeout': 5}, CFG), '▸ Bash: ls -la')
        self.assertEqual(core.fmt_call('shell', {'command': ['git', 'status']}, CFG), '▸ shell: git status')

    def test_agent_names_resolve(self):
        self.assertEqual(resolve('claude'), 'cc')
        self.assertEqual(resolve('MiniMax'), 'mmx')
        self.assertEqual(resolve('cursor'), 'cursor')
        self.assertEqual(resolve('grok'), 'grok')
        self.assertEqual(resolve('deepseek'), 'deepseek')
        self.assertEqual(resolve('harmes'), 'hermes')
        self.assertEqual(resolve('openclaw'), 'openclaw')
        self.assertEqual(resolve('aider'), 'aider')
        self.assertEqual(len(NAMES), 15)


class Render(unittest.TestCase):
    def test_merges_turns_and_tags_the_source(self):
        th = thread([e('1', 'user', 'hi'), e('2', 'assistant', 'looking'), e('3', 'tool', '▸ ls'),
                     e('4', 'assistant', 'done'), e('5', 'user', 'thanks', author='kimi')])
        msgs = sync.render(th, CFG)
        self.assertEqual([m['role'] for m in msgs], ['user', 'assistant', 'user'])
        self.assertIn('Agy+Kimi', msgs[0]['text'])
        self.assertEqual(msgs[1]['text'], 'looking\n\n▸ ls\n\ndone')
        self.assertEqual(sync.thread_title(th), 'Auth refactor (Agy+Kimi)')

    def test_starts_from_the_latest_summary(self):
        th = thread([e('1', 'user', 'old'), e('2', 'assistant', 'old reply'),
                     e('3', 'user', 'what happened so far', kind='summary'), e('4', 'user', 'next')])
        msgs = sync.render(th, CFG)
        self.assertNotIn('old reply', ''.join(m['text'] for m in msgs))
        self.assertIn('[Summary of earlier conversation]', msgs[0]['text'])

    def test_drops_oldest_messages_past_the_budget(self):
        els = []
        for i in range(10):
            els += [e(f'u{i}', 'user', 'q' * 100), e(f'a{i}', 'assistant', 'a' * 100)]
        msgs = sync.render(thread(els), dict(CFG, max_chars=500))
        self.assertLessEqual(len(msgs), 7)
        self.assertIn('earlier messages were omitted', msgs[0]['text'])


class RoundTrip(unittest.TestCase):
    """Every writable agent must read back exactly what it wrote, with the tagged title."""

    def roundtrip(self, key, cwd):
        agent = AGENTS[key]
        th = thread([e('1', 'user', 'remember MANGO'), e('2', 'assistant', 'stored')])
        ctx = {'cfg': CFG}
        if key == 'kimi':
            ctx['kimi_bind'] = {'type': 'profile.bind', 'agentId': 'main', 'modelAlias': 'm', 'profileName': 'agent',
                                'thinkingEffort': 'high', 'systemPrompt': '', 'disallowedTools': []}
        res = agent.write(None, cwd, sync.render(th, CFG), 'Auth refactor (Agy)', ctx)
        sessions = agent.list(CFG)
        s = sessions[f'{key}:{res["id"]}']
        els = sync.load(s, CFG)
        self.assertEqual({x['id'] for x in els}, set(res['seen']), key)
        self.assertEqual(els[-1]['text'], 'stored', key)
        self.assertIn('remember MANGO', els[0]['text'], key)
        self.assertTrue(s['is_hop'], key)
        if key != 'oc':
            self.assertEqual(s.get('title') or '', 'Auth refactor (Agy)', key)
        return agent, res

    def test_claude(self):
        agent, res = self.roundtrip('cc', os.getcwd())
        with open(res['path'], encoding='utf-8') as f:
            self.assertIn('"customTitle":"Auth refactor (Agy)"', f.read())  # Claude's tail scan needs compact JSON

    def test_codex(self):
        self.roundtrip('codex', os.getcwd())

    def test_qwen(self):
        _, res = self.roundtrip('qwen', os.getcwd())
        with open(res['path'], encoding='utf-8') as f:
            self.assertIn('"subtype":"custom_title"', f.read())  # Qwen greps for this exact string

    def test_pi(self):
        self.roundtrip('pi', os.getcwd())

    def test_kimi(self):
        os.makedirs(os.path.join(TMP, '.kimi-code'), exist_ok=True)
        self.roundtrip('kimi', os.getcwd())


    def test_claude_detects_a_continued_mirror(self):
        agent, res = self.roundtrip('cc', os.getcwd())
        with open(res['path'], encoding='utf-8') as f:
            last = [json.loads(line) for line in f if '"uuid"' in line][-1]
        with open(res['path'], 'a', encoding='utf-8') as f:
            f.write(json.dumps({'type': 'user', 'uuid': 'u-new', 'parentUuid': last['uuid'], 'sessionId': res['id'],
                                'timestamp': '2026-09-23T06:00:00Z', 'message': {'role': 'user', 'content': 'codeword?'}}) + '\n')
            f.write(json.dumps({'type': 'assistant', 'uuid': 'a-new', 'parentUuid': 'u-new', 'sessionId': res['id'],
                                'timestamp': '2026-09-23T06:00:01Z',
                                'message': {'role': 'assistant', 'content': [
                                    {'type': 'thinking', 'thinking': '', 'signature': 'x'},
                                    {'type': 'text', 'text': 'MANGO'}]}}) + '\n')
        s = agent.list(CFG)[f'cc:{res["id"]}']
        new = [x for x in sync.load(s, CFG) if x['id'] not in set(res['seen'])]
        self.assertEqual([(x['role'], x['text']) for x in new], [('user', 'codeword?'), ('assistant', 'MANGO')])


class Antigravity(unittest.TestCase):
    def test_reads_transcript_steps(self):
        path = os.path.join(TMP, 'transcript_full.jsonl')
        steps = [
            {'step_index': 0, 'type': 'USER_INPUT', 'source': 'USER_EXPLICIT', 'created_at': '2026-09-22T04:18:45Z',
             'content': '<USER_REQUEST>\nfix the build\n</USER_REQUEST>\n<ADDITIONAL_METADATA>t</ADDITIONAL_METADATA>'},
            {'step_index': 1, 'type': 'PLANNER_RESPONSE', 'source': 'MODEL', 'content': 'Checking.',
             'thinking': 'hidden', 'tool_calls': [{'name': 'run_command', 'args': {'CommandLine': 'npm test'}}]},
            {'step_index': 2, 'type': 'RUN_COMMAND', 'source': 'MODEL',
             'content': 'Created At: x\nCompleted At: y\n1 failing'},
            {'step_index': 3, 'type': 'SYSTEM_MESSAGE', 'source': 'SYSTEM', 'content': 'ignored'},
        ]
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(json.dumps(s) for s in steps))
        els = AGENTS['agy'].read({'path': path}, CFG)
        self.assertEqual([(x['role'], x['text']) for x in els], [
            ('user', 'fix the build'), ('assistant', 'Checking.'),
            ('tool', '▸ run_command: npm test'), ('tool', '  ⎿ 1 failing')])


if __name__ == '__main__':
    unittest.main()
