#!/usr/bin/env python3
"""Create a Chinese specimen book: name, description, real weights, digits and symbols."""
import argparse
import base64
import hashlib
import html
import json
import os
import tempfile
from pathlib import Path

from fontTools.ttLib import TTFont as Font
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

from cjk_font import STYLES

W, H = 720, 1000


class Book:
    def __init__(self, manifest):
        self.path = Path(manifest).resolve()
        self.data = json.loads(self.path.read_text(encoding='utf-8'))
        self.styles = []
        self.renders = []
        self.palette = self.data.get('theme', {'header':'#b9bbaf','paper':'#f3f0e6','ink':'#151811'})
        for i, entry in enumerate(self.data['styles']):
            row = dict(entry)
            row['path'] = (self.path.parent/row['font']).resolve()
            row['font_object'] = Font(row['path'])
            row['cm'] = row['font_object'].getBestCmap()
            row['webpath'] = (self.path.parent/row['webfont']).resolve()
            if set(Font(row['webpath']).getBestCmap())!=set(row['cm']):
                raise ValueError('Desktop and web font coverage differ: '+row['label'])
            row['upm'] = row['font_object']['head'].unitsPerEm
            if row['font_object']['OS/2'].usWeightClass != row['weight'] or STYLES.get(row['label']) != row['weight']:
                raise ValueError('Specimen label/weight does not match real font: '+row['label'])
            row['key'] = 'Specimen'+str(i)
            row['mode'] = 'embedded TrueType' if 'glyf' in row['font_object'] else 'vector outlines'
            if 'glyf' in row['font_object']:
                pdfmetrics.registerFont(TTFont(row['key'],str(row['path'])))
            self.styles.append(row)
        if not self.styles: raise ValueError('At least one real font is required')
        self.styles.sort(key=lambda row:row['weight'])
        self.regular = min(self.styles,key=lambda row:abs(row['weight']-400))
        self.hero = self.styles[-1]
        self.cover_styles = self.styles if len(self.styles)<=3 else [self.styles[0],self.styles[len(self.styles)//2],self.styles[-1]]

    def width(self, text, row, size):
        return sum(row['font_object']['hmtx'][row['cm'][ord(ch)]][0] for ch in text)*size/row['upm']

    def text(self, text, row, size, x, top, maximum=None):
        missing = sorted({c for c in text if ord(c) not in row['cm'] or row['font_object'].getGlyphID(row['cm'][ord(c)])==0})
        if missing: raise ValueError('Specimen has missing glyphs: '+''.join(missing))
        width = self.width(text,row,size)
        if maximum is not None and width>maximum:
            size *= maximum/width
            width = maximum
        if x+width > W-20 or x<20:
            raise ValueError('Specimen line exceeds horizontal page bounds: '+text)
        baseline = H-top-size*.87
        if baseline<12: raise ValueError('Specimen line exceeds vertical page bounds: '+text)
        if row['mode']=='embedded TrueType':
            self.c.setFont(row['key'],size)
            self.c.drawString(x,baseline,text)
        else:
            from fontTools.pens.reportLabPen import ReportLabPen
            class CanvasOutlinePen(ReportLabPen):
                def _closePath(self):
                    self.path.close()
            gs=row['font_object'].getGlyphSet();cursor=0
            self.c.saveState();self.c.translate(x,baseline);self.c.scale(size/row['upm'],size/row['upm'])
            for ch in text:
                name=row['cm'][ord(ch)];pen=CanvasOutlinePen(gs,self.c.beginPath())
                gs[name].draw(pen);self.c.saveState();self.c.translate(cursor,0);self.c.drawPath(pen.path,fill=1,stroke=0);self.c.restoreState()
                cursor+=row['font_object']['hmtx'][name][0]
            self.c.restoreState()
        self.renders.append({'text':text,'style':row['label'],'size':round(size,2),'x':x,'top':top,'width':round(width,2)})

    def paper(self, color=None):
        self.c.setFillColor(HexColor(color or self.palette['paper']));self.c.rect(0,0,W,H,fill=1,stroke=0)
        self.c.setFillColor(HexColor(self.palette['ink']));self.c.setStrokeColor(HexColor(self.palette['ink']))

    def rule(self, top, left=30, right=690, width=1.1):
        self.c.setLineWidth(width);self.c.line(left,H-top,right,H-top)

    def underline(self):
        self.c.saveState();self.c.translate(0,H);self.c.scale(1,-1)
        for points in [
            [('M',100,276),('C',220,265,502,262,622,279),('L',592,286),('C',415,274,215,289,100,284)],
            [('M',140,298),('C',300,289,545,289,632,304),('L',609,312),('C',480,297,266,307,140,304)]]:
            p=self.c.beginPath()
            for command in points:
                if command[0]=='M':p.moveTo(*command[1:])
                elif command[0]=='L':p.lineTo(*command[1:])
                else:p.curveTo(*command[1:])
            p.close();self.c.drawPath(p,fill=1,stroke=0)
        self.c.restoreState()

    def footer(self, number):
        self.text(self.data['title']+' / '+str(number),self.regular,9,48,972,624)

    def cover(self):
        self.paper(self.palette['header'])
        self.text(self.data.get('latin_name',''),self.regular,13,48,35,624)
        title=self.data['title'];size=200;size=min(size,570/(self.width(title,self.hero,1)))
        self.text(title,self.hero,size,(W-self.width(title,self.hero,size))/2,70,570)
        self.underline()
        for i,line in enumerate(self.data['description']):
            self.text(line,self.regular,23,66,337+i*36,588)
        self.text(self.data['summary'],self.regular,11,48,414,624)
        self.c.setFillColor(HexColor(self.palette['paper']));self.c.rect(0,0,W,H-448,fill=1,stroke=0)
        self.c.setFillColor(HexColor(self.palette['ink']));self.c.rect(22,22,676,530,fill=0,stroke=1)
        row_h=min(99,300/len(self.cover_styles))
        for i,row in enumerate(self.cover_styles):
            top=470+i*row_h
            self.text(row['label']+' / '+str(row['weight']),row,11,44,top,630)
            self.text(self.data['sample_line'],row,33,44,top+28,630)
        self.rule(787,22,698)
        self.text('数字与符号',self.regular,12,44,807,630)
        self.text(self.data['digits'],self.regular,31,44,837,630)
        self.text(self.data['cover_symbols'],self.hero,27,44,889,630)
        self.text('完整字重与字符样张，见后页。',self.regular,9,44,947,630)
        self.c.showPage()

    def weight_page(self,row,number):
        self.paper()
        self.text(self.data['title'],row,84,48,39,440)
        self.text(row['label']+' / '+str(row['weight']),row,16,454,62,220)
        self.text(self.data['weight_descriptions'][row['label']],row,20,48,154,624)
        for i,line in enumerate(self.data['headline']):self.text(line,row,62,48,215+i*79,624)
        self.rule(398,48,672)
        for i,line in enumerate(self.data['cjk_rows']):self.text(line,row,26,48,429+i*47,624)
        self.rule(644,48,672)
        for i,(size,line) in enumerate([(24,self.data['body'][0]),(18,self.data['body'][1]),(14,self.data['body'][2])]):
            self.text(str(size)+' pt',self.regular,9,48,676+i*69,80)
            self.text(line,row,size,111,674+i*69,561)
        self.text(self.data['digits'],row,28,48,893,624)
        self.footer(number);self.c.showPage()

    def symbol_page(self,number,rows):
        self.paper()
        self.text(self.data.get('symbol_heading','数字与符号'),self.hero,48,48,44,624)
        self.text(self.data.get('symbol_description','分别展示各个原生字重。'),self.regular,18,48,125,624)
        for i,row in enumerate(rows):
            top=194+i*72
            self.text(row['label'],row,11,48,top+8,90)
            self.text(self.data['digits'],row,39,150,top,522)
        self.rule(422,48,672)
        self.text('中文标点',self.regular,13,48,444,624)
        for i,line in enumerate(self.data['punctuation']):self.text(line,self.regular,29,48,478+i*49,624)
        self.rule(601,48,672)
        self.text('符号',self.regular,13,48,622,624)
        for i,line in enumerate(self.data['symbols']):self.text(line,self.hero,30,48,656+i*47,624)
        self.rule(786,48,672)
        for i,line in enumerate(self.data['colophon']):self.text(line,self.regular,11,48,814+i*26,624)
        self.footer(number);self.c.showPage()

    def write_html(self,out,href_base):
        out=Path(out).resolve();href_base=Path(href_base).resolve()
        faces=[]
        for row in self.styles:
            path=(self.path.parent/row['webfont']).resolve()
            href='data:font/woff2;base64,'+base64.b64encode(path.read_bytes()).decode('ascii') if self.data.get('embed_webfonts',True) else os.path.relpath(path,href_base)
            faces.append('@font-face{font-family:Specimen;src:url('+json.dumps(href)+') format("woff2");font-weight:'+str(row['weight'])+';font-style:normal;}')
        data=self.data;esc=html.escape
        css=''.join(faces)+'''*{box-sizing:border-box}body{margin:0;background:#d5d5cc;color:#151811;font-family:Specimen; font-synthesis:none}.sheet{max-width:900px;margin:auto;background:#f3f0e6}.hero{padding:38px 48px 40px;background:#b9bbaf}.latin{font-size:15px}.hero h1{font-size:clamp(110px,25vw,245px);font-weight:500;line-height:1.16;text-align:center;margin:24px 0 0}.stroke{width:86%;margin:0 auto 22px;height:25px}.description{font-size:27px;line-height:1.6;margin:20px 14px}.summary{font-size:13px}.samples{margin:0 20px;border:1.5px solid #151811;padding:25px}.weight{padding:22px 0 30px;border-bottom:1px solid #151811}.label{font-size:13px}.sample{font-size:clamp(26px,4vw,44px);line-height:1.6;margin:12px 0;white-space:pre-wrap;overflow-wrap:anywhere}.alphabet{font-size:28px;line-height:1.8;letter-spacing:.06em}.symbols{padding:30px 0}.symbols p{font-size:30px;overflow-wrap:anywhere}.footer{font-size:13px;padding:28px 0;line-height:1.8}textarea{font-family:inherit;font-size:26px;width:100%;background:#faf8f0;border:1px solid #555;padding:14px;margin:12px 0;line-height:1.6}button{font:inherit;color:inherit;font-size:14px;cursor:pointer;border:1px solid #151811;background:transparent;padding:8px 14px}.status{font-size:13px;min-height:26px}.interactive{padding:25px 0}@media print{body{background:white}.sheet{max-width:none}.interactive{display:none}}'''
        sections=''
        for row in self.styles:
            sections+='<section class="weight" style="font-weight:'+str(row['weight'])+'"><div class="label">'+esc(row['label'])+' / '+str(row['weight'])+'</div><p class="sample live">'+esc(data['sample_line'])+'</p><div class="alphabet">'+esc(data['cjk_rows'][0])+'</div></section>'
        page='<!doctype html><html lang="zh-Hans"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>'+esc(data['title'])+' · 字体样张</title><style>'+css+'</style><main class="sheet"><header class="hero"><div class="latin">'+esc(data.get('latin_name',''))+'</div><h1>'+esc(data['title'])+'</h1><svg class="stroke" viewBox="0 0 600 30" aria-hidden="true"><path d="M10 12 Q210 -2 582 12 L562 19 Q300 8 10 19Z M50 25 Q320 12 590 25 L570 29 Q300 20 50 29Z" fill="currentColor"/></svg><p class="description">'+'<br>'.join(map(esc,data['description']))+'</p><div class="summary">'+esc(data['summary'])+'</div></header><div class="samples">'+sections+'<section class="symbols"><div class="label">数字与符号</div><p>'+esc(data['digits'])+'</p>'+''.join('<p>'+esc(s)+'</p>' for s in data['punctuation']+data['symbols'])+'</section><section class="interactive"><label for="custom">写点自己的文字</label><textarea id="custom">'+esc(data['sample_line'])+'</textarea><button id="apply">应用试字</button><p class="status" id="status" role="status"></p></section><footer class="footer">'+'<br>'.join(map(esc,data['colophon']))+'</footer></div></main></html>'
        page=page.replace('font-weight:500;line-height:1.16','font-weight:'+str(self.hero['weight'])+';line-height:1.16')
        page=page.replace('#b9bbaf',self.palette['header']).replace('#f3f0e6',self.palette['paper']).replace('#151811',self.palette['ink'])
        shared=set.intersection(*(set(row['cm']) for row in self.styles))
        language=data.get('language','zh-Hans')
        if language not in ['zh-Hans','zh-Hant','zh-Hant-TW','zh-Hant-HK']:
            raise ValueError('Unsupported handbook language: '+str(language))
        traditional=language.startswith('zh-Hant')
        page=page.replace('lang="zh-Hans"','lang="'+language+'"',1)
        if traditional:
            for old,new in {
                '· 字体样张</title>':'· 字體樣張</title>',
                '<div class="label">数字与符号</div>':'<div class="label">數字與符號</div>',
                '<label for="custom">写点自己的文字</label>':'<label for="custom">寫點自己的文字</label>',
                '<button id="apply">应用试字</button>':'<button id="apply">套用試字</button>'
            }.items():page=page.replace(old,new)
        script=r'''<script>const covered=new Set(__COVERAGE__);const input=document.getElementById("custom"),status=document.getElementById("status");document.getElementById("apply").addEventListener("click",()=>{const value=input.value;const missing=[...new Set([...value].filter(c=>!["\n","\r","\t"].includes(c)&&!covered.has(c.codePointAt(0))))];if(missing.length){status.textContent=__MISSING__+missing.join("、");return;}document.querySelectorAll(".live").forEach(el=>el.textContent=value);status.textContent=__SUCCESS__;});</script>'''
        script=script.replace('__COVERAGE__',json.dumps(sorted(shared),separators=(',',':')))
        script=script.replace('__MISSING__',json.dumps('未套用，字庫尚無：' if traditional else '未应用，字库尚无：',ensure_ascii=False))
        script=script.replace('__SUCCESS__',json.dumps('已套用，所有展示字重均有覆蓋。' if traditional else '已应用，所有展示字重均有覆盖。',ensure_ascii=False))
        page=page.replace('</html>',script+'</html>')
        (out/'preview.html').write_text(page,encoding='utf-8')
        shared=set.intersection(*(set(row['cm']) for row in self.styles))
        (out/'coverage-codepoints.json').write_text(json.dumps(sorted(shared)),encoding='utf-8')

    def build(self,out):
        out=Path(out).resolve()
        if out.exists() and any(out.iterdir()):raise ValueError('Handbook output must be a new directory')
        out.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.'+out.name+'-',dir=out.parent) as temp:
            staging=Path(temp)/'book';staging.mkdir()
            pages=self._write(staging,out)
            os.rename(staging,out)
        print(json.dumps({'pdf':str(out/'handbook.pdf'),'pages':pages,'html':str(out/'preview.html')},ensure_ascii=False))

    def _write(self,out,href_base):
        self.c=canvas.Canvas(str(out/'handbook.pdf'),pagesize=(W,H),pageCompression=1)
        self.c.setTitle(self.data['title']+' · 字体样张');self.c.setAuthor(self.data.get('author','Pally'))
        self.cover()
        for i,row in enumerate(self.styles):self.weight_page(row,i+2)
        groups=[self.styles[i:i+3] for i in range(0,len(self.styles),3)]
        for i,group in enumerate(groups):self.symbol_page(len(self.styles)+2+i,group)
        pages=1+len(self.styles)+len(groups)
        self.c.save();self.write_html(out,href_base)
        report={'page_count':pages,'layout':'name-description-weights-digits-symbols','missing_glyphs':[],
                'pdf_fonts':[{k:row[k] for k in ['label','weight','mode']} for row in self.styles],
                'font_sha256':{row['label']:hashlib.sha256(row['path'].read_bytes()).hexdigest() for row in self.styles},
                'text_blocks':self.renders,'html_preview':{'embedded_fonts':self.data.get('embed_webfonts',True),'embedded_coverage':True,'missing_input':'blocked'},'visual_review':'required after PDF rendering'}
        (out/'book-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        return pages


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',required=True);p.add_argument('--out-dir',required=True)
    a=p.parse_args()
    try:Book(a.manifest).build(a.out_dir)
    except (ValueError,KeyError,OSError) as error:p.exit(2,str(error)+'\n')
