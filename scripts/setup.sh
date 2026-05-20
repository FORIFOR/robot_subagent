#!/usr/bin/env bash
# Robot sub-agent setup. Idempotent — safe to re-run.
#
#   ./scripts/setup.sh          # full setup
#   ./scripts/setup.sh --no-node # skip Ink UI (Node) install
#
# Requirements:
#   - python3 >= 3.11   (required)
#   - node    >= 18     (optional; Ink TUI)
#   - ollama            (optional; local LLM)

set -euo pipefail

cd "$(dirname "$0")/.."

SKIP_NODE=0
for arg in "$@"; do
    case "$arg" in
        --no-node) SKIP_NODE=1 ;;
        -h|--help)
            sed -n '2,12p' "$0"
            exit 0
            ;;
    esac
done

say()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
ok()   { printf '  \033[1;32mok\033[0m  %s\n' "$*"; }
warn() { printf '  \033[1;33mwarn\033[0m  %s\n' "$*"; }
err()  { printf '  \033[1;31merror\033[0m %s\n' "$*" >&2; }

# --- Python -----------------------------------------------------------------

say "Checking Python"
if ! command -v python3 >/dev/null; then
    err "python3 not found. Install Python 3.11+ first."
    exit 1
fi
PY_VER=$(python3 -c 'import sys; print("{}.{}".format(*sys.version_info))')
PY_MAJOR=${PY_VER%%.*}
PY_MINOR=${PY_VER##*.}
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
    err "Python 3.11+ required, found $PY_VER"
    exit 1
fi
ok "python3 $PY_VER"

if [ ! -d .venv ]; then
    say "Creating .venv"
    python3 -m venv .venv
fi

say "Installing Python deps (editable)"
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e .
ok ".venv/bin/robot-agent ready"

# --- .env -------------------------------------------------------------------

if [ ! -f .env ]; then
    cp .env.example .env
    say "Created .env from .env.example"
    warn "Edit .env to set OPENAI_API_KEY / OPENAI_BASE_URL / ROBOT_AGENT_MODEL / OPENVLA_URL"
else
    ok ".env already exists"
fi

# --- Node (optional) --------------------------------------------------------

if [ "$SKIP_NODE" -eq 1 ]; then
    say "Skipping Node (--no-node)"
elif command -v npm >/dev/null; then
    say "Installing Node deps for Ink UI"
    npm install --silent
    ok "Ink UI ready: npm run ui"
else
    warn "node/npm not found. To use the Ink UI: install Node 18+ then run 'npm install'."
fi

# --- Ollama check (optional) ------------------------------------------------

say "Checking Ollama"
if command -v ollama >/dev/null; then
    if curl -s --max-time 2 http://localhost:11434/api/tags >/dev/null 2>&1; then
        ok "Ollama server reachable at http://localhost:11434"
        MODEL=$(grep -E '^ROBOT_AGENT_MODEL=' .env 2>/dev/null | cut -d= -f2- | tr -d '[:space:]' || true)
        MODEL=${MODEL:-qwen3:14b}
        if curl -s http://localhost:11434/api/tags | grep -q "\"$MODEL\""; then
            ok "Model '$MODEL' already pulled"
        else
            warn "Model '$MODEL' not pulled yet. Run: ollama pull $MODEL"
        fi
    else
        warn "Ollama installed but server not responding. Start it with: ollama serve"
    fi
else
    warn "Ollama not installed. To use a local LLM: https://ollama.com, or set OPENAI_API_KEY in .env."
fi

# --- Done -------------------------------------------------------------------

cat <<'EOF'

==> Setup complete. Try:

  # Show registered skills
  .venv/bin/robot-agent skills

  # Parse a Japanese utterance
  .venv/bin/robot-agent parse "キューブをつかんで"

  # Textual TUI (in-process)
  .venv/bin/robot-agent ui

  # Ink TUI (Node)
  npm run ui

  # Make shortcuts
  make parse TEXT='キューブをつかんで'
  make ui     # Textual
  make ink    # Ink
  make test
EOF
