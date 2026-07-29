# 贡献约定

## 分支

`main` 保存可审计、可复查的工程基线。常规工作从 `main` 创建任务分支，建议命名为 `docs/<topic>`、`m0/<topic>`、`m1/<topic>` 或 `tools/<topic>`；任务完成并检查后再合并。无父提交的工作区初始化可直接在 `main` 创建首个提交。

## 提交

提交标题格式为：

```text
type(scope): summary
```

允许的 `type`：`docs`、`feat`、`fix`、`test`、`build`、`chore`、`refactor`。例如：

```text
docs(project): establish engineering workspace
feat(m1-can): add target-angle frame codec
fix(m0-inventory): sort repository-relative paths
```

每个提交只服务于一个明确目的；不要将格式化、无关重命名或上游资产复制混入同一提交。使用显式暂存（逐文件 `git add <path>`）确认提交范围，避免 `git add .` 或 `git add -A`。

## 提交前检查

提交前至少执行与改动相匹配的测试或结构检查，并运行：

```bash
git diff --check
git status --short
```

记录文件必须说明证据来源、测量或未知项；实验记录必须包含安全边界和验收结论。不得提交密钥、派生构建产物、未审查的上游资产，或把推断写成事实。
