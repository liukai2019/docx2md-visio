from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from .docx import extract_visio_files, inspect_document, safe_extract_docx
from .markdown import merge_markdown
from .models import Manifest
from .report import write_manifest, write_report
from .tools import ToolError, run_convert2mermaid, run_pandoc, tool_version
from .vsdx import VsdxError, convert_vsdx, mermaid_structure_counts


class PipelineError(RuntimeError):
    pass


def convert(
    source: Path,
    output_dir: Path,
    pandoc: str = "pandoc",
    converter_command: list[str] | None = None,
    keep_work: bool = False,
) -> Manifest:
    source = source.resolve()
    output_dir = output_dir.resolve()
    converter_command = converter_command or ["convert2mermaid"]
    if not source.is_file():
        raise PipelineError(f"Input file does not exist: {source}")
    if source.suffix.lower() != ".docx":
        raise PipelineError("Input must have a .docx extension.")
    output_dir.mkdir(parents=True, exist_ok=True)

    work_context = (
        tempfile.TemporaryDirectory(prefix="docx2md-visio-")
        if not keep_work
        else None
    )
    work_root = (
        Path(work_context.name)
        if work_context
        else output_dir / ".docx2md-visio-work"
    )
    if keep_work:
        if work_root.exists():
            shutil.rmtree(work_root)
        work_root.mkdir(parents=True)

    try:
        package_root = work_root / "package"
        safe_extract_docx(source, package_root)
        diagrams = inspect_document(package_root)
        output_markdown = output_dir / f"{source.stem}.md"
        manifest = Manifest(
            source_document=str(source),
            output_markdown=output_markdown.name,
            diagrams=diagrams,
            tool_versions={
                "pandoc": tool_version([pandoc]),
                "convert2mermaid": tool_version(converter_command),
            },
        )
        extract_visio_files(package_root, diagrams, output_dir)

        draft = work_root / "draft.md"
        media_root = output_dir / "assets"
        try:
            run_pandoc(pandoc, source, draft, media_root)
        except ToolError as exc:
            raise PipelineError(f"Pandoc failed: {exc}\n{exc.output}") from exc

        for diagram in diagrams:
            if not diagram.source_vsdx:
                continue
            source_vsdx = output_dir / diagram.source_vsdx
            raw_mermaid = source_vsdx.parent / "raw.mmd"
            try:
                run_convert2mermaid(converter_command, source_vsdx, raw_mermaid)
                diagram.raw_mermaid = raw_mermaid.relative_to(output_dir).as_posix()
                if diagram.status != "unmapped":
                    diagram.status = "mermaid_generated"
                native_candidate = source_vsdx.parent / "native-fallback.mmd"
                try:
                    native_nodes, native_edges = convert_vsdx(
                        source_vsdx, native_candidate
                    )
                    external_nodes, external_edges = mermaid_structure_counts(
                        raw_mermaid.read_text(encoding="utf-8")
                    )
                    if (
                        external_nodes < native_nodes
                        or external_edges < native_edges
                    ):
                        shutil.move(native_candidate, raw_mermaid)
                        diagram.warnings.append(
                            "External convert2mermaid output was structurally "
                            f"incomplete ({external_nodes} nodes/{external_edges} "
                            f"edges versus {native_nodes}/{native_edges}); used "
                            "native Open XML output."
                        )
                    else:
                        native_candidate.unlink(missing_ok=True)
                except VsdxError as validation_exc:
                    diagram.warnings.append(
                        "Could not cross-check external Mermaid output with the "
                        f"native parser: {validation_exc}"
                    )
            except ToolError as exc:
                diagram.warnings.append(
                    f"External convert2mermaid failed; used native Open XML fallback: {exc}"
                )
                if exc.output:
                    (source_vsdx.parent / "converter.log").write_text(
                        exc.output, encoding="utf-8"
                    )
                try:
                    node_count, edge_count = convert_vsdx(
                        source_vsdx, raw_mermaid
                    )
                    diagram.raw_mermaid = raw_mermaid.relative_to(
                        output_dir
                    ).as_posix()
                    if diagram.status != "unmapped":
                        diagram.status = "mermaid_generated"
                    diagram.warnings.append(
                        f"Native fallback extracted {node_count} nodes and "
                        f"{edge_count} edges."
                    )
                except VsdxError as fallback_exc:
                    diagram.status = "conversion_failed"
                    diagram.warnings.append(
                        f"Native VSDX fallback failed: {fallback_exc}"
                    )

        draft_text = draft.read_text(encoding="utf-8")
        merged = merge_markdown(draft_text, diagrams, output_dir)
        output_markdown.write_text(merged, encoding="utf-8")
        write_manifest(manifest, output_dir / "manifest.json")
        write_report(manifest, output_dir / "conversion-report.md")
        return manifest
    finally:
        if work_context:
            work_context.cleanup()
