from __future__ import annotations

import zipfile
from pathlib import Path


DOCUMENT_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document
 xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:v="urn:schemas-microsoft-com:vml"
 xmlns:o="urn:schemas-microsoft-com:office:office">
 <w:body>
  <w:p><w:r><w:t>Before diagram</w:t></w:r></w:p>
  <w:p>
   <w:r>
    <w:object>
     <v:shape><v:imagedata r:id="rIdPreview"/></v:shape>
     <o:OLEObject Type="Embed" ProgID="Visio.Drawing.15" r:id="rIdVisio"/>
    </w:object>
   </w:r>
  </w:p>
  <w:p><w:r><w:t>After diagram</w:t></w:r></w:p>
 </w:body>
</w:document>
"""

RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rIdPreview"
  Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
  Target="media/image1.png"/>
 <Relationship Id="rIdVisio"
  Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/package"
  Target="embeddings/Microsoft_Visio_1.vsdx"/>
</Relationships>
"""

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="xml" ContentType="application/xml"/>
</Types>
"""


def make_docx(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES)
        archive.writestr("word/document.xml", DOCUMENT_XML)
        archive.writestr("word/_rels/document.xml.rels", RELS_XML)
        archive.writestr("word/media/image1.png", b"preview")
        archive.writestr(
            "word/embeddings/Microsoft_Visio_1.vsdx", b"PK fake-vsdx"
        )

