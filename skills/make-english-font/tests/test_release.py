"""Observable release invariants using a caller-supplied licensed upright glyf VF."""
import argparse,copy,importlib.util,json,tempfile
from pathlib import Path
from fontTools.ttLib import TTFont
S=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('release_font',S/'scripts/release_font.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base',required=True);ap.add_argument('--license',required=True);a=ap.parse_args()
 with tempfile.TemporaryDirectory(prefix='english-skill-test-') as tmp:
  p=Path(tmp);cfg=p/'config.json';out=p/'kit';c={'family':'Pally Release Test','style':'Light','weight':300,'axes':{'wght':300},'license_reviewed':True,'reserved_names':[],'specimen_title':'Test','sample':'AVATAR To office café','description':'Native instance test.'};cfg.write_text(json.dumps(c));m.release(a.base,cfg,a.license,out)
  assert {q.name for q in out.iterdir()}=={'PallyReleaseTest-Light.ttf','资料'}
  assert (out/'资料/OFL.txt').read_bytes()==Path(a.license).read_bytes()
  count=0
  def reject(name,fn):
   nonlocal count
   try:fn()
   except (ValueError,FileExistsError):count+=1;return
   raise AssertionError(name+' was not rejected')
  reject('existing output',lambda:m.release(a.base,cfg,a.license,out))
  for name,patch in [('missing',{'sample':'Test\U0010ffff'}),('unknownaxis',{'axes':{'ZZZZ':300}}),('axisrange',{'axes':{'wght':1e6}}),('fakeweight',{'weight':700,'style':'Bold'}),('unreviewed',{'license_reviewed':False}),('sourcename',{'family':TTFont(a.base)['name'].getDebugName(1)})]:
   cfg.write_text(json.dumps({**c,**patch}));bad=p/name;reject(name,lambda:m.release(a.base,cfg,a.license,bad));assert not bad.exists()
  f=TTFont(out/'PallyReleaseTest-Light.ttf');g=copy.deepcopy(f);next(t for t in g['cmap'].tables if t.isUnicode()).cmap.pop(65,None);reject('cmap corrupted',lambda:m.check_same(f,g,['ABC'],'test'))
  g=copy.deepcopy(f);n=g.getBestCmap()[65];aw,lsb=g['hmtx'].metrics[n];g['hmtx'].metrics[n]=(aw+1,lsb);reject('advance corrupted',lambda:m.check_same(f,g,['ABC'],'test'))
  g=copy.deepcopy(f)
  for t in g['cmap'].tables:
   if t.isUnicode():t.cmap.pop(32,None)
  assert m.missing(g,' ')==[' '], 'mapped space must be checked'
  print('Native release, OFL byte preservation, flat kit, missing-space detection and',count,'rejection invariants passed.')
if __name__=='__main__':main()
