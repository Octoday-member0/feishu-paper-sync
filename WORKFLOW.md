# 论文同步 Workflow（可转发）

把 arXiv 最近论文同步到飞书知识库，并按仓库格式提交一个 PR。适合每周一次，10 篇/批。

## 角色分工（1 人也能全做）

| 环节 | 谁做 | 产出 |
|---|---|---|
| 选题 + 核数 | 论文同学 / agent | 10 篇候选 + 关键数字 |
| 飞书写入 | 有应用权限的同学 / agent | 论文表 + 论文研读页 + 首页 |
| Git PR | 有 `Octoday-member0` PAT 的同学 / agent | 1 个 commit + 1 个 PR |
| 验收 | 另一人交叉检查 | 验收清单 |

关键原则：**选题的人不写数字，写数字的人必须回原文核对**。agent 可以全做，但人要抽查 2–3 篇。

## 一、一次性准备

### 1. 飞书应用权限

应用需要：

- `wiki:wiki:readonly`：读知识库
- `docx:document`：读写两个文档
- `bitable:app`：读写论文表
- `drive:drive`：上传封面

并把应用加为以下位置的**可编辑协作者**：

1. 知识库首页
2. 论文研读页
3. 论文汇总多维表格

没有权限的典型报错：

- 论文表：`91403 Forbidden`
- 文档：`1770032 forBidden`
- 封面上传：`1061004 forbidden`

> 首页文档可能属于另一位管理员，分享权限只给 `full_access`。如果首页加不进去，先做论文表 + 论文页，首页交给 owner 授权后补，**不要伪造“首页已更新”**。

### 2. 凭证

从内部渠道拿，不要写进 Git：

```bash
export FEISHU_APP_ID='<APP_ID>'
export FEISHU_APP_SECRET='<APP_SECRET>'
export GITHUB_TOKEN='<Octoday-member0 PAT>'
```

### 3. 拉自动化仓库

```bash
rm -rf /tmp/feishu-paper-sync /tmp/fps.tar.gz
curl -fsSL https://codeload.github.com/Octoday-member0/feishu-paper-sync/tar.gz/refs/heads/main -o /tmp/fps.tar.gz
mkdir -p /tmp/feishu-paper-sync
tar -xzf /tmp/fps.tar.gz -C /tmp/feishu-paper-sync --strip-components=1
cd /tmp/feishu-paper-sync
python3 feishu_paper_sync.py token
```

输出 `status=ok` 才继续。

## 二、每次更新的 6 步

### Step 1：拉候选

```bash
curl -sS --max-time 60 \
  "https://export.arxiv.org/api/query?search_query=cat:cs.RO&start=0&max_results=80&sortBy=submittedDate&sortOrder=descending" \
  -o /tmp/arxiv_ro.xml
```

选 **10 篇**，硬标准：

- 首次提交在最近 7 天内，不是 revision
- 与飞书已有记录不重复（标题规范化 + arXiv id 双重去重）
- 方向覆盖：VLA / 操作 / 运动控制 / 世界模型 / 空间智能 / 跨本体 / 数据 / RL
- 优先有项目页/代码、数字清楚、机构可核实
- 不为凑数编造论文、作者、机构、指标、链接

### Step 2：回原文核数

每篇至少打开 arXiv abs + HTML 正文，核实：

- 标题、arXiv id、首次提交日期、venue
- 机构（作者区，不猜）
- 一句话中文摘要
- 2–4 个关键实验数字（必须能在摘要/表格找到）
- 数据 / 模型 / 硬件
- 代码或项目页
- 封面图 URL（arXiv HTML 的 teaser / architecture 图）

### Step 3：写批次 JSON

```bash
mkdir -p /tmp/feishu-paper-sync/data
```

新建 `data/papers_<YYYYMMDD>.json`，格式照 `examples/papers_20261110.json`。每篇要同时有：

- 飞书字段：`title`、`arxiv_id`、`url`、`date`、`venue`、`categories`、`summary`、`org`、`results`、`data`、`model`、`code_url`、`cover_url`
- 仓库字段：`repo_category`、`one_line_en`、`org_en`、`repo_highlights`、`repo_results`、`data_model_en`、`repo_highlights_zh`、`repo_results_zh`、`data_model_zh`

顶层还要有：`batch_date`、`homepage_title`、`intro_zh`、`intro_short_zh`、`highlights`（5 条）。

### Step 4：写飞书

