# 论文同步 · 使用说明（两段提示词，复制粘贴即可）

这个仓库**不是流程文档**，日常只需要两段提示词，复制粘贴给 AI 即可：

| 步骤 | 复制哪个文件 | 丢给谁 | 产出 |
|---|---|---|---|
| ① 更新飞书 | [PROMPT-飞书更新.md](PROMPT-飞书更新.md) | doubao work / DeepSeek Harness / Codex | 论文表 +10 条、论文研读页、知识库首页 |
| ② 提交 Git | [PROMPT-Git提交.md](PROMPT-Git提交.md) | Codex / DeepSeek Harness | 按仓库格式的 1 个 commit |

不需要克隆仓库、不需要安装/运行任何脚本。

---

## 一、怎么用（发给同事的就是这段）

### 第 1 步：更新飞书（一段提示词）

1. 打开 [PROMPT-飞书更新.md](PROMPT-飞书更新.md)，点右上角 **Raw**（或 **Copy raw file**）后**全选复制**；
2. 粘贴到 doubao work 或 DeepSeek Harness，发送；
3. Agent 会先要一次性的 **App Secret**（向知识库 owner 要，见第三节），粘贴给它；
4. 等它跑完，会输出「飞书更新」报告（论文表 +N 条、论文研读页、首页状态）。

### 第 2 步：提交 Git（另一段提示词）

1. 飞书更新完成后，打开 [PROMPT-Git提交.md](PROMPT-Git提交.md)，同样 **Raw → 全选复制**；
2. 粘贴给 Codex / DeepSeek Harness，发送；
3. Agent 会从飞书论文表读**还没入库的最近论文**（用 arXiv id 与仓库去重），回 arXiv 补齐英文与特点，按 `Octoday-Hub/Embodied-AI` 既有格式插入中英两个论文页，**生成 1 个 commit**；
4. 默认只 commit 不推送；要 push / 开 PR 就在末尾加一句「推送」或「开 PR」。

> 两段提示词可以连着用。第二段默认取飞书表里**还没进仓库的最近论文**（按 arXiv id 去重，同一批跨多天也能正确识别），不需要把论文数据贴来贴去；如果想只入库指定几篇，把 arXiv id 列表直接贴在第二段提示词末尾即可。

### 直接转给同事的一段话（可复制）

> 帮忙做一下本周的论文同步：打开 https://github.com/Octoday-member0/feishu-paper-sync/blob/main/PROMPT-飞书更新.md ，把整段内容复制，粘到 doubao work 或 DeepSeek Harness 里发送。它会问你要飞书 App Secret（找我要）。跑完把报告发我。之后再用同仓库的 PROMPT-Git提交.md 跑一次 Git 提交。

---

## 二、验收标准（就是需求本身）

第 1 步完成后，去飞书知识库检查：

- [ ] **论文汇总多维表格**：新增 **10 条**最近一周的论文记录；标题 / 日期 / 类别 / 摘要 / 机构 / 会议 / 原文链接 / 实验结论 / 数据 / 模型字段完整，封面有图；
- [ ] **论文研读页**：导语更新为本批说明（含「10 篇」），表格 10 行是本批新论文，5 条重点论文已更新；
- [ ] **知识库首页**：「近期更新 → 📄 论文」卡片标题日期更新为本批日期，正文有「本次新增 10 篇近期具身智能论文」的介绍；
- [ ] 同一 arXiv id 不重复入库，不删旧数据。

第 2 步完成后检查：

- [ ] `topics/03-papers.md` 与 `topics/03-papers_EN.md` 各新增 N 条，中英 1:1；
- [ ] 只有这两个文件被改动，且是**一个 commit**，作者 `Octoday-member0 <dev_intern@dexunit.com>`；
- [ ] 没有直接 push 上游 `main`（要推送就推 `Octoday-member0/Embodied-AI` 的 `update/papers-<日期>` 分支）。

---

## 二·五、实测记录（2026-11-19，用本仓库两段提示词跑通）

