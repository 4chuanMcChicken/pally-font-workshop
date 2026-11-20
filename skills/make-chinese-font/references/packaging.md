# 用户字体包结构

用户已明确要求：解压后第一层直接看到可安装的字体，其余文件收进一个大文件夹。此要求适用于后续交付包，不改变构建引擎的内部目录。

```text
字体名-v版本/
  PallyName-Regular.ttf
  PallyName-Medium.ttf
  资料/
    先看这里.txt
    handbook/
    book-manifest.json
    fonts/regular/  # WOFF2、CSS、许可、配方、报告等
    fonts/medium/
```

真实原生字重全部平铺；若实际输出为 OTF，平铺 OTF，不伪装改扩展名为 TTF。不要添加重复的字体文件、顶层报告或多层嵌套的 ZIP。

先在工作目录完成字体、手册及审核，再生成单独的用户包：

```sh
python "$SKILL_DIR/scripts/package_font.py" --kit staging-kit --out-dir releases/字体名-v版本 --zip releases/字体名-v版本.zip
```

脚本把所有 TTF/OTF 移到根目录，其他内容移入 `资料/`，并修复 JSON manifest、HTML、CSS 中原有的本地文件引用。不更改字体二进制、家族名、字重或许可证。输入和目标必须不同，目标不得已存在；同名字体冲突会停止，让调用者明确命名。不要把原始截图、无关候选或辅助字体放进 staging-kit。

交付前验证根目录只有安装字体和 `资料/`；ZIP 完整可解压；各字体 SHA256 与构建结果相同。打包后检查 `资料/handbook/preview.html` 的字体载入、自定义文字和缺字阻断。默认内嵌字体和字表；若浏览器工具限制本地文件协议，用本机 HTTP 检查并注明直开未实测。最终消息优先提供单独 TTF（用户可以直接下载）和完整 ZIP，手册按需要展示。
