# robot-subagent

Natural-language → safe VLA instruction CLI / TUI for WidowX-class arms.

```
ユーザー自然文
  ↓
Robot Command Sub Agent       (this repo)
  - skill 選択 / slot 抽出 / VLA命令文 正規化
  ↓
Safety Gate
  ↓
OpenVLA Server (POST /infer)
  ↓
LeRobot / Trossen Bridge → WidowX
```

The agent only emits a `RobotCommand` JSON matching a registered skill. Joint
angles, free-form code, and multi-step planning are out of scope by design.

---

## Quickstart (clone → run in 3 commands)

Requirements: **Python 3.11+** (required) · **Node 18+** (optional, Ink UI) ·
**Ollama** (optional, local LLM — alternative is an OpenAI key).

```bash
git clone https://github.com/FORIFOR/robot_subagent.git
cd robot_subagent
./scripts/setup.sh                 # venv + pip + npm + .env from example
ollama pull qwen3:14b              # if using Ollama (default model)
make parse TEXT='キューブをつかんで'   # smoke test through the full agent
```

Then pick a UI:

```bash
make ui     # Textual TUI (Python, in-process)
make ink    # Ink TUI (Node + React)
```

### Configuring the LLM backend

Edit `.env` (created from `.env.example` on first setup):

```env
# Local Ollama (default)
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
ROBOT_AGENT_MODEL=qwen3:14b

# Or hosted OpenAI
# OPENAI_API_KEY=sk-...
# (leave OPENAI_BASE_URL unset)
# ROBOT_AGENT_MODEL=gpt-4o-mini

# Robot backend
OPENVLA_URL=http://localhost:8000/infer
```

---

## Make shortcuts

```bash
make help                          # list targets
make setup                         # run scripts/setup.sh
make test                          # pytest
make skills                        # list registered skills
make parse TEXT='りんごを取って'      # parse only
make run   TEXT='りんごを取って'      # parse + dry-run print
make ui                            # Textual TUI
make ink                           # Ink TUI
make clean                         # remove .venv / node_modules / caches
```

Each Make target picks up `OPENAI_API_KEY` / `OPENAI_BASE_URL` /
`ROBOT_AGENT_MODEL` from your environment or `.env`.

---

## CLI reference

```
robot-agent skills                     # list (= skills list)
robot-agent skills show <id>           # detail
robot-agent skills add  --id ...       # append a skill
robot-agent skills remove <id>         # remove

robot-agent parse "..."                # parse-only, formatted
robot-agent run "..."                  # parse + dry-run
robot-agent run "..." --execute        # send to OpenVLA (confirms)
robot-agent run "..." --execute --yes  # send to OpenVLA (no prompt)

robot-agent ui                         # Textual TUI

robot-agent parse-json   "..."         # JSON-only output (for Ink/Node)
robot-agent skills-json                # JSON registry dump
robot-agent execute-json "..."         # parse + safety + OpenVLA (JSON)
```

Ink TUI is launched via `npm run ui` (or `make ink`). It calls the JSON CLIs
above as a child process.

---

## Layout

```
robot_subagent/
  pyproject.toml
  Makefile
  scripts/
    setup.sh
  .env.example
  config/
    skill_registry.yaml          # whitelist of skills
  robot_agent/                   # Python package
    cli.py                       # Typer + Rich
    tui.py                       # Textual TUI
    agent.py                     # OpenAI Agents SDK + Ollama-compatible
    schemas.py                   # Pydantic: Skill, RobotCommand, SafetyResult
    skills.py                    # YAML loader + add/remove helpers
    safety.py                    # safe / needs_confirmation / blocked
    openvla_client.py            # POST $OPENVLA_URL
    prompts.py                   # system prompt
  src/ink/                       # Ink + React UI
    index.tsx app.tsx types.ts pythonBridge.ts
    components/
      SkillList.tsx ChatLog.tsx CommandInput.tsx StatusBar.tsx
  package.json tsconfig.json
  tests/test_smoke.py
```

---

## Design rules

- The agent's only output is a `RobotCommand` matching a registered skill.
- Every command runs through `safety_check` before any network call.
- `--dry-run` is the default. `--execute` is opt-in and prompts unless `--yes`.
- Adding a new task = appending to `skill_registry.yaml`. No code change.
- Non-robot input (chitchat, unknown verbs) is normalized to
  `skill_id="unknown"` / `vla_instruction="NOOP"` and blocked by safety.
- `/`-prefixed input in either TUI is a UI command, never sent to the LLM.

---

## Troubleshooting

- **`fatal: not a git repository`** — you cloned from somewhere else;
  `git init && git remote add origin ...` first.
- **`OpenAIError: Missing credentials`** — `.env` is missing or
  `OPENAI_API_KEY` is unset. For Ollama set it to literally `ollama`.
- **`Tracing client error 401`** — harmless; we already disable tracing when
  `OPENAI_BASE_URL` is set, but if you see this, your env didn't load.
- **Ink: `Raw mode is not supported`** — you're running in a non-TTY (CI, pipe).
  Run from a real terminal.
- **Ollama model not found** — `ollama pull <model>`. Default is `qwen3:14b`;
  smaller alternatives that are decent at JSON output: `llama3.1:8b`,
  `gemma3:12b`.

---

## Roadmap

1. ✅ MVP: parse / run / chat / ui / Ink TUI / skills CRUD / safety gate.
2. Per-skill `executor` field (`lerobot_record_act` etc.) and dispatch.
3. RealSense image + `robot_state` in the OpenVLA payload.
4. JSONL logging of `(utterance, command, verdict, vla_response)` under `logs/`.
5. LangGraph promotion when state / human-in-the-loop demands it.
