# 复现记录工作区

此目录保存独立编写的复现工程记录，不保存或重新分发上游 Dummy Robot 的源码、CAD、PCB、固件或历史。

## 事实标记

- `evidence`：可定位的原始来源或可复现测量，例如文件路径、版本、数据手册页码、照片、示波器截图或原始数据文件。
- `inference`：由一个或多个证据导出的工程判断；必须链接其依据并明确适用条件。
- `unknown`：当前不能由证据确认、且尚未通过测量验证的信息；应写明需要的验证方法或阻塞条件。

三者不得互相替代。未验证的推断保持为 `inference` 或 `unknown`，不能写成 V0 事实。

## 母本引用

母本和复现仓库采用相邻目录，默认从复现仓库以 `../Dummy-Robot` 访问只读母本。正式记录不写 `/home/...` 等本机绝对路径，而使用：

```text
upstream:<relative-posix-path>
```

例如：

```text
upstream:2.Firmware/Core-STM32F4-fw/Robot/instances/dummy_robot.cpp
```

M0 的 `source-lock.json` 保存母本规范 URL、实际 checkout URL、完整提交 SHA 和参与清单的资产根。母本资产根存在未提交修改时，不得生成正式清单。

## 实验与数据命名

实验记录使用 `YYYY-MM-DD-<milestone>-<topic>.md`，例如 `2026-08-01-m1-can-loopback.md`。原始数据与记录同名并保留可识别扩展名，例如 `2026-08-01-m1-can-loopback.csv`、`2026-08-01-m1-can-loopback.png`。名称使用小写 ASCII、连字符分词，不使用“final”“new”等不可追溯词。

提交记录必须能通过 Git 提交 SHA 关联到实验。体积较大或工具专有的临时采集文件按 `.gitignore` 处理；需要复核的摘要数据、处理脚本、配置和正式 CSV 可提交。

## 记录工作流

1. 从 `templates/experiment-record.md` 创建具体实验记录，并在上电前填写问题、来源证据、接线、预测、仪器设置和低压安全边界。
2. 运行实验，保存原始数据及其采集条件；若出现问题，按 `logs/failure-log.md` 的模式记录，不猜测根因。
3. 将结果逐项对照验收标准，声明结论的 `evidence`、`inference` 或 `unknown` 状态，并映射回 Dummy Robot 的对应接口、部件或风险。
4. 在 `logs/decision-log.md` 中记录已经接受的可追溯决策及其复审条件；提交前完成复核清单。

模板是最低要求。复制模板后将标题改为具体实验名，不能以未填写的模板充当实验结论。
