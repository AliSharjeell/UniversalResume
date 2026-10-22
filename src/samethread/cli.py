"""SameThread (`hop`): one chat history across every coding agent you use.

Every chat is mirrored into the other agents' own session stores, so each agent's native
resume picker lists it, titled with the agents that wrote it: "Fix login (Agy)",
"Fix login (Agy+Claude)". Originals are never modified; hop only rewrites mirrors it created.
Agents hop can't write into (Antigravity, MiniMax Code) are reached with `hop resume <agent>`,
which seeds a new conversation from the transcript.

State lives in ~/.hop: config.json, index.json, threads/<id>.json, hop.log.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

from . import __version__
from .agents import AGENTS, NAMES, resolve, targets
from .core import (HANDOFF_DIR, HOP_DIR, INDEX_PATH, LOCK_PATH, THREAD_DIR, ago, load_config, now_ms, read_json, same_path,
                   settings, write_json)
from .sync import detach, locked_sync, render, tag, thread_title, wait_lock


def all_threads():
    out = {}
    if os.path.isdir(THREAD_DIR):
        for fname in os.listdir(THREAD_DIR):
            if fname.endswith('.json'):
                th = read_json(os.path.join(THREAD_DIR, fname), None)
                if th and 'tid' in th:
                    out[th['tid']] = th
    idx = read_json(INDEX_PATH, {})
    for tid in set(idx.get('copies', {}).values()):
        if tid not in out:
            th = read_json(os.path.join(THREAD_DIR, tid + '.json'), None)
            if th:
                out[tid] = th
    return sorted(out.values(), key=lambda t: t.get('updated', 0), reverse=True)


def scoped(args):
    threads = all_threads()
    if not args.all:
        threads = [t for t in threads if same_path(t['cwd'], os.getcwd())]
    return threads


def pick(threads, query):
    if query is None:
        return threads[0] if threads else None
    if query.isdigit() and 1 <= int(query) <= len(threads):
        return threads[int(query) - 1]
    hits = [t for t in threads if query.lower() in thread_title(t).lower() or t['tid'].startswith(query)]
    return hits[0] if hits else None


def shown(cmd):
    return ' '.join(f'"{c}"' if ' ' in c else c for c in cmd)


def launch(cmd, cwd):
    exe = shutil.which(cmd[0]) or cmd[0]
    use_shell = sys.platform == 'win32' and exe.lower().endswith(('.cmd', '.bat'))
    sys.exit(subprocess.call([exe] + cmd[1:], cwd=cwd if cwd and os.path.isdir(cwd) else None, shell=use_shell))


def cmd_list(args):
    threads = scoped(args)
    if not threads:
        print('No chats for this folder yet.' + ('' if args.all else ' Try: hop list --all'))
        return
    for i, th in enumerate(threads[:args.limit], 1):
        muted = '  ·  not mirrored' if th.get('forgotten') or {'cc', 'oc'} <= set(th.get('suppressed', [])) else ''
        print(f'{i:>3}. {thread_title(th)}  ·  {ago(th["updated"])}{muted}' + (f'  ·  {th["cwd"]}' if args.all else ''))
        for key, cp in sorted(th['copies'].items(), key=lambda kv: list(AGENTS).index(kv[0].split(':')[0]) if kv[0].split(':')[0] in AGENTS else 999):
            tool, sid = key.split(':', 1)
            state = 'mirror' if cp['owned'] else 'original'
            behind = '' if cp['upto'] == len(th['elements']) else ' (behind)'
            cmd_str = shown(AGENTS[tool].resume_cmd(sid)) if tool in AGENTS else sid
            print(f'       {NAMES.get(tool, tool):<9} {state:<8}{behind}  {cmd_str}')


def format_seamless_prompt(th, cfg, path):
    tid = th.get('tid', '')
    title = th.get('base_title') or th.get('title') or thread_title(th) or 'Untitled'
    origin = tag(th) or 'another agent'

    msgs = render(th, cfg)
    recent_blocks = []
    total = 0
    max_chars = 3500
    for m in reversed(msgs):
        role_label = 'User' if m['role'] == 'user' else 'Assistant'
        txt = re.sub(r'^\[hop\][^\n]*\n\n?', '', m['text']).strip()
        if len(txt) > 800:
            txt = txt[:790] + '...'
        block = f'{role_label}:\n{txt}\n'
        if total + len(block) > max_chars and recent_blocks:
            break
        recent_blocks.append(block)
        total += len(block)
    recent_blocks.reverse()
    transcript_text = '\n'.join(recent_blocks)

    return (
        f'[hop-handoff:{tid}] Continuing conversation "{title}" seamlessly from {origin}.\n\n'
        f'--- Prior Conversation Context ---\n'
        f'{transcript_text}\n'
        f'--- End of Context ---\n\n'
        f'Pick up exactly where we left off. Greet the user naturally, give a 1-sentence recap of the task in progress, and ask how to proceed.'
    )


def seed(agent, th):
    """Continue a chat in an agent hop can't write into with full seamless context."""
    cfg = load_config()
    path = os.path.join(HANDOFF_DIR, th['tid'] + '.md')
    body = [f'# {thread_title(th)}\n']
    for m in render(th, cfg):
        body.append(f'## {"User" if m["role"] == "user" else "Assistant"}\n\n{m["text"]}\n')
    os.makedirs(HANDOFF_DIR, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(body))
    pending = read_json(os.path.join(HANDOFF_DIR, 'pending.json'), {})
    pending[th['tid']] = now_ms() - 60000
    write_json(os.path.join(HANDOFF_DIR, 'pending.json'), pending)
    prompt = format_seamless_prompt(th, cfg, path)
    cmd = agent.seed_cmd(prompt)
    if not cmd:
        sys.exit(f'Agent {agent.name} does not support starting a session via command line.')
    launch(cmd, th['cwd'])


