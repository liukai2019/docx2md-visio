import os
from pathlib import Path

from docx2md_visio.tools import run_markitdown


def test_run_markitdown_command(tmp_path: Path) -> None:
    source = tmp_path / "source.docx"
    source.write_bytes(b"docx")
    destination = tmp_path / "source.ai.md"
    implementation = tmp_path / "markitdown_impl.py"
    implementation.write_text(
        """import pathlib, sys
source = pathlib.Path(sys.argv[1])
destination = pathlib.Path(sys.argv[sys.argv.index("-o") + 1])
destination.write_text("# AI view\\n\\n" + source.name + "\\n", encoding="utf-8")
""",
        encoding="utf-8",
    )
    run_markitdown([os.environ.get("PYTHON", "python"), str(implementation)], source, destination)
    assert destination.read_text(encoding="utf-8") == "# AI view\n\nsource.docx\n"

