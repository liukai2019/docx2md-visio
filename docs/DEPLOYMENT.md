# Offline deployment

## Supported topology

The canonical pipeline is fully local:

```text
DOCX
  -> Pandoc canonical Markdown and media
  -> OOXML relationship/VSDX mapping
  -> native VSDX geometry and draft Mermaid
  -> conservative replacement, manifest and report
  -> deterministic Markdown audit
  -> optional Claude review of flagged items
```

MarkItDown is optional and runs beside, not after, the canonical pipeline. Its
`.ai.md` output is comparison evidence and must never overwrite the Pandoc
result.

## Prepare an external-network bundle

Python 3.10+ and the repository are required. Pandoc, Node,
convert2mermaid, and an existing Python wheelhouse can optionally be bundled:

```powershell
.\scripts\New-OfflineBundle.ps1 `
  -Destination .\release\docx2md-visio-offline `
  -PandocPath C:\Tools\Pandoc `
  -NodePath C:\Tools\node `
  -Convert2MermaidPath C:\src\convert2mermaid `
  -WheelhousePath C:\wheelhouse
```

The script refuses to overwrite an existing destination. Transfer the
resulting ZIP using the organization's approved process.

## Install inside the isolated network

```powershell
Expand-Archive .\docx2md-visio-offline.zip -DestinationPath C:\Tools
Set-Location C:\Tools\docx2md-visio-offline\project
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --no-index --find-links ..\tools\wheelhouse .
```

If no wheelhouse is needed, use `pip install .`. Pandoc can also remain in its
existing system installation.

Node and convert2mermaid are optional legacy comparison tools. The default
native workflow requires neither.

## Run and correct

```powershell
docx2md-visio .\input\design.docx -o .\output `
  --pandoc C:\Tools\Pandoc\pandoc.exe

# Optional legacy comparison:
docx2md-visio .\input\design.docx -o .\output-auto `
  --pandoc C:\Tools\Pandoc\pandoc.exe `
  --converter-mode auto `
  --converter C:\Tools\node\node.exe `
  --converter C:\Tools\convert2mermaid\dist\cli.js

docx2md-visio-correct .\output\design.md --write --fail-on never
```

To produce an optional AI-oriented comparison:

```powershell
docx2md-visio .\input\design.docx -o .\output `
  --markitdown C:\Tools\markitdown\.venv\Scripts\markitdown.exe

docx2md-visio-correct .\output\design.md `
  --reference .\output\design.ai.md --write --fail-on never
```

## Claude Code

The repository contains
`.claude/skills/correct-docx-markdown/SKILL.md`. Start Claude Code from the
repository root so it can discover the project skill, then invoke:

```text
Use $correct-docx-markdown to audit output/design.md. Do not invent technical
content and leave ambiguous findings for human review.
```

For Visio/Mermaid human review invoke the separate reminder skill:

```text
Use $review-visio-mermaid on .\output. Remind me of only the next safe step.
Do not redraw the diagram for me.
```

Mermaid review remains separate: Stage 1 creates `context.md`, `raw.mmd`,
`diagram.json`, `geometry-summary.md`, `diagnostic.svg`, and
`review-prompt.md`; Stage 2 backs up and triages; Stage 3 is human editing and
checking; Stage 4 applies only after explicit human approval. See
`docs/MANUAL_REVIEW.md`.

## Acceptance checks

1. `python -m pytest` passes.
2. `pandoc --version` succeeds.
3. A synthetic sample conversion produces Markdown, assets, manifest, and both
   reports.
4. Every `review_required` diagram still displays its original preview.
5. No `.ai.md` file is used as canonical output.
