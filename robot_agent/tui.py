"""Textual TUI: Claude Code-like terminal UI for the robot sub-agent.

Layout:
    +----------------+----------------------------+
    | Skills (left)  | Conversation log (right)   |
    |                |                            |
    |                +----------------------------+
    |                | Input box                  |
    +----------------+----------------------------+

Slash commands:
    /run     execute the last parsed command (only when execute mode is ON)
    /mode    toggle dry-run <-> execute
    /skills  reload skill_registry.yaml and redraw the left panel
    /clear   clear the log
    /help    show available slash commands
    /quit    exit (Ctrl+C also works)

Keybindings:
    F5       refresh skills
    F9       toggle execute mode
    Ctrl+L   clear log
    Ctrl+C   quit
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from rich.panel import Panel
from rich.table import Table
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, RichLog

from .agent import normalize_command
from .openvla_client import send_to_openvla
from .safety import safety_check
from .schemas import RobotCommand, SkillRegistry
from .skills import load_skill_registry


@dataclass
class UiConfig:
    execute: bool = False


class RobotAgentApp(App):
    CSS = """
    Screen { layout: vertical; }
    #main { height: 1fr; }
    #skills_panel { width: 40; border: solid $primary; padding: 0 1; }
    #right { width: 1fr; }
    #log { height: 1fr; border: solid $secondary; padding: 0 1; }
    #input { height: 3; border: solid $accent; }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear_log", "Clear"),
        Binding("f5", "refresh_skills", "Refresh"),
        Binding("f9", "toggle_execute", "Toggle exec"),
    ]

    def __init__(self, execute: bool = False) -> None:
        super().__init__()
        self.config = UiConfig(execute=execute)
        self.registry: Optional[SkillRegistry] = None
        self.skills_view: Optional[RichLog] = None
        self.log_view: Optional[RichLog] = None
        self.input: Optional[Input] = None
        self.last_command: Optional[RobotCommand] = None

    # -- composition --------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main"):
            self.skills_view = RichLog(id="skills_panel", markup=True, wrap=True)
            yield self.skills_view
            with Vertical(id="right"):
                self.log_view = RichLog(id="log", markup=True, wrap=True)
                yield self.log_view
                self.input = Input(
                    placeholder=(
                        "ロボット命令を入力。/help でコマンド一覧、/run で直前を実行"
                    ),
                    id="input",
                )
                yield self.input
        yield Footer()

    def on_mount(self) -> None:
        self.load_and_render_skills()
        self._write_system_message()
        if self.input:
            self.input.focus()

    # -- rendering helpers --------------------------------------------------

    def _mode_text(self) -> str:
        return "EXECUTE" if self.config.execute else "DRY-RUN"

    def _write_system_message(self) -> None:
        if not self.log_view:
            return
        self.log_view.write(
            Panel(
                f"Robot Agent UI started\nmode={self._mode_text()}\n"
                "Enter: parse / /run: execute last / /mode: toggle / /help: commands",
                title="System",
            )
        )

    def load_and_render_skills(self) -> None:
        self.registry = load_skill_registry()
        if not self.skills_view:
            return
        self.skills_view.clear()

        table = Table(show_header=True, header_style="bold")
        table.add_column("skill")
        table.add_column("template")
        table.add_column("color", justify="center")
        for s in self.registry.skills:
            table.add_row(s.id, s.vla_template, "req" if s.color_required else "opt")
        self.skills_view.write(table)

        self.skills_view.write("")
        self.skills_view.write("[bold]Examples[/bold]")
        for s in self.registry.skills:
            if s.examples:
                self.skills_view.write(f"[cyan]{s.id}[/cyan]")
                for ex in s.examples[:3]:
                    user = ex.get("user", "")
                    self.skills_view.write(f"  - {user}")

        self.skills_view.write("")
        self.skills_view.write("[bold]Mode[/bold]")
        self.skills_view.write(
            "[red]EXECUTE[/red]" if self.config.execute else "[yellow]DRY-RUN[/yellow]"
        )

    def _write_help(self) -> None:
        if not self.log_view:
            return
        self.log_view.write(
            Panel(
                "/run     直前に生成されたコマンドを実行 (executeモードのみ)\n"
                "/mode    dry-run <-> execute 切替\n"
                "/skills  skill_registry.yaml を再読込\n"
                "/clear   ログクリア\n"
                "/help    このヘルプ\n"
                "/quit    終了\n"
                "F5 / F9 / Ctrl+L もキー操作で同じことができます。",
                title="Help",
            )
        )

    # -- input dispatch -----------------------------------------------------

    _EXIT_PHRASES = {
        "exit", "quit", "q",
        "終了", "おわり", "終わり", "ばいばい", "バイバイ", "さようなら",
    }

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        if self.input:
            self.input.value = ""

        # Anything starting with '/' is a UI command — never forward to the LLM.
        if text.startswith("/"):
            self._handle_slash_command(text)
            return

        if text.lower() in self._EXIT_PHRASES or text in self._EXIT_PHRASES:
            self.exit()
            return

        asyncio.create_task(self._parse_command(text))

    def _handle_slash_command(self, text: str) -> None:
        if not self.log_view:
            return

        head = text.split()[0].lower()
        if head in {"/quit", "/exit"}:
            self.exit()
            return
        if head == "/skills":
            self.action_refresh_skills()
            return
        if head in {"/mode", "/toggle", "/execute"}:
            self.action_toggle_execute()
            return
        if head == "/clear":
            self.action_clear_log()
            return
        if head in {"/help", "/?"}:
            self._write_help()
            return
        if head == "/run":
            asyncio.create_task(self._execute_last())
            return

        self.log_view.write(
            Panel(
                f"Unknown command: {text}\n\n"
                "使えるコマンド:\n"
                "/run     直前に生成されたコマンドを実行\n"
                "/mode    dry-run / execute 切替\n"
                "/skills  skill_registry.yaml を再読込\n"
                "/clear   ログクリア\n"
                "/help    ヘルプ表示\n"
                "/quit    終了",
                title="Command Error",
            )
        )

    # -- workers ------------------------------------------------------------

    async def _parse_command(self, text: str) -> None:
        if not self.log_view:
            return
        self.log_view.write(Panel(text, title="user"))
        try:
            # normalize_command is blocking (LLM round-trip); run off-loop.
            command = await asyncio.to_thread(normalize_command, text)
            if self.registry is None:
                self.registry = load_skill_registry()
            safety = safety_check(command, self.registry)

            table = Table(title="RobotCommand")
            table.add_column("field", style="bold")
            table.add_column("value")
            for k, v in command.model_dump().items():
                table.add_row(k, str(v))
            self.log_view.write(table)
            self.log_view.write(Panel(safety.model_dump_json(indent=2), title="Safety"))

            if not safety.ok:
                self.log_view.write("[red]Blocked. /run できません。[/red]")
                self.last_command = None
                return

            self.last_command = command
            if self.config.execute:
                self.log_view.write(
                    "[yellow]Command prepared. /run で実行。[/yellow]"
                )
            else:
                self.log_view.write(
                    "[yellow]Dry-run. /mode (or F9) で実行モードへ切替後、/run。[/yellow]"
                )
        except Exception as e:
            self.log_view.write(f"[red]Error:[/red] {e}")

    async def _execute_last(self) -> None:
        if not self.log_view:
            return
        if self.last_command is None:
            self.log_view.write(
                "[yellow]直前のコマンドがありません。まず自然文を入力してください。[/yellow]"
            )
            return
        if self.registry is None:
            self.registry = load_skill_registry()
        safety = safety_check(self.last_command, self.registry)
        if not safety.ok:
            self.log_view.write("[red]Last command is blocked. Not executing.[/red]")
            return
        if not self.config.execute:
            self.log_view.write(
                "[yellow]Execute mode OFF. /mode で切替してください。[/yellow]"
            )
            return

        self.log_view.write("[red]Sending to OpenVLA...[/red]")
        try:
            result = await asyncio.to_thread(send_to_openvla, self.last_command)
            self.log_view.write(
                Panel(result.model_dump_json(indent=2), title="OpenVLA Result")
            )
        except Exception as e:
            self.log_view.write(f"[red]Execution error:[/red] {e}")

    # -- actions ------------------------------------------------------------

    def action_clear_log(self) -> None:
        if self.log_view:
            self.log_view.clear()
            self._write_system_message()

    def action_refresh_skills(self) -> None:
        self.load_and_render_skills()
        if self.log_view:
            self.log_view.write("[green]Skills refreshed.[/green]")

    def action_toggle_execute(self) -> None:
        self.config.execute = not self.config.execute
        self.load_and_render_skills()
        if self.log_view:
            self.log_view.write(f"[bold]Mode:[/bold] {self._mode_text()}")
