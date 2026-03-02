"""Textual application screens and CLI entry points for uv-init-tui."""

from __future__ import annotations

import shutil
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from shlex import join as shlex_join, quote as shlex_quote

import typer
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.message import Message
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    SelectionList,
    Static,
    Switch,
)

from .config import AppConfig, CONFIG_PATH, load_config, save_config
from .pyproject_edit import set_project_scripts
from .uv_cmd import UVError, build_uv_add_cmd, build_uv_init_cmd, uv_add, uv_init


@dataclass(frozen=True)
class InitPlan:
    """
    Collected user choices for creating a project.

    This gets passed from the wizard screen to the run screen so the run screen
    can operate without needing to query UI widgets again.
    """

    target_dir: Path
    name: str
    description: str
    is_lib: bool
    python_version: str
    deps: list[str]
    scripts: dict[str, str]
    overwrite: bool


DEFAULT_PROJECTS_DIR = Path.home() / "dev" / "py"
PROJECT_NAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$")


def _slugify_project_name(name: str) -> str:
    """Convert arbitrary input into a normalized project-name slug."""
    slug = name.strip().lower()
    slug = re.sub(r"[^a-z0-9._-]+", "-", slug)
    slug = re.sub(r"[-_.]+", "-", slug)
    return slug.strip("-")


def _resolve_project_name(name: str) -> str | None:
    """Return a valid project name, using a sluggified fallback when needed."""
    raw = name.strip()
    if PROJECT_NAME_RE.fullmatch(raw):
        return raw

    slug = _slugify_project_name(raw)
    if PROJECT_NAME_RE.fullmatch(slug):
        return slug
    return None


def _format_shell_preview(*, cwd: Path, cmd: Sequence[str]) -> str:
    """
    Render a command as a copy/paste-able shell equivalent.

    Runtime uses `subprocess(..., cwd=...)`; this text mirrors that by prefixing
    the command with `cd <cwd> && ...`.
    """
    return f"cd {shlex_quote(str(cwd))} && {shlex_join(list(cmd))}"


def _build_preview_text(plan: InitPlan) -> str:
    """Build the confirmation text showing exact uv commands to be executed."""
    init_cmd = build_uv_init_cmd(
        name=plan.target_dir.name,
        description=plan.description,
        is_lib=plan.is_lib,
        python_version=plan.python_version,
    )
    project_root = plan.target_dir.resolve()

    lines = ["The following uv commands will run:", ""]
    lines.append(_format_shell_preview(cwd=project_root.parent, cmd=init_cmd))

    if plan.deps:
        add_cmd = build_uv_add_cmd(deps=plan.deps)
        lines.append(_format_shell_preview(cwd=project_root, cmd=add_cmd))
    else:
        lines.append("(No `uv add` command; no dependencies selected.)")

    if plan.scripts:
        lines.extend(
            [
                "",
                f"Non-uv step: update [project.scripts] in {project_root / 'pyproject.toml'}",
            ]
        )
    if plan.overwrite:
        lines.extend(["", f"Non-uv step: remove existing directory first: {project_root}"])

    return "\n".join(lines)


