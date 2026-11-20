#!/usr/bin/env python3
"""Atomic full-cmap upright glyf native-instance release with actual specimen and round-trip checks."""
import argparse,base64,copy,hashlib,html,io,json,os,re,shutil,tempfile
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
import uharfbuzz as hb
from PIL import Image,ImageDraw,ImageFont
WEIGHTS={100:'Thin',200:'ExtraLight',300:'Light',400:'Regular',500:'Medium',600:'SemiBold',700:'Bold',800:'ExtraBold',900:'Black'}
ASCII=''.join(map(chr,range(32,127)))
LATIN1=ASCII+''.join(map(chr,range(160,256)))
PROBE='AVATAR To Wa fi fl ffi office café naïve Ångström coöperate 0123456789 € £ @ &'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(p,obj):Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def missing(f,text):
 cm=f.getBestCmap();return sorted({c for c in text if c not in '\r\n\t' and ord(c) not in cm})
def maps(f):
 return [(t.platformID,t.platEncID,t.language,t.format,copy.deepcopy(getattr(t,'cmap',{})),copy.deepcopy(getattr(t,'uvsDict',{}))) for t in f['cmap'].tables if t.isUnicode()]
def outlines(f):
 gs=f.getGlyphSet();out={}
 for n in f.getGlyphOrder():
  p=DecomposingRecordingPen(gs);gs[n].draw(p);out[n]=hashlib.sha256(repr(p.value).encode()).hexdigest()
 return out
def fontbytes(f):
 t=copy.deepcopy(f);t.flavor=None;b=io.BytesIO();t.save(b);return b.getvalue()
def shape(f,text):
 if not text:return []
 hf=hb.Font(hb.Face(fontbytes(f)));hb.ot_font_set_funcs(hf);hf.scale=(f['head'].unitsPerEm,)*2
 b=hb.Buffer();b.add_str(text);b.guess_segment_properties();hb.shape(hf,b)
 return [(i.codepoint,i.cluster,p.x_advance,p.y_advance,p.x_offset,p.y_offset) for i,p in zip(b.glyph_infos,b.glyph_positions)]
def check_same(a,b,texts,label):
 if maps(a)!=maps(b):raise ValueError(label+': Unicode cmap changed')
 if a.getGlyphOrder()!=b.getGlyphOrder():raise ValueError(label+': glyph order changed')
 if outlines(a)!=outlines(b):raise ValueError(label+': decomposed outlines changed')
 if a['hmtx'].metrics!=b['hmtx'].metrics:raise ValueError(label+': advances/sidebearings changed')
 for t in texts:
  if shape(a,t)!=shape(b,t):raise ValueError(label+': shaping changed for '+repr(t))
 return {'unicode_cmap':'pass','all_glyph_outlines':'pass','all_horizontal_metrics':'pass','harfbuzz_samples':len(texts)}
def rename(f,c,source):
 fam=c['family'];style=c['style'];weight=c['weight'];version=c.get('version','0.100');ps=re.sub('[^A-Za-z0-9]','',fam)+'-'+style
 if not re.fullmatch('[A-Za-z][A-Za-z0-9 ]{1,50}',fam):raise ValueError('family must be a short ASCII family name')
 old=source['name'].getDebugName(16) or source['name'].getDebugName(1)
 forbidden=[old]+c.get('reserved_names',[])
 if any(n and n.casefold() in fam.casefold() for n in forbidden):raise ValueError('family uses source family or reviewed Reserved Font Name')
 n=f['name'];remove={1,2,3,4,5,6,7,16,17,18,21,22,25};n.names=[r for r in n.names if r.nameID not in remove]
 ribbi=style in ('Regular','Bold')
 records={1:fam if ribbi else fam+' '+style,2:style if ribbi else 'Regular',3:f'{version};PALL;{ps}',4:fam+' '+style,5:'Version '+version,6:ps,16:fam,17:style}
 for nid,s in records.items():
  n.setName(s,nid,3,1,0x409);n.setName(s,nid,1,0,0)
 f['OS/2'].fsSelection &= ~((1<<0)|(1<<5)|(1<<6))
 f['OS/2'].fsSelection |= 1<<5 if style=='Bold' else 1<<6
 f['head'].macStyle=1 if style=='Bold' else 0
 f['head'].fontRevision=float(version)
 return ps

def specimen_png(font,c,path):
 im=Image.new('RGB',(1440,1650),'#111211');d=ImageDraw.Draw(im);ink='#dddcd3';muted='#9b9d93'
 def draw(text,y,size=52,fill=ink):
  ft=ImageFont.truetype(str(font),size)
  while d.textlength(text,font=ft)>1300:
   size-=1;ft=ImageFont.truetype(str(font),size)
  d.text((70,y),text,font=ft,fill=fill)
 draw(c.get('specimen_title',c['family']),65,140)
 draw(c.get('description',''),255,30,muted)
 draw(c['style']+' / '+str(c['weight']),350,28,muted)
 draw(c.get('sample','Lone leaf boat'),410,130)
 draw('ABCDEFGHIJKLMNOPQRSTUVWXYZ',635,55)
 draw('abcdefghijklmnopqrstuvwxyz',730,61)
 draw('0123456789',865,92)
 draw('.,!? :; () [] {} @ # % & + - = /',1000,48)
 draw('Quiet shapes, an open horizon.',1140,60)
 for i,size in enumerate([16,24,48,96]):draw('Open circles. A quiet day.',1260+i*78,size)
 im.save(path)

