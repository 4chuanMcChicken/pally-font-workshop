#!/usr/bin/env python3
"""Create flat per-family/all-font kits plus Skills and poster ZIPs, with CRC checks."""
from pathlib import Path
import argparse,json,zipfile,hashlib,shutil,io
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,default=ROOT/'dist');a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True);data=json.loads((ROOT/'catalog.json').read_text());v='v'+data['version'];es=data['families'];produced=[]
 def archive(name,items):
  target=out/name
  if target.exists():raise FileExistsError(target)
  with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
   for source,arc in items:
    assert not arc.startswith('/') and '..'not in Path(arc).parts
    if isinstance(source,bytes):z.writestr(arc,source)
    else:z.write(source,arc)
  with zipfile.ZipFile(target) as z:assert z.testzip()is None
  produced.append(target);print(target.name,target.stat().st_size,flush=True)
 font_items=[]
 for i,e in enumerate(es):
  stem='Pally-'+e['slug']+'-'+v;items=[];d=ROOT/'fonts'/e['slug'];info=e['name']+'\n\n安装：双击最外层的 TTF 或 OTF 文件。\n实际字重：'+', '.join(s['style']+' '+str(s['weight']) for s in e['styles'])+'\n来源：'+e['upstream']+'\n改动：'+e['changes']+'\n许可：SIL OFL 1.1，见本文件夹 OFL.txt。\n完整项目：https://github.com/4chuanMcChicken/pally-font-workshop\n'
  for s in e['styles']:
   f=ROOT/s['file'];items.append((f,stem+'/'+f.name));font_items.append((f,'Pally-All-Fonts-'+v+'/'+f.name))
  for p in sorted((d/'资料').rglob('*')):
   if p.is_file():items.append((p,stem+'/资料/'+str(p.relative_to(d/'资料'))));font_items.append((p,'Pally-All-Fonts-'+v+'/资料/'+e['slug']+'/'+str(p.relative_to(d/'资料'))))
  poster=ROOT/'posters'/(str(i+1).zfill(2)+'-'+e['slug']+'.png');items.extend([(poster,stem+'/资料/poster.png'),(info.encode(),stem+'/资料/使用说明.txt')]);font_items.extend([(poster,'Pally-All-Fonts-'+v+'/资料/'+e['slug']+'/poster.png'),(info.encode(),'Pally-All-Fonts-'+v+'/资料/'+e['slug']+'/使用说明.txt')]);archive(stem+'.zip',items)
 archive('Pally-All-Fonts-'+v+'.zip',font_items)
 root='Pally-Font-Skills-'+v;items=[]
 for p in sorted((ROOT/'skills').rglob('*')):
  if p.is_file() and '__pycache__'not in p.parts and p.suffix!='.pyc':items.append((p,root+'/'+str(p.relative_to(ROOT))))
 readme='Pally Font Skills\n\n四个入口一起安装，简体/繁体入口依赖中文核心。\npython3 scripts/install_skills.py --dry-run\npython3 scripts/install_skills.py\n已有同名 Skill 时拒绝覆盖；用 --dest 指定其他目录。\n\n特别感谢 Arlan Marat (@arla6ka) 的 design.how / make-font。英文保留部分 MIT 代码与原始版权；新增中文引擎、简繁路由、覆盖检查、真实小样与扁平交付。原始许可在 skills/make-english-font/LICENSE，新代码为 MIT。\nhttps://github.com/4chuanMcChicken/pally-font-workshop\n'
 items.extend([(ROOT/'scripts/install_skills.py',root+'/scripts/install_skills.py'),(ROOT/'LICENSE',root+'/LICENSE'),(readme.encode(),root+'/README.txt')]);archive(root+'.zip',items)
 root='Pally-Posters-'+v;items=[(p,root+'/'+p.name) for p in sorted((ROOT/'posters').glob('*.png'))];items.extend([(ROOT/'posters/poster-catalog.pdf',root+'/poster-catalog.pdf'),(ROOT/'posters/contact-sheet.jpg',root+'/contact-sheet.jpg'),((ROOT/'artwork/README.md').read_bytes(),root+'/README.md')]);archive(root+'.zip',items)
 shutil.copyfile(ROOT/'posters/poster-catalog.pdf',out/('Pally-Poster-Catalog-'+v+'.pdf'));produced.append(out/('Pally-Poster-Catalog-'+v+'.pdf'))
 checks=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(produced));(out/'SHA256SUMS.txt').write_text(checks);print('Assets:',len(produced)+1)
if __name__=='__main__':main()
