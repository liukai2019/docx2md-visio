from __future__ import annotations

import subprocess
from pathlib import Path


class ToolError(RuntimeError):
    def __init__(self, message: str, command: list[str], output: str = "") -> None:
        super().__init__(message)
        self.command = command
        self.output = output


def run_command(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ToolError(f"Command was not found: {command[0]}", command) from exc
    if result.returncode != 0:
        raise ToolError(
            f"Command failed with exit code {result.returncode}: {' '.join(command)}",
            command,
            result.stdout,
        )
    return result


def tool_version(command: list[str]) -> str:
    try:
        result = run_command([*command, "--version"])
    except ToolError:
        return "unknown"
    first_line = result.stdout.strip().splitlines()
    return first_line[0] if first_line else "unknown"


def run_pandoc(
    executable: str,
    source: Path,
    draft_markdown: Path,
    media_root: Path,
) -> None:
    draft_markdown.parent.mkdir(parents=True, exist_ok=True)
    media_root.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            executable,
            str(source),
            "--from=docx",
            "--to=gfm",
            "--wrap=none",
            f"--extract-media={media_root.name}",
            f"--output={draft_markdown}",
        ],
        cwd=media_root.parent,
    )


def run_convert2mermaid(
    command_prefix: list[str], source: Path, destination: Path
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            *command_prefix,
            "-i",
            str(source),
            "-o",
            str(destination),
            "-f",
            "mmd",
        ]
    )
    if not destination.is_file():
        raise ToolError(
            f"Converter reported success but did not create {destination}",
            command_prefix,
        )