def portable_html(f,c,woff,path):
 cm=sorted(f.getBestCmap());title=c.get('specimen_title',c['family']);desc=c.get('description','');sample=c.get('sample','Lone leaf boat')
 data=base64.b64encode(Path(woff).read_bytes()).decode()
 page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title><style>@font-face{font-family:Specimen;src:url(data:font/woff2;base64,__DATA__) format('woff2');font-weight:__WEIGHT__;font-style:normal}*{box-sizing:border-box}body{background:#111211;color:#dddcd3;max-width:1200px;margin:auto;padding:6vw;font-family:system-ui}h1,.font{font-family:Specimen;font-weight:__WEIGHT__;font-synthesis:none}h1{font-size:clamp(60px,12vw,160px);margin:0}p{line-height:1.6;color:#a3a59a}.font{line-height:1.2;overflow-wrap:anywhere}#preview{font-size:clamp(36px,7vw,90px)}.alphabet{font-size:clamp(26px,4vw,58px)}section{padding:40px 0;border-top:1px solid #44483d}textarea{width:100%;background:#22251f;color:inherit;padding:20px;font:20px system-ui}label{display:block;margin:20px 0 8px}#status{min-height:30px}a{color:inherit}</style><h1>__TITLE__</h1><p>__DESC__</p><p>__STYLE__ · __WEIGHT__ · __COUNT__ mapped codepoints</p><section><label for="input">Try your text</label><textarea id="input" disabled>__SAMPLE__</textarea><p id="status" aria-live="polite">Loading embedded font…</p><div id="preview" class="font">__SAMPLE__</div></section><section class="alphabet font">ABCDEFGHIJKLMNOPQRSTUVWXYZ<br>abcdefghijklmnopqrstuvwxyz<br>0123456789<br>.,!? :; () [] {} @ # % &amp; + − = /</section><section><div class="font" style="font-size:16px">Open circles. A quiet day. 16px</div><div class="font" style="font-size:24px">Open circles. A quiet day. 24px</div><div class="font" style="font-size:48px">Open circles. A quiet day. 48px</div><div class="font" style="font-size:96px">Open circles. 96px</div></section><p>__NOTE__</p><script>const coverage=new Set(__COVERAGE__);const input=document.querySelector('#input'),preview=document.querySelector('#preview'),status=document.querySelector('#status');function update(){const bad=[...new Set([...input.value].filter(c=>!/[\\r\\n\\t]/.test(c)&&!coverage.has(c.codePointAt(0))))];if(bad.length){status.textContent='Unsupported characters: '+bad.join(' ')+' — previous valid sample retained.';return}preview.textContent=input.value;status.textContent='Loaded embedded font. All characters in this sample are supported.'}document.fonts.load('__WEIGHT__ 32px Specimen').then(faces=>{if(!faces.length)throw Error('Font not loaded');input.disabled=false;update()}).catch(e=>status.textContent='Font failed to load: '+e.message);input.addEventListener('input',update);</script></html>'''
 # Check every hard-coded font sample too; avoid a silently falling-back symbol.
 if 0x2212 not in cm:page=page.replace(' + − = /',' + - = /')
 values={'TITLE':html.escape(title),'DESC':html.escape(desc),'DATA':data,'WEIGHT':str(c['weight']),'STYLE':html.escape(c['style']),'COUNT':str(len(cm)),'SAMPLE':html.escape(sample),'NOTE':html.escape(c.get('change_note','Native source instance; no reference outlines copied.')),'COVERAGE':json.dumps(cm)}
 for k,v in values.items():page=page.replace('__'+k+'__',v)
 Path(path).write_text(page,encoding='utf-8')

def release(base_path,config_path,license_path,out):
 c=json.loads(Path(config_path).read_text());out=Path(out)
 if out.exists():raise ValueError('output exists; use a new version directory')
 if c.get('license_reviewed') is not True:raise ValueError('review source license and RFNs before building')
 lic=Path(license_path).read_text(encoding='utf-8-sig')
 if 'SIL OPEN FONT LICENSE Version 1.1' not in lic and 'SIL OPEN FONT LICENSE' not in lic:raise ValueError('default publisher requires reviewed OFL source')
 source=TTFont(base_path)
 if 'glyf' not in source or source['post'].italicAngle or source['OS/2'].fsSelection&1:raise ValueError('v0.1 native release supports upright glyf only')
 axes=c.get('axes',{})
 if 'fvar' in source:
  defs={a.axisTag:a for a in source['fvar'].axes}
  if set(axes)-set(defs):raise ValueError('unknown axis')
  loc={k:axes.get(k,a.defaultValue) for k,a in defs.items()}
  if any(not(a.minValue<=loc[k]<=a.maxValue) for k,a in defs.items()):raise ValueError('axis outside native range')
  expected=instantiateVariableFont(source,loc,inplace=False,updateFontNames=False)
 else:
  if axes:raise ValueError('static font has no axes')
  loc={};expected=copy.deepcopy(source)
 # Compare compiled native instances: glyf serialization rounds fractional interpolation coordinates.
 expected=TTFont(io.BytesIO(fontbytes(expected)))
 weight=int(c['weight'])
 if weight not in WEIGHTS or c['style']!=WEIGHTS[weight] or expected['OS/2'].usWeightClass!=weight:raise ValueError('style/weight does not match native instance')
 texts=[ASCII,c.get('required_text',''),c.get('sample','Lone leaf boat'),c.get('specimen_title',c['family']),c.get('description',''),'Quiet shapes, an open horizon.','Open circles. A quiet day.']
 for t in texts:
  bad=missing(expected,t)
  if bad:raise ValueError('missing required characters: '+''.join(bad))
 for t in [PROBE,'e\u0301 a\u0308 A\u030a','office affine AVATAR To Wa']:
  if not missing(expected,t):texts.append(t)
 f=copy.deepcopy(expected);ps=rename(f,c,source)
 out.parent.mkdir(parents=True,exist_ok=True);stage=Path(tempfile.mkdtemp(prefix='.'+out.name+'-',dir=out.parent))
 try:
  info=stage/'资料';info.mkdir();web=info/'webfonts';web.mkdir();ttf=stage/(ps+'.ttf');f.save(ttf);f=TTFont(ttf)
  checks={'native_instance_to_ttf':check_same(expected,f,texts,'native→TTF')}
  woff=web/(ps+'.woff2');wf=TTFont(ttf);wf.flavor='woff2';wf.save(woff);wf=TTFont(woff)
  checks['woff2_roundtrip']=check_same(f,wf,texts,'TTF→WOFF2')
  xml=info/'.roundtrip.ttx';binary=info/'.roundtrip.ttf';f.saveXML(xml);xf=TTFont();xf.importXML(xml);xf.save(binary);xf=TTFont(binary)
  checks['xml_recompile']=check_same(f,xf,texts,'XML→binary');xml.unlink();binary.unlink()
  if 'fvar'in f:raise ValueError('variation axes survived static release')
  if f['name'].getDebugName(16)!=c['family']:raise ValueError('family naming mismatch')
  specimen_png(ttf,c,info/'specimen.png');portable_html(f,c,woff,info/'preview.html')
  shutil.copyfile(license_path,info/'OFL.txt');shutil.copyfile(config_path,info/'design.json')
  (info/'fonts.css').write_text('@font-face{font-family:"'+c['family']+'";src:url("webfonts/'+ps+'.woff2") format("woff2");font-weight:'+str(weight)+';font-style:normal;}\n')
  report={'skill_version':'0.1','family':c['family'],'style':c['style'],'weight':weight,'native_axes':loc,'source_file':Path(base_path).name,'source_sha256':sha(base_path),'license_sha256':sha(license_path),'output_sha256':sha(ttf),'mapped_codepoints':len(f.getBestCmap()),'glyph_count':len(f.getGlyphOrder()),'coverage':{'printable_ascii':{'covered':95,'total':95},'printable_latin1':{'covered':len(set(map(ord,LATIN1))&set(f.getBestCmap())),'total':len(LATIN1),'missing':missing(f,LATIN1)},'required_missing':[]},'checks':checks,'changed_outlines_relative_to_native_instance':0,'actual_changes':c.get('change_note','Native axis instantiation and renaming only.'),'not_run':['FontBakery','OTS','all kerning pairs','OS font installation/menu','all-language shaping'],'browser_ui_test':'not run by release script; inspect separately'}
  dump(info/'report.json',report);(info/'FONTLOG.txt').write_text(c['family']+' '+c.get('version','0.100')+'\nSource: '+str(Path(base_path).name)+'\n'+report['actual_changes']+'\nSource copyright and OFL retained. Reference images are not bundled.\n')
  (info/'使用说明.txt').write_text('安装：双击最外层 TTF。\n试字：打开本文件夹 preview.html；网页已内嵌真实字体。\n字形、覆盖、来源与检查见 report.json。OFL.txt 为源许可原文。\n')
  os.rename(stage,out);print(json.dumps({'out':str(out),'font':ps+'.ttf','coverage':report['coverage'],'checks':checks},ensure_ascii=False))
 except Exception:
  shutil.rmtree(stage,ignore_errors=True);raise

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('base');ap.add_argument('--config',required=True);ap.add_argument('--license',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();release(a.base,a.config,a.license,a.out)
if __name__=='__main__':main()