def cmd_resume(args):
    try:
        key = resolve(args.agent)
    except KeyError:
        sys.exit(f'Unknown agent "{args.agent}". Supported: {", ".join(AGENTS)}')
    agent = AGENTS[key]
    th = pick(scoped(args), args.query) or (pick(all_threads(), args.query) if args.query else None)
    if not th:
        sys.exit('No matching chat. See: hop list')
    copies = [k for k in th['copies'] if k.startswith(key + ':')]
    if copies:
        best = max(copies, key=lambda k: (th['copies'][k]['upto'], th['copies'][k]['owned']))
        launch(agent.resume_cmd(best.split(':', 1)[1]), th['cwd'])
    if agent.writable:
        try:
            cfg = load_config()
            res = agent.write(None, th['cwd'], render(th, cfg), thread_title(th), {})
            if res:
                sid, seen, sig = res['id'], res['seen'], res['sig']
                th['copies'][f'{key}:{sid}'] = {'owned': True, 'seen': seen, 'sig': sig, 'upto': len(th['elements']), 'title': thread_title(th)}
                write_json(os.path.join(THREAD_DIR, th['tid'] + '.json'), th)
                launch(agent.resume_cmd(sid), th['cwd'])
        except Exception:
            pass
    seed(agent, th)


def cmd_agents(args):
    cfg = load_config()
    writable = set(targets(cfg))
    print(f'{"agent":<10} {"installed":<10} {"mirrors":<9} resume')
    for key, agent in AGENTS.items():
        found = agent.detect()
        mode = 'written' if key in writable else ('seeded' if not agent.writable else '-')
        print(f'{agent.name:<10} {"yes" if found else "no":<10} {mode if found else "-":<9} hop resume {key}')


def cmd_sync(args):
    if args.detach:
        detach(['sync', '--quiet'] + (['--days', str(args.days)] if args.days else []))
        return
    stats = locked_sync(load_config(), args.days, args.dry_run)
    if stats is not None and not settings['quiet']:
        print('done: ' + (', '.join(f'{k} {v}' for k, v in sorted(stats.items())) or 'nothing changed'))


def cmd_hook(args):
    """Entry point for agent hooks: never blocks the agent; prints valid JSON for hook protocols that need it."""
    if args.json:
        print('{}', flush=True)
    if not os.environ.get('HOP_SYNCING'):
        detach(['sync', '--quiet'])


def delete_copy(key, cp):
    AGENTS[key.split(':')[0]].delete(cp)


def cmd_forget(args):
    th = pick(scoped(args), args.query)
    if not th:
        sys.exit('No matching chat. See: hop list')
    if not wait_lock():
        sys.exit('A sync is still running; try again in a moment.')
    try:
        th = read_json(os.path.join(THREAD_DIR, th['tid'] + '.json'), th)
        for key, cp in list(th['copies'].items()):
            if cp['owned']:
                delete_copy(key, cp)
                del th['copies'][key]
        th['suppressed'], th['forgotten'] = list(AGENTS), True
        write_json(os.path.join(THREAD_DIR, th['tid'] + '.json'), th)
    finally:
        os.remove(LOCK_PATH)
    print(f'Deleted the mirrors of "{thread_title(th)}" and stopped mirroring it. The original is untouched.')


def cmd_clean(args):
    threads = all_threads()
    owned = [(k, cp, th) for th in threads for k, cp in th['copies'].items() if cp['owned']]
    if not args.yes:
        for k, cp, th in owned:
            print(f'would delete {NAMES.get(k.split(":")[0])} mirror: {cp.get("title") or thread_title(th)}')
        print(f'{len(owned)} mirrors. Originals are untouched. Re-run with --yes to delete.')
        return
    for k, cp, th in owned:
        try:
            delete_copy(k, cp)
        except Exception as e:
            print(f'! {k}: {e}')
    shutil.rmtree(THREAD_DIR, ignore_errors=True)
    for p in (INDEX_PATH, os.path.join(HANDOFF_DIR, 'pending.json')):
        if os.path.exists(p):
            os.remove(p)
    print(f'deleted {len(owned)} mirrors and reset hop state')


