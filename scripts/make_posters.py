#!/usr/bin/env python3
"""Render the reference specimen layout with real font outlines and original narrative art."""
from pathlib import Path
import argparse,json,io,hashlib
from PIL import Image
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.reportLabPen import ReportLabPen as BasePen
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
import uharfbuzz as hb
class PathPen(BasePen):
 def _closePath(self):self.path.close()
class Face:
 def __init__(self,path):
  self.path=Path(path);self.f=TTFont(path);self.cm=self.f.getBestCmap();self.gs=self.f.getGlyphSet();self.order=self.f.getGlyphOrder();self.upm=self.f['head'].unitsPerEm;self.hf=hb.Font(hb.Face(self.path.read_bytes()));hb.ot_font_set_funcs(self.hf);self.hf.scale=(self.upm,self.upm);self.bounds={}
 def shape(self,s):
  bad=sorted({c for c in s if ord(c)not in self.cm})
  if bad:raise ValueError('Missing glyphs in '+self.path.name+': '+''.join(bad))
  b=hb.Buffer();b.add_str(s);b.guess_segment_properties();hb.shape(self.hf,b);return list(zip(b.glyph_infos,b.glyph_positions))
 def box(self,shaped):
  boxes=[];cursor=0
  for i,p in shaped:
   name=self.order[i.codepoint]
   if name not in self.bounds:
    pen=BoundsPen(self.gs);self.gs[name].draw(pen);self.bounds[name]=pen.bounds
   b=self.bounds[name]
   if b:boxes.append((b[0]+cursor+p.x_offset,b[1]+p.y_offset,b[2]+cursor+p.x_offset,b[3]+p.y_offset))
   cursor+=p.x_advance
  return (min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)) if boxes else (0,0,cursor,0)
