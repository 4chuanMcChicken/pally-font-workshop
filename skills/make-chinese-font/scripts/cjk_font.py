#!/usr/bin/env python3
"""CJK reference profiling and OFL native-axis font-kit builder. No network access."""
import argparse, hashlib, html, io, json, math, os, re, shutil, tempfile, unicodedata
from pathlib import Path
from types import SimpleNamespace
from fontTools.ttLib import TTFont, TTLibError
from fontTools import subset
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.unicodedata import script as unicode_script

STYLES = {'Thin':100, 'ExtraLight':200, 'Light':300, 'Regular':400,
          'Medium':500, 'SemiBold':600, 'Bold':700, 'ExtraBold':800, 'Black':900}
STYLE_ZH = {'Thin':'极细', 'ExtraLight':'特细', 'Light':'细体', 'Regular':'常规',
            'Medium':'中等', 'SemiBold':'半粗', 'Bold':'粗体', 'ExtraBold':'特粗', 'Black':'重黑'}
STYLE_ZH_TRAD = {'Thin':'極細', 'ExtraLight':'特細', 'Light':'細體', 'Regular':'常規',
                 'Medium':'中等', 'SemiBold':'半粗', 'Bold':'粗體', 'ExtraBold':'特粗', 'Black':'重黑'}
CHARSETS = Path(__file__).resolve().parents[1]/'assets/charsets'

def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load(path):
    if Path(path).read_bytes()[:4] == b'ttcf':
        raise ValueError('TTC/OTC: extract and verify the intended regional face first.')
    return TTFont(path)

def chars(text):
    return sorted(set(ord(c) for c in text if c not in '\r\n\t'))

def coverage(font, text):
    cm = font.getBestCmap() or {}
    return [{'char': chr(c), 'code': f'U+{c:04X}'} for c in chars(text) if cm.get(c) in [None, '.notdef']]

def coverage_summary(font):
    cm = font.getBestCmap() or {}
    valid = {cp for cp, glyph in cm.items() if glyph != '.notdef'}
    # Character counts, not language support or design-completion claims.
    return {'mapped_codepoints': len(cm), 'usable_codepoints': len(valid),
            'han_named_codepoints': sum(unicodedata.name(chr(cp), '').startswith(
                ('CJK UNIFIED IDEOGRAPH-', 'CJK COMPATIBILITY IDEOGRAPH-')) for cp in valid),
            'ascii_printable': sum(cp in valid for cp in range(0x20, 0x7F)),
            'supplementary_codepoints': sum(cp > 0xFFFF for cp in valid),
            'notdef_mappings': [f'U+{cp:04X}' for cp, glyph in cm.items() if glyph == '.notdef'],
            'classification_unicode_version': unicodedata.unidata_version}

def check_coverage(a):
    f = load(a.font)
    text = Path(a.charset_file).read_text(encoding='utf-8')
    if not text.strip(): raise ValueError('Character list is empty')
    if any(0xFE00 <= ord(c) <= 0xFE0F or 0xE0100 <= ord(c) <= 0xE01EF for c in text):
        raise ValueError('Variation sequences require separate cmap14/IVS verification')
    missing = coverage(f, text)
    write(a.out, {'font_sha256': digest(a.font), 'charset_sha256': digest(a.charset_file),
                  'required_codepoints': len(chars(text)), 'covered_codepoints': len(chars(text)) - len(missing),
                  'missing': missing, 'coverage': coverage_summary(f),
                  'scope': 'character mapping only; not regional-form or shaping certification'})
    if missing: raise ValueError(f'{len(missing)} required characters missing; see {a.out}')

def recipe_identity(cfg):
    return {k: v for k, v in cfg.items() if k != 'subset'}

