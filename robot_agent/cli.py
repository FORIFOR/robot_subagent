"""Typer + Rich CLI entry point."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .agent import normalize_command
from .openvla_client import send_to_openvla
from .safety import safety_check
from .schemas import RobotCommand, Skill
from .skills import (
    DEFAULT_SKILL_PATH,
    add_skill,
    find_skill,
    load_skill_registry,
    remove_skill,
    save_skill_registry,
)

load_dotenv()

app = typer.Typer(help="Robot Sub Agent CLI", add_completion=False)
skills_app = typer.Typer(help="Manage the skill registry.", invoke_without_command=True)
app.add_typer(skills_app, name="skills")
console = Console()


def _print_command(command: RobotCommand) -> None:
    table = Table(title="RobotCommand", show_lines=False)
    table.add_column("field", style="bold")
    table.add_column("value")
    for key, value in command.model_dump().items():
        table.add_row(key, str(value))
    console.print(table)


def _parse_and_check(text: str) -> tuple[RobotCommand, object]:
    command = normalize_command(text)
    registry = load_skill_registry()
    safety = safety_check(command, registry)
    return command, safety


# ---------------------------------------------------------------------------
# parse / run / chat
# ---------------------------------------------------------------------------


@app.command()
def parse(text: str = typer.Argument(..., help="Natural language robot command")) -> None:
    """Parse natural language into a RobotCommand (no execution)."""
    command, safety = _parse_and_check(text)
    _print_command(command)
    console.print(Panel(safety.model_dump_json(indent=2), title="Safety"))


@app.command()
def run(
    text: str = typer.Argument(..., help="Natural language robot command"),
    execute: bool = typer.Option(False, "--execute", help="Send command to OpenVLA"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Parse and optionally execute."""
    command, safety = _parse_and_check(text)
    _print_command(command)
    console.print(Panel(safety.model_dump_json(indent=2), title="Safety"))

    if not safety.ok:
        console.print("[red]Blocked. Command was not sent to OpenVLA.[/red]")
        raise typer.Exit(code=1)

    if not execute:
        console.print("[yellow]Dry-run only. Add --execute to send to OpenVLA.[/yellow]")
        return

    if safety.level != "safe" and not yes:
        approved = typer.confirm("実機に送信しますか？", default=False)
        if not approved:
            console.print("[yellow]Cancelled.[/yellow]")
            return

    result = send_to_openvla(command)
    console.print(Panel(result.model_dump_json(indent=2), title="OpenVLA Result"))


# ---------------------------------------------------------------------------
# JSON commands (for Ink/Node TUI and other external consumers)
# ---------------------------------------------------------------------------


def _skill_to_json(skill: Skill | None) -> dict | None:
    """Public-shape JSON for one skill. Includes executor stubs for forward compat."""
    if skill is None:
        return None
    return {
        "id": skill.id,
        "description": skill.description,
        "aliases": list(skill.aliases),
        "template": skill.vla_template,
        "template_with_color": skill.vla_template_with_color,
        "allowed_objects": list(skill.allowed_objects),
        "allowed_colors": list(skill.allowed_colors),
        "object_required": skill.object_required,
        "color_required": skill.color_required,
        # Executor stubs — populated when a `lerobot_record_act` adapter ships.
        "executor_type": None,
        "single_task": None,
        "policy_path": None,
    }


@app.command("parse-json")
def parse_json(text: str = typer.Argument(..., help="Natural language robot command")) -> None:
    """Parse a command and emit a single JSON object on stdout (for Ink UI)."""
    command = normalize_command(text)
    registry = load_skill_registry()
    safety = safety_check(command, registry)
    skill = find_skill(registry, command.skill_id)

    payload = {
        "ok": safety.ok,
        "command": command.model_dump(),
        "safety": safety.model_dump(),
        "skill": _skill_to_json(skill),
        "shell_command": None,  # filled in once an executor abstraction lands
    }
    typer.echo(json.dumps(payload, ensure_ascii=False))


@app.command("skills-json")
def skills_json() -> None:
    """Emit the full skill registry as JSON on stdout."""
    registry = load_skill_registry()
    payload = {"skills": [_skill_to_json(s) for s in registry.skills]}
    typer.echo(json.dumps(payload, ensure_ascii=False))