class WizardScreen(Screen):
    """
    Main wizard UI.

    If enable_scripts is True, we expose a small editor for [project.scripts].
    """

    BINDINGS = [
        ("ctrl+s", "start", "Start"),
        ("ctrl+e", "edit_config", "Config"),
        ("escape", "quit", "Quit"),
    ]

    def __init__(self, cfg: AppConfig, *, enable_scripts: bool = False) -> None:
        """Initialize the wizard screen with loaded config and feature flags."""
        super().__init__()
        self.cfg: AppConfig = cfg
        self.enable_scripts: bool = enable_scripts
        self._syncing_name_to_dir: bool = False

        # Holds the scripts user has added in the session.
        # Key = script name, value = "module:callable".
        self._scripts: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        """Build the main form used to collect project initialization inputs."""
        yield Header()

        with ScrollableContainer(id="body"):
            yield Static("uv init TUI", id="title")

            yield Label("Project name:")
            yield Input(placeholder="my-cool-project", id="name")

            yield Label("Target directory:")
            yield Input(value=str(DEFAULT_PROJECTS_DIR), id="dir")

            with Horizontal(id="overwrite_row"):
                yield Label("Directory exists. Overwrite?")
                yield Switch(value=False, id="overwrite")

            yield Label("Description:")
            yield Input(placeholder="A brief description…", id="desc")

            with Horizontal(id="switches"):
                with Vertical(id="library"):
                    yield Label("Library project? (--lib)")
                    yield Switch(value=bool(self.cfg.default_is_lib), id="is_lib")
                with Vertical(id="package"):
                    yield Label("Package project? (--package)")
                    yield Switch(value=bool(self.cfg.default_is_pkg), id="is_pkg")

            yield Label("Python version (--python):")
            yield Input(value=self.cfg.default_python, id="pyver")

            yield Label("Dependencies (picked -> `uv add ...`):")
            deps_sel = SelectionList[str](id="deps")
            default_deps = set(self.cfg.default_dependencies)
            for dep in self.cfg.common_dependencies:
                deps_sel.add_option((dep, dep, dep in default_deps))
            yield deps_sel

            # Optional: scripts editor (enabled by Typer flag --scripts)
            if self.enable_scripts:
                yield Label("Entry scripts ([project.scripts])")
                yield Label('Add mappings like:  mytool  ->  my_pkg.cli:main')

                with Horizontal():
                    yield Input(placeholder="script name (e.g. mytool)", id="script_name")
                    yield Input(placeholder="entry (e.g. my_pkg.cli:main)", id="script_entry")
                    yield Button("Add", id="script_add")

                scripts_table = DataTable(id="scripts_table")
                scripts_table.add_columns("Name", "Entry point")
                yield scripts_table

                with Horizontal():
                    yield Button("Remove selected", id="script_remove")
                    yield Button("Clear", id="script_clear")

            with Horizontal(id="buttons"):
                yield Button("Run (Ctrl+S)", variant="success", id="run")
                yield Button("Config (Ctrl+E)", id="config")
                yield Button("Quit (Esc)", variant="error", id="quit_btn")

            yield Static("", id="status")

        yield Footer()

    def on_mount(self) -> None:
        """Apply post-mount widget setup for optional components."""
        # Small UX tweak: DataTable cursor makes sense as row-based selection.
        if self.enable_scripts:
            self.query_one("#scripts_table", DataTable).cursor_type = "row"

        self.query_one("#overwrite_row", Horizontal).display = False
        self._sync_target_dir_from_name()
        self._refresh_overwrite_state()

    def _project_dir_for_name(self, name: str) -> Path:
        """Map a project name to the default `$HOME/dev/py/{name}` directory."""
        normalized = _resolve_project_name(name) or name.strip()
        return DEFAULT_PROJECTS_DIR / normalized if normalized else DEFAULT_PROJECTS_DIR

    def _sync_target_dir_from_name(self) -> None:
        """Mirror current project name into the target directory input."""
        name = self.query_one("#name", Input).value
        target = self._project_dir_for_name(name)
        self._syncing_name_to_dir = True
        self.query_one("#dir", Input).value = str(target)
        self._syncing_name_to_dir = False

    def _refresh_overwrite_state(self) -> bool:
        """Show/hide overwrite toggle based on whether target directory exists."""
        dir_str = self.query_one("#dir", Input).value.strip()
        target_path = Path(dir_str).expanduser()
        exists = target_path.exists()

        row = self.query_one("#overwrite_row", Horizontal)
        overwrite_switch = self.query_one("#overwrite", Switch)
        name_input = self.query_one("#name", Input)
        dir_input = self.query_one("#dir", Input)
        row.display = exists
        name_input.set_class(exists, "warning-path")
        dir_input.set_class(exists, "warning-path")
        if not exists:
            overwrite_switch.value = False
        return exists

    def _status(self, text: str) -> None:
        """Display a short status message in the wizard footer area."""
        self.query_one("#status", Static).update(text)

    def action_quit(self) -> None:
        """Exit the TUI application."""
        self.app.exit()

    def action_edit_config(self) -> None:
        """Open the configuration editor screen."""
        self.app.push_screen(ConfigScreen(self.cfg))

    def action_start(self) -> None:
        """Keyboard action to trigger run/confirm flow."""
        self._run()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Route button presses to wizard actions and script-editor handlers."""
        bid = event.button.id

        # Scripts editor handlers (if enabled)
        if self.enable_scripts and bid == "script_add":
            self._add_script()
            return
        if self.enable_scripts and bid == "script_remove":
            self._remove_selected_script()
            return
        if self.enable_scripts and bid == "script_clear":
            self._scripts.clear()
            self._refresh_scripts_table()
            return

        # Main buttons
        if bid == "run":
            self._run()
        elif bid == "config":
            self.action_edit_config()
        elif bid == "quit_btn":
            self.action_quit()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Keep directory mirroring and overwrite visibility up to date."""
        if event.input.id == "name" and not self._syncing_name_to_dir:
            self._sync_target_dir_from_name()

        if event.input.id in {"name", "dir"}:
            exists = self._refresh_overwrite_state()
            name_value = self.query_one("#name", Input).value.strip()
            resolved_name = _resolve_project_name(name_value)
            if not resolved_name:
                self._status("Project name is invalid and cannot be sluggified into a valid name.")
            elif resolved_name != name_value:
                self._status(f'Project name will be normalized to "{resolved_name}".')
            elif exists:
                self._status("Warning: target directory already exists.")
            else:
                self._status("")

    def _add_script(self) -> None:
        """Add a script entry to the in-memory script mapping + refresh table."""
        name = self.query_one("#script_name", Input).value.strip()
        entry = self.query_one("#script_entry", Input).value.strip()

        if not name or not entry:
            self._status("Script name and entry point are required.")
            return

        # Minimal validation: entry points commonly look like module:callable.
        # This isn’t perfect, but it catches accidental whitespace-y nonsense.
        if ":" not in entry or entry.startswith(":") or entry.endswith(":"):
            self._status('Entry point should look like "module:callable".')
            return

        self._scripts[name] = entry
        self._refresh_scripts_table()
        self.query_one("#script_name", Input).value = ""
        self.query_one("#script_entry", Input).value = ""

    def _remove_selected_script(self) -> None:
        """Remove the currently selected script row (if any)."""
        table = self.query_one("#scripts_table", DataTable)
        if table.row_count == 0:
            return

        coord = table.cursor_coordinate
        row_key = table.coordinate_to_cell_key(coord).row_key
        # Textual returns a RowKey wrapper, not a raw string.
        key_value = getattr(row_key, "value", row_key)
        script_name = str(key_value)
        if script_name in self._scripts:
            del self._scripts[script_name]
            self._refresh_scripts_table()

    def _refresh_scripts_table(self) -> None:
        """Re-render the scripts table from `self._scripts`."""
        if not self.enable_scripts:
            return
        table = self.query_one("#scripts_table", DataTable)
        table.clear()
        for name, entry in sorted(self._scripts.items()):
            # Use `name` as row key so we can delete by selection easily.
            table.add_row(name, entry, key=name)

    def _run(self) -> None:
        """
        Validate inputs, build a plan, then open confirmation.
        """
        dir_str = self.query_one("#dir", Input).value.strip() or "."
        name = self.query_one("#name", Input).value.strip()
        desc = self.query_one("#desc", Input).value.strip() or "Add your description here"
        is_lib = self.query_one("#is_lib", Switch).value
        pyver = self.query_one("#pyver", Input).value.strip() or self.cfg.default_python

        deps_widget = self.query_one("#deps", SelectionList)
        deps = list(deps_widget.selected)

        if not name:
            self._status("Project name is required.")
            return
        resolved_name = _resolve_project_name(name)
        if not resolved_name:
            self._status("Project name is invalid and cannot be sluggified into a valid name.")
            return

        target_dir = Path(dir_str).expanduser().resolve()
        overwrite = self.query_one("#overwrite", Switch).value

        if target_dir.name != resolved_name:
            self._status(
                f'Project name resolves to "{resolved_name}". Target directory name must match.'
            )
            return

        if target_dir.exists() and not overwrite:
            self._status(
                "Target directory already exists. Toggle overwrite or change name/target directory."
            )
            self._refresh_overwrite_state()
            return

        scripts = dict(self._scripts) if self.enable_scripts else {}

        plan = InitPlan(
            target_dir=target_dir,
            name=resolved_name,
            description=desc,
            is_lib=is_lib,
            python_version=pyver,
            deps=deps,
            scripts=scripts,
            overwrite=overwrite,
        )
        self.app.push_screen(ConfirmScreen(plan), self._on_confirm)

    def _on_confirm(self, plan: InitPlan | None) -> None:
        """Proceed to execution only when the confirmation screen approves."""
        if plan is not None:
            self.app.push_screen(RunScreen(plan))


