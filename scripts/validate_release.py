#!/usr/bin/env python3
"""Verify the distributed fonts, licenses, Skills, artwork and portable repository paths."""
from pathlib import Path
import json,hashlib,re
from fontTools.ttLib import TTFont
from PIL import Image
from pypdf import PdfReader
import yaml
ROOT=Path(__file__).resolve().parents[1]
def main():
 c=json.loads((ROOT/'catalog.json').read_text());families=c['families'];names=set();files=[]
 for i,e in enumerate(families):
  d=ROOT/'fonts'/e['slug'];license=d/'资料/OFL.txt';assert 'SIL OPEN FONT LICENSE' in license.read_text(encoding='utf-8-sig').upper(),str(license)
  assert all(p.name=='资料' or p.suffix in ['.ttf','.otf'] for p in d.iterdir()),str(d)
  for s in e['styles']:
   p=ROOT/s['file'];f=TTFont(p);assert hashlib.sha256(p.read_bytes()).hexdigest()==s['sha256'],str(p);assert len(f.getBestCmap())==s['mapped_codepoints'];assert f['OS/2'].usWeightClass==s['weight'];key=f['name'].getDebugName(6);assert key not in names;names.add(key);assert 'Open Font License' in f['name'].getDebugName(13);files.append(s['file'])
  poster=ROOT/'posters'/(str(i+1).zfill(2)+'-'+e['slug']+'.png');im=Image.open(poster);im.verify();im=Image.open(poster);assert im.size==(2340,3060),str(poster)
  assert (ROOT/'artwork/backgrounds'/(e['slug']+'.png')).is_file()
 for name in ['make-chinese-font','make-simplified-chinese-font','make-traditional-chinese-font','make-english-font']:
  p=ROOT/'skills'/name/'SKILL.md';m=yaml.safe_load(p.read_text().split('---',2)[1]);assert m['name']==name and m['description']
 assert 'Copyright (c) 2026 Arlan Marat' in (ROOT/'skills/make-english-font/LICENSE').read_text()
 assert len(PdfReader(ROOT/'posters/poster-catalog.pdf').pages)==len(families)
 assert len(families)==11 and len(files)==16
 # Text resources must be portable and contain no workstation paths or credential-like secrets.
 checked=0
 for p in ROOT.rglob('*'):
  if not p.is_file() or '.git'in p.parts or '__pycache__'in p.parts:continue
  if p.suffix in ['.py','.md','.json','.yaml','.yml','.txt'] or p.name in ['LICENSE','UPSTREAM.txt']:
   s=p.read_text(encoding='utf-8')
   prefixes=[chr(47)+part for part in ('Users/','private/tmp/','var/folders/')]
   assert not any(prefix in s for prefix in prefixes),'Workstation path in '+str(p.relative_to(ROOT))
   assert not re.search(r'gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}',s),'Credential-like text in '+str(p)
   checked+=1
 result={'version':c['version'],'families':len(families),'font_files':len(files),'poster_pngs':len(families),'skills':4,'text_resources_checked':checked,'checks':['all font SHA256 and cmap counts','actual weight metadata','unique PostScript names','OFL notices and per-family licenses','original Arlan Marat copyright','flat family directories','all poster PNG dimensions and decoding','PDF page count','Skill frontmatter','portable paths and no credential-like strings'],'not_run':['FontBakery','OTS','IVS/vertical/region certification','exhaustive all-language shaping','per-glyph aesthetic review'],'status':'pass'}
 (ROOT/'docs/release-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
