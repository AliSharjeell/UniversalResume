<h1 align="center">Universal Resume</h1>

<p align="center">
Type <code>resume</code> in any terminal. See all your coding conversations across agents. Pick any chat, choose which agent you want to resume it with, and keep coding without missing a beat—even when an agent hits its usage limit.
</p>

<p align="center">
Built with <a href="https://github.com/anomalyco/opentui">OpenTUI</a>.
</p>

<p align="center">
  <img src="assets/1-hit-usage-limit.png" alt="Hit agent usage limit" width="100%" />
</p>

<p align="center">
  <img src="assets/2-universal-resume-tui.png" alt="Universal Resume TUI" width="100%" />
</p>

<p align="center">
  <img src="assets/3-pick-agent.png" alt="Choose agent to resume with" width="100%" />
</p>

<p align="center">
  <img src="assets/4-resumed-conversation.png" alt="Continue coding in another agent" width="100%" />
</p>

---

## Quick Install (One-Liner)

### Windows (PowerShell)
```powershell
irm https://raw.githubusercontent.com/AliSharjeell/UniversalResume/main/install.ps1 | iex
```

### macOS & Linux (Terminal)
```bash
curl -fsSL https://raw.githubusercontent.com/AliSharjeell/UniversalResume/main/install.sh | bash
```

Once installed, just write:
```bash
resume
```

---

## Why Universal Resume?

- **Hit rate limits on Claude?** Instantly switch to **Codex**, **OpenCode**, or **Antigravity**.
- **Started in Codex?** Hop into **Claude Code** or **Gemini CLI** with full history and context preserved.
- **Zero copy-pasting:** Every conversation across 9 coding agents is automatically tracked and mirrored into each agent's native format.
- **Run anywhere:** Works in any directory, terminal, or shell on Windows, macOS, and Linux.

---

## Supported Agents

| Coding Agent | CLI Command | Resume Mode |
|---|---|---|
| **Claude Code** | `claude` | Native session resume |
| **Codex CLI** | `codex` | Native session resume |
| **Antigravity CLI** | `agy` | Seeded continuous handoff |
| **OpenCode** | `opencode` | Native session resume |
| **Gemini CLI** | `gemini` | Native session resume |
| **MiniMax Code** | `minimax` | Seeded continuous handoff |
| **Qwen Code** | `qwen` | Native session resume |
| **Pi Agent** | `pi` | Native session resume |
| **Kimi Code** | `kimi` | Native session resume |

---

## TUI Features & Keybindings

- **Auto-Sync on Start:** Every time you open `resume`, it automatically pulls fresh turns from all installed coding agents in the background.
- **Manual Sync Button:** Click `[Sync (S)]` or press `s` / `Ctrl+S` anytime to re-sync active sessions on the fly.
- **Instant Search:** Start typing anywhere to filter chats by title, recent agent, or project folder.
- **Scope Toggle (Tab):** Press `Tab` to switch between chats for the current folder and all projects across your machine.
- **Live Inspector:** Inspect participant agents, turn metrics, active mirror statuses, and transcript snippets before launching.

| Key | Action |
|---|---|
| `↑` / `↓` | Navigate conversation list |
| `Enter` | Choose conversation & open Agent Picker |
| `1`–`9` | Quick-launch agent immediately |
| `Tab` | Toggle between Current Folder & All Projects |
| `s` or `Ctrl+S` | Trigger manual session sync |
| `[Sync]` | Click with mouse to sync |
| Type text | Live fuzzy / substring filter |
| `Backspace` | Erase search character / Back |
| `Esc` | Clear search / Back / Exit |

---

## License

MIT © [Ali Sharjeel](https://github.com/AliSharjeell)
