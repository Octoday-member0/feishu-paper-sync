# feishu-paper-sync

一段提示词，自动把 **10 篇最近一周的 arXiv `cs.RO` 论文**同步进 **星期八 / Octoday Hub 具身智能知识库**：

1. 写入飞书「论文汇总」多维表格（含字段与封面）；
2. 更新「论文研读」页（导语 + 10 行表格 + 5 条重点论文）；
3. 更新知识库首页「近期更新 → 📄 论文」卡片；
4. 再把同一批论文按 `Octoday-Hub/Embodied-AI` 仓库格式整理成 **1 个 commit**（可选推送 / 开 PR）。

日常使用**不需要克隆本仓库、不需要安装脚本**，复制两段提示词给 AI 即可。

## 30 秒上手

| 步骤 | 复制这个文件 | 丢给谁 |
|---|---|---|
| ① 更新飞书 | **[PROMPT-飞书更新.md](PROMPT-飞书更新.md)** | doubao work / DeepSeek Harness / Codex |
| ② 提交 Git | **[PROMPT-Git提交.md](PROMPT-Git提交.md)** | Codex / DeepSeek Harness |

打开文件 → 点 **Raw** → 全选复制 → 粘贴发送。Agent 会要一次飞书 **App Secret**（向知识库 owner 要）。

完整使用说明、验收标准、权限准备、常见问题见 **[WORKFLOW.md](WORKFLOW.md)**。

## 验收标准

- 飞书论文表新增 **10 条**最近一周论文，字段完整、封面有图、无重复；
- 论文研读页更新导语 + 10 行表格 + 5 条重点；
- 知识库首页论文卡片更新日期与「本次新增 10 篇近期具身智能论文」说明；
- Git 侧中英论文页各 +N 条，**一个 commit**，作者 `Octoday-member0 <dev_intern@dexunit.com>`。

## 文件说明

| 文件 | 说明 |
|---|---|
| `PROMPT-飞书更新.md` | 一段复制即用的飞书更新提示词（自包含，无仓库依赖） |
| `PROMPT-Git提交.md` | 一段复制即用的 Git 论文入库提示词（默认只 commit） |
| `WORKFLOW.md` | 使用说明 + 验收标准 + 权限准备 + FAQ |
| `MAINTAINER.md` | 维护者手册：可选脚本路径、批次 JSON 格式、排错 |
| `feishu_paper_sync.py` | 维护者脚本：飞书写入 / 校验 / 补首页（可选） |
| `feishu_to_git_pr.py` | 维护者脚本：批次 → 中英文条目 → commit → push fork → PR（可选） |
| `examples/papers_20261110.json` | 批次数据样例（脚本路径用） |

## 安全说明

本仓库是 public 的。提示词里只包含 app_id、app_token、table_id、doc_token 这类资源标识，**不包含** App Secret、不包含 GitHub PAT；App Secret 由使用者运行时粘贴，只存在于当次会话。