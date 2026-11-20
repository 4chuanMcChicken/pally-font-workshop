#!/usr/bin/env python3
"""Create a consumer kit: installable fonts at root, supporting files under 资料."""
from pathlib import Path
import argparse
import json
import os
import re
import shutil
import tempfile
import zipfile


def package(kit, out, zip_path=None):
    kit, out = Path(kit).resolve(), Path(out).resolve()
    if not kit.is_dir() or out.exists() or out == kit or kit in out.parents:
        raise ValueError('Input must exist; output must be new and outside input')
    if zip_path and Path(zip_path).exists():
        raise ValueError('ZIP output already exists')
    files = sorted(p for p in kit.rglob('*') if p.is_file() and not any(
        part in {'.DS_Store', '__pycache__', '.git'} for part in p.relative_to(kit).parts))
    if any(p.is_symlink() for p in files):
        raise ValueError('Symlinks are not accepted in a release kit')
    fonts = [p for p in files if p.suffix.lower() in {'.ttf', '.otf'}]
    if not fonts:
        raise ValueError('No installable font in input')
    names = [p.name.casefold() for p in fonts]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate font filenames; rename explicitly before packaging')
    mapping = {p: (Path(p.name) if p in fonts else Path('资料') / p.relative_to(kit)) for p in files}
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.' + out.name + '-', dir=out.parent))
    zip_tmp = None
    try:
        for old, rel in mapping.items():
            new = stage / rel
            new.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old, new)

        def rewrite(value, old_file, new_file):
            if not isinstance(value, str) or not value or '\n' in value:
                return value
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', value) or value.startswith('#'):
                return value
            old_target = (old_file.parent / value).resolve()
            if old_target in mapping:
                return Path(os.path.relpath(stage / mapping[old_target], new_file.parent)).as_posix()
            return value

        def walk(value, old, new):
            if isinstance(value, dict):
                return {k: walk(v, old, new) for k, v in value.items()}
            if isinstance(value, list):
                return [walk(v, old, new) for v in value]
            return rewrite(value, old, new)

        for old, rel in mapping.items():
            new = stage / rel
            if old.suffix.lower() == '.json':
                value = json.loads(old.read_text())
                new.write_text(json.dumps(walk(value, old, new), ensure_ascii=False, indent=2) + '\n')
            elif old.suffix.lower() in {'.html', '.css'}:
                text = old.read_text()
                # Local font/link paths are quoted in the generators' HTML and CSS.
                text = re.sub(r'([\"\x27])([^\"\x27\n]+)\1',
                              lambda m: m[1] + rewrite(m[2], old, new) + m[1], text)
                new.write_text(text)
        (stage/'资料'/'先看这里.txt').write_text(
            '安装字体：回到上一层，双击 TTF（或 OTF）文件，再点击安装。\n'
            '有多个字重时，可以一起安装；网页字体 WOFF2 无需桌面安装。\n'
            '手册在 handbook/，原生字重、来源、覆盖与许可见各字体构建目录。\n'
            '分享时请保留整个字体包及许可文件。\n')
        os.rename(stage, out)
        if zip_path:
            zip_path = Path(zip_path).resolve()
            zip_path.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(prefix='.' + zip_path.name, dir=zip_path.parent)
            os.close(fd)
            zip_tmp = Path(name)
            with zipfile.ZipFile(zip_tmp, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
                for p in sorted(out.rglob('*')):
                    if p.is_file():
                        z.write(p, Path(out.name) / p.relative_to(out))
            with zipfile.ZipFile(zip_tmp) as z:
                if z.testzip():
                    raise ValueError('ZIP integrity check failed')
            os.rename(zip_tmp, zip_path)
        return {'folder': str(out), 'fonts': [p.name for p in fonts], 'support_folder': '资料',
                'zip': str(zip_path) if zip_path else None}
    except BaseException:
        if stage.exists():
            shutil.rmtree(stage)
        if zip_tmp and zip_tmp.exists():
            zip_tmp.unlink()
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kit', required=True)
    parser.add_argument('--out-dir', required=True)
    parser.add_argument('--zip')
    args = parser.parse_args()
    print(json.dumps(package(args.kit, args.out_dir, args.zip), ensure_ascii=False))