W,H=1170,1530
SUBTITLES={'tuanzi':'A LITTLE WAY HOME','neon-circuit':'AFTER THE LAST TRAM','ink-gravity':'THE SEA REMEMBERS','wonky-notes':'A BEAUTIFULLY CROOKED DAY','cloudwind':'LET THE WIND TAKE ITS TIME','evening-letter':'A LETTER AT BLUE HOUR','prism':'LIGHT TAKES ANOTHER SHAPE','slowday':'THERE IS NO NEED TO HURRY','nuomi':'A SUMMER MADE OF SMALL THINGS','leafline':'SOME THINGS LEARN TO DRIFT','sidekick':'EVERY SMALL ADVENTURE NEEDS A FRIEND'}
def build(root,out):
 root=Path(root).resolve();out=Path(out).resolve();out.parent.mkdir(parents=True,exist_ok=True);data=json.loads((root/'catalog.json').read_text())['families'];c=canvas.Canvas(str(out),pagesize=(W,H),pageCompression=1);c.setTitle('Pally Font Workshop - Narrative Type Specimens');c.setAuthor('Pally contributors');cache={};blocks=[]
 def face(path):
  p=(root/path).resolve()
  if p not in cache:cache[p]=Face(p)
  return cache[p]
 info=face('fonts/tuanzi/PallyTuanzi-Regular.ttf')
 def text(s,row,size,x,top,maxw=1020,color='#20251c',kind='sample'):
  sh=row.shape(s);box=row.box(sh);iw=(box[2]-box[0])*size/row.upm
  if iw>maxw:size*=maxw/iw;iw=maxw
  scale=size/row.upm;ih=(box[3]-box[1])*scale
  if x<20 or x+iw>W-20 or top<0 or top+ih>H-20:raise ValueError('Poster text overflow: '+s)
  c.setFillColor(HexColor(color));c.saveState();c.translate(x-box[0]*scale,H-top-box[3]*scale);c.scale(scale,scale);cursor=0
  for i,p in sh:
   pen=PathPen(row.gs,c.beginPath());row.gs[row.order[i.codepoint]].draw(pen);c.saveState();c.translate(cursor+p.x_offset,p.y_offset);c.drawPath(pen.path,fill=1,stroke=0);c.restoreState();cursor+=p.x_advance
  c.restoreState();blocks.append({'text':s,'font':str(row.path.relative_to(root)),'size':round(size,2),'x':x,'top':top,'ink_width':round(iw,2),'ink_height':round(ih,2),'kind':kind})
 def line(top,x1=40,x2=1120):c.setStrokeColor(HexColor(ink));c.setLineWidth(1.2);c.line(x1,H-top,x2,H-top)
 for index,e in enumerate(data):
  start=len(blocks);styles=e['styles'];regular=min(styles,key=lambda r:abs(r['weight']-400));hero=face(styles[-1]['file']);regularf=face(regular['file']);color,paper,ink=e['colors'];slug=e['slug']
  # Palette changes follow the final narrative image instead of treating all headers as white-on-photo.
  if slug=='prism':color='#f8e0a8'
  if slug=='slowday':color='#514454'
  if slug=='tuanzi':color='#42364f'
  c.setFillColor(HexColor(paper));c.rect(0,0,W,H,fill=1,stroke=0)
  bg=root/'artwork/backgrounds'/(slug+'.png');im=Image.open(bg);iw,ih=im.size;s=max(W/iw,575/ih);dw,dh=iw*s,ih*s;c.saveState();clip=c.beginPath();clip.rect(0,H-575,W,575);c.clipPath(clip,stroke=0,fill=0);c.drawImage(ImageReader(im),(W-dw)/2,H-575+(575-dh)/2,dw,dh,mask='auto');c.restoreState()
  # Two-line names deliberately offset; a generous title is carried by the real typeface.
  title=e['title_lines']
  if len(title)==1:text(title[0],hero,325,78,171,800,color,'title')
  else:
   size=260 if slug in ['cloudwind','neon-circuit'] else 238
   if e['language']=='Latin':size=245
   maxh=max(hero.box(hero.shape(t))[3]-hero.box(hero.shape(t))[1] for t in title);size=min(size,212*hero.upm/maxh)
   text(title[0],hero,size,76,70,800,color,'title');text(title[1],hero,size,180,310,800,color,'title')
  text(SUBTITLES[slug],regularf,16,760 if slug=='ink-gravity' else 80,58 if slug=='ink-gravity' else 538,340 if slug=='ink-gravity' else 850,'#fff0c7' if slug=='ink-gravity' else ('#fff4cf' if slug=='sidekick' else color),'subtitle')
  count=regular['mapped_codepoints'];han=regular['han_mappings'];weights=' / '.join(s['style'] for s in styles);scope=f'{count:,} 个码位'+(f' / {han:,} 个汉字码位' if han else ' / Latin')
  text(weights+' / '+scope,info,16,80,596,1030,ink,'metadata')
  c.setStrokeColor(HexColor(ink));c.setLineWidth(1.2);c.rect(40,H-1494,1080,848,fill=0,stroke=1)
  rows=[styles[0],styles[min(1,len(styles)-1)],styles[-1]];first=rows[0];text(first['style']+' / '+str(first['weight']),info,16,75,684,900,ink,'metadata');text(e['sample'],face(first['file']),64,75,751,995,ink)
  for n,(row,top) in enumerate(zip(rows[1:],[918,1072])):
   if n==0 and row['style']!=first['style'] or n==1 and row['style']!=rows[1]['style']:text(row['style']+' / '+str(row['weight']),info,13,75,top-39,900,ink,'metadata')
   rf=face(row['file']);sample=e['rows'][n]
   if e['language']=='Latin':text(sample,rf,58,75,top,995,ink)
   else:
    for j,ch in enumerate(sample.split()):text(ch,rf,106,75+j*212,top,200,ink)
  line(1190);text('数字与符号',info,17,75,1225,990,ink,'metadata');text('0123456789',regularf,52,75,1284,995,ink)
  punct='! ? ... ( ) [ ] @ & # % + - =';text(punct,regularf,42,75,1366,995,ink);text('完整字体与原始许可，见下载包。 / PALLY FONT WORKSHOP',info,12,75,1450,995,ink,'metadata');c.showPage()
  print(f'{index+1:02d} {slug}: {len(blocks)-start} real-font text blocks',flush=True)
 c.save();report={'pages':len(data),'canvas':[W,H],'png_scale':2,'layout':{'image':[0,0,1170,575],'caption_top':596,'specimen_box':[40,646,1080,848],'symbol_separator_top':1190},'rendering':'HarfBuzz-shaped actual font glyph vector outlines; raster images contain no generated text','font_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in cache},'text_blocks':blocks,'visual_review':'required after rasterizing all pages'};(out.parent/'poster-render-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));return len(data)
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',default=str(Path(__file__).resolve().parents[1]));ap.add_argument('--out',default=None);a=ap.parse_args();build(a.root,a.out or Path(a.root)/'posters/poster-catalog.pdf')
