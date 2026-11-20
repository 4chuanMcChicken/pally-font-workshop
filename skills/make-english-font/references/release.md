# 默认构建合同

配置示例（按实际来源填写）：
```json
{
  "family": "Pally Orbit",
  "style": "Light",
  "weight": 300,
  "axes": {"wght": 300},
  "version": "0.100",
  "holder": "Pally",
  "license_reviewed": true,
  "reserved_names": [],
  "required_text": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,!?()[]{}:;@#%&+-=/",
  "specimen_title": "Orbit",
  "description": "Geometric circles, quiet rhythm.",
  "sample": "Lone leaf boat",
  "change_note": "Native weight instance and new naming; source outlines and spacing retained."
}
```

发布器拒绝未知/越界轴、未核实许可、原生字重不符、缺字、既有输出。完整保留源 cmap 子表的 Unicode 映射（含 format14）；不子集化 TTF 或 WOFF2。所有轴固定；只重写家族命名，保留功能 UI name IDs 和原始版权。保留原始 OFL 文件字节。

检查：TTF/WOFF2 cmap 往返、XML 重新编译、样本文字的 HarfBuzz glyph/cluster/advance/offset 对照、全部源字形的分解轮廓与字宽对照（相对于原生实例），报告扩展 Latin 与实际缺字。内嵌字体网页使用共同 cmap 拦截缺字。原生实例的设计可以沿用；未经编辑的全部轮廓不可计为自主设计。

required_text 原样核对，不做 NFC/NFKC 以消除缺字。默认检查 printable ASCII。默认实例核对额外覆盖 éèêëáäåçñöøüßÆŒ（仅当源支持），另报组合重音实际 shape 结果。Latin-1 printable 档是 U+0020–007E 和 U+00A0–00FF，不含控制码。

需要字形编辑或调参时将修改配方、输入 SHA、全部受影响别名和编辑前后差异独立记录；不能用默认发布器的“原生轮廓一致”去验收发生设计变化的文件。

v0.1 校验范围由真实运行生成的 report.json 决定；该文件的检查通过不是 FontBakery/OTS 或版权认证。
