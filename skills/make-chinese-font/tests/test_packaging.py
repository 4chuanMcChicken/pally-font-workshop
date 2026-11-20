import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from package_font import package

class PackagingTests(unittest.TestCase):
    def test_flatten_preserves_fonts_and_relocates_references(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); kit=p/'kit';(kit/'fonts/regular').mkdir(parents=True);(kit/'handbook').mkdir()
            font=kit/'fonts/regular/Sample-Regular.ttf';font.write_bytes(b'unchanged font bytes')
            (font.parent/'Sample-Regular.woff2').write_bytes(b'web font')
            (font.parent/'fonts.css').write_text('src:url("Sample-Regular.ttf"); src:url("Sample-Regular.woff2")')
            (kit/'book-manifest.json').write_text(json.dumps({'styles':[{'font':'fonts/regular/Sample-Regular.ttf','webfont':'fonts/regular/Sample-Regular.woff2'}]}))
            (kit/'handbook/preview.html').write_text('src:url("../fonts/regular/Sample-Regular.woff2")')
            out=p/'release';z=p/'release.zip';package(kit,out,z)
            self.assertEqual(set(x.name for x in out.iterdir()),{'Sample-Regular.ttf','资料'})
            self.assertEqual(((out/font.name).resolve()).read_bytes(),font.read_bytes())
            manifest=out/'资料/book-manifest.json';row=json.loads(manifest.read_text())['styles'][0]
            self.assertEqual((manifest.parent/row['font']).resolve(),(out/font.name).resolve())
            self.assertTrue((manifest.parent/row['webfont']).is_file())
            self.assertIn('../../../Sample-Regular.ttf',(out/'资料/fonts/regular/fonts.css').read_text())
            with zipfile.ZipFile(z) as archive:self.assertIsNone(archive.testzip())
            self.assertTrue(font.exists())
    def test_duplicate_names_stop_before_output(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);kit=p/'kit'
            for name in ['a','b']:
                (kit/name).mkdir(parents=True);(kit/name/'same.ttf').write_bytes(b'x')
            with self.assertRaisesRegex(ValueError,'Duplicate'):package(kit,p/'out')
            self.assertFalse((p/'out').exists())
    def test_existing_target_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'kit').mkdir();(p/'out').mkdir();(p/'out/keep').write_text('keep')
            with self.assertRaises(ValueError):package(p/'kit',p/'out')
            self.assertEqual((p/'out/keep').read_text(),'keep')

if __name__=='__main__':unittest.main()
