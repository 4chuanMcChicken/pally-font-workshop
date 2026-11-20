"""Mapping benchmarks only: these tests do not certify regional glyph forms."""
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from cjk_font import CHARSETS,profile_checks

class MappingFont:
    def __init__(self,characters):self.cm={ord(c):'glyph'+str(ord(c)) for c in characters}
    def getBestCmap(self):return self.cm

class TraditionalProfileTests(unittest.TestCase):
    def test_traditional_regions_receive_their_mapping_benchmark(self):
        text=(CHARSETS/'big5-common-5401.txt').read_text()
        self.assertEqual(len(set(text)),5401)
        for region in ['zh-Hant-TW','zh-Hant-HK']:
            p=profile_checks(MappingFont(text),region)
            self.assertEqual(p['big5-common-5401']['covered'],5401)
            self.assertEqual(p['big5-common-5401']['missing'],[])
            self.assertNotIn('common-3500',p)
    def test_simplified_benchmarks_remain_separate(self):
        p=profile_checks(MappingFont('葉'),'zh-Hans')
        self.assertIn('common-3500',p)
        self.assertIn('standard-8105',p)
        self.assertNotIn('big5-common-5401',p)
    def test_one_reference_character_is_not_full_traditional_coverage(self):
        p=profile_checks(MappingFont('葉'),'zh-Hant-TW')['big5-common-5401']
        self.assertEqual(p['covered'],1)
        self.assertEqual(len(p['missing']),5400)

if __name__=='__main__':unittest.main()