| 项目 | 结果 |
|---|---|
| 飞书论文表 | 320 → **330** 条，本批 +10（Z-sight / RoboMorpher / SHAPE / RoboTeam / LuxTac / ScaleVLA / ALOHA Lightning / HubEgo-100K / DexFormer 2.0 / MoViC），字段与封面完整 |
| 论文研读页 | 导语 + 表格 10 行 + 5 条重点全部更新 ✅ |
| 知识库首页 | ⚠️ `1770032 forBidden`（应用不是首页协作者），卡片仍为 `10.30｜📄 论文`；验收记录里如实标注「待 owner 授权」 |
| Git | 生成 1 个 commit：`c4f107a`（作者 `Octoday-member0 <dev_intern@dexunit.com>`），只改 `topics/03-papers.md` + `topics/03-papers_EN.md`，各 +130 行；commit 保留在 fork 分支 `Octoday-member0/Embodied-AI:update/papers-20261119`（PR #29 已按需求撤回、未合并，分支可随时重新开 PR） |
| 用时 | 约 40 分钟（含逐篇回 arXiv 核实、封面下载与核验） |

首页权限补上之后，用提示词里第 7.4 节的「补首页模式」+ `/tmp/feishu_batch_<日期>.json` 即可补，不用重跑整批。

---

## 三、一次性准备（owner 做一次即可）

### 1. 飞书应用权限

应用 `cli_aa63c8579579dbf1` 需要 scope：

- `wiki:wiki:readonly`：读知识库；
- `docx:document`：读写「论文研读」「知识库首页」两个文档；
- `bitable:app`：读写论文汇总多维表格；
- `drive:drive`：上传封面。

并把应用加为以下三处的**可编辑协作者**：

1. 论文汇总多维表格；
2. 论文研读页；
3. 知识库首页。

> ⚠️ **当前已知缺口（2026-11-19 核对）**：应用对论文表、论文研读页可编辑；对**知识库首页**返回 `1770032 forBidden`，首页论文卡片此前一直停留在 `10.30｜📄 论文`。需要首页 owner 打开首页文档 → 右上角「···」→ 添加协作者 → 搜索应用 ID `cli_aa63c8579579dbf1` → 设为「可编辑」。没有这一步，验收标准里的「首页有论文更新说明」无法达成（提示词会如实标注「⚠️ 待 owner 授权」，不会伪造）。

### 2. App Secret 的分发

- App Secret **不写进本仓库**（仓库是 public 的），也不写进提示词；
- 提示词运行时会主动向使用者索要；
- 由 owner 通过内部渠道（飞书私聊等）发给要跑同步的同事，一次性配置即可。

### 3. Git 侧（只影响第 2 步的推送）

- 只做本地 commit：不需要任何凭证；
- 要 push / 开 PR：需要一个对 `Octoday-member0/Embodied-AI` 有写权限的 PAT，或用已登录 `gh` 的账号。

---

## 四、常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| Agent 说没有命令/联网能力 | 所用 agent 不支持执行 shell / HTTP | 换 DeepSeek Harness / Codex 等能执行命令的 agent |
| 论文表报 `91403` | 应用不是论文表可编辑协作者 | owner 把应用加为表「可编辑」 |
| 论文页 / 首页报 `1770032` | 应用不是文档可编辑协作者 | 论文页找 owner 授权；首页见上文缺口说明。授权后对 agent 说「只补首页」并给出 `/tmp/feishu_batch_<日期>.json` 即可，不用重跑整批 |
| 封面失败 `1061004` | 上传无权限 | 跳过封面即可，非必填 |
| `99991672` | 应用缺 scope | owner 在飞书开放平台补权限 |
| `99991663` | App Secret 错误 / token 失效 | 向 owner 重新确认 secret |
| arXiv HTML 404 | 论文没有 HTML 版 | 用 abs 页 + PDF 核实 |
| 第二段选多了 / 选少了 | 飞书表里同期有多批 | 正常会按 arXiv id 与仓库去重，不会重复入库；想精确控制就在提示词末尾贴本批 arXiv id 列表 |

---

## 五、仓库里的其它文件

| 文件 | 用途 |
|---|---|
| `PROMPT-飞书更新.md` | 一段复制即用的飞书更新提示词 |
| `PROMPT-Git提交.md` | 一段复制即用的 Git 论文入库提示词 |
| `examples/papers_20261110.json` | 2026-11-10 批次的完整数据，字段样例参考 |
| `feishu_paper_sync.py` / `feishu_to_git_pr.py` | 维护者用的脚本路径（可选，日常不需要） |
| `MAINTAINER.md` | 维护者手册：脚本用法、批次 JSON 格式、排错 |

> 仓库是 public 的：提示词里只有 app_id、app_token、table_id、doc_token 这些资源标识，**没有** App Secret、没有 GitHub PAT。App Secret 只在运行时由使用者粘贴。