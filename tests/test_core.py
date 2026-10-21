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


class Regressions(unittest.TestCase):
    def test_kimi_updated_timestamp_is_integer(self):
        s_dir = os.path.join(TMP, '.kimi-code', 'sessions', 'test_session')
        os.makedirs(os.path.join(s_dir, 'agents', 'main'), exist_ok=True)
        idx_path = os.path.join(TMP, '.kimi-code', 'session_index.jsonl')
        wire = os.path.join(s_dir, 'agents', 'main', 'wire.jsonl')
        with open(wire, 'w') as f:
            f.write('')
        with open(idx_path, 'w') as f:
            f.write(json.dumps({'sessionId': 's1', 'sessionDir': s_dir, 'workDir': TMP}) + '\n')
        with open(os.path.join(s_dir, 'state.json'), 'w') as f:
            f.write(json.dumps({'updatedAt': '2026-07-18T13:10:14.672Z', 'title': 'Test'}))

        sessions = AGENTS['kimi'].list(CFG)
        self.assertIn('kimi:s1', sessions)
        self.assertIsInstance(sessions['kimi:s1']['updated'], int)
        mixed = [sessions['kimi:s1'], {'updated': 1790000000000}]
        sorted(mixed, key=lambda s: s['updated'])

    def test_hermes_cli_commands(self):
        agent = AGENTS['hermes']
        cmd = agent.resume_cmd('test-session')
        self.assertIn('--resume', cmd)
        self.assertNotIn('resume', cmd[1:])
        seed = agent.seed_cmd('hello')
        self.assertIn('-q', seed)
        self.assertNotIn('-m', seed)

    def test_on_demand_resume_dict_unpacking(self):
        th = thread([e('1', 'user', 'hello')])
        agent = AGENTS['codex']
        cfg = core.DEFAULT_CONFIG
        res = agent.write(None, th['cwd'], sync.render(th, cfg), sync.thread_title(th), {})
        # Simulating cli.py line 112: unpacking must succeed without ValueError
        sid = res['id']
        seen = res['seen']
        sig = res['sig']
        self.assertTrue(bool(sid and sig))