class ConfirmScreen(ModalScreen[InitPlan | None]):
    """
    Confirmation dialog shown before running any command.

    This screen is the "Back to edit" checkpoint for the wizard.
    """

    BINDINGS = [
        ("enter", "execute", "Execute"),
        ("ctrl+s", "execute", "Execute"),
        ("escape", "back_to_edit", "Back to edit"),
    ]

    def __init__(self, plan: InitPlan) -> None:
        """Initialize the confirmation modal with an immutable init plan."""
        super().__init__()
        self.plan: InitPlan = plan

    def compose(self) -> ComposeResult:
        """Build the modal showing command preview and confirmation controls."""
        with Vertical(id="confirm_body"):
            yield Static("Preview Commands", id="confirm_title")
            yield Static(
                "Review the exact `uv` commands before execution.",
                id="confirm_subtitle",
            )
            # Keep long command lines and larger plans navigable in the modal.
            with ScrollableContainer(id="preview_box"):
                yield Static(_build_preview_text(self.plan), id="preview_commands")
            with Horizontal(id="confirm_buttons"):
                yield Button("Back to edit", id="confirm_back")
                yield Button("Execute", variant="success", id="confirm_execute")

    def action_execute(self) -> None:
        """Confirm and dismiss the modal with the current plan."""
        self.dismiss(self.plan)

    def action_back_to_edit(self) -> None:
        """Cancel execution and return to the wizard for edits."""
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Map modal button presses to execute/back actions."""
        if event.button.id == "confirm_back":
            self.action_back_to_edit()
        if event.button.id == "confirm_execute":
            self.action_execute()


class RunScreen(Screen):
    """
    Executes the plan:

      1) uv init
      2) (optional) patch [project.scripts]
      3) uv add deps

    We log output verbosely so failures are debuggable without leaving the app.
    """

    def __init__(self, plan: InitPlan) -> None:
        """Initialize run screen state and in-memory log buffer."""
        super().__init__()
        self.plan: InitPlan = plan
        self._log_lines: list[str] = []

    def compose(self) -> ComposeResult:
        """Build the run view containing output log and back button."""
        yield Header()
        with Vertical(id="run_body"):
            yield Static("Running…", id="run_title")
            yield Static("", id="log")
            yield Button("Back", id="back")
        yield Footer()

    def on_mount(self) -> None:
        """Start execution immediately after the screen mounts."""
        self._go()

    def _log(self, text: str) -> None:
        """Append a line to the run log widget."""
        self._log_lines.append(text)
        self.query_one("#log", Static).update("\n".join(self._log_lines).strip())

    def _go(self) -> None:
        """Execute the planned init/add/scripts workflow and capture output."""
        project_root = self.plan.target_dir.resolve()
        parent_dir = project_root.parent

        if not parent_dir.exists():
            parent_dir.mkdir(parents=True, exist_ok=True)
            self._log(f"Created parent directory: {parent_dir}")

        if self.plan.overwrite and project_root.exists():
            if project_root.is_dir():
                shutil.rmtree(project_root)
            else:
                project_root.unlink()
            self._log(f"Removed existing path: {project_root}")

        self._log(f"Target directory: {self.plan.target_dir}")
        self._log(f"Project name:     {project_root.name}")
        self._log(f"Library:          {self.plan.is_lib}")
        self._log(f"Python:           {self.plan.python_version}")
        self._log(f"Deps:             {', '.join(self.plan.deps) if self.plan.deps else '(none)'}")
        self._log(
            f"Scripts:          {', '.join(self.plan.scripts.keys()) if self.plan.scripts else '(none)'}"
        )
        self._log("")

        try:
            init_cmd = build_uv_init_cmd(
                name=project_root.name,
                description=self.plan.description,
                is_lib=self.plan.is_lib,
                python_version=self.plan.python_version,
            )
            self._log(f"$ {shlex_join(init_cmd)}")
            out = uv_init(
                target_dir=parent_dir,
                name=project_root.name,
                description=self.plan.description,
                is_lib=self.plan.is_lib,
                python_version=self.plan.python_version,
            )
            if out:
                self._log(out)

            if not project_root.exists():
                raise UVError(f"`uv init` completed but project directory was not created: {project_root}")

            pyproject_path = project_root / "pyproject.toml"

            if self.plan.scripts:
                set_project_scripts(pyproject_path, self.plan.scripts)
                self._log(f"Updated [project.scripts] in {pyproject_path}")

            if self.plan.deps:
                add_cmd = build_uv_add_cmd(deps=self.plan.deps, no_sync=True)
                self._log(f"$ {shlex_join(add_cmd)}")
            out2 = uv_add(project_root=project_root, deps=self.plan.deps, no_sync=True)
            if out2:
                self._log(out2)

            self._log("")
            self._log("✅ Done.")
        except UVError as e:
            self._log("")
            self._log("❌ uv failed:")
            self._log(str(e))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Return to the previous screen when Back is pressed."""
        if event.button.id == "back":
            self.app.pop_screen()