```bash
cd /tmp/feishu-paper-sync
python3 feishu_paper_sync.py preview --input data/papers_<YYYYMMDD>.json
python3 feishu_paper_sync.py apply   --input data/papers_<YYYYMMDD>.json
python3 feishu_paper_sync.py verify  --input data/papers_<YYYYMMDD>.json
```

`apply` 是幂等的：已存在的记录会跳过，文档和首页会刷新。

首页无权限时：

```bash
python3 feishu_paper_sync.py apply --input data/papers_<YYYYMMDD>.json --skip-home
python3 feishu_paper_sync.py verify --input data/papers_<YYYYMMDD>.json --skip-home
# owner 授权后只补首页
python3 feishu_paper_sync.py home --input data/papers_<YYYYMMDD>.json
```

### Step 5：Git PR

```bash
rm -rf /tmp/Embodied-AI /tmp/ea-papers
git clone --depth 1 https://github.com/Octoday-Hub/Embodied-AI.git /tmp/Embodied-AI
cd /tmp/Embodied-AI
git fetch origin main
git worktree add /tmp/ea-papers -b update/papers-<YYYYMMDD> origin/main
```

写 `/tmp/pr_body.md`（批次日期、10 篇论文表、改动文件、验收清单、飞书来源），然后：

```bash
cd /tmp/feishu-paper-sync
export GITHUB_TOKEN='<Octoday-member0 PAT>'
python3 feishu_to_git_pr.py \
  --input data/papers_<YYYYMMDD>.json \
  --repo /tmp/ea-papers \
  --branch update/papers-<YYYYMMDD> \
  --title "docs: 新增 10 篇 <YYYY-MM> 具身智能论文（飞书论文库同步）" \
  --body-file /tmp/pr_body.md
```

脚本会：插入中英文六字段表格 → `git diff --check` → 以 `Octoday-member0` 提交 → push 到 `Octoday-member0/Embodied-AI` → 对 `Octoday-Hub/Embodied-AI:main` 开 PR。

禁止：直接 push 上游 `main`、在上游建分支、提交 `.env`/token/临时文件。

### Step 6：验收 + 报告

```bash
python3 feishu_paper_sync.py verify --input data/papers_<YYYYMMDD>.json
```

必须看到 `✅ 验收通过`。报告至少包含：

- 飞书论文表：+N 条（record_id）
- 论文研读页：导语/表格/重点
- 首页：✅ 已更新 / ⚠️ 待 owner 授权
- PR：URL、commit、改动文件
- 本批论文表（标题 / arXiv / 方向 / 日期）

## 三、验收清单

- [ ] 10 篇都是最近 7 天首次提交，不是 revision
- [ ] 与飞书、Git 仓库均无重复
- [ ] 标题、日期、机构、数字能在原文找到
- [ ] 飞书 10 条记录字段无空、封面有图
- [ ] 论文页导语 + 10 行表 + 5 条重点
- [ ] 首页卡片日期与新批次一致（或明确标注待授权）
- [ ] 中英文条目 1:1，顺序、链接一致
- [ ] PR 只有 `topics/03-papers.md` + `topics/03-papers_EN.md`
- [ ] commit 作者是 `Octoday-member0 <dev_intern@dexunit.com>`
- [ ] PR base 是 `Octoday-Hub/Embodied-AI:main`，不是直接 push

## 四、常见错误

| 报错 | 原因 | 处理 |
|---|---|---|
| `91403` | 应用不是论文表可编辑协作者 | 加表协作者 |
| `1770032` | 应用不是文档可编辑协作者 | 加文档/首页协作者 |
| `1061004` | 封面上传无权限 | 开 `drive:drive` + 表编辑 |
| `99991672` | 应用缺 scope | 开放平台补权限 |
| `99991663` | token 失效 | 重新 `token` |
| `404` on arXiv HTML | 论文没有 HTML | 用 abs 页 + PDF |
| PR `not mergeable` | 上游 main 已更新 | rebase 到最新 `origin/main` 再 push |

## 五、和 agent 的配合

给 agent 的完整提示词在 `PROMPT.md`（含凭证，仅内部转发）。  
给同事的公开模板在 `PROMPT_TEMPLATE.md`（占位符，可放公开仓库）。

一句话版本：

> 按 `WORKFLOW.md` 走：选 10 篇最近 cs.RO → 回原文核数 → 写 `papers_<日期>.json` → `preview/apply/verify` → `feishu_to_git_pr.py` 开 PR → 按验收清单报告。首页无权限时 `--skip-home`，owner 授权后 `home` 补，不许写成已更新。