def profile_checks(font, language='zh-Hans'):
    manifest = json.loads((CHARSETS/'index.json').read_text(encoding='utf-8'))
    result = {}
    for key, entry in manifest.items():
        if entry['language'] not in [language, 'zh'] and not (entry['language']=='zh-Hant' and language.startswith('zh-Hant-')):
            continue
        path = CHARSETS/entry['file']
        if digest(path) != entry['sha256']:
            raise ValueError('Character profile checksum mismatch: '+key)
        text = path.read_text(encoding='utf-8')
        if len(chars(text)) != entry['count']:
            raise ValueError('Character profile count mismatch: '+key)
        missing = coverage(font, text)
        result[key] = {'required':entry['count'], 'covered':entry['count']-len(missing),
                       'missing':missing, 'source':entry['source'], 'version':entry['version'],
                       'charset_sha256':entry['sha256'], 'scope':'Unicode mapping only; not a font standard certification'}
    return result

def unicode_mappings(font):
    result = {}
    for table in font['cmap'].tables:
        if not table.isUnicode():
            continue
        key = (table.platformID, table.platEncID, table.format, getattr(table, 'language', None))
        # A post format 3 font can synthesize different glyph names on reopen.
        # The builder preserves glyph ordering; names are not mapping identity.
        value = ({cp:font.getGlyphID(name) for cp,name in getattr(table,'cmap',{}).items()},
                 {selector:[(cp,None if name is None else font.getGlyphID(name)) for cp,name in pairs]
                  for selector,pairs in getattr(table,'uvsDict',{}).items()})
        if key in result and result[key] != value:
            raise ValueError('Conflicting duplicate Unicode cmap tables')
        result[key] = value
    return result

def assert_mapping_equal(expected, actual):
    if unicode_mappings(expected) != unicode_mappings(actual):
        raise ValueError('Unicode character-to-glyph mapping changed')

def normalized(value):
    if isinstance(value, (int, float)):
        if not math.isfinite(value): raise ValueError('Non-finite outline coordinate')
        return round(float(value), 6)
    if isinstance(value, (tuple, list)):
        return [normalized(v) for v in value]
    return value

def outline_digest(glyphset, name):
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    pen = DecomposingRecordingPen(glyphset)
    glyphset[name].draw(pen)
    return hashlib.sha256(json.dumps(normalized(pen.value), separators=(',',':')).encode()).hexdigest()

def script_runs(text):
    scripts = [unicode_script(c) for c in text]
    previous = None
    for i, tag in enumerate(scripts):
        if tag not in ['Zyyy', 'Zinh', 'Zzzz']:
            previous = tag
        else:
            scripts[i] = previous
    following = 'Hani'
    for i in range(len(scripts)-1, -1, -1):
        if scripts[i] is None: scripts[i] = following
        else: following = scripts[i]
    start = 0
    for i in range(1, len(text)+1):
        if i == len(text) or scripts[i] != scripts[start]:
            yield text[start:i], scripts[start], start
            start = i

def assert_equivalent(expected, actual, text, language):
    assert_mapping_equal(expected, actual)
    if expected['head'].unitsPerEm != actual['head'].unitsPerEm:
        raise ValueError('Units per em changed')
    if shape(expected, text, language) != shape(actual, text, language):
        raise ValueError('Shaped glyph outlines, clusters or positions changed')

def glyph_template(a):
    from fontTools.pens.svgPathPen import SVGPathPen
    font = load(a.font)
    if 'glyf' not in font or 'fvar' in font:
        raise ValueError('Core glyph editing currently requires a static glyf font')
    if Path(a.out).exists(): raise ValueError('Glyph template already exists; use a new file')
    if coverage(font, a.text): raise ValueError('Template characters are missing from the base')
    cm = font.getBestCmap(); gs = font.getGlyphSet(); seen = set(); entries = []
    for char in a.text:
        name = cm[ord(char)]
        if name in seen: continue
        seen.add(name)
        pen = SVGPathPen(gs); gs[name].draw(pen)
        aliases = ''.join(chr(cp) for cp, glyph in sorted(cm.items()) if glyph == name)
        entries.append({'characters':aliases, 'path':pen.getCommands(), 'note':'Edit this outline in font units (Y up); keep advance unchanged'})
    if not entries: raise ValueError('No template characters supplied')
    write(a.out, {'source_sha256':digest(a.font), 'units_per_em':font['head'].unitsPerEm,
                  'coordinate_system':'font units, Y up', 'edits':entries})

