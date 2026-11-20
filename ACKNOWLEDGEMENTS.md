# 致谢与来源

## 原始 Skill

特别感谢 **Arlan Marat（[@arla6ka](https://github.com/arla6ka)）** 的 [design.how](https://github.com/arla6ka/design.how) 与其中的 `make-font`。本项目从它“分析参考 → 开放底库 → 测量/拟合 → 字距 → 字样册”的方法出发，并复用了部分 MIT 代码。

固定参考提交：`1ce5304466db2ba47a7a7524603e86df77c702bd`。

英文 Skill 保留的原始脚本：`fontlib.py`、`measure_font.py`、`measure_image.py`、`make_targets.py`、`fit_font.py`、`space_font.py`。原始 `Copyright (c) 2026 Arlan Marat` 和 MIT 许可保留在 `skills/make-english-font/LICENSE`。这不是只借用了一个名字，也不是将原项目的实现称为全部自行原创。

我们新增了中文引擎、简体/繁体路由、简繁独立覆盖检查、真实字样确认、保守原生字重发布、缺字阻断、扁平字体包和本次海报集。字体逐字绘制与关键字修改的范围见各自 SOURCE.json；多数中文字符来自允许修改的开放底库。

这是独立衍生项目，原作者及各字体原作者未被宣称为本项目背书。

## 字体底库

下面的版权信息来自实际字体文件；每套原始 OFL 文本都单独随字体分发。

### 团子 / Tuanzi

保留 975 圆原生轮廓与字重，整理字体名称和交付。

来源：https://github.com/lxgw/975Yuan

原始版权记录：

> Copyright 2020-2026 LXGW (https://github.com/lxgw/975Yuan), with Reserved Font Name '霞鹜', '霞鶩', '落霞孤鹜', '落霞孤鶩' and 'LXGW'.
> Copyright 2014-2025 Adobe (http://www.adobe.com/), with Reserved Font Name 'Source'. Source is a trademark of Adobe in the United States and/or other countries.
> Copyright 2024-2026 Tamcy (https://github.com/chiron-fonts/chiron-go-round-tc).
> Copyright 2024-2026 Takushun Wu (https://github.com/takushun-wu/), with Reserved Font Name 'WenYuan Rounded', '文渊圆体'.
> Copyright 2020 Chun yu Yao (https://github.com/max32002/swei-gothic)
> Copyright 2019 Ek Type (www.ektype.in)
> Modifications: Pally

许可：[OFL.txt](fonts/tuanzi/资料/OFL.txt)；详见 [SOURCE.json](fonts/tuanzi/资料/SOURCE.json)。

### 霓虹回路 / Neon Circuit

保留 Glow Sans SC Condensed Book 原生 CFF 轮廓；原生字重数值为 500，实际格式为 OTF。

来源：https://github.com/welai/glow-sans

原始版权记录：

> Glow Sans (c) 2021 Project Welai
> Modifications: Pally

许可：[OFL.txt](fonts/neon-circuit/资料/OFL.txt)；详见 [SOURCE.json](fonts/neon-circuit/资料/SOURCE.json)。

### 墨有引力 / Ink Gravity

保留 Ma Shan Zheng 原生轮廓，整理名称、字样和交付。

来源：https://github.com/google/fonts/tree/main/ofl/mashanzheng

原始版权记录：

> Copyright 2018 The MaShanZheng Project Authors (https://github.com/googlefonts/mashanzheng)
> Modifications: Pally

许可：[OFL.txt](fonts/ink-gravity/资料/OFL.txt)；详见 [SOURCE.json](fonts/ink-gravity/资料/SOURCE.json)。

### 歪歪日记 / Wonky Notes

以 Yozai 为底库；仅「乱」「写」轻微旋转，其余轮廓继承底库。

来源：https://github.com/lxgw/yozai-font

原始版权记录：

> Copyright 2020, 2024 LXGW (https://github.com/lxgw/yozai-font)
> Original Font Data Copyright (C) Y.OzVox.
> Modifications: Pally

许可：[OFL.txt](fonts/wonky-notes/资料/OFL.txt)；详见 [SOURCE.json](fonts/wonky-notes/资料/SOURCE.json)。

### 云野生风 / Cloudwind

保留 Liu Jian Mao Cao 原生草书轮廓；没有从参考截图提取字形。

来源：https://github.com/google/fonts/tree/main/ofl/liujianmaocao

原始版权记录：

> Copyright 2018 The Liu Jian Mao Cao Project Authors (https://www.github.com/googlefonts/liujianmaocao)
> Modifications: Pally

许可：[OFL.txt](fonts/cloudwind/资料/OFL.txt)；详见 [SOURCE.json](fonts/cloudwind/资料/SOURCE.json)。

### 晚风来信 / Evening Letter

保留 LXGW WenKai 1.530 原生轮廓与两个原生字重，整理名称与交付。

来源：https://github.com/lxgw/LxgwWenKai

原始版权记录：

> Copyright 2021-2026 LXGW (https://github.com/lxgw/LxgwWenKai), with Reserved Font Name '霞鹜', '霞鶩', '落霞孤鹜', '落霞孤鶩' and 'LXGW'.
> Copyright 2020 The Klee Project Authors (https://github.com/fontworks-fonts/Klee)
> Modifications: Pally

许可：[OFL.txt](fonts/evening-letter/资料/OFL.txt)；详见 [SOURCE.json](fonts/evening-letter/资料/SOURCE.json)。

### 折光 / Prism

公开版从 LXGW Marker Gothic 重建：全角字共享宽高变换、轻微转角与斜线弯曲；不包含私人版从截图提取的「葉」。

来源：https://github.com/lxgw/LxgwMarkerGothic

原始版权记录：

> Copyright 2021-2026 The LXGW Marker Gothic Project Authors (https://github.com/lxgw/LxgwMarkerGothic)

许可：[OFL.txt](fonts/prism/资料/OFL.txt)；详见 [SOURCE.json](fonts/prism/资料/SOURCE.json)。

### 慢慢来 / Slowday

公开版从 Yozai 重建；自/由分别轻微旋转 -1.5/+1.5 度，不包含私人版从截图提取的轮廓。

来源：https://github.com/lxgw/yozai-font

原始版权记录：

> Copyright 2020, 2024 LXGW (https://github.com/lxgw/yozai-font)
> Original Font Data Copyright (C) Y.OzVox.

许可：[OFL.txt](fonts/slowday/资料/OFL.txt)；详见 [SOURCE.json](fonts/slowday/资料/SOURCE.json)。

### 糯米日常 / Nuomi

保留已确认的 Yozai 原生手写轮廓；这是字体选型与整理版，没有重绘全部汉字。

来源：https://github.com/lxgw/yozai-font

原始版权记录：

> Copyright 2020, 2024 LXGW (https://github.com/lxgw/yozai-font)
> Original Font Data Copyright (C) Y.OzVox.
> Modifications: Pally

许可：[OFL.txt](fonts/nuomi/资料/OFL.txt)；详见 [SOURCE.json](fonts/nuomi/资料/SOURCE.json)。

### Leafline / Leafline

Urbanist 1.303 原生 400 底库；独立重绘 a/n/h/m/f/t，含重音组件共 38 个轮廓变化，并调整 ra/Pa 阅读字距。

来源：https://github.com/coreyhu/Urbanist

原始版权记录：

> Copyright 2021 The Urbanist Project Authors (https://github.com/coreyhu/Urbanist)

许可：[OFL.txt](fonts/leafline/资料/OFL.txt)；详见 [SOURCE.json](fonts/leafline/资料/SOURCE.json)。

### Sidekick / Sidekick

基于 DM Sans 拟合比例和分类字宽；原生 ss02 单层 a 设为默认，保留重音字映射与布局。

来源：https://github.com/googlefonts/dm-fonts

原始版权记录：

> Copyright 2014 The DM Sans Project Authors (https://github.com/googlefonts/dm-fonts)
> Copyright 2026 Pally (modifications)

许可：[OFL.txt](fonts/sidekick/资料/OFL.txt)；详见 [SOURCE.json](fonts/sidekick/资料/SOURCE.json)。