class RegressionTests(unittest.TestCase):
    def test_el_and_dedup_preserve_turns_when_id_is_none(self):
        e1 = core.el(None, 'user', 'first message', 1000)
        e2 = core.el(None, 'assistant', 'second message', 2000)
        self.assertNotEqual(e1['id'], e2['id'])
        self.assertNotEqual(e1['id'], 'None')
        self.assertNotEqual(e2['id'], 'None')
        deduped = core.dedup([e1, e2])
        self.assertEqual(len(deduped), 2)

    def test_same_path_handles_case_and_symlinks(self):
        with tempfile.TemporaryDirectory() as td:
            real_dir = os.path.join(td, "real_dir")
            os.makedirs(real_dir)
            symlink_dir = os.path.join(td, "symlink_dir")
            os.symlink(real_dir, symlink_dir)
            self.assertTrue(core.same_path(real_dir, symlink_dir))
            self.assertTrue(core.same_path(real_dir.upper(), symlink_dir.lower()))

    def test_fork_clears_owned_flag(self):
        s = sync.Sync(CFG)
        th = sync.new_thread('cc:orig', 'Base Thread', os.getcwd())
        th['elements'] = [e('1', 'user', 'prompt'), e('2', 'assistant', 'reply')]
        th['copies']['cc:orig'] = {'owned': True, 'seen': ['1', '2'], 'sig': 's1', 'upto': 2}
        s.threads[th['tid']] = th
        new_elements = [core.el('3', 'user', 'followup', 3000)]
        s.fork(th, 'cc:orig', new_elements, 3000)
        # The diverged fork must have owned=False so clean won't delete the user's active session
        forked_tid = s.idx['copies']['cc:orig']
        forked_thread = s.threads[forked_tid]
        self.assertFalse(forked_thread['copies']['cc:orig']['owned'])

    def test_all_threads_reads_unindexed_threads_from_disk(self):
        from samethread import cli
        unindexed_tid = 'unindexed_test_thread'
        th_data = {
            'tid': unindexed_tid,
            'base_title': 'Unindexed Chat',
            'cwd': os.getcwd(),
            'updated': 123456789,
            'elements': [],
            'copies': {}
        }
        th_path = os.path.join(core.THREAD_DIR, f'{unindexed_tid}.json')
        core.write_json(th_path, th_data)
        try:
            threads = cli.all_threads()
            self.assertTrue(any(t['tid'] == unindexed_tid for t in threads))
        finally:
            if os.path.exists(th_path):
                os.remove(th_path)

    def test_wait_lock_reclaims_stale_pid_without_hanging(self):
        # Create a lockfile with a dead PID (e.g. 99999999)
        os.makedirs(os.path.dirname(core.LOCK_PATH), exist_ok=True)
        with open(core.LOCK_PATH, 'w') as f:
            f.write('99999999')
        # wait_lock should detect the dead PID and acquire lock immediately without waiting 60s
        acquired = sync.wait_lock(seconds=2)
        self.assertTrue(acquired)
        if os.path.exists(core.LOCK_PATH):
            os.remove(core.LOCK_PATH)

    def test_writable_agents_provide_seed_cmd(self):
        for key in ('claude', 'codex', 'opencode', 'qwen', 'kimi', 'pi'):
            agent = AGENTS[resolve(key)]
            cmd = agent.seed_cmd('continue conversation')
            self.assertIsNotNone(cmd, f'Agent {key} returned None for seed_cmd')
            self.assertIsInstance(cmd, list)
            self.assertIn('continue conversation', ' '.join(cmd))

    def test_openhands_seed_cmd_uses_t_flag(self):
        agent = AGENTS['openhands']
        cmd = agent.seed_cmd('continue conversation')
        self.assertIn('-t', cmd)

    def test_adapters_parse_list_content_and_none_id(self):
        # Deepseek, Grok, Hermes, OpenClaw, OpenHands, Cursor, Kimi
        with tempfile.TemporaryDirectory() as td:
            # Test deepseek json format with list content and None id
            ds_path = os.path.join(td, 'deepseek.json')
            with open(ds_path, 'w') as f:
                json.dump({
                    'messages': [
                        {'id': None, 'role': 'user', 'content': [{'type': 'text', 'text': 'hello deepseek'}]},
                        {'id': None, 'role': 'assistant', 'content': [{'type': 'text', 'text': 'reply deepseek'}]}
                    ]
                }, f)
            els = AGENTS['deepseek'].read({'path': ds_path}, CFG)
            self.assertEqual(len(els), 2)
            self.assertEqual(els[0]['text'], 'hello deepseek')
            self.assertEqual(els[1]['text'], 'reply deepseek')
            self.assertNotEqual(els[0]['id'], els[1]['id'])

            # Test kimi with string content in context.append_message
            kimi_path = os.path.join(td, 'kimi_wire.jsonl')
            with open(kimi_path, 'w') as f:
                f.write(json.dumps({
                    'type': 'context.append_message',
                    'time': 1000,
                    'message': {
                        'id': 'm1',
                        'role': 'user',
                        'content': 'kimi prompt string',
                        'origin': {'kind': 'user'}
                    }
                }) + '\n')
            k_els = AGENTS['kimi'].read({'path': kimi_path}, CFG)
            self.assertEqual(len(k_els), 1)
            self.assertEqual(k_els[0]['text'], 'kimi prompt string')

    def test_cmd_list_handles_unknown_agent_key(self):
        from samethread import cli
        import io
        from unittest.mock import patch
        th = thread([e('1', 'user', 'test')])
        th['copies']['unknown_tool:123'] = {'owned': True, 'seen': ['1'], 'sig': 's1', 'upto': 1}
        args = type('Args', (), {'all': True, 'limit': 10})()
        with patch('samethread.cli.scoped', return_value=[th]), patch('sys.stdout', new=io.StringIO()):
            # Must not raise ValueError: list.index(x): x not in list
            cli.cmd_list(args)


if __name__ == '__main__':
    unittest.main()
