<p align="center">
  <img src="assets/hero.svg" alt="SameThread: hop between coding agents, stay on the same thread" width="100%">
</p>

<p align="center">
  <a href="#quick-start"><img src="https://img.shields.io/badge/setup-3_commands-5EEAD4?style=for-the-badge" alt="Setup: 3 commands"></a>
  <a href="#supported-agents"><img src="https://img.shields.io/badge/agents-9-8AA4FF?style=for-the-badge" alt="9 agents"></a>
  <a href="#how-it-works"><img src="https://img.shields.io/badge/resume-native,_not_a_summary-E8845C?style=for-the-badge" alt="Native resume"></a>
  <a href="#interactive-opentui-session-picker-resume"><img src="https://img.shields.io/badge/UI-OpenTUI-FF4088?style=for-the-badge" alt="OpenTUI"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/bun-1.1%2B-FBF0DF?logo=bun&logoColor=black" alt="Bun 1.1+">
  <img src="https://img.shields.io/badge/dependencies-0-brightgreen" alt="Zero Python dependencies">
  <a href="https://github.com/AliSharjeell/UniversalResume/actions"><img src="https://img.shields.io/badge/platform-windows_|_macos_|_linux-lightgrey" alt="Platform"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT"></a>
</p>

<p align="center">
  <b>Plan it in Claude Code. Grind it out in Codex or Qwen. Finish it in Antigravity or Kimi.</b><br>
  SameThread puts every conversation into every agent's own <code>/resume</code> list, full history included.
</p>

---

## Why this exists

I use Claude Code for the heavy reasoning and cheaper agents for the easy stuff. Every switch meant starting from zero, because each agent keeps its history in its own private format:

| Agent | Where your chats live |
|---|---|
| Claude Code | JSONL files under `~/.claude/projects` |
| OpenCode | a SQLite database, `opencode.db` |
| Codex CLI | rollout JSONL files under `~/.codex/sessions` |
| Gemini CLI | JSONL files under `~/.gemini/tmp`, keyed by a project registry |
| Qwen Code | JSONL files under `~/.qwen/projects` |
| Pi | a JSONL entry tree under `~/.pi/agent/sessions` |
| Kimi Code | an event log plus `state.json` under `~/.kimi-code/sessions` |
| Antigravity CLI | per-conversation protobuf databases |
| MiniMax Code | a SQLite runtime database |

None of them can see the others. So you re-explain the task, paste logs again, and lose the thread.

**SameThread makes the conversation follow you.** Open any agent, hit `/resume`, and the chat you had somewhere else is there, with the whole history, tagged with where it has been.

<p align="center">
  <img src="assets/pickers.svg" alt="The same chat appearing in Claude Code's /resume, OpenCode's sessions list and hop list" width="100%">
</p>

