# Changelog

## 0.2.0

- Add a standard-library VSDX Open XML parser for basic nodes and connectors.
- Fall back when external convert2mermaid is unavailable or exits with error.
- Cross-check external Mermaid structure against the source VSDX and replace
  silently incomplete output.
- Handle mixed and empty Visio text elements without `undefined.replace`
  failures.
- Decode external tool output as UTF-8 with replacement on Windows.
- Add generated, non-confidential VSDX and DOCX regression samples.

## 0.1.0

- Initial deterministic DOCX relationship mapping, Pandoc conversion,
  VSDX extraction, convert2mermaid invocation, Markdown merge, manifest and
  conversion report.
