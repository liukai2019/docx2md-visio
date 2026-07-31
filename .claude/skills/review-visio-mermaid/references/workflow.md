# Manual-first workflow

## State machine

```text
review_required
  ├─ keep original ────────────────> done without replacement
  ├─ accept raw draft ─> edit/check ─> human approve ─> apply
  └─ manual redraw ───> edit/check ─> human approve ─> apply
```

## Commands

```powershell
docx2md-visio-review backup OUTPUT_DIR
docx2md-visio-review list OUTPUT_DIR
```

Create one new `final.mmd`:

```powershell
docx2md-visio-review scaffold OUTPUT_DIR `
  --diagram diagram-003 --type sequence
```

The command refuses to overwrite an existing asset. The human edits the file
using the Word/Visio original as authority. `raw.mmd`,
`geometry-summary.md`, and `diagnostic.svg` are evidence, not truth.

Check message labels:

```powershell
docx2md-visio-review check OUTPUT_DIR --diagram diagram-003
```

Exit code 2 means missing or unexpected labels. The check is an inventory
check, not a proof of correct arrows, order, grouping, or protocol meaning.

After the human confirms the local Mermaid preview:

```powershell
docx2md-visio-apply OUTPUT_DIR --diagram diagram-003 --approve
```

Only after the human has examined every reported difference may they use:

```powershell
docx2md-visio-apply OUTPUT_DIR --diagram diagram-003 `
  --approve --allow-message-differences
```

Continue with `docx2md-visio-review list OUTPUT_DIR`.

## Reminder algorithm

1. If any `final=yes`, run backup.
2. If a `final.mmd` has no `manual-check.json`, request a check.
3. If the check fails, present missing/unexpected lists.
4. If the check passes but status is `review_required`, request visual approval.
5. If status is `converted_after_review`, move to the next diagram.
6. Never interpret silence as approval.