def apply_glyph_edits(font, manifest, source_sha256):
    if manifest is None: return []
    if 'glyf' not in font or 'fvar' in font:
        raise ValueError('Core glyph editing currently requires a static glyf font')
    if not isinstance(manifest, dict) or manifest.get('source_sha256') != source_sha256:
        raise ValueError('Glyph edit manifest does not match source SHA256')
    if manifest.get('units_per_em') != font['head'].unitsPerEm or manifest.get('coordinate_system') != 'font units, Y up':
        raise ValueError('Glyph edit coordinate system/UPM mismatch')
    entries = manifest.get('edits')
    if not isinstance(entries, list) or not entries: raise ValueError('Glyph edit list is empty')
    from fontTools.svgLib.path import parse_path
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from fontTools.pens.cu2quPen import Cu2QuPen
    cm = font.getBestCmap(); targets = {}; records = []
    for entry in entries:
        characters = entry.get('characters')
        if not isinstance(characters, str) or not characters or coverage(font, characters):
            raise ValueError('Glyph edit characters must already exist in the base')
        names = {cm[ord(c)] for c in characters}
        if len(names) != 1: raise ValueError('Each edit must target one glyph and all its aliases')
        name = names.pop()
        aliases = {cp for cp, value in cm.items() if value == name}
        if aliases != set(map(ord, characters)):
            raise ValueError('Glyph edit must explicitly include all Unicode aliases')
        if name in targets: raise ValueError('Duplicate edited glyph')
        if not isinstance(entry.get('path'), str) or not entry['path'].strip():
            raise ValueError('Edited outline path is empty')
        targets[name] = entry
    for name in font.getGlyphOrder():
        glyph = font['glyf'][name]
        if glyph.isComposite() and any(c.glyphName in targets for c in glyph.components):
            raise ValueError('Edited glyph is a shared composite component; automatic propagation is not supported')
    for name, entry in targets.items():
        before = outline_digest(font.getGlyphSet(), name)
        class ClosedGlyphPen(TTGlyphPen):
            def endPath(self):
                raise ValueError('Edited outline contains an open contour; close every path with Z')
        pen = ClosedGlyphPen(None)
        # Cubic paths are converted with a bounded error, then quantized to TrueType units.
        converter = Cu2QuPen(pen, max_err=0.5)
        parse_path(entry['path'], converter)
        glyph = pen.glyph()
        if glyph.numberOfContours <= 0: raise ValueError('Edited glyph must have a nonempty closed outline')
        if any(not math.isfinite(v) for point in glyph.coordinates for v in point):
            raise ValueError('Edited outline has non-finite coordinates')
        glyph.recalcBounds(font['glyf'])
        os2 = font['OS/2']; upm = font['head'].unitsPerEm
        if glyph.yMax > os2.usWinAscent or glyph.yMin < -os2.usWinDescent or glyph.xMin < -upm or glyph.xMax > 2*upm:
            raise ValueError('Edited outline exceeds the supported font/line bounds')
        advance, _ = font['hmtx'][name]
        font['glyf'][name] = glyph
        font['hmtx'][name] = (advance, glyph.xMin)
        after = outline_digest(font.getGlyphSet(), name)
        records.append({'glyph':name, 'characters':entry['characters'], 'before_sha256':before,
                        'after_sha256':after, 'outline_changed':before!=after,
                        'advance_preserved':advance, 'note':entry.get('note','')})
    return records

def axes(font):
    return {a.axisTag: [a.minValue, a.defaultValue, a.maxValue] for a in font['fvar'].axes} if 'fvar' in font else {}

