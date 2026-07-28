from __future__ import annotations

import argparse
import base64
import zipfile
from pathlib import Path

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="xml" ContentType="application/xml"/>
 <Default Extension="png" ContentType="image/png"/>
 <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
 <Override PartName="/visio/document.xml" ContentType="application/vnd.ms-visio.drawing.main+xml"/>
 <Override PartName="/visio/pages/pages.xml" ContentType="application/vnd.ms-visio.pages+xml"/>
 <Override PartName="/visio/pages/page1.xml" ContentType="application/vnd.ms-visio.page+xml"/>
</Types>
"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="visio/document.xml"/>
</Relationships>
"""

VISIO_DOCUMENT = """<?xml version="1.0" encoding="UTF-8"?>
<VisioDocument xmlns="http://schemas.microsoft.com/office/visio/2012/main">
 <StyleSheets>
  <StyleSheet ID="0" Name="No Style" LineStyle="0" FillStyle="0" TextStyle="0">
   <Cell N="LineWeight" V="0.01"/>
  </StyleSheet>
 </StyleSheets>
</VisioDocument>
"""

PAGES = """<?xml version="1.0" encoding="UTF-8"?>
<Pages xmlns="http://schemas.microsoft.com/office/visio/2012/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
 <Page ID="1" Name="Synthetic Flow">
  <Rel r:id="rId1"/>
 </Page>
</Pages>
"""

PAGES_RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/page" Target="page1.xml"/>
</Relationships>
"""

PAGE = """<?xml version="1.0" encoding="UTF-8"?>
<PageContents xmlns="http://schemas.microsoft.com/office/visio/2012/main">
 <Shapes>
  <Shape ID="1" NameU="Process">
   <Cell N="PinX" V="2"/><Cell N="PinY" V="4"/>
   <Cell N="Width" V="2"/><Cell N="Height" V="1"/>
   <Text><cp IX="0"/><pp IX="0"/>Receive request</Text>
  </Shape>
  <Shape ID="2" NameU="Process">
   <Cell N="PinX" V="6"/><Cell N="PinY" V="4"/>
   <Cell N="Width" V="2"/><Cell N="Height" V="1"/>
   <Text><cp IX="0"/><pp IX="0"/>Return response</Text>
  </Shape>
  <Shape ID="3" NameU="Dynamic connector">
   <Cell N="BeginX" V="3"/><Cell N="EndX" V="5"/>
   <Text><cp IX="0"/><fld IX="0"/></Text>
  </Shape>
 </Shapes>
 <Connects>
  <Connect FromSheet="3" FromCell="BeginX" ToSheet="1" ToCell="PinX"/>
  <Connect FromSheet="3" FromCell="EndX" ToSheet="2" ToCell="PinX"/>
 </Connects>
</PageContents>
"""

DOCX_DOCUMENT = """<?xml version="1.0" encoding="UTF-8"?>
<w:document
 xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:v="urn:schemas-microsoft-com:vml"
 xmlns:o="urn:schemas-microsoft-com:office:office">
 <w:body>
  <w:p><w:r><w:t>Synthetic Visio example</w:t></w:r></w:p>
  <w:p><w:r><w:object>
   <v:shape><v:imagedata r:id="rIdPreview"/></v:shape>
   <o:OLEObject Type="Embed" ProgID="Visio.Drawing.15" r:id="rIdVisio"/>
  </w:object></w:r></w:p>
  <w:p><w:r><w:t>The diagram above is generated and contains no confidential data.</w:t></w:r></w:p>
 </w:body>
</w:document>
"""

DOCX_RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rIdPreview" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>
 <Relationship Id="rIdVisio" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/package" Target="embeddings/synthetic.vsdx"/>
</Relationships>
"""

DOCX_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="xml" ContentType="application/xml"/>
 <Default Extension="png" ContentType="image/png"/>
 <Default Extension="vsdx" ContentType="application/vnd.ms-visio.drawing"/>
 <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""

DOCX_ROOT_RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""

# A valid 1x1 transparent PNG.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAF"
    "gAI/ScL5WQAAAABJRU5ErkJggg=="
)


def write_vsdx(path: Path) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES)
        archive.writestr("_rels/.rels", ROOT_RELS)
        archive.writestr("visio/document.xml", VISIO_DOCUMENT)
        archive.writestr("visio/pages/pages.xml", PAGES)
        archive.writestr("visio/pages/_rels/pages.xml.rels", PAGES_RELS)
        archive.writestr("visio/pages/page1.xml", PAGE)
    return path.read_bytes()


def write_docx(path: Path, vsdx: bytes) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", DOCX_CONTENT_TYPES)
        archive.writestr("_rels/.rels", DOCX_ROOT_RELS)
        archive.writestr("word/document.xml", DOCX_DOCUMENT)
        archive.writestr("word/_rels/document.xml.rels", DOCX_RELS)
        archive.writestr("word/media/image1.png", PNG)
        archive.writestr("word/embeddings/synthetic.vsdx", vsdx)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir", type=Path, default=Path("samples"), help="Output directory"
    )
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    vsdx_path = output / "synthetic-flow.vsdx"
    docx_path = output / "synthetic-word-with-visio.docx"
    write_docx(docx_path, write_vsdx(vsdx_path))
    print(vsdx_path)
    print(docx_path)


if __name__ == "__main__":
    main()

