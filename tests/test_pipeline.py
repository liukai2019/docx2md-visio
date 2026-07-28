from __future__ import annotations

import json
import os
from pathlib import Path

from docx2md_visio.pipeline import convert

from .helpers import make_docx


def _write_executable(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)


def test_end_to_end_using_command_launchers(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "sample.docx"
    output = tmp_path / "output"
    make_docx(source)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    if os.name == "nt":
        pandoc = bin_dir / "pandoc.cmd"
        converter = bin_dir / "convert2mermaid.cmd"
        pandoc.write_text(
            '@python "%~dp0pandoc_impl.py" %*\n', encoding="utf-8"
        )
        converter.write_text(
            '@python "%~dp0converter_impl.py" %*\n', encoding="utf-8"
        )
    else:
        pandoc = bin_dir / "pandoc"
        converter = bin_dir / "convert2mermaid"
        _write_executable(
            pandoc, '#!/bin/sh\nexec python3 "$(dirname "$0")/pandoc_impl.py" "$@"\n'
        )
        _write_executable(
            converter,
            '#!/bin/sh\nexec python3 "$(dirname "$0")/converter_impl.py" "$@"\n',
        )
    (bin_dir / "pandoc_impl.py").write_text(
        """import pathlib, sys
if "--version" in sys.argv:
 print("fake-pandoc 1.0"); raise SystemExit()
out = pathlib.Path(next(a.split("=",1)[1] for a in sys.argv if a.startswith("--output=")))
media = pathlib.Path(next(a.split("=",1)[1] for a in sys.argv if a.startswith("--extract-media=")))
(media/"media").mkdir(parents=True, exist_ok=True)
(media/"media"/"image1.png").write_bytes(b"preview")
out.write_text("Before\\n\\n![](assets/media/image1.png)\\n\\nAfter\\n", encoding="utf-8")
""",
        encoding="utf-8",
    )
    (bin_dir / "converter_impl.py").write_text(
        """import pathlib, sys
if "--version" in sys.argv:
 print("fake-converter 1.0"); raise SystemExit()
out = pathlib.Path(sys.argv[sys.argv.index("-o")+1])
out.write_text("flowchart LR\\n  A --> B\\n", encoding="utf-8")
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    manifest = convert(
        source,
        output,
        pandoc=str(pandoc),
        converter_command=[str(converter)],
    )

    markdown = (output / "sample.md").read_text(encoding="utf-8")
    saved = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert "```mermaid" in markdown
    assert "A --> B" in markdown
    assert manifest.diagrams[0].status == "converted"
    assert saved["diagrams"][0]["paragraph_index"] == 1
    assert (output / "conversion-report.md").is_file()
