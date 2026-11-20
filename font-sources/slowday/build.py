#!/usr/bin/env python3
"""Build Slowday's two original-source rotations. Code: MIT; fonts: OFL."""
import argparse,json,hashlib,math
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();r=json.loads(Path(__file__).with_name('recipe.json').read_text())
if hashlib.sha256(a.base.read_bytes()).hexdigest()!=r['source_sha256']:raise ValueError('Wrong source version')
if a.out.exists():raise FileExistsError(a.out)
f=TTFont(a.base);gs=f.getGlyphSet();edited={};x,y=r['center']
for ch,deg in r['rotations_degrees'].items():
 n=f.getBestCmap()[ord(ch)];pen=TTGlyphPen(gs);t=Transform().translate(x,y).rotate(math.radians(deg)).translate(-x,-y);gs[n].draw(TransformPen(pen,t));edited[n]=pen.glyph()
for n,g in edited.items():f['glyf'][n]=g;g.recalcBounds(f['glyf']);f['hmtx'][n]=(f['hmtx'][n][0],g.xMin)
f.save(a.out);print('Working font saved; rename through the font workflow before redistribution.')