@app.command("execute-json")
def execute_json(
    text: str = typer.Argument(..., help="Natural language robot command"),
) -> None:
    """Parse, safety-check, send to OpenVLA, and emit a single JSON object on stdout.

    Currently the executor is the OpenVLA HTTP client. When a `lerobot_record_act`
    adapter is wired in, dispatch by skill.executor.type here.
    """
    command = normalize_command(text)
    registry = load_skill_registry()
    safety = safety_check(command, registry)

    if not safety.ok:
        typer.echo(
            json.dumps(
                {
                    "ok": False,
                    "error": safety.reason,
                    "safety": safety.model_dump(),
                    "command": command.model_dump(),
                },
                ensure_ascii=False,
            )
        )
        raise typer.Exit(code=1)

    result = send_to_openvla(command)
    typer.echo(
        json.dumps(
            {
                "ok": result.ok,
                "result": result.model_dump(),
                "safety": safety.model_dump(),
                "command": command.model_dump(),
            },
            ensure_ascii=False,
        )
    )


@app.command("ollama-models-json")
def ollama_models_json() -> None:
    """List models pulled into the local Ollama and emit JSON on stdout."""
    from .ollama_test_client import list_ollama_models

    try:
        models = list_ollama_models()
        typer.echo(json.dumps({"ok": True, "models": models}, ensure_ascii=False))
    except Exception as e:
        typer.echo(
            json.dumps({"ok": False, "models": [], "error": str(e)}, ensure_ascii=False)
        )
        raise typer.Exit(code=1)


@app.command("llm-chat-json")
def llm_chat_json(
    text: str = typer.Argument(..., help="User message"),
    model: str = typer.Option("qwen3:14b", "--model", help="Ollama model id"),
    temperature: float = typer.Option(0.2, "--temperature"),
) -> None:
    """Send one chat to Ollama and emit timing + system metrics as JSON."""
    from .ollama_test_client import chat_with_ollama_measured

    system = (
        "あなたは日本語で自然に回答するアシスタントです。"
        "短く、明確に、日本語で答えてください。"
    )
    result = chat_with_ollama_measured(
        prompt=text,
        model=model,
        system=system,
        temperature=temperature,
    )
    typer.echo(json.dumps(result.to_dict(), ensure_ascii=False))


@app.command()
def ui(
    execute: bool = typer.Option(False, "--execute", help="Start in execute mode"),
) -> None:
    """Launch the Textual TUI."""
    from .tui import RobotAgentApp

    RobotAgentApp(execute=execute).run()


@app.command()
def chat(
    execute: bool = typer.Option(False, "--execute", help="Send accepted commands to OpenVLA"),
) -> None:
    """Interactive Claude Code-like REPL."""
    console.print(Panel("Robot Sub Agent started. Type 'exit' to quit.", title="robot-agent"))
    while True:
        try:
            text = typer.prompt("robot")
        except (EOFError, KeyboardInterrupt):
            console.print()
            return
        if text.strip().lower() in {"exit", "quit", "q"}:
            return
        try:
            command, safety = _parse_and_check(text)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            continue

        _print_command(command)
        console.print(Panel(safety.model_dump_json(indent=2), title="Safety"))

        if not safety.ok:
            console.print("[red]Blocked.[/red]")
            continue

        if not execute:
            console.print("[yellow]Dry-run. Use --execute to send.[/yellow]")
            continue

        approved = typer.confirm("実機に送信しますか？", default=False)
        if not approved:
            console.print("[yellow]Cancelled.[/yellow]")
            continue
        result = send_to_openvla(command)
        console.print(Panel(result.model_dump_json(indent=2), title="OpenVLA Result"))


# ---------------------------------------------------------------------------
# skills list / show / add / remove
# ---------------------------------------------------------------------------


def _render_skill_table(skills: list[Skill]) -> Table:
    table = Table(title="Skill Registry")
    table.add_column("id", style="bold")
    table.add_column("description")
    table.add_column("color_req", justify="center")
    table.add_column("objects")
    table.add_column("colors")
    table.add_column("template")
    for s in skills:
        table.add_row(
            s.id,
            s.description,
            "y" if s.color_required else "-",
            ", ".join(s.allowed_objects),
            ", ".join(s.allowed_colors),
            s.vla_template,
        )
    return table


