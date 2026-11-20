"""Set FONT_BOOK_MANIFEST to a real released kit manifest."""
import base64,json,os,re,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from font_book import Book

@unittest.skipUnless(os.environ.get('FONT_BOOK_MANIFEST'),'Set FONT_BOOK_MANIFEST')
class PortablePreviewTests(unittest.TestCase):
    def make_book(self):return Book(os.environ['FONT_BOOK_MANIFEST'])
    def test_all_webfont_bytes_and_shared_coverage_are_embedded(self):
        b=self.make_book()
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);b.write_html(p,p);html=(p/'preview.html').read_text()
            blobs=re.findall(r'data:font/woff2;base64,([A-Za-z0-9+/=]+)',html)
            self.assertEqual([base64.b64decode(x) for x in blobs],[r['webpath'].read_bytes() for r in b.styles])
            self.assertNotIn('fetch(',html)
            embedded=json.loads(re.search(r'new Set\((\[[0-9,]+\])\)',html)[1])
            expected=set.intersection(*(set(r['cm']) for r in b.styles))
            self.assertEqual(set(embedded),expected)
            self.assertEqual(set(json.loads((p/'coverage-codepoints.json').read_text())),expected)
    def test_external_mode_still_resolves_to_actual_font_files(self):
        b=self.make_book();b.data['embed_webfonts']=False
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);b.write_html(p,p);html=(p/'preview.html').read_text()
            paths=re.findall(r'src:url\(("[^"\n]+")\)',html)
            self.assertEqual([(p/json.loads(x)).resolve() for x in paths],[r['webpath'] for r in b.styles])
    def test_traditional_controls_follow_manifest_without_converting_sample(self):
        b=self.make_book();b.data['language']='zh-Hant-TW';b.data['sample_line']='叶葉 风風'
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);b.write_html(p,p);html=(p/'preview.html').read_text()
            self.assertIn('lang="zh-Hant-TW"',html)
            self.assertIn('<button id="apply">套用試字</button>',html)
            self.assertIn('叶葉 风風',html)

if __name__=='__main__':unittest.main()
