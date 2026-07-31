# Correction asset provenance

The durable store defaults to a sibling `corrections/` directory:

```text
corrections/
├── manifest.json
└── assets/
    └── document-name/
        └── SOURCE-DOCX-SHA256/
            └── diagram-003/
                └── SOURCE-VSDX-SHA256/
                    ├── final-FINAL-MMD-SHA256.mmd
                    └── final-FINAL-MMD-SHA256.metadata.json
```

The `.mmd` remains byte-for-byte usable Mermaid. Its adjacent metadata records:

- original DOCX name and SHA-256 when accessible;
- output Markdown;
- diagram ID, document part, order, and paragraph;
- preview and embedding parts;
- source VSDX path and SHA-256;
- geometry JSON path and SHA-256;
- final Mermaid SHA-256;
- draft/approved backup events and timestamps.

`corrections/manifest.json` is an index, not the sole source of provenance.
Never separate an `.mmd` from its `.metadata.json` when transferring assets.

Restore only an approved correction whose source VSDX SHA-256 exactly matches:

```powershell
docx2md-visio-review restore OUTPUT_DIR --diagram diagram-003
```

Restore creates `final.mmd` for human reinspection; it does not apply it.