def inspect(a):
    f = load(a.font)
    text = Path(a.text_file).read_text() if a.text_file else ''
    features = {}
    for tag in ['GSUB', 'GPOS']:
        if tag in f and f[tag].table.FeatureList:
            features[tag] = sorted(set(r.FeatureTag for r in f[tag].table.FeatureList.FeatureRecord))
    write(a.out, {'family': f['name'].getDebugName(1), 'sha256': digest(a.font), 'axes': axes(f),
                  'glyph_count': len(f.getGlyphOrder()), 'codepoints': len(f.getBestCmap() or {}),
                  'format': 'glyf' if 'glyf' in f else 'CFF2' if 'CFF2' in f else 'CFF',
                  'features': features, 'has_uvs': any(t.format == 14 for t in f['cmap'].tables),
                  'coverage': coverage_summary(f),
                  'weight':f['OS/2'].usWeightClass, 'coverage_profiles':profile_checks(f, a.language),
                  'missing': coverage(f, text), 'regional_forms': 'not verified by cmap inspection'})

def profile(a):
    import numpy as np
    from PIL import Image
    if a.cols < 1 or not a.labels or len(a.labels) % a.cols:
        raise ValueError('labels must fill complete rows of known equal-size cells')
    im = np.asarray(Image.open(a.image).convert('L'), dtype=float) / 255
    rows = len(a.labels) // a.cols
    h, w = im.shape
    if min(h / rows, w / a.cols) < 48:
        raise ValueError('Use cells at least 48 px; smaller samples are too uncertain')
    result = []
    for i, ch in enumerate(a.labels):
        ry, cx = divmod(i, a.cols)
        cell = 1 - im[round(ry*h/rows):round((ry+1)*h/rows), round(cx*w/a.cols):round((cx+1)*w/a.cols)]
        yy, xx = np.where(cell > .5)
        if not len(xx):
            raise ValueError(f'Empty cell for {ch!r}; check crop and polarity')
        hh, ww = cell.shape
        mass = cell.sum(); gy, gx = np.indices(cell.shape)
        result.append({'character': ch, 'bbox_cell': [float(xx.min()/ww), float(yy.min()/hh), float((xx.max()+1)/ww), float((yy.max()+1)/hh)],
                       'ink_fraction': float(cell.mean()), 'ink_centroid_cell': [float((cell*gx).sum()/mass/ww), float((cell*gy).sum()/mass/hh)]})
    write(a.out, {'normalization': 'explicit screenshot cell, not font em', 'confidence': 'manual crop and label verification required',
                  'not_measured': ['stroke topology', 'radical structure', 'optical center', 'font units'], 'cells': result})

def shape(font, text, language):
    import uharfbuzz as hb
    mem = io.BytesIO(); original = font.flavor; font.flavor = None; font.save(mem); font.flavor = original
    raw = mem.getvalue()
    canonical = TTFont(io.BytesIO(raw)); glyphset = canonical.getGlyphSet(); order = canonical.getGlyphOrder(); cache = {}
    face = hb.Face(raw); hf = hb.Font(face); hb.ot_font_set_funcs(hf)
    result = []
    for line in text.splitlines():
        if not line: continue
        runs = []
        for content, script, offset in script_runs(line):
            buf = hb.Buffer(); buf.add_str(content); buf.script = script; buf.guess_segment_properties()
            buf.language = 'en' if script == 'Latn' else language
            hb.shape(hf, buf)
            glyphs = []
            for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
                if info.codepoint == 0:
                    raise ValueError('HarfBuzz produced .notdef in required corpus')
                name = order[info.codepoint]
                if name not in cache: cache[name] = outline_digest(glyphset, name)
                glyphs.append((cache[name], info.cluster+offset, pos.x_advance, pos.y_advance, pos.x_offset, pos.y_offset))
            runs.append((script, glyphs))
        result.append(runs)
    return result

def build(a):
    destination = Path(a.out).absolute()
    if destination.is_symlink() or (destination.exists() and (not destination.is_dir() or any(destination.iterdir()))):
        raise ValueError('Output directory is not empty; use a new version directory')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.'+destination.name+'-', dir=destination.parent) as temp:
        staging = Path(temp)/'release'
        report = _build(SimpleNamespace(**{**vars(a), 'out':str(staging)}))
        # Staging is on the same filesystem. A non-empty concurrent release cannot be overwritten.
        os.rename(staging, destination)
    print(json.dumps(report,ensure_ascii=False,indent=2))

