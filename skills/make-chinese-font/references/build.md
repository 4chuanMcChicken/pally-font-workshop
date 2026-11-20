# 构建与验证 v0.3

## 输入与能力

工具离线运行，不安装系统字体。支持静态 glyf/CFF 或 glyf 可变字体；TTC/OTC 须先提取并核实地区 face。CFF2/VARC 明确拒绝。全部变体轴固定，不混合不同实例的 X/Y。核心字编辑仅支持静态 glyf。

```json
{
  "family": "Pally Han",
  "display_name": "小伴中文",
  "style": "Regular",
  "weight": 400,
  "version": "0.300",
  "holder": "Pally",
  "language": "zh-Hans",
  "axes": {},
  "subset": false,
  "license_reviewed": true,
  "reserved_names": [],
  "required_coverage_profiles": ["common-3500", "punctuation-digits"]
}
```

family 是新的 ASCII 工程名；display_name 写入 Windows Unicode 本地化 name IDs 1/2/4/16/17，PostScript 名保持 ASCII。简中、台繁、港繁使用各自语言 ID。底库名称和许可中的 RFN 同时检查英文名与中文名；不要遗漏许可中的保留名称。

style/weight 对应：Thin 100、ExtraLight 200、Light 300、Regular 400、Medium 500、SemiBold 600、Bold 700、ExtraBold 800、Black 900。静态字体必须与 OS/2 原生字重一致；可变轴 wght 必须与配置一致。源项目的样式名称可能不符合常见数字映射，先读真实 OS/2 值，再命名输出，不用改数字来制造新笔画。

license_reviewed 由代理在核对来源、对应 OFL 1.1、版权与 RFN 后设置；不是要求最终用户接受协议。原许可与修改记录随包保留。其他许可需要对应实现，不直接转成 OFL。纯英文设计使用独立英文流程，本工具不默认合并其他 Latin 字库。

## 入口与覆盖

- inspect：实际码位、原生字重、变体轴、布局特性、必需语料缺字及内置覆盖基准；默认语言 zh-Hans，可设 --language。
- preview：强制语料子集；--previous-build 合并同来源、同配方的历史 corpus.txt。更改配方或来源 SHA256 时拒绝累积。
- export：强制保留完整源 Unicode 映射，即使旧配置 subset=true。
- build：兼容显式 subset 配置；缺省为 false。
- coverage FONT --charset-file chars.txt --out coverage.json：按纯 UTF-8 字表检查；缺字保存诊断并非零退出。不得把带序号/注释的文本当字表。

内置基准：common-3500、standard-8105、punctuation-digits，以及面向 zh-Hant-TW/HK 的 big5-common-5401。Big5 表来自 Python 3.11.4 big5 codec 的 A440-C67E 映射，SHA256、提取方法已记录；仅验证字符映射，不认证地区字形。前两项从北京市教委公开的 GF 0023-2020 规范中按《字表》序号和 UCS 列提取，编号完整且无重复；数据文件及源 PDF SHA256 见 assets/charsets/index.json。两处 PDF 文本层未给出正常 Unicode 字符，已按同页可见 UCS 列核对，提取采用 UCS 而非字形文本层。

构建前检查完整底库对 required_coverage_profiles 的覆盖；缺字则失败。默认空列表保留旧配方兼容性；正文/UI 的配方应明确加入 common-3500 和 punctuation-digits。标题/书法试样可采用有限范围，不能因此宣称通用覆盖。

report.coverage.source_profiles 与 output_profiles 分别描述源底库和本次产物。子集只含少量字符时，输出基准覆盖也会相应下降，不将底库可用性冒充子集实际覆盖。原生码位保留、地区字形正确、IVS、规范符合性、审美质量是不同结论。

## 可靠性与校验

输出在目标目录同一文件系统的临时目录构建，校验和附件全部完成后才原子重命名为正式目录。异常时临时文件清理，已有非空发布目录不得覆盖；临时目录不可作为成功结果交付。

检查所有 Unicode cmap 表，包括存在时的 format 14 映射保留。实际排版按 Unicode script 分段；汉字与 Latin 不因一行开头不同而共用错误 script。比较实际替代字形的分解轮廓摘要、cluster、advance 和 offset，不仅比较码位集合或字距，也不机械比较可能变化的 glyph ID。

此构建器保留基线 glyph order，映射表按该稳定顺序的索引核对，避免 post format 3 重建 glyph 名称产生误报。排版结果的比较使用实际轮廓摘要，不依赖 glyph 名称或排版结果中的数字 ID。

XML 检查执行导出、导入、二进制重编译、重新打开，再比较映射及语料排版语义；WOFF2 重新核对全部 Unicode 映射与排版字形。轮廓摘要使用序列化后的规范轮廓；轮廓点表达不同可能使摘要不同，遇到失败应检查原因，不直接忽略。

行级 Han/Latin 分段不是完整的双向文本布局实现。输入中的变体选择符仍拒绝；IVS、复杂双向文本、竖排需专门流程。

## 样张与人工检查

profile-grid 只用于已知标签、逐字等大、48 px 以上、无格线透视的网格；输出是格子归一化墨色统计，不是笔画或中宫模型。普通参考图以视觉分析为主。

HTML 不是 PDF。需要 handbook 时另行分页打印并检查；没有生成就明确未完成。实际字体加载/回退、字形地区、小字号粘连、字框裁切和换行仍需人工或专门渲染工具验证。FontBakery/OTS 未运行就标注，不能由 round-trip 推断通过。

简繁兼容的一个字体可选定优先地区进行构建，再用 coverage 对另一范围的字表与用户语料额外验收。不要将 language 改成不支持的 both，或以单一地区的 report 代替双范围检查。
