# Manual-first Mermaid workflow

## Principle

Complex Visio-to-Mermaid conversion is a human review task. The original
preview remains authoritative. The program extracts evidence, protects manual
assets, checks message inventory, and performs deterministic Markdown
replacement. Claude reminds and assists with bounded syntax problems; it does
not decide visual or protocol semantics.

## Stage 1: convert without automatic replacement

The defaults are now native VSDX parsing and review of every diagram:

```powershell
docx2md-visio .\input\design.docx -o .\output
```

No Node.js or convert2mermaid installation is required. Use the old
cross-checked external path only for comparison:

```powershell
docx2md-visio .\input\design.docx -o .\output `
  --converter-mode auto `
  --converter node `
  --converter .\tools\convert2mermaid\dist\cli.js
```

Stage 1 writes `HUMAN-REVIEW.md`. Every diagram keeps its original preview
under the default `--review-policy all`.

## Stage 2: preserve assets and triage

Run before editing and before rerunning Stage 1:

```powershell
docx2md-visio-review backup .\output
docx2md-visio-review list .\output
```

For each diagram choose:

1. `keep original`: no Mermaid replacement;
2. `accept draft`: use `--type raw`, then inspect it;
3. `manual redraw`: use `--type sequence` or `flowchart`.

Never repair a fundamentally wrong flowchart incrementally. Start a blank
`sequenceDiagram` when the source is a signaling/time-sequence diagram.

## Stage 3: edit and check

```powershell
docx2md-visio-review scaffold .\output `
  --diagram diagram-003 --type sequence
```

Open three views side by side:

- original Word/Visio preview;
- `final.mmd`;
- local Mermaid preview.

After editing:

```powershell
docx2md-visio-review check .\output --diagram diagram-003
```

The check compares one-dimensional labeled VSDX shapes with Mermaid message
labels. It detects missing, unexpected, and duplicate labels. It cannot prove
correct direction, order, grouping, or meaning; the human checks those.

## Stage 4: approve and apply

```powershell
docx2md-visio-apply .\output --diagram diagram-003 --approve
```

Apply performs this order:

1. back up every `final.mmd` as a draft asset;
2. validate Mermaid declaration;
3. run message conservation;
4. require explicit override for reviewed differences;
5. verify that the exact Markdown preview can be replaced;
6. record the selected asset as approved;
7. back up and update the document Markdown, manifest, and report.

## Durable assets

The default store is `.\corrections` beside the output directory. Each Mermaid
file has a sidecar `.metadata.json`; both must travel together. Assets are
content-addressed and never overwritten.

After a new conversion, restore a matching approved correction:

```powershell
docx2md-visio-review restore .\output --diagram diagram-003
```

Matching uses the source VSDX SHA-256. A changed source does not silently reuse
an old correction.

## Claude Code reminder

Start Claude Code at the repository root and say:

```text
Use $review-visio-mermaid on .\output. Remind me of only the next safe step.
Do not redraw the diagram for me.
```

Claude should back up first, list status, select one pending diagram, and wait
for the human's triage or visual approval.
