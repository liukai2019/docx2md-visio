# docx2md-visio

`docx2md-visio` converts a Word `.docx` containing embedded Visio `.vsdx`
diagrams into GitHub-Flavored Markdown with Mermaid blocks.

The pipeline is deterministic and offline-friendly. AI is not required:

```text
DOCX
 ├─ Pandoc → draft Markdown + media
 ├─ Open XML relationships → preview ↔ VSDX ↔ paragraph mapping
 ├─ embedded VSDX extraction
 ├─ convert2mermaid → Mermaid
 └─ exact Markdown image replacement + manifest + report
```

## MVP guarantees

- The source DOCX is never modified.
- Embedded VSDX files are copied, not rewritten.
- Word relationship IDs determine the VSDX/preview mapping.
- Ambiguous or missing mappings are reported rather than guessed.
- A failed diagram conversion leaves the original Pandoc image in Markdown.
- A low-confidence native conversion is saved as a draft but does not replace
  the original preview.
- The final output retains links to the original extracted VSDX files.
- The runtime has no Python package dependencies.

## Requirements

- Python 3.10+
- [Pandoc](https://pandoc.org/)
- Optional: [convert2mermaid](https://github.com/jgreywolf/convert2mermaid)
  available as a command, or its Node CLI path supplied explicitly. If it is
  missing, fails, or silently loses basic graph structure, the MVP
  automatically uses its built-in Open XML converter.

All tools can be installed or copied into an offline network in advance.

## Install

From a downloaded source archive:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install .
```

For development:

```powershell
pip install -e .
```

## Usage

When `convert2mermaid` is already on `PATH`:

```powershell
docx2md-visio .\documents\design.docx -o .\output
```

When running the bundled JavaScript CLI:

```powershell
docx2md-visio .\documents\design.docx -o .\output `
  --converter node `
  --converter .\tools\convert2mermaid\dist\cli.js
```

Use explicit offline tool paths if desired:

```powershell
docx2md-visio .\documents\design.docx -o .\output `
  --pandoc .\tools\pandoc\pandoc.exe `
  --converter .\tools\node\node.exe `
  --converter .\tools\convert2mermaid\dist\cli.js `
  --keep-work
```

`--converter` is repeatable because the converter command may consist of an
executable plus a JavaScript entrypoint. The program appends:

```text
-i <source.vsdx> -o <raw.mmd> -f mmd
```

## Output

```text
output/
├── design.md
├── manifest.json
├── conversion-report.md
└── assets/
    ├── media/
    │   └── image1.png
    └── visio/
        └── diagram-001/
            ├── source.vsdx
            ├── raw.mmd
            ├── diagram.json
            ├── geometry-summary.md
            ├── diagnostic.svg
            ├── context.md
            ├── review-prompt.md
            ├── final.mmd       # created by optional review stage
            └── converter.log  # only when the converter fails with output
```

When optional MarkItDown comparison is enabled, the output also contains
`design.ai.md`. It is an AI-oriented reference only; `design.md` remains the
canonical result.

Each successfully mapped Pandoc image is replaced with:

````markdown
<!-- VISIO-BEGIN: diagram-001 -->
```mermaid
flowchart LR
  A --> B
```

[Original Visio diagram](assets/visio/diagram-001/source.vsdx)
<!-- VISIO-END: diagram-001 -->
````

## How deterministic mapping works

A Word object normally contains two relationship IDs: one for its preview and
one for the embedded package. `docx2md-visio` reads
`word/document.xml` and `word/_rels/document.xml.rels` to resolve:

```text
paragraph 28
 ├─ rIdPreview → word/media/image5.emf
 └─ rIdVisio   → word/embeddings/Microsoft_Visio_4.vsdx
```

Pandoc's Markdown reference ending in `media/image5.emf` can then be replaced
without relying on file ordering or AI inference. Pandoc 3.10 may emit a
multiline HTML `<img src="...">` element for media carrying size/style
attributes; the matcher supports both that representation and normal
`![alt](src)` Markdown.

## Current scope and limitations

The MVP supports embedded VSDX objects referenced from the main document part
through common Word VML/OLE and DrawingML structures. It deliberately reports
instead of guessing when:

- a VSDX is present but not referenced by a supported object structure;
- the preview image is missing from Pandoc output;
- the same preview occurs more than once;
- an external converter fails.

The built-in parser reads VSDX page, shape, text, box geometry, line endpoints,
parent IDs and connector XML with the Python standard library. The geometry
layer is domain-neutral: it reports visual facts and generic spatial
relationships but does not claim that geometric containment proves protocol or
business membership. Master inheritance, nested group coordinate transforms,
advanced geometry paths and exact styling remain outside the current scope.

### Geometry evidence

For every parseable VSDX, Stage 1 creates:

- `diagram.json`: complete extracted L1 geometry facts and derived relations;
- `geometry-summary.md`: compact labeled shapes, lines and high-confidence
  relations for a smaller-model review;
- `diagnostic.svg`: a visual box/line overlay labeled with source Shape IDs.

`spatially_inside` means at least 90% of a shape or sampled line lies within
another shape's bounding box. `spatially_overlaps` means at least 20%. These
relations use geometry only and must not be promoted to domain semantics
without supporting evidence.

### Conservative replacement policy

Native output is marked `review_required` instead of replacing the preview
when any of these conditions apply:

- more than one Visio page;
- more than 10 basic nodes;
- more than 25% of nodes have no directly readable label;
- one or more connector endpoints cannot be resolved.

The draft remains at `assets/visio/diagram-NNN/raw.mmd`, and the reason is
recorded in both `manifest.json` and `conversion-report.md`. This policy avoids
presenting a flattened flowchart as an accurate conversion of a signaling,
sequence, UML, or other structurally complex Visio diagram.

## Three-stage offline review workflow

The deterministic converter, Claude review and final Markdown application are
separate stages. Claude never edits the document Markdown directly.

### Stage 1: deterministic conversion and context generation

```powershell
python -m docx2md_visio `
  .\documents\design.docx `
  -o .\output `
  --converter node `
  --converter .\tools\convert2mermaid\dist\cli.js
```

If convert2mermaid is unavailable, omit both `--converter` arguments. The
built-in Open XML fallback will run after the default command cannot be found.

For each mapped diagram, Stage 1 now creates:

```text
output/assets/visio/diagram-001/
├── source.vsdx
├── raw.mmd
├── diagram.json
├── geometry-summary.md
├── diagnostic.svg
├── context.md
└── review-prompt.md
```

`context.md` is generated deterministically from Pandoc's draft Markdown. It
contains the nearest preceding heading and bounded text before and after the
preview. It remains inside the offline output directory and may contain
document content, so apply the same confidentiality controls as the source
DOCX.

### Stage 2: let Claude create a candidate final.mmd

Process one `review_required` diagram at a time. Open PowerShell in that
diagram's directory:

```powershell
Set-Location .\output\assets\visio\diagram-001

$reviewInput = @"
$(Get-Content .\review-prompt.md -Raw)

## geometry-summary.md
$(Get-Content .\geometry-summary.md -Raw)

## context.md
$(Get-Content .\context.md -Raw)

## raw.mmd
$(Get-Content .\raw.mmd -Raw)
"@

$candidate = $reviewInput | claude -p --max-turns 2
$candidate | Set-Content .\final.mmd -Encoding utf8
```

Inspect `final.mmd` manually. It must contain plain Mermaid source beginning
with a declaration such as `sequenceDiagram` or `flowchart TD`. It must not
contain triple-backtick Markdown fences or explanatory prose. If Claude cannot
establish participant names or connections from the supplied evidence, keep
the original preview and do not run Stage 3.

If `geometry-summary.md` contains a labeled frame or grouping that does not
appear in `final.mmd`, treat the candidate as incomplete unless
`review-notes.md` explains a Mermaid representation limitation. Consult
`diagram.json` and `diagnostic.svg` when the compact summary is ambiguous.

For a signaling diagram, a candidate may look like:

```text
sequenceDiagram
    participant P117 as Participant n117
    participant P122 as Participant n122
    P117->>P122: INVITE F1
    P122->>P117: 100 Trying F2
```

### Stage 3: apply one human-approved final.mmd

After comparing `final.mmd` with the original preview:

```powershell
python -m docx2md_visio.apply_review `
  .\output `
  --diagram diagram-001 `
  --approve
```

The installed console command is equivalent:

```powershell
docx2md-visio-apply .\output --diagram diagram-001 --approve
```

The apply command:

- requires the explicit `--approve` flag;
- validates the Mermaid declaration;
- rejects Markdown code fences and empty output;
- uses `manifest.json` to replace the exact preview;
- wraps `final.mmd` in a Markdown Mermaid code block;
- retains a link to `source.vsdx`;
- creates `<document>.md.pre-review` before the first reviewed replacement;
- records `converted_after_review` and `final_mermaid` in `manifest.json`.

Repeat Stages 2 and 3 for each diagram that a human approves. Unapproved
diagrams continue to display their original Pandoc preview.

## Markdown correction skill

The repository includes a Claude Code project skill at
`.claude/skills/correct-docx-markdown/`. It combines a deterministic audit with
strict review guardrails.

Run the audit without AI:

```powershell
docx2md-visio-correct .\output\design.md --write --fail-on never
```

With an optional MarkItDown second opinion:

```powershell
docx2md-visio .\documents\design.docx -o .\output `
  --markitdown markitdown

docx2md-visio-correct .\output\design.md `
  --reference .\output\design.ai.md `
  --write --fail-on never
```

The command writes `correction-report.json` and `correction-report.md`.
Automatic changes are limited to newline normalization, BOM removal, final
newline normalization, and collapsing excessive blank lines outside fenced
code. Potentially semantic changes—including Pandoc backslash escapes,
headings, tables, missing images, and orphaned HTML—are only reported.

Start Claude Code in the repository root and ask:

```text
Use $correct-docx-markdown to audit output/design.md.
```

Claude must use MarkItDown only as supporting evidence and must not edit
reviewed Mermaid blocks through the document correction workflow.

## Complete offline deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the supported topology,
bundle creation, isolated-network installation, Claude Code operation, and
acceptance checks. `scripts/New-OfflineBundle.ps1` can package the repository
with optional Pandoc, Node, convert2mermaid, and wheelhouse directories.

Headers, footers, text boxes stored outside the main document flow, linked
rather than embedded Visio files, and visual floating-object coordinates are
not yet mapped. Multi-page behavior is determined by the installed
convert2mermaid version.

## Test

The test suite uses synthetic DOCX files and fake external commands, so it
does not require Pandoc or convert2mermaid:

```powershell
pip install pytest
pytest
```

Generate a non-confidential synthetic VSDX and a DOCX embedding that VSDX:

```powershell
python .\scripts\generate_sample.py
```

The generated flow contains two nodes and one connector. Its connector text
uses an empty field structure that exposes a known fragile assumption in
`vsdx-js`, while the built-in parser handles it deterministically.

Or run the standard-library tests after installing a test runner in the
offline environment.

## Security

DOCX is a ZIP container. Extraction checks every member path before writing it
to prevent path traversal. External tools receive argument arrays rather than
shell command strings.

## Roadmap

- Parse headers, footers and additional document parts.
- Resolve Master-inherited geometry and nested Group coordinate transforms.
- Add exact Geometry-section paths and richer multi-page diagnostics.
- Add optional Mermaid syntax validation.
- Add an optional, separate AI review layer.
- Package the CLI behind a Claude Code or Codex skill.

## License

MIT
