---
name: review-visio-mermaid
description: Guide a human through manual-first Visio-to-Mermaid review for docx2md-visio outputs. Use when Claude Code must inspect HUMAN-REVIEW.md or manifest.json, report the next pending diagram, remind the user to preserve every final.mmd, scaffold a human-editable Mermaid file, run deterministic message-conservation checks, restore a prior correction by source VSDX hash, or apply an explicitly approved correction without redrawing complex diagrams itself.
---

# Review Visio Mermaid

Act as a workflow guide and safety checker. Let the human interpret and redraw
the visual structure.

## Always start

1. Locate the output directory containing `HUMAN-REVIEW.md` and
   `manifest.json`.
2. Back up all existing manual assets before any edit or conversion rerun:

   ```powershell
   docx2md-visio-review backup OUTPUT_DIR
   ```

3. List current state:

   ```powershell
   docx2md-visio-review list OUTPUT_DIR
   ```

4. Tell the user the next pending diagram and ask them to choose:
   `keep original`, `accept draft`, or `manual redraw`.

## Guide one diagram

- For `keep original`, make no file change.
- For `accept draft`, scaffold with `--type raw`.
- For a signaling/time-sequence diagram, scaffold with `--type sequence`.
- For a node/edge diagram, scaffold with `--type flowchart`.
- Never overwrite an existing `final.mmd`. Back it up first.
- Ask the human to edit `final.mmd` beside the original preview and a local
  Mermaid preview.
- Run `docx2md-visio-review check` after editing.
- Report every missing and unexpected message. Do not invent a fix.
- Ask for explicit visual approval before running `docx2md-visio-apply`.
- Applying automatically backs up every `final.mmd`; the approved asset gets an
  approved provenance event.

Read [workflow details](references/workflow.md) when choosing or applying a
review action. Read [asset provenance](references/asset-provenance.md) when
backing up, restoring, moving, or auditing correction assets.

## Boundaries

- Do not regenerate a complex diagram from `source.vsdx` without an explicit,
  bounded user request.
- Do not treat geometry as protocol semantics.
- Do not silently allow message-conservation differences.
- Do not delete or replace anything under `corrections/`.
- Use Claude only for reminders, comparison, and small Mermaid syntax fixes.