- **Real resume, not a summary.** The full conversation is written into each agent's own session store, so its native picker and `--resume` flags just work.
- **Automatic.** One hook per agent syncs in the background after every turn. Nothing to remember, nothing to run.
- **Tagged.** `Auth refactor (Agy)` came from Antigravity. `Auth refactor (Agy+Codex)` went through both. Your own chats stay untagged.
- **Round-trips.** Continue a mirrored chat anywhere; the next sync carries the new turns to every other agent.
- **Safe.** Originals are never modified. SameThread only rewrites the mirrors it created. `hop forget`, `hop clean` and `hop uninstall` undo everything.
- **Universal OpenTUI Terminal Picker:** Type `resume` anywhere to open a fast, beautiful TUI built with [OpenTUI](https://github.com/anomalyco/opentui).

---

## Installation & Setup

### Prerequisites
- **Python**: 3.9 or newer (`python --version`)
- **Runtime**: [Bun](https://bun.sh) (recommended) or Node.js 20+

### Windows

```powershell
# 1. Install Bun (if not already installed)
powershell -c "irm bun.sh/install.ps1 | iex"

# 2. Clone repository
git clone https://github.com/AliSharjeell/UniversalResume.git
cd UniversalResume

# 3. Install dependencies and register global resume CLI
bun install
npm link
pip install -e .

# 4. Wire auto-sync hooks and initial sync
hop install
hop sync

# 5. Launch anywhere in terminal!
resume
```

### macOS

```bash
# 1. Install Bun (if not already installed)
curl -fsSL https://bun.sh/install | bash

# 2. Clone repository
git clone https://github.com/AliSharjeell/UniversalResume.git
cd UniversalResume

# 3. Install dependencies and register global resume CLI
bun install
npm link
pip install -e .

# 4. Wire auto-sync hooks and initial sync
hop install
hop sync

# 5. Launch anywhere in terminal!
resume
```

### Linux

```bash
# 1. Install Bun (if not already installed)
curl -fsSL https://bun.sh/install | bash

# 2. Clone repository
git clone https://github.com/AliSharjeell/UniversalResume.git
cd UniversalResume

# 3. Install dependencies and register global resume CLI
bun install
npm link
pip install -e .

# 4. Wire auto-sync hooks and initial sync
hop install
hop sync

# 5. Launch anywhere in terminal!
resume
```

---

## Interactive OpenTUI Session Picker (`resume`)

Built with [OpenTUI](https://github.com/anomalyco/opentui), run `resume` anywhere in your terminal:

- ⚡ **Auto-Sync on Startup:** Every time you write `resume` in your terminal, SameThread automatically scans all installed agents and syncs recent turns in the background before rendering.
- ⟳ **Manual Sync Button & Hotkey:** Hit the interactive `[⟳ Sync (S)]` button in the header or press `s` / `Ctrl+S` anytime inside the TUI to manually refresh all active sessions.
- 🎯 **Browse & Filter:** Displays all past and recent conversations, which coding agent was recently working on them, and relative time. Type to filter instantly.
- 📁 **Folder Scope Toggle (`Tab`):** Press `Tab` to toggle between the current directory and all projects across your machine.
- 📖 **Transcript Preview:** Inspect the original goal, turn counts, and participant agents in the detail panel.
- 🚀 **Hop Into Any Agent:** Press `Enter` on any conversation, choose which agent you want to resume with (`Codex`, `Claude Code`, `Antigravity`, `OpenCode`, `Gemini`, `MiniMax`, `Qwen`, `Pi`, `Kimi`), and jump straight into the session.

| Key | Action |
|---|---|
| `↑` / `↓` | Navigate conversation list |
| `Enter` | Select chat & open Resume dialog |
| `1` - `9` | Quick-pick agent to launch immediately |
| `Tab` | Toggle between current folder & all projects |
| Type text | Live fuzzy / substring filter |
| `Backspace` | Erase search character / Back |
| `s` or `Ctrl+S` | Trigger manual session sync |
| `[⟳ Sync]` | Click with mouse to sync |
| `Esc` | Clear search / Back / Exit |

## Supported agents

| Agent | Reads | Writes a native, resumable chat | Syncs automatically on | Verified |
|---|:---:|---|---|---|
| **Claude Code** | ✅ | ✅ JSONL session + `/rename`-style title | `Stop` + `SessionEnd` hooks | resume ✔ · hook ✔ |
| **OpenCode** 1.x | ✅ | ✅ through OpenCode's own `opencode import` | plugin, every `session.idle` | resume ✔ · hook ✔ |
| **Codex CLI** | ✅ | ✅ rollout file + `session_index` title | `notify` in `config.toml` | resume ✔ · hook ✔ |
| **Qwen Code** | ✅ | ✅ JSONL session + `custom_title` | `Stop` hook | resume ✔ · title ✔ · hook ✔ |
| **Pi** | ✅ | ✅ entry tree + `session_info` name | extension, every `agent_end` | resume ✔ · hook ✔ |
| **Kimi Code** 2.x | ✅ | ✅ event log + custom title | `[[hooks]]` `Stop` in `config.toml` | resume ✔ · hook ✔ |
| **Gemini CLI** | ✅ | ✅ in folders Gemini already knows | `AfterAgent` + `SessionEnd` hooks | listed with title ✔ |
| **Antigravity CLI** (`agy`) | ✅ | ➖ no import API: `hop resume agy` seeds a new conversation | `Stop` hook | read ✔ · hook ✔ |
| **MiniMax Code** | ✅ | ➖ `hop resume mmx` seeds a new session | none yet: picked up by any other agent's sync | read ✔ |

"resume ✔" means a mirror written by SameThread was reopened with the agent's own resume command, and the model answered a question only the imported history could answer. Tested on Windows 11 with Claude Code 2.1.280, OpenCode 1.18.32, Codex 0.156.1, Qwen Code 0.24.4, Pi 0.87.1, Kimi Code 2.0.2, Gemini CLI 0.62 nightly, agy 1.2.9 and MiniMax Code 0.5.2. Storage paths are the same on macOS and Linux, and CI runs the tests on all three systems.

## How it works

```mermaid
flowchart LR
    A["Claude · OpenCode · Codex<br/>Qwen · Pi · Kimi · Gemini"] -- read --> T(("thread<br/><sub>~/.hop/threads</sub>"))
    R["Antigravity · MiniMax"] -- read --> T
    T -- "native mirror, tagged" --> A
    T -. "hop resume (seeded)" .-> R
```

1. **Every chat becomes a thread.** Each agent's transcript is read into a neutral format: user turns, assistant turns, tool calls and results.
2. **Mirrors are written into each agent's own store.** They're titled with the agents that wrote the conversation, and timestamped with the real last activity, so they sort naturally in the picker.
3. **Continuing a mirror is detected by message IDs.** Anything new is appended to the thread, and every other copy is rewritten, so all of them catch up.
4. **Nothing is ever lost.** If two copies are continued separately, the later one splits off as its own `[fork]` chat.
5. **Only portable parts cross over.** Tool calls from other agents arrive as readable lines (`▸ Bash: npm test` / `⎿ 2 failing`). Hidden reasoning is dropped: it's signed per provider and can't be replayed to another model.
6. **New agent installed? It gets your recent chats.** When a new agent shows up, the next sync backfills it.

## Commands

| Command | What it does |
|---|---|
| `resume` | Launch the interactive OpenTUI terminal session picker anywhere. |
| `hop tui` | Shortcut to open the interactive OpenTUI session picker. |
| `hop sync` | Mirror new and changed chats. The hooks run this for you. |
| `hop list [-a]` | Chats for this folder (or all folders), with the exact resume command for every copy. |
| `hop resume <agent> [n]` | Open chat *n* in any agent: `cc`, `oc`, `codex`, `gemini`, `qwen`, `pi`, `kimi`, `agy`, `mmx`. For Antigravity and MiniMax it seeds a new conversation, and its turns flow back to the others. |
| `hop agents` | Which agents are installed, and how hop reaches each. |
| `hop forget <n\|title>` | Delete a chat's mirrors and stop mirroring it. |
| `hop install` / `hop uninstall` | Add or remove the hooks. `hop install` backs up every config file it touches first. |
| `hop clean --yes` | Delete every mirror SameThread ever made and reset its state. |

## Configuration

`~/.hop/config.json` is created on first run:

| Key | Default | Meaning |
|---|---|---|
| `targets` | `"auto"` | Agents to write mirrors into. `auto` means every writable agent that is installed; or list them, e.g. `["cc", "codex"]`. |
| `max_age_days` | `30` | Only chats active in this window are picked up. |
| `cc_entrypoints` | `["cli"]` | Claude sessions to include (skips `claude -p` automation runs). |
| `path_remap` | `{"C:\\Windows\\System32": "~"}` | Treat chats started in one folder as if they came from another. |
| `max_chars` | `400000` | Budget per mirrored chat, so smaller models can load it. |
| `tool_output_chars` | `1500` | Per tool result, trimmed from the middle. |
| `oc_model` | *latest used* | `provider/model` for OpenCode mirrors. |

Logs go to `~/.hop/hop.log`.

## Honest limits

- **Two agents can't be written to.** Antigravity's conversations are runtime-owned protobuf, and MiniMax Code's store is a migration-managed database. For both, `hop resume` opens a new conversation that reads the transcript first.
- **Mirrors are copies, not a live shared session.** If you continue the same chat in two agents at once, you get a fork, not a merge.
- **Long chats get trimmed.** They start from the latest compaction summary if there is one, then keep the newest messages that fit in `max_chars`.
- **Some agents need a first run.** Gemini CLI mirrors go only into folders Gemini has already opened. Kimi mirrors copy the agent profile from your newest real Kimi session. OpenCode needs the chat's folder to still exist.
- **Codex has one `notify` slot.** If you already use it, hop leaves it alone, and Codex chats sync whenever another agent does.
- **These are private formats.** An agent update can break a reader. Check `~/.hop/hop.log` and open an issue.

## How it compares

| | **SameThread** | [casr](https://github.com/Dicklesworthstone/cross_agent_session_resumer) | [agent-session-resume](https://github.com/hacktivist123/agent-session-resume) |
|---|:---:|:---:|:---:|
| Chat shows up in the target's native `/resume` | ✅ | ✅ | ❌ handoff summary |
| Writes into current OpenCode (1.x) and Kimi Code | ✅ | ❌ | ➖ |
| Automatic sync through hooks | ✅ | ❌ one-shot | ❌ one-shot |
| Round-trips with source tags | ✅ | ❌ | ❌ |
| Number of agents | 9 | 15+ | 6 |

casr covers more agents. Reach for it when you need a one-off conversion to something like Cursor or Aider. SameThread is for people who switch between agents all day and want it to be invisible.

## Roadmap

- [ ] Cursor CLI and Crush adapters
- [ ] `pipx install samethread` from PyPI
- [ ] Native Antigravity and MiniMax writes, if they ship import APIs
- [ ] Optional merge of forks

Adding an agent is one file in [`src/samethread/agents/`](src/samethread/agents/): a lister, a reader and, if the agent allows it, a writer and a hook. PRs welcome.

## Development

```bash
git clone https://github.com/GodrezJr2/samethread && cd samethread
pip install -e .
python -m unittest discover -s tests -v
```

## Star history

<a href="https://star-history.com/#GodrezJr2/samethread&Date">
  <img src="https://api.star-history.com/svg?repos=GodrezJr2/samethread&type=Date" alt="Star history" width="600">
</a>

## License

[MIT](LICENSE)