@skills_app.callback(invoke_without_command=True)
def skills_default(ctx: typer.Context) -> None:
    """Default action: `robot-agent skills` lists all skills."""
    if ctx.invoked_subcommand is None:
        registry = load_skill_registry()
        console.print(_render_skill_table(registry.skills))


@skills_app.command("list")
def skills_list() -> None:
    """List all registered skills."""
    registry = load_skill_registry()
    console.print(_render_skill_table(registry.skills))


@skills_app.command("show")
def skills_show(
    skill_id: str = typer.Argument(..., help="Skill id to display"),
) -> None:
    """Show every field of a single skill."""
    registry = load_skill_registry()
    skill = find_skill(registry, skill_id)
    if skill is None:
        console.print(f"[red]skill_id '{skill_id}' not found[/red]")
        raise typer.Exit(code=1)

    table = Table(title=f"Skill: {skill.id}", show_header=False)
    table.add_column("field", style="bold")
    table.add_column("value")
    for k, v in skill.model_dump().items():
        table.add_row(k, str(v))
    console.print(table)


@skills_app.command("add")
def skills_add(
    skill_id: str = typer.Option(..., "--id", help="Unique skill id, e.g. move_to_home"),
    description: str = typer.Option(..., "--description", help="Short description"),
    vla_template: str = typer.Option(..., "--vla-template", help='e.g. "Pick the apple"'),
    vla_template_with_color: str | None = typer.Option(
        None, "--with-color", help='Colored variant, e.g. "Pick the {color} apple"'
    ),
    objects: list[str] = typer.Option(
        [], "--object", help="Allowed object (repeatable). Omit for object-less skills."
    ),
    colors: list[str] = typer.Option(
        [], "--color", help="Allowed color (repeatable)."
    ),
    color_required: bool = typer.Option(
        False, "--color-required/--color-optional", help="Whether color is required."
    ),
    no_object_required: bool = typer.Option(
        False, "--no-object-required", help="Skill does not take an object (e.g. move_to_home)."
    ),
    path: Path = typer.Option(DEFAULT_SKILL_PATH, "--path", help="Registry YAML to edit."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print resulting YAML and don't save."),
) -> None:
    """Append a new skill to skill_registry.yaml.

    Examples and complex per-skill metadata still belong in YAML — this command
    only writes the core fields. Edit the file afterward to add examples.
    """
    new_skill = Skill(
        id=skill_id,
        description=description,
        object_required=not no_object_required,
        color_required=color_required,
        vla_template=vla_template,
        vla_template_with_color=vla_template_with_color,
        allowed_objects=list(objects),
        allowed_colors=list(colors),
    )

    registry = load_skill_registry(path)
    try:
        updated = add_skill(registry, new_skill)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)

    if dry_run:
        console.print("[yellow]--dry-run: not saving.[/yellow]")
        console.print(_render_skill_table(updated.skills))
        return

    save_skill_registry(updated, path)
    console.print(f"[green]added[/green] [bold]{new_skill.id}[/bold] -> {path}")
    console.print(_render_skill_table(updated.skills))


@skills_app.command("remove")
def skills_remove(
    skill_id: str = typer.Argument(..., help="Skill id to remove"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    path: Path = typer.Option(DEFAULT_SKILL_PATH, "--path", help="Registry YAML to edit."),
) -> None:
    """Remove a skill by id."""
    registry = load_skill_registry(path)
    if find_skill(registry, skill_id) is None:
        console.print(f"[red]skill_id '{skill_id}' not found[/red]")
        raise typer.Exit(code=1)

    if not yes:
        approved = typer.confirm(f"'{skill_id}' を削除しますか？", default=False)
        if not approved:
            console.print("[yellow]Cancelled.[/yellow]")
            return

    updated = remove_skill(registry, skill_id)
    save_skill_registry(updated, path)
    console.print(f"[green]removed[/green] [bold]{skill_id}[/bold] -> {path}")
    console.print(_render_skill_table(updated.skills))


def main() -> None:  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