def _build(a):
    cfg = json.loads(Path(a.config).read_text()); text = Path(a.text_file).read_text(encoding='utf-8')
    if a.command == 'export': cfg['subset'] = False
    elif a.command == 'preview': cfg['subset'] = True
    else: cfg.setdefault('subset', False)
    previous = getattr(a, 'previous_build', None)
    if previous:
        previous = Path(previous)
        previous_report = json.loads((previous/'report.json').read_text(encoding='utf-8'))
        previous_cfg = json.loads((previous/'design.json').read_text(encoding='utf-8'))
        if previous_report['source_sha256'] != digest(a.font) or recipe_identity(previous_cfg) != recipe_identity(cfg):
            raise ValueError('Previous preview uses a different source or recipe; build a new preview without --previous-build')
        text = (previous/'corpus.txt').read_text(encoding='utf-8') + '\n' + text
    if cfg.get('glyph_edits') is not None:
        manifest = cfg['glyph_edits']
        if not isinstance(manifest,dict) or not isinstance(manifest.get('edits'),list):
            raise ValueError('Invalid glyph edit manifest')
        if any(not isinstance(e,dict) or not isinstance(e.get('characters'),str) for e in manifest['edits']):
            raise ValueError('Invalid glyph edit entry')
        text += '\n'+''.join(e['characters'] for e in manifest['edits'])
    if not text.strip(): raise ValueError('Required corpus is empty')
    if any(0xFE00 <= ord(c) <= 0xFE0F or 0xE0100 <= ord(c) <= 0xE01EF for c in text):
        raise ValueError('Variation sequences require separate cmap14/IVS verification; this builder does not support them')
    if any(unicodedata.category(c) == 'Cc' and c not in '\n\r' for c in text):
        raise ValueError('Remove control characters (including tabs) from the test corpus')
    family = cfg['family']; style = cfg['style']; weight = cfg['weight']; version = cfg['version']; holder = cfg['holder']
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9 -]{1,60}', family): raise ValueError('Use a distinct ASCII family identifier; display_name may be Chinese')
    if STYLES.get(style) != weight: raise ValueError('Style/weight mismatch or unsupported style')
    if not re.fullmatch(r'\d{1,2}\.\d{3}', version): raise ValueError('Version must be N.NNN')
    if not holder.strip(): raise ValueError('holder required')
    if cfg.get('language') not in ['zh-Hans', 'zh-Hant-TW', 'zh-Hant-HK']: raise ValueError('Explicit Chinese region required')
    display_name = cfg.get('display_name', family)
    if not isinstance(display_name, str) or not display_name.strip(): raise ValueError('display_name must be nonempty text')
    if not isinstance(cfg.get('subset'), bool): raise ValueError('subset must explicitly be true or false')
    license_text = Path(a.license).read_text(encoding='utf-8')
    if cfg.get('license_reviewed') is not True or not isinstance(cfg.get('reserved_names'), list): raise ValueError('Verify original license and Reserved Font Names first')
    if 'SIL OPEN FONT LICENSE' not in license_text.upper() or '1.1' not in license_text: raise ValueError('Only reviewed OFL 1.1 builds supported')
    f = load(a.font); base_family = f['name'].getDebugName(1) or ''
    notices = ' '.join(n.toUnicode() for n in f['name'].names if n.nameID == 13)
    if 'open font license' not in notices.lower(): raise ValueError('Base font has no OFL name-table notice; inspect provenance manually')
    declared = re.findall(r"Reserved Font Name[s]?\s+['\"]([^'\"]+)['\"]", license_text, re.I)
    if any(n.casefold() not in [v.casefold() for v in cfg['reserved_names']] for n in declared):
        raise ValueError('Reserved Font Names in license missing from configuration')
    if f['OS/2'].fsSelection & 1 or ('post' in f and f['post'].italicAngle != 0):
        raise ValueError('Only upright bases supported; do not relabel italic as upright')
    for reserved in cfg['reserved_names'] + declared + [base_family]:
        if reserved and any(reserved.casefold() in n.casefold() for n in [family,display_name]): raise ValueError('New family conflicts with base or Reserved Font Name')
    if 'CFF2' in f or 'VARC' in f: raise ValueError('CFF2/VARC builds not implemented in v1; use a verified static or glyf VF base')
    if coverage(f,text): raise ValueError('Missing corpus characters: '+json.dumps(coverage(f,text),ensure_ascii=False))
    source_mapping = unicode_mappings(f); source_cm = set(f.getBestCmap()); source_coverage = coverage_summary(f); ax = axes(f); requested = cfg.get('axes',{})
    if ax and cfg.get('glyph_edits') is not None:
        raise ValueError('Instantiate and verify a static glyf source before editing core glyphs')
    profiles = profile_checks(f, cfg['language'])
    required_profiles = cfg.get('required_coverage_profiles', [])
    if not isinstance(required_profiles, list) or any(key not in profiles for key in required_profiles):
        raise ValueError('Unknown required coverage profile for this language')
    if any(profiles[key]['missing'] for key in required_profiles):
        raise ValueError('Required coverage profile has missing characters: '+', '.join(key for key in required_profiles if profiles[key]['missing']))
    if set(requested)-set(ax): raise ValueError('Unknown variation axis')
    loc = {k: requested.get(k, v[1]) for k,v in ax.items()}
    if any(not math.isfinite(v) or not ax[k][0] <= v <= ax[k][2] for k,v in loc.items()): raise ValueError('Axis out of range')
    if 'wght' in loc and loc['wght'] != weight: raise ValueError('wght must match the named weight in this builder')
    if 'wght' not in loc and f['OS/2'].usWeightClass != weight: raise ValueError('Static base weight differs; cannot manufacture a new weight')
    # Subset before instancing makes pilot builds tractable; retain shaping closure and all scripts.
    if cfg['subset']:
        opt = subset.Options(); opt.layout_features=['*']; opt.layout_scripts=['*']; opt.name_IDs=['*']; opt.name_languages=['*']
        sub = subset.Subsetter(options=opt); sub.populate(unicodes=chars(text)); sub.subset(f)
    if ax: f = instantiateVariableFont(f, loc, inplace=True, updateFontNames=False)
    edits = apply_glyph_edits(f, cfg.get('glyph_edits'), digest(a.font))
    baseline_mapping = unicode_mappings(f)
    baseline = shape(f,text,cfg['language'])
    ps = family.replace(' ','')+'-'+style
    copyright_text = f['name'].getDebugName(0) or ''
    if not copyright_text: raise ValueError('Missing original copyright; inspect source first')
    replacement = {0: copyright_text+'\nModifications: '+holder, 1: family if style in ['Regular','Bold'] else family+' '+style,
                   2: style if style in ['Regular','Bold'] else 'Regular', 3: version+';NONE;'+ps, 4: family+' '+style,
                   5:'Version '+version, 6:ps, 8:holder, 16:family, 17:style,
                   13:'This Font Software is licensed under the SIL Open Font License, Version 1.1.',14:'https://openfontlicense.org'}
    # Remove obsolete identity records, preserve feature-name IDs and original designer credit.
    f['name'].names=[n for n in f['name'].names if n.nameID not in set(replacement)|{7,11,18,20,21,22,25}]
    for k,v in replacement.items(): f['name'].setName(v,k,3,1,0x409)
    localized = (STYLE_ZH if cfg['language']=='zh-Hans' else STYLE_ZH_TRAD)[style]
    lang_id = {'zh-Hans':0x804, 'zh-Hant-TW':0x404, 'zh-Hant-HK':0xC04}[cfg['language']]
    for name_id, value in {1:display_name if style in ['Regular','Bold'] else display_name+' '+localized,
                           2:localized if style in ['Regular','Bold'] else ('常规' if cfg['language']=='zh-Hans' else '常規'),
                           4:display_name+' '+localized,16:display_name,17:localized}.items():
        f['name'].setName(value,name_id,3,1,lang_id)
    f['head'].fontRevision=float(version); f['OS/2'].achVendID='NONE'; f['OS/2'].usWeightClass=weight
    f['OS/2'].fsSelection &= ~((1<<0)|(1<<5)|(1<<6))
    if weight>=700: f['OS/2'].fsSelection |= (1<<5)
    elif weight==400: f['OS/2'].fsSelection |= (1<<6)
    f['head'].macStyle &= ~3
    if weight>=700: f['head'].macStyle |= 1
    if 'CFF ' in f:
        cff=f['CFF '].cff; cff.fontNames=[ps]; top=cff.topDictIndex[0]; top.FamilyName=family; top.FullName=family+' '+style; top.version=version
    out=Path(a.out)
    if out.exists() and any(out.iterdir()): raise ValueError('Output directory is not empty; use a new version directory')
    out.mkdir(parents=True,exist_ok=True)
    suffix='.ttf' if 'glyf' in f else '.otf'; desktop=out/(ps+suffix); f.flavor=None; f.save(desktop)
    actual=TTFont(desktop)
    if coverage(actual,text): raise ValueError('Output lost required characters')
    if unicode_mappings(actual)!=baseline_mapping: raise ValueError('Unicode character-to-glyph mapping changed')
    if not cfg['subset'] and unicode_mappings(actual)!=source_mapping: raise ValueError('Full build lost Unicode mappings')
    if baseline!=shape(actual,text,cfg['language']): raise ValueError('Shaping changed during renaming')
    # XML round trip checks serializability, not typographic correctness.
    xml=io.BytesIO(); actual.saveXML(xml); xml.seek(0); rt=TTFont(); rt.importXML(xml)
    binary=io.BytesIO(); rt.save(binary); binary.seek(0)
    assert_equivalent(actual, TTFont(binary), text, cfg['language'])
    web=out/(ps+'.woff2'); actual.flavor='woff2'; actual.save(web); wf=TTFont(web)
    assert_mapping_equal(actual, wf)
    if shape(wf,text,cfg['language'])!=baseline: raise ValueError('WOFF2 shaping differs')
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    gs, ws = actual.getGlyphSet(), wf.getGlyphSet()
    for cp in chars(text):
        gp=DecomposingRecordingPen(gs); wp=DecomposingRecordingPen(ws)
        gs[actual.getBestCmap()[cp]].draw(gp); ws[wf.getBestCmap()[cp]].draw(wp)
        if gp.value != wp.value: raise ValueError('WOFF2 corpus outline mismatch')
    shutil.copyfile(a.license,out/'OFL.txt'); write(out/'design.json',cfg)
    (out/'corpus.txt').write_text(text, encoding='utf-8')
    (out/'fonts.css').write_text('@font-face{font-family:"'+family+'";src:url("'+web.name+'") format("woff2");font-weight:'+str(weight)+';font-style:normal;font-display:swap;}\n')
    report={'family':family,'style':style,'version':version,'source_family':base_family,'source_sha256':digest(a.font),
            'source_license_sha256':digest(a.license),'axes':loc,'language':cfg['language'],
            'scope':'corpus subset' if cfg['subset'] else 'all base cmap characters; corpus-only shaping validation',
            'coverage': {'source':source_coverage, 'output':coverage_summary(actual),
                         'source_profiles':profiles, 'output_profiles':profile_checks(actual,cfg['language']),
                         'required_corpus_codepoints':len(chars(text)),
                         'omitted_base_codepoints':len(source_cm-set(actual.getBestCmap())),
                         'full_base_cmap_preserved':unicode_mappings(actual)==source_mapping},
            'status':'complete',
            'design_changes': {'method':'explicit glyph outline edits' if edits else 'native axis instancing' if ax else 'original outlines retained',
                               'edited_existing_glyphs':sum(e['outline_changed'] for e in edits), 'new_codepoints_added':0,
                               'edits':edits, 'component_editing':'not implemented'},
            'glyphs':len(actual.getGlyphOrder()),'codepoints':len(actual.getBestCmap()),'missing':[],
            'passed':['required corpus coverage','no .notdef in horizontal corpus','name-change shaped outline/cluster/position invariance','WOFF2 shaped outline/cluster/position parity','WOFF2 corpus outline parity','all Unicode cmap tables retained','XML binary recompile and semantic round trip'] + (['full base Unicode mappings retained'] if not cfg['subset'] else []),
            'not_run':['FontBakery','OTS','regional shape visual review','browser fallback review','vertical shaping','IVS'],
            'outputs':{desktop.name:digest(desktop),web.name:digest(web)}}
    write(out/'report.json',report)
    (out/'FONTLOG.txt').write_text(f'{family} {version}\nBase: {base_family}\nModification holder: {holder}\nOriginal copyright: {copyright_text}\nNative axes: {loc}\nScope: {report["scope"]}\nExplicit glyph edits: {len(edits)}; see report.json. No missing codepoints generated. Original OFL enclosed.\n')
    lang=cfg['language']; escaped=html.escape(text); display=html.escape(cfg.get('display_name',family))
    sections=''.join(f'<section><h2>{size}px</h2><p class="sample" style="font-size:{size}px">{escaped}</p></section>' for size in [16,24,48,96])
    (out/'specimen.html').write_text(f'<!doctype html><html lang="{lang}"><meta charset="utf-8"><title>{display}</title><link rel="stylesheet" href="fonts.css"><style>body{{margin:48px;background:#f5f4ef;color:#222;font-family:sans-serif}}.sample{{font-family:"{family}";font-weight:{weight};line-height:1.7;white-space:pre-wrap;overflow-wrap:anywhere}}section{{padding:24px;background:white;margin:24px 0;break-inside:avoid}}h1{{font-weight:400}}@media print{{section{{break-before:page}}}}</style><h1>{display} · {version}</h1><p>{html.escape(report["scope"])} / {style} / {report["codepoints"]} Unicode characters</p>{sections}</html>')
    return report

