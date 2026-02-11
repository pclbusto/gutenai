
import unittest
import os
import shutil
from pathlib import Path
from core.guten_core import GutenCore

class TestHookIndex(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_epub_env").resolve()
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir()
        
        # Create minimal EPUB structure
        self.text_dir = self.test_dir / "OEBPS" / "Text"
        self.text_dir.mkdir(parents=True)
        
        # Create OPF
        (self.test_dir / "META-INF").mkdir()
        (self.test_dir / "META-INF" / "container.xml").write_text("""<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
   <rootfiles>
      <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
   </rootfiles>
</container>""")

        self.opf_content = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata>
    <dc:title xmlns:dc="http://purl.org/dc/elements/1.1/">Test Book</dc:title>
  </metadata>
  <manifest>
    <item id="chap1" href="Text/chap1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chap1"/>
  </spine>
</package>"""
        (self.test_dir / "OEBPS" / "content.opf").write_text(self.opf_content)
        
        # Create HTML with hooks
        self.html_content = """
        <html>
            <body>
                <h1 id="heading1">Chapter 1</h1>
                <p id="para-1">First paragraph.</p>
                <div id="complex-id-123">Content</div>
            </body>
        </html>
        """
        (self.text_dir / "chap1.xhtml").write_text(self.html_content)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_indexing(self):
        # Open core
        core = GutenCore.open_folder(self.test_dir)
        
        # Check index
        stats = core.hook_index.build_full_index()
        print(f"Stats: {stats}")
        
        hooks = core.hook_index.get_all_hooks()
        ids = [h.hook_id for h in hooks]
        
        print(f"Found IDs: {ids}")
        
        self.assertIn("heading1", ids)
        self.assertIn("para-1", ids)
        self.assertIn("complex-id-123", ids)

if __name__ == "__main__":
    unittest.main()