class ConfigScreen(Screen):
    """
    Simple in-app editor for ~/.config/uv-init-tui/config.toml
    """

    class Saved(Message):
        """Posted when config is saved so the app can refresh screens."""

    def __init__(self, cfg: AppConfig) -> None:
        """Initialize config editor with the current application config."""
        super().__init__()
        self.cfg: AppConfig = cfg

    def compose(self) -> ComposeResult:
        """Build the configuration editor form."""
        yield Header()
        with ScrollableContainer():
            yield Static(f"Config: {CONFIG_PATH}", id="cfg_title")

            yield Label("Default directory:")
            yield Input(value=self.cfg.default_directory, id="cfg_dir")

            yield Label("Default python version:")
            yield Input(value=self.cfg.default_python, id="cfg_py")

            with Horizontal():
                yield Label("Default is library?")
                yield Switch(value=self.cfg.default_is_lib, id="cfg_lib")

            yield Label("Common dependencies (comma-separated):")
            yield Input(value=", ".join(self.cfg.common_dependencies), id="cfg_common")

            yield Label("Default selected dependencies (comma-separated):")
            yield Input(value=", ".join(self.cfg.default_dependencies), id="cfg_default")

            with Horizontal():
                yield Button("Save", variant="success", id="save")
                yield Button("Cancel", variant="error", id="cancel")

            yield Static("", id="cfg_status")
        yield Footer()

    def _status(self, text: str) -> None:
        """Display a status message in the config editor."""
        self.query_one("#cfg_status", Static).update(text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle Save/Cancel actions and persist updated configuration."""
        if event.button.id == "cancel":
            self.app.pop_screen()
            return

        if event.button.id != "save":
            return

        # Gather and sanitize inputs
        self.cfg.default_directory = self.query_one("#cfg_dir", Input).value.strip() or "."
        self.cfg.default_python = self.query_one("#cfg_py", Input).value.strip() or "3.14"
        self.cfg.default_is_lib = self.query_one("#cfg_lib", Switch).value

        common = self.query_one("#cfg_common", Input).value
        defaults = self.query_one("#cfg_default", Input).value

        self.cfg.common_dependencies = [x.strip() for x in common.split(",") if x.strip()]
        self.cfg.default_dependencies = [x.strip() for x in defaults.split(",") if x.strip()]

        save_config(self.cfg)
        self._status("Saved.")
        self.app.pop_screen()
        self.app.post_message(self.Saved())


class UVInitTui(App):
    """
    Root Textual app.

    We pass enable_scripts from the Typer CLI to the wizard screen.
    """

    CSS_PATH = Path(__file__).resolve().parents[2] / "styles.tcss"

    def __init__(self, *, enable_scripts: bool = False) -> None:
        """Initialize app-wide flags and load persisted configuration."""
        super().__init__()
        self.enable_scripts: bool = enable_scripts
        self.cfg: AppConfig = load_config()

    def on_mount(self) -> None:
        """Push the initial wizard screen when the app starts."""
        self.push_screen(WizardScreen(self.cfg, enable_scripts=self.enable_scripts))

    def on_config_screen_saved(self, _: ConfigScreen.Saved) -> None:
        """Reload config from disk and rebuild the wizard with new defaults."""
        # Reload from disk (covers in-app edits + manual edits)
        self.cfg = load_config()

        # Rebuild wizard so it uses the updated defaults.
        self.pop_screen()
        self.push_screen(WizardScreen(self.cfg, enable_scripts=self.enable_scripts))


# -------------------------
# Typer CLI entry point
# -------------------------

cli = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
    help="Textual wizard for `uv init` (and optional dependency + script setup).",
)


@cli.command()
def run(
    scripts: bool = typer.Option(
        False,
        "--scripts",
        help="Enable configuring [project.scripts] for the generated project.",
    )
) -> None:
    """
    Launch the TUI.

    Args:
        scripts: If True, show an extra step for [project.scripts].
    """
    UVInitTui(enable_scripts=scripts).run()


def main() -> None:
    """
    Console script entry point (declared in pyproject.toml).

    We route into Typer so `uv-init-tui --help` works as expected.
    """
    cli()
