from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


class CorrectionError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def default_corrections_dir(output_dir: Path) -> Path:
    return output_dir.resolve().parent / "corrections"


def _load_output_manifest(output_dir: Path) -> dict:
    path = output_dir / "manifest.json"
    if not path.is_file():
        raise CorrectionError(f"Missing output manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_asset_manifest(root: Path) -> dict:
    path = root / "manifest.json"
    if not path.is_file():
        return {"schema_version": 1, "assets": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_asset_manifest(root: Path, manifest: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _safe_component(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")
    return cleaned or fallback


def _optional_hash(path: Path) -> str | None:
    return sha256_file(path) if path.is_file() else None


def backup_final_mmds(
    output_dir: Path,
    corrections_dir: Path | None = None,
    approved_diagram: str | None = None,
) -> list[dict]:
    output_dir = output_dir.resolve()
    root = (corrections_dir or default_corrections_dir(output_dir)).resolve()
    output_manifest = _load_output_manifest(output_dir)
    asset_manifest = _load_asset_manifest(root)
    added: list[dict] = []
    source_document = Path(
        output_manifest.get("source_document", "document.docx")
    )
    document_name = source_document.name
    document_component = _safe_component(source_document.stem, "document")
    document_hash = (
        output_manifest.get("source_document_sha256")
        or _optional_hash(source_document)
        or "document-hash-unavailable"
    )

    for diagram in output_manifest.get("diagrams", []):
        source_value = diagram.get("source_vsdx")
        if not source_value:
            continue
        diagram_dir = output_dir / Path(source_value).parent
        final_path = diagram_dir / "final.mmd"
        source_path = output_dir / source_value
        if not final_path.is_file() or not source_path.is_file():
            continue
        source_hash = sha256_file(source_path)
        final_hash = sha256_file(final_path)
        diagram_component = _safe_component(
            str(diagram.get("id") or "diagram"), "diagram"
        )
        relative = (
            Path("assets")
            / document_component
            / document_hash
            / diagram_component
            / source_hash
            / f"final-{final_hash}.mmd"
        )
        asset_path = root / relative
        metadata_path = asset_path.with_suffix(".metadata.json")
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        if not asset_path.exists():
            shutil.copy2(final_path, asset_path)
        geometry_value = diagram.get("geometry_json")
        geometry_path = (
            output_dir / geometry_value if geometry_value else Path()
        )
        approved = diagram.get("id") == approved_diagram
        event = {
            "approved": approved,
            "backed_up_at": datetime.now(timezone.utc).isoformat(),
        }
        if metadata_path.is_file():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if event not in metadata.setdefault("backup_events", []):
                metadata["backup_events"].append(event)
        else:
            metadata = {
                "schema_version": 1,
                "asset_type": "human_reviewed_mermaid",
                "asset": relative.as_posix(),
                "source": {
                    "document_name": document_name,
                    "document_sha256": document_hash,
                    "output_markdown": output_manifest.get("output_markdown"),
                    "diagram_id": diagram.get("id"),
                    "document_part": diagram.get("document_part"),
                    "document_order": diagram.get("document_order"),
                    "paragraph_index": diagram.get("paragraph_index"),
                    "preview_part": diagram.get("preview_part"),
                    "embedding_part": diagram.get("embedding_part"),
                    "source_vsdx": source_value,
                    "source_vsdx_sha256": source_hash,
                    "manifest_source_vsdx_sha256": diagram.get(
                        "source_vsdx_sha256"
                    ),
                    "geometry_json": geometry_value,
                    "geometry_json_sha256": _optional_hash(geometry_path),
                },
                "final_mmd_sha256": final_hash,
                "backup_events": [event],
            }
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        duplicate = next(
            (
                item
                for item in asset_manifest["assets"]
                if item.get("source_vsdx_sha256") == source_hash
                and item.get("final_mmd_sha256") == final_hash
                and item.get("diagram_id") == diagram.get("id")
                and item.get("document_sha256") == document_hash
                and item.get("approved") == approved
            ),
            None,
        )
        if duplicate:
            added.append(duplicate)
            continue
        record = {
            "document": document_name,
            "document_sha256": document_hash,
            "diagram_id": diagram.get("id"),
            "embedding_part": diagram.get("embedding_part"),
            "source_vsdx_sha256": source_hash,
            "final_mmd_sha256": final_hash,
            "asset": relative.as_posix(),
            "metadata": metadata_path.relative_to(root).as_posix(),
            "approved": approved,
            "backed_up_at": event["backed_up_at"],
        }
        asset_manifest["assets"].append(record)
        added.append(record)
    _write_asset_manifest(root, asset_manifest)
    return added


def restore_final_mmd(
    output_dir: Path,
    diagram_id: str,
    corrections_dir: Path | None = None,
) -> Path:
    output_dir = output_dir.resolve()
    root = (corrections_dir or default_corrections_dir(output_dir)).resolve()
    output_manifest = _load_output_manifest(output_dir)
    records = [
        item
        for item in output_manifest.get("diagrams", [])
        if item.get("id") == diagram_id
    ]
    if len(records) != 1 or not records[0].get("source_vsdx"):
        raise CorrectionError(f"Cannot resolve source VSDX for {diagram_id}.")
    diagram = records[0]
    source_path = output_dir / diagram["source_vsdx"]
    source_hash = sha256_file(source_path)
    asset_manifest = _load_asset_manifest(root)
    matches = [
        item
        for item in asset_manifest.get("assets", [])
        if item.get("source_vsdx_sha256") == source_hash
        and item.get("approved")
    ]
    if not matches:
        raise CorrectionError(
            f"No approved correction matches source VSDX SHA-256 {source_hash}."
        )
    selected = sorted(matches, key=lambda item: item["backed_up_at"])[-1]
    asset_path = root / selected["asset"]
    if not asset_path.is_file():
        raise CorrectionError(f"Correction asset is missing: {asset_path}")
    destination = output_dir / Path(diagram["source_vsdx"]).parent / "final.mmd"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(asset_path, destination)
    return destination


def _normalise_message(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().strip('"')


def extracted_messages(diagram_json: Path) -> list[str]:
    document = json.loads(diagram_json.read_text(encoding="utf-8"))
    return [
        _normalise_message(str(shape.get("text", "")))
        for page in document.get("pages", [])
        for shape in page.get("shapes", [])
        if shape.get("kind") == "one_dimensional"
        and _normalise_message(str(shape.get("text", "")))
    ]


SEQUENCE_MESSAGE_RE = re.compile(
    r"(?:-->>|->>|-->|->|-\)|--x|-x)\s*[^:]*:\s*(.+?)\s*$"
)
FLOW_LABEL_RE = re.compile(r"\|[\"']?(.+?)[\"']?\|")


def mermaid_messages(source: str) -> list[str]:
    messages: list[str] = []
    for line in source.splitlines():
        sequence = SEQUENCE_MESSAGE_RE.search(line)
        if sequence:
            messages.append(_normalise_message(sequence.group(1)))
            continue
        flow = FLOW_LABEL_RE.search(line)
        if flow:
            messages.append(_normalise_message(flow.group(1)))
    return messages


def message_conservation(diagram_json: Path, final_mmd: Path) -> dict:
    expected = Counter(extracted_messages(diagram_json))
    actual = Counter(
        mermaid_messages(final_mmd.read_text(encoding="utf-8-sig"))
    )
    missing = list((expected - actual).elements())
    unexpected = list((actual - expected).elements())
    return {
        "expected_count": sum(expected.values()),
        "actual_count": sum(actual.values()),
        "missing": missing,
        "unexpected": unexpected,
        "passed": not missing and not unexpected,
    }