def cmd_install(args, remove=False):
    for agent in AGENTS.values():
        if not agent.detect():
            print(f'  {agent.name}: not found, skipped')
            continue
        try:
            msg = (agent.uninstall if remove else agent.install)(args.dry_run)
        except Exception as e:
            msg = f'failed: {e}'
        if msg:
            print(f'  {agent.name}: {msg}')
    if not args.dry_run:
        if remove:
            print('\nHooks removed. Mirrors stay; delete them with `hop clean --yes`.')
        else:
            print('\nHooks installed. Universal Resume keeps your chats synced automatically.')
            try:
                locked_sync(load_config(), 365, False)
            except Exception:
                pass


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        pass
    ap = argparse.ArgumentParser(prog='hop', description='SameThread: one chat history across your coding agents.')
    ap.add_argument('--version', action='version', version=f'samethread {__version__}')
    sub = ap.add_subparsers(dest='cmd', required=True)

    p = sub.add_parser('install', help='wire up auto-sync hooks for every installed agent')
    p.add_argument('--dry-run', action='store_true')
    p.set_defaults(fn=cmd_install)

    p = sub.add_parser('uninstall', help='remove the hooks `hop install` added (chats and mirrors stay)')
    p.add_argument('--dry-run', action='store_true')
    p.set_defaults(fn=lambda a: cmd_install(a, remove=True))

    p = sub.add_parser('agents', help='supported agents, which are installed, and how hop reaches them')
    p.set_defaults(fn=cmd_agents)

    p = sub.add_parser('sync', help='mirror new and changed chats into every agent')
    p.add_argument('--days', type=int, help='only adopt chats active in the last N days (default: config)')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--detach', action='store_true', help='run in the background and return immediately')
    p.add_argument('-q', '--quiet', action='store_true')
    p.set_defaults(fn=cmd_sync)

    for name, fn, hlp in (('list', cmd_list, 'show chats for this folder and how to resume them'),
                          ('resume', cmd_resume, 'open a chat in any agent (seeds a new one where hop cannot write)'),
                          ('agy', cmd_resume, 'shortcut for: hop resume agy'),
                          ('forget', cmd_forget, "delete a chat's mirrors and stop mirroring it")):
        p = sub.add_parser(name, help=hlp)
        if name == 'resume':
            p.add_argument('agent', help=f'{", ".join(AGENTS)} (or the full name)')
        if name == 'agy':
            p.set_defaults(agent='agy')
        if name != 'list':
            p.add_argument('query', nargs='?', help='number from `hop list`, or part of the title')
        p.add_argument('-a', '--all', action='store_true', help='all folders, not just the current one')
        p.add_argument('-n', '--limit', type=int, default=30)
        p.set_defaults(fn=fn)

    p = sub.add_parser('hook', help='called by agent hooks; starts a background sync')
    p.add_argument('--json', action='store_true', help='print {} for hook protocols that need JSON (agy)')
    p.add_argument('payload', nargs='*', help=argparse.SUPPRESS)  # Codex `notify` appends its event JSON
    p.set_defaults(fn=cmd_hook)

    p = sub.add_parser('clean', help='delete every mirror hop created and reset its state')
    p.add_argument('--yes', action='store_true')
    p.set_defaults(fn=cmd_clean)

    for name in ('tui', 'ui'):
        p = sub.add_parser(name, help='launch the OpenTUI interactive terminal session selector')
        p.set_defaults(fn=lambda a: main_resume_tui())

    args = ap.parse_args()
    settings['quiet'] = getattr(args, 'quiet', False) or args.cmd == 'hook'
    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    args.fn(args)


def main_resume_tui():
    """Launch the OpenTUI interactive resume interface."""
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    tui_script = os.path.join(root_dir, 'tui', 'index.tsx')
    bun_exe = shutil.which('bun')
    pending_file = os.path.join(HOP_DIR, 'pending_launch.json')

    if os.path.exists(pending_file):
        try:
            os.remove(pending_file)
        except Exception:
            pass

    if bun_exe and os.path.exists(tui_script):
        cmd = [bun_exe, 'run', tui_script] + sys.argv[1:]
        env = dict(os.environ, RESUME_RUNNER='1')
        try:
            ret = subprocess.call(cmd, env=env)
        except KeyboardInterrupt:
            sys.exit(0)

        if ret != 0:
            sys.exit(ret)

        if os.path.exists(pending_file):
            launch_spec = read_json(pending_file, None)
            try:
                os.remove(pending_file)
            except Exception:
                pass
            if launch_spec and 'agentKey' in launch_spec and 'tid' in launch_spec:
                sys.argv = ['hop', 'resume', launch_spec['agentKey'], launch_spec['tid']]
                main()
        sys.exit(0)
    else:
        # Fallback to standard hop list
        sys.argv = ['hop', 'list'] + sys.argv[1:]
        main()


if __name__ == '__main__':
    main()

