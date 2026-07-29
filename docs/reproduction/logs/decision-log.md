# 决策日志

每个已接受决策必须包含：`ID`、`date`、`decision`、`alternatives`、`evidence`、`consequence`、`revisit condition`。ID 使用递增格式 `DEC-0001`；日期采用 ISO 8601 (`YYYY-MM-DD`)。证据应区分 evidence、inference 和 unknown；尚未接受的讨论不写入本日志。

## DEC-0001

- **date：** 2026-07-22
- **decision：** 采用 V0 数字基线与 Rev.B 实体双基线：V0 用于忠实理解、比较和验证；Rev.B 用于经过计算与实验验证的实体优化，不制造完整 V0 整机。
- **alternatives：** 仅制造原版 V0；仅做 Rev.B 而不建立 V0 数字基线。
- **evidence：** `docs/superpowers/specs/2026-07-22-dummy-robot-reproduction-design.md` 第 2.1 节（evidence：已确认项目边界）。
- **consequence：** M0 记录需保留对母本的可追溯映射；高成本六轴制造资源集中于 Rev.B，V0 样件仅用于风险消除。
- **revisit condition：** 若上游资产许可、关键原版参数或 Rev.B 验证结果改变了双基线的成本、合规性或技术可行性，则复审。

## DEC-0002

- **date：** 2026-07-29
- **decision：** 将母本仓库与复现仓库分离；本仓库只保存独立编写的工程记录及后续授权成果。
- **alternatives：** 在母本工作树内直接记录；复制母本源码、CAD、PCB、固件或原始 Git 历史到复现仓库。
- **evidence：** 当前仓库的上游与许可边界（`README.md`）以及设计说明第 4.5 节的许可证待确认结论（evidence）。
- **consequence：** 复现工作可独立审计，避免未经许可的再分发；需要引用上游时记录链接、路径、版本或哈希，而非复制资产。
- **revisit condition：** 若获得清晰、适用的上游许可并且纳入某类资产确有必要，可按许可范围重新评估。
