#!/usr/bin/env python3
"""Rebuild the public Prism working font from its licensed native source. Code: MIT; fonts: OFL."""
import argparse,json,math,hashlib
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.misc.transform import Transform
class StylePen(BasePen):
 def __init__(self,gs,T,radius=5,bow=70):
  super().__init__(gs);self.T=T;self.r=radius;self.bow=bow;self.contours=[];self.cur=None
 def _moveTo(self,p):self.cur=[];self.start=self.T.transformPoint(p);self.last=self.start
 def _lineTo(self,p):
  p=self.T.transformPoint(p);self.cur.append(('l',self.last,p));self.last=p
 def _qCurveToOne(self,c,p):
  c=self.T.transformPoint(c);p=self.T.transformPoint(p);self.cur.append(('q',self.last,c,p));self.last=p
 def _curveToOne(self,c1,c2,p):
  c1=self.T.transformPoint(c1);c2=self.T.transformPoint(c2);p=self.T.transformPoint(p);self.cur.append(('c',self.last,c1,c2,p));self.last=p
 def _closePath(self):
  if self.last!=self.start:self.cur.append(('l',self.last,self.start))
  if self.cur:self.contours.append(self.cur)
  self.cur=None
 def _endPath(self):raise ValueError('Open font contour')
 def glyph(self):
  pen=TTGlyphPen(None)
  for segs in self.contours:
   n=len(segs);joins={}
   for i,s in enumerate(segs):
    nxt=segs[(i+1)%n]
    if s[0]!='l' or nxt[0]!='l':continue
    a,p=s[1],s[2];b=nxt[2];u=(p[0]-a[0],p[1]-a[1]);v=(b[0]-p[0],b[1]-p[1]);lu=math.hypot(*u);lv=math.hypot(*v)
    if min(lu,lv)<2:continue
    cosine=(u[0]*v[0]+u[1]*v[1])/(lu*lv)
    if not -.95<cosine<.98:continue
    trim=min(self.r,.15*lu,.15*lv)
    joins[i]=((p[0]-u[0]*trim/lu,p[1]-u[1]*trim/lu),p,(p[0]+v[0]*trim/lv,p[1]+v[1]*trim/lv))
   first=joins[n-1][2] if n-1 in joins else segs[0][1];pen.moveTo(first)
   for i,s in enumerate(segs):
    start=joins[(i-1)%n][2] if (i-1)%n in joins else s[1];end=joins[i][0] if i in joins else s[-1]
    if s[0]=='l':
     dx=end[0]-start[0];dy=end[1]-start[1];length=math.hypot(dx,dy)
     if abs(dx)>45 and abs(dy)>45 and length>100:
      bend=min(self.bow,length*.13)*(1 if dx*dy>0 else -1);control=((start[0]+end[0])/2+bend,(start[1]+end[1])/2);pen.qCurveTo(control,end)
     else:pen.lineTo(end)
    elif s[0]=='q':pen.qCurveTo(s[2],end)
    else:pen.curveTo(s[2],s[3],end)
    if i in joins:pen.qCurveTo(joins[i][1],joins[i][2])
   pen.closePath()
  return pen.glyph()

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args();r=json.loads(Path(__file__).with_name('recipe.json').read_text())
 if hashlib.sha256(a.base.read_bytes()).hexdigest()!=r['source_sha256']:raise ValueError('Source version/SHA differs from recipe')
 if a.out.exists():raise FileExistsError(a.out)
 f=TTFont(a.base);gs=f.getGlyphSet();v=r['transform'];t=Transform(v['sx'],0,0,v['sy'],v['cx']*(1-v['sx']),v['cy']*(1-v['sy']));new={}
 for n in f.getGlyphOrder():
  if f['hmtx'][n][0]>=800 and n!='.notdef':p=StylePen(gs,t);gs[n].draw(p);new[n]=p.glyph()
 for n,g in new.items():f['glyf'][n]=g;g.recalcBounds(f['glyf']);f['hmtx'][n]=(f['hmtx'][n][0],getattr(g,'xMin',0))
 f.save(a.out);print('Working outline font saved; rename with the font workflow before redistribution.')
if __name__=='__main__':main()
