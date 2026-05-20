# robot-subagent

Natural-language → safe VLA instruction CLI for WidowX-class arms driven by
OpenVLA / LeRobot.

```
ユーザー自然文
  ↓
Robot Command Sub Agent       (this repo)
  - skill 選択 / slot 抽出 / VLA命令文 正規化
  ↓
Safety Gate
  ↓
OpenVLA Server  (POST /infer)
  ↓
LeRobot / Trossen Bridge
  ↓
WidowX 実機
```

The sub-agent is intentionally narrow: it only emits a `RobotCommand` JSON
matching a registered skill. Joint angles, free-form code, and multi-step
planning are out of scope by design.

## Stack

- **CLI**: Typer + Rich
- **Agent**: OpenAI Agents SDK (`Agent` + `Runner.run_sync` + `output_type=RobotCommand`)
- **Schema**: Pydantic v2
- **Skills**: YAML (`config/skill_registry.yaml`) loaded with `yaml.safe_load`
- **Execution**: OpenVLA HTTP server → LeRobot / Trossen bridge

## Quickstart

```bash
cd robot_subagent
python -m venv .venv && source .venv/bin/activate
pip install -e .

cp .env.example .env   # set OPENAI_API_KEY and OPENVLA_URL

# show registered skills
robot-agent skills

# parse only (no network calls)
robot-agent parse "赤いキューブをつかんで"

# dry-run (no --execute → never sends to OpenVLA)
robot-agent run "赤いキューブをつかんで"

# actually send to OpenVLA
robot-agent run "赤いキューブをつかんで" --execute
robot-agent run "赤いキューブをつかんで" --execute --yes   # skip confirm

# interactive
robot-agent chat
robot-agent chat --execute
```

## Layout

```
robot-subagent/
  pyproject.toml
  .env.example
  README.md
  robot_agent/
    __init__.py
    cli.py              # Typer + Rich
    agent.py            # OpenAI Agents SDK
    schemas.py          # Pydantic
    skills.py           # YAML loader
    safety.py           # safe / needs_confirmation / blocked
    openvla_client.py   # POST /infer
    prompts.py
  config/
    skill_registry.yaml
  logs/
  tests/
```

## Design rules

- The Agent's `output_type` is `RobotCommand` — it cannot return anything else.
- Every command runs through `safety_check` before any network call.
- `--dry-run` is the default. `--execute` is opt-in and prompts unless `--yes`.
- Adding a new task = adding an entry to `skill_registry.yaml`. No code change.

## Roadmap

1. ✅ MVP: parse / run / chat / skills + safety gate.
2. Stream RealSense image + `robot_state` into the OpenVLA payload.
3. Persist (utterance, command, verdict, vla_response) as JSONL under `logs/`.
4. Add per-skill workspace bounds + max-step caps.
5. Promote orchestration to LangGraph only if state / human-in-the-loop demands it.
