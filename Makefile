.PHONY: setup test skills parse run ui ink clean help

# Default LLM env. Override by exporting these or putting them in .env.
OPENAI_API_KEY ?= ollama
OPENAI_BASE_URL ?= http://localhost:11434/v1
ROBOT_AGENT_MODEL ?= qwen3:14b
TEXT ?= キューブをつかんで

help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk -F ':.*?## ' '{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup:  ## Run scripts/setup.sh (venv + pip + npm + .env)
	./scripts/setup.sh

test:  ## Run the Python test suite
	.venv/bin/python -m pytest tests/ -q

skills:  ## List registered skills
	.venv/bin/robot-agent skills

parse:  ## Parse one utterance.  Override with:  make parse TEXT='...'
	OPENAI_API_KEY=$(OPENAI_API_KEY) OPENAI_BASE_URL=$(OPENAI_BASE_URL) ROBOT_AGENT_MODEL=$(ROBOT_AGENT_MODEL) \
	    .venv/bin/robot-agent parse "$(TEXT)"

run:  ## Parse + dry-run (no execute). Override TEXT=...
	OPENAI_API_KEY=$(OPENAI_API_KEY) OPENAI_BASE_URL=$(OPENAI_BASE_URL) ROBOT_AGENT_MODEL=$(ROBOT_AGENT_MODEL) \
	    .venv/bin/robot-agent run "$(TEXT)"

ui:  ## Launch the Textual TUI
	OPENAI_API_KEY=$(OPENAI_API_KEY) OPENAI_BASE_URL=$(OPENAI_BASE_URL) ROBOT_AGENT_MODEL=$(ROBOT_AGENT_MODEL) \
	    .venv/bin/robot-agent ui

ink:  ## Launch the Ink (Node) TUI
	OPENAI_API_KEY=$(OPENAI_API_KEY) OPENAI_BASE_URL=$(OPENAI_BASE_URL) ROBOT_AGENT_MODEL=$(ROBOT_AGENT_MODEL) \
	    npm run ui

clean:  ## Remove venv, node_modules, caches
	rm -rf .venv node_modules .pytest_cache .ruff_cache robot_subagent.egg-info \
	       robot_agent/__pycache__ tests/__pycache__