def main():
    ap=argparse.ArgumentParser(description=__doc__); sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('inspect');p.add_argument('font');p.add_argument('--text-file');p.add_argument('--language',default='zh-Hans',choices=['zh-Hans','zh-Hant-TW','zh-Hant-HK']);p.add_argument('--out',required=True);p.set_defaults(run=inspect)
    p=sub.add_parser('profile-grid');p.add_argument('image');p.add_argument('--labels',required=True);p.add_argument('--cols',type=int,required=True);p.add_argument('--out',required=True);p.set_defaults(run=profile)
    p=sub.add_parser('coverage',help='Check an explicit UTF-8 character list; fail on missing characters')
    p.add_argument('font');p.add_argument('--charset-file',required=True);p.add_argument('--out',required=True);p.set_defaults(run=check_coverage)
    p=sub.add_parser('glyph-template',help='Export editable SVG path data for a few existing static TrueType glyphs')
    p.add_argument('font');p.add_argument('--text',required=True);p.add_argument('--out',required=True);p.set_defaults(run=glyph_template)
    for command in ['build','preview','export']:
        p=sub.add_parser(command,help={'build':'Build using recipe subset setting (default full)', 'preview':'Build a fast corpus subset', 'export':'Export complete base coverage, overriding old subset recipes'}[command])
        p.add_argument('font');p.add_argument('--config',required=True);p.add_argument('--text-file',required=True);p.add_argument('--license',required=True);p.add_argument('--out',required=True);p.set_defaults(run=build)
        if command == 'preview': p.add_argument('--previous-build',help='Accumulate the previous preview corpus with the identical source and recipe')
    a=ap.parse_args()
    try:a.run(a)
    except (ValueError,KeyError,OSError,RuntimeError,TTLibError) as e:ap.exit(2,str(e)+'\n')
if __name__=='__main__':main()
