"""Set FONT_BOOK_MANIFEST to a released font-kit manifest; install requirements-book.txt.

Optional CFF_FONT and CFF_WEBFONT enable the CFF vector smoke test.
"""
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


@unittest.skipUnless(os.environ.get('FONT_BOOK_MANIFEST'), 'Set FONT_BOOK_MANIFEST for specimen tests')
class FontBookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
        from font_book import Book
        from reportlab.pdfgen import canvas
        cls.Book=Book;cls.canvas=canvas
        cls.manifest=Path(os.environ['FONT_BOOK_MANIFEST']).resolve()

    def test_missing_glyph_is_rejected(self):
        book=self.Book(self.manifest);book.c=self.canvas.Canvas(io.BytesIO());book.paper()
        with self.assertRaisesRegex(ValueError,'missing glyphs'):
            book.text('\U0010FFFF',book.regular,24,48,100)

    def test_false_weight_label_is_rejected(self):
        data=json.loads(self.manifest.read_text())
        data['styles'][0]['weight']=900 if data['styles'][0]['weight']!=900 else 100
        for row in data['styles']:
            row['font']=str(self.manifest.parent/row['font'])
            row['webfont']=str(self.manifest.parent/row['webfont'])
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'invalid.json';path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'label/weight'):self.Book(path)

    def test_failed_book_leaves_no_partial_release(self):
        book=self.Book(self.manifest)
        def failure(*args):raise RuntimeError('Injected late PDF failure')
        book.symbol_page=failure
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'release'
            with self.assertRaisesRegex(RuntimeError,'Injected'):book.build(output)
            self.assertFalse(output.exists())
            self.assertFalse(list(Path(temp).glob('.release-*')))

    def test_cff_vector_line(self):
        if not os.environ.get('CFF_FONT') or not os.environ.get('CFF_WEBFONT'):
            self.skipTest('Set CFF_FONT and CFF_WEBFONT for vector outline test')
        data=json.loads(self.manifest.read_text())
        data['styles']=[{'label':'Medium','weight':500,'font':os.environ['CFF_FONT'],'webfont':os.environ['CFF_WEBFONT']}]
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'cff.json';path.write_text(json.dumps(data));book=self.Book(path)
            memory=io.BytesIO();book.c=self.canvas.Canvas(memory);book.paper()
            book.text('乱写 Font 123',book.hero,30,48,100);book.c.save()
            self.assertTrue(memory.getvalue().startswith(b'%PDF'))


if __name__=='__main__':unittest.main()
