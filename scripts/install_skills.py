#!/usr/bin/env python3
"""Install all four sibling Skills atomically per directory; refuse existing names."""
import argparse,os,shutil,tempfile
from pathlib import Path
NAMES=('make-chinese-font','make-simplified-chinese-font','make-traditional-chinese-font','make-english-font')
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--dest',type=Path,default=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'skills');ap.add_argument('--dry-run',action='store_true');a=ap.parse_args();source=Path(__file__).resolve().parents[1]/'skills';dest=a.dest.expanduser().resolve()
 for name in NAMES:
  if not (source/name/'SKILL.md').is_file():ap.error('Incomplete source bundle: '+name)
 collisions=[name for name in NAMES if (dest/name).exists()]
 if a.dry_run:
  for name in NAMES:print(('EXISTS ' if name in collisions else 'ADD    ')+str(dest/name))
  return
 if collisions:ap.error('Refusing existing Skills: '+', '.join(collisions)+'. Use a different --dest or manage your existing versions explicitly.')
 dest.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='.font-skills-',dir=dest) as tmp:
  staged=Path(tmp)
  for name in NAMES:shutil.copytree(source/name,staged/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.DS_Store'))
  for name in NAMES:
   if (dest/name).exists():raise FileExistsError('Destination changed during preparation: '+str(dest/name))
  for name in NAMES:os.rename(staged/name,dest/name);print('Installed '+str(dest/name))
if __name__=='__main__':main()
