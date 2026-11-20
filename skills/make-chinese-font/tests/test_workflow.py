"""Behavior checks. Set FONT_TEST_BASE, FONT_TEST_LICENSE and FONT_TEST_CONFIG.

Uses a small temporary subset for speed. Full-font release checks are separate.
Run: python -m unittest discover -s tests -v
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from importlib.util import spec_from_file_location, module_from_spec
from types import SimpleNamespace
from unittest.mock import patch
import io

from fontTools import subset
from fontTools.ttLib import TTFont


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.script = Path(__file__).resolve().parents[1] / 'scripts/cjk_font.py'
        spec = spec_from_file_location('cjk_test_engine',cls.script)
        cls.engine = module_from_spec(spec); spec.loader.exec_module(cls.engine)
        cls.license = Path(os.environ['FONT_TEST_LICENSE'])
        cls.cfg = json.loads(Path(os.environ['FONT_TEST_CONFIG']).read_text(encoding='utf-8'))
        cls.cfg.update(family='Workflow Han', display_name='工作流测试', subset=True)
        cls.config = cls.root/'design.json'
        cls.config.write_text(json.dumps(cls.cfg), encoding='utf-8')
        font = TTFont(os.environ['FONT_TEST_BASE'])
        options = subset.Options()
        options.name_IDs = ['*']
        options.name_languages = ['*']
        options.layout_features = ['*']
        sub = subset.Subsetter(options=options)
        sub.populate(text='一小伴你好世界新增测试Pally 123，。！')
        sub.subset(font)
        cls.base = cls.root/('base.ttf' if 'glyf' in font else 'base.otf')
        font.save(cls.base)
        cls.base_count = len(font.getBestCmap())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def call(self, command, *args, expected=0):
        result = subprocess.run([sys.executable, str(self.script), command,
                                 str(self.base), *map(str, args)], capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def build(self, mode, name, text, *extra, expected=0, config=None):
        corpus = self.root/(name+'.txt')
        corpus.write_text(text, encoding='utf-8')
        output = self.root/name
        result = self.call(mode, '--config', config or self.config, '--text-file', corpus,
                           '--license', self.license, '--out', output, *extra, expected=expected)
        return output, result

    def test_export_overrides_old_subset_recipe(self):
        output, _ = self.build('export', 'full', '小伴')
        report = json.loads((output/'report.json').read_text())
        self.assertEqual(report['codepoints'], self.base_count)
        self.assertEqual(report['coverage']['omitted_base_codepoints'], 0)
        self.assertFalse(json.loads((output/'design.json').read_text())['subset'])

    def test_legacy_build_defaults_to_full(self):
        cfg = dict(self.cfg)
        del cfg['subset']
        path = self.root/'default-config.json'
        path.write_text(json.dumps(cfg))
        output, _ = self.build('build', 'default-full', '小伴', config=path)
        self.assertEqual(json.loads((output/'report.json').read_text())['codepoints'], self.base_count)

    def test_preview_accumulates_characters(self):
        first, _ = self.build('preview', 'preview-one', '小伴')
        second, _ = self.build('preview', 'preview-two', '你好', '--previous-build', first)
        report = json.loads((second/'report.json').read_text())
        self.assertEqual(report['coverage']['required_corpus_codepoints'], 4)
        self.assertEqual((second/'corpus.txt').read_text(), '小伴\n你好')
        self.assertGreater(report['coverage']['omitted_base_codepoints'], 0)

    def test_rejects_changed_recipe_for_accumulation(self):
        first, _ = self.build('preview', 'drift-first', '小伴')
        cfg = dict(self.cfg, family='Other Han')
        path = self.root/'changed.json'
        path.write_text(json.dumps(cfg))
        output, result = self.build('preview', 'drift-second', '你好', '--previous-build', first,
                                   expected=2, config=path)
        self.assertIn('different source or recipe', result.stderr)
        self.assertFalse(output.exists())

    def test_missing_characters_save_diagnostics_and_fail(self):
        charset = self.root/'missing.txt'
        charset.write_text('小伴\U0010FFFF', encoding='utf-8')
        report = self.root/'missing.json'
        self.call('coverage', '--charset-file', charset, '--out', report, expected=2)
        data = json.loads(report.read_text())
        self.assertEqual(data['missing'], [{'char': '\U0010FFFF', 'code': 'U+10FFFF'}])

    def test_missing_corpus_fails_without_output(self):
        output, _ = self.build('export', 'missing-build', '小伴\U0010FFFF', expected=2)
        self.assertFalse(output.exists())

    def test_does_not_overwrite_existing_release(self):
        output, _ = self.build('export', 'immutable', '小伴')
        original = (output/'report.json').read_bytes()
        self.build('export', 'immutable', '你好', expected=2)
        self.assertEqual((output/'report.json').read_bytes(), original)

    def test_mapping_swap_is_detected_even_when_widths_match(self):
        original = TTFont(self.base); changed = TTFont(self.base); seen = set()
        for table in changed['cmap'].tables:
            if table.isUnicode() and hasattr(table,'cmap') and id(table.cmap) not in seen:
                seen.add(id(table.cmap))
                table.cmap[ord('你')],table.cmap[ord('好')] = table.cmap[ord('好')],table.cmap[ord('你')]
        self.assertEqual(set(original.getBestCmap()),set(changed.getBestCmap()))
        with self.assertRaisesRegex(ValueError,'mapping changed'):
            self.engine.assert_mapping_equal(original,changed)
        self.assertNotEqual(self.engine.shape(original,'你好','zh-Hans'),self.engine.shape(changed,'你好','zh-Hans'))

    def test_actual_shaped_substitution_is_checked(self):
        from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
        original = TTFont(self.base); changed = TTFont(self.base)
        if 'GSUB' in changed: del changed['GSUB']
        cm=changed.getBestCmap()
        addOpenTypeFeaturesFromString(changed, 'languagesystem hani ZHS; feature locl { script hani; language ZHS; sub '+cm[ord('你')]+' by '+cm[ord('好')]+'; } locl;')
        self.engine.assert_mapping_equal(original,changed)
        self.assertNotEqual(self.engine.shape(original,'你好','zh-Hans'),self.engine.shape(changed,'你好','zh-Hans'))

    def test_mixed_text_is_split_into_script_runs(self):
        self.assertEqual([script for _,script,_ in self.engine.script_runs('Pally 中文')],['Latn','Hani'])
        self.assertEqual([script for _,script,_ in self.engine.script_runs('中文 Pally')],['Hani','Latn'])

    def test_synthesized_glyph_names_do_not_cause_false_mapping_failure(self):
        font=TTFont(self.base)
        if 'glyf' not in font:self.skipTest('post 3 synthetic-name fixture is TrueType-specific')
        name=font.getBestCmap()[ord('一')]
        for table in font['cmap'].tables:
            if table.isUnicode() and hasattr(table,'cmap'):table.cmap[0x2F00]=name
        font['post'].formatType=3.0
        mem=io.BytesIO();font.save(mem);mem.seek(0);reopened=TTFont(mem)
        self.assertNotEqual(font.getBestCmap()[ord('一')],reopened.getBestCmap()[ord('一')])
        self.engine.assert_equivalent(font,reopened,'一你好','zh-Hans')

    def direct_args(self,name,config=None):
        corpus=self.root/(name+'.txt'); corpus.write_text('小伴你好',encoding='utf-8')
        return SimpleNamespace(command='preview',font=str(self.base),config=str(config or self.config),
                               text_file=str(corpus),license=str(self.license),out=str(self.root/name))

    def test_failed_web_export_leaves_no_partial_release(self):
        original_save=TTFont.save
        def fail_web(font,target,*args,**kwargs):
            if font.flavor=='woff2': raise RuntimeError('injected WOFF2 failure')
            return original_save(font,target,*args,**kwargs)
        args=self.direct_args('failed-web')
        with patch.object(TTFont,'save',fail_web),self.assertRaisesRegex(RuntimeError,'injected'),redirect_stdout(io.StringIO()):
            self.engine.build(args)
        self.assertFalse(Path(args.out).exists())
        self.assertFalse(list(self.root.glob('.failed-web-*')))

    def test_xml_round_trip_must_recompile_and_preserve_mapping(self):
        original_import=TTFont.importXML
        def corrupt_import(font,*args,**kwargs):
            result=original_import(font,*args,**kwargs)
            for table in font['cmap'].tables:
                if table.isUnicode() and hasattr(table,'cmap'): table.cmap.pop(ord('小'),None)
            return result
        args=self.direct_args('bad-roundtrip')
        with patch.object(TTFont,'importXML',corrupt_import),self.assertRaisesRegex(ValueError,'mapping changed'),redirect_stdout(io.StringIO()):
            self.engine.build(args)
        self.assertFalse(Path(args.out).exists())

    def test_chinese_internal_names_are_written(self):
        output,_=self.build('preview','localized','小伴')
        font=TTFont(next(p for p in output.iterdir() if p.suffix in ['.ttf','.otf']))
        self.assertEqual(font['name'].getName(16,3,1,0x804).toUnicode(),'工作流测试')
        self.assertEqual(font['name'].getName(17,3,1,0x804).toUnicode(),self.engine.STYLE_ZH[self.cfg['style']])
        self.assertTrue(font['name'].getDebugName(6).isascii())

    def test_native_600_weight_is_supported(self):
        # Synthetic metadata fixture checks the contract; a real 600 source is built separately.
        font=TTFont(self.base);font['OS/2'].usWeightClass=600
        native=self.root/('native600.ttf' if 'glyf' in font else 'native600.otf');font.save(native)
        cfg=dict(self.cfg,style='SemiBold',weight=600);config=self.root/'600.json';config.write_text(json.dumps(cfg))
        args=self.direct_args('native600',config);args.font=str(native)
        with redirect_stdout(io.StringIO()): self.engine.build(args)
        report=json.loads((Path(args.out)/'report.json').read_text())
        self.assertEqual(report['style'],'SemiBold')

    def test_cannot_relabel_existing_weight(self):
        weight=600 if self.cfg['weight']!=600 else 800
        style='SemiBold' if weight==600 else 'ExtraBold'
        path=self.root/'mismatch.json';path.write_text(json.dumps(dict(self.cfg,weight=weight,style=style)))
        output,result=self.build('preview','fake-weight','小伴',config=path,expected=2)
        self.assertIn('cannot manufacture a new weight',result.stderr)
        self.assertFalse(output.exists())

    def test_standard_profiles_are_counted_and_strict_mode_blocks_missing(self):
        font=TTFont(self.base);profiles=self.engine.profile_checks(font)
        self.assertEqual(profiles['common-3500']['required'],3500)
        self.assertEqual(profiles['standard-8105']['required'],8105)
        self.assertTrue(profiles['common-3500']['missing'])
        path=self.root/'strict.json';path.write_text(json.dumps(dict(self.cfg,required_coverage_profiles=['common-3500'])))
        output,result=self.build('export','strict-missing','小伴',config=path,expected=2)
        self.assertIn('Required coverage profile',result.stderr)
        self.assertFalse(output.exists())

    def edit_manifest(self,font):
        if 'glyf' not in font: self.skipTest('Pilot outline editing supports static glyf only')
        name=font.getBestCmap()[ord('一')]
        aliases=''.join(chr(cp) for cp,gn in sorted(font.getBestCmap().items()) if gn==name)
        return {'source_sha256':self.engine.digest(self.base),'units_per_em':font['head'].unitsPerEm,
                'coordinate_system':'font units, Y up','edits':[{'characters':aliases,'path':'M100 300 L900 300 L900 400 L100 400 Z','note':'test drawing'}]}

    def test_core_outline_edit_changes_geometry_without_dropping_characters(self):
        font=TTFont(self.base);manifest=self.edit_manifest(font)
        before=font.getBestCmap().copy()
        records=self.engine.apply_glyph_edits(font,manifest,self.engine.digest(self.base))
        self.assertEqual(before,font.getBestCmap())
        self.assertTrue(records[0]['outline_changed'])
        self.assertEqual(records[0]['advance_preserved'],TTFont(self.base)['hmtx'][before[ord('一')]][0])

    def test_core_edit_rejects_wrong_source(self):
        font=TTFont(self.base);manifest=self.edit_manifest(font);manifest['source_sha256']='wrong'
        with self.assertRaisesRegex(ValueError,'SHA256'): self.engine.apply_glyph_edits(font,manifest,self.engine.digest(self.base))

    def test_core_edit_rejects_out_of_bounds(self):
        font=TTFont(self.base);manifest=self.edit_manifest(font)
        manifest['edits'][0]['path']='M0 0 L100000 0 L100000 100000 Z'
        with self.assertRaisesRegex(ValueError,'bounds'): self.engine.apply_glyph_edits(font,manifest,self.engine.digest(self.base))

    def test_core_edit_is_validated_in_complete_export(self):
        font=TTFont(self.base);manifest=self.edit_manifest(font)
        path=self.root/'edit-config.json';path.write_text(json.dumps(dict(self.cfg,glyph_edits=manifest)))
        output,_=self.build('export','core-edit','小伴',config=path)
        report=json.loads((output/'report.json').read_text())
        self.assertEqual(report['codepoints'],self.base_count)
        self.assertEqual(report['design_changes']['edited_existing_glyphs'],1)
        self.assertTrue(report['design_changes']['edits'][0]['outline_changed'])

    def test_open_core_contour_is_rejected(self):
        font=TTFont(self.base);manifest=self.edit_manifest(font)
        manifest['edits'][0]['path']='M100 300 L900 300 L900 400'
        with self.assertRaisesRegex(ValueError,'open contour'): self.engine.apply_glyph_edits(font,manifest,self.engine.digest(self.base))

    def test_undeclared_aliases_are_rejected(self):
        font=TTFont(self.base);manifest=self.edit_manifest(font)
        name=font.getBestCmap()[ord('一')]
        for table in font['cmap'].tables:
            if table.isUnicode() and hasattr(table,'cmap'):table.cmap[0x2F00]=name
        with self.assertRaisesRegex(ValueError,'aliases'): self.engine.apply_glyph_edits(font,manifest,self.engine.digest(self.base))

    def test_shared_components_cannot_change_silently(self):
        from fontTools.pens.ttGlyphPen import TTGlyphPen
        font=TTFont(self.base);manifest=self.edit_manifest(font);cm=font.getBestCmap()
        pen=TTGlyphPen(font.getGlyphSet());pen.addComponent(cm[ord('一')],(1,0,0,1,0,0))
        font['glyf'][cm[ord('好')]]=pen.glyph()
        with self.assertRaisesRegex(ValueError,'shared composite component'): self.engine.apply_glyph_edits(font,manifest,self.engine.digest(self.base))


if __name__ == '__main__':
    unittest.main()
