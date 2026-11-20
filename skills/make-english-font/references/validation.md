# v0.1 实测记录 · 2026-11-18

- Urbanist 1.303 原生 wght=300：491 个码位、496 个 glyph；ASCII 95/95、Latin-1 指定范围 191/191。
- Outfit 1.100 原生 300 静态实例：360 个码位；ASCII 95/95，Latin-1 指定范围 190/191，缺 U+00AD（soft hyphen），如实报告，未补为假字。
- 两者均通过完整 Unicode cmap、全部分解轮廓、所有 horizontal metrics、10 组 HarfBuzz 样本的 TTF/WOFF2/XML 重新编译对照。
- Outfit 的 3 条高位 UI name IDs 与 OFL 原文件字节保留。
- 负例拒绝：既有输出、缺字、未知轴、越界轴、假字重、源家族重命名违规、未核实许可；并检测非 best cmap 子表被破坏和 advance 被破坏。
- 英文网页通过本机 HTTP 实测：内嵌字体加载、café naïve Ångström、数字输入，以及输入 🙂 后阻断回退并保留上一份有效字样。本地 file 直开未实测。
- 继承测量器已运行 Urbanist 300 的文件测量与 90 px/em 自测（cap 63 px）。最大类宽误差 2.05%；圆形小写 sidebearing 偏差约 -10.6 cap-normalized units。不能将其 0.3% 求解器阈值当作截图测量精度。用户 Lone leaf / boat 图缺 H，测量器拒绝；因此采用视觉结构对照，没有伪造完整参数。

未执行 FontBakery、OTS、全部 kerning pairs、全部语言/组合、CFF、italic、可选 x/y 求解器的完整发布。已测范围不能代表这些项目。

可复现发布/负例检查（提供允许修改的、覆盖 ASCII 的 upright glyf VF）：
```sh
python tests/test_release.py --base path/to/base-vf.ttf --license path/to/OFL.txt
```
构建配置中测试实例使用 wght=300；所选源须原生支持该实例。无字体二进制随 Skill 分发。
