# 失败日志

每条真实失败必须包含：`ID`、`symptom`、`reproduction`、`layer classification`、`measurements`、`root cause`、`correction`、`regression test`。ID 使用递增格式 `FAIL-0001`；日期可在各字段中补充。`layer classification` 必须且只能选用以下一个值：`power`、`wiring`、`physical`、`peripheral`、`driver`、`protocol`、`application`、`toolchain`。

## 当前状态

当前没有已确认的真实失败记录。出现可复现症状后，按上述字段建立条目；在根因未经证据确认前，保留为待验证假设而非编造结论。
