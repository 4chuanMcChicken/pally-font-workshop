#!/usr/bin/env python3
"""Export all poster PNGs and the contact sheet from the same final PDF."""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess, tempfile
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pdftoppm', default='pdftoppm')
    args = ap.parse_args()
    families = json.loads((ROOT / 'catalog.json').read_text())['families']
    pdf = ROOT / 'posters/poster-catalog.pdf'
    sheet = Image.new('RGB', (1600, 1620), '#e4e1d7')
    draw = ImageDraw.Draw(sheet)
    with tempfile.TemporaryDirectory() as tmp:
        prefix = Path(tmp) / 'page'
        subprocess.run([args.pdftoppm, '-r', '144', '-png', str(pdf), str(prefix)], check=True)
        pages = sorted(Path(tmp).glob('page-*.png'))
        assert len(pages) == len(families)
        for i, (page, family) in enumerate(zip(pages, families)):
            target = ROOT / 'posters' / f"{i+1:02d}-{family['slug']}.png"
            shutil.copyfile(page, target)
            pic = Image.open(target)
            assert pic.size == (2340, 3060)
            pic.thumbnail((375, 495))
            x, y = 12 + i % 4 * 400, 12 + i // 4 * 540
            sheet.paste(pic, (x, y))
            draw.text((x, y + 500), family['slug'], fill='#333333')
    sheet.save(ROOT / 'posters/contact-sheet.jpg', quality=95)
    paths = [pdf, ROOT / 'posters/contact-sheet.jpg', *sorted((ROOT / 'posters').glob('*.png'))]
    manifest = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (ROOT / 'posters/raster-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')

if __name__ == '__main__':
    main()
