# 维护者手册（脚本路径，可选）

日常同步请直接用两段提示词：

- [PROMPT-飞书更新.md](PROMPT-飞书更新.md)
- [PROMPT-Git提交.md](PROMPT-Git提交.md)

本文件只给维护者参考：当你需要**确定性地**跑飞书写入、或想批量重放一个历史批次时，可以用仓库里的两个脚本。脚本能力与提示词等价，只是把 API 调用固化成了代码。

---

## 1. 一次性准备

### 1.1 飞书应用

应用 `cli_aa63c8579579dbf1` 需要：

| Scope | 用途 |
|---|---|
| `wiki:wiki:readonly` | 读知识库 |
| `docx:document` | 读写「论文研读」「知识库首页」 |
| `bitable:app` | 读写论文汇总多维表格 |
| `drive:drive` | 上传封面 |

并把应用加为 **论文汇总多维表格、论文研读页、知识库首页** 的「可编辑」协作者。

> ⚠️ 2026-11-19 核对：应用对首页仍报 `1770032 forBidden`，需要首页 owner 授权后才能补首页卡片。论文表与论文研读页正常。

### 1.2 凭证

```bash
export FEISHU_APP_ID='cli_aa63c8579579dbf1'
export FEISHU_APP_SECRET='<向 owner 索取，不要写进 Git>'
```

Git 侧推送 / 开 PR 时：

```bash
export GITHUB_TOKEN='<Octoday-member0 PAT，repo scope>'
```

### 1.3 拉仓库

```bash
rm -rf /tmp/feishu-paper-sync /tmp/fps.tar.gz
curl -fsSL https://codeload.github.com/Octoday-member0/feishu-paper-sync/tar.gz/refs/heads/main -o /tmp/fps.tar.gz
mkdir -p /tmp/feishu-paper-sync
tar -xzf /tmp/fps.tar.gz -C /tmp/feishu-paper-sync --strip-components=1
cd /tmp/feishu-paper-sync
python3 feishu_paper_sync.py token   # 输出 status=ok 才能继续
```

---

## 2. 批次 JSON 格式

新建 `data/papers_<YYYYMMDD>.json`，格式照 [`examples/papers_20261110.json`](examples/papers_20261110.json)。

每篇论文需要同时包含飞书字段和仓库字段：

```json
{
  "title": "...",
  "arxiv_id": "2611.10872",
  "url": "https://arxiv.org/abs/2611.10872",
  "date": "2026-11-07",
  "venue": "arXiv 预印本",
  "categories": ["VLA模型", "空间智能"],
  "summary": "一句话中文摘要",
  "org": "机构（中文）",
  "results": "实验结论，带关键数字",
  "data": "数据设置",
  "model": "模型/方法",
  "code_url": "https://...",
  "cover_url": "https://arxiv.org/html/.../fig.png",
  "repo_category": "embodied-foundation-models",
  "one_line_en": "...",
  "org_en": "...",
  "repo_highlights": ["..."],
  "repo_results": ["..."],
  "data_model_en": "...",
  "repo_highlights_zh": ["..."],
  "repo_results_zh": ["..."],
  "data_model_zh": "..."
}
```

顶层还需要：`batch_date`、`homepage_title`（如 `11.10｜📄 论文`）、`intro_zh`、`intro_short_zh`、`highlights`（5 条，每条含 `arxiv_id`、`text`、`link_text`、`link_url`）。

`categories` 只能取 13 个值：
`空间智能`、`数据与生成`、`运动与控制`、`模仿学习`、`强化学习`、`VLA模型`、`感知与多模态`、`世界模型`、`部署与加速`、`推理与规划`、`跨本体泛化`、`机器人基础模型`、`仿真与基准`。

`repo_category` 只能取 8 个值：
`embodied-foundation-models`、`manipulation`、`locomotion`、`navigation`、`simulators`、`datasets`、`benchmarks`、`survey`。

---

## 3. 飞书写入

```bash
cd /tmp/feishu-paper-sync
python3 feishu_paper_sync.py preview --input data/papers_<YYYYMMDD>.json
python3 feishu_paper_sync.py apply   --input data/papers_<YYYYMMDD>.json
python3 feishu_paper_sync.py verify  --input data/papers_<YYYYMMDD>.json
```

`apply` 是幂等的：已存在的记录（标题规范化相同或 arXiv id 相同）会跳过，文档和首页会刷新。

首页无权限时：

```bash
python3 feishu_paper_sync.py apply --input data/papers_<YYYYMMDD>.json --skip-home
python3 feishu_paper_sync.py verify --input data/papers_<YYYYMMDD>.json --skip-home
# owner 授权后只补首页，不用重跑整批
python3 feishu_paper_sync.py home --input data/papers_<YYYYMMDD>.json
```

### 子命令

| 命令 | 用途 |
|---|---|
| `token` | 验证 App 凭证 |
| `list` | 查看最新 20 条记录 |
| `preview --input` | 校验批次 JSON + 显示去重结果 |
| `apply --input` | 上传封面、建记录、更新论文研读页 + 首页，然后校验 |
| `apply --input --skip-home` | 同上，但容忍首页无权限 |
| `home --input` | 只刷新首页论文卡片（权限恢复后补） |
| `verify --input` | 检查记录 / 论文页 / 首页 |
| `verify --input --skip-home` | 跳过首页检查 |
| `export --input --out` | 输出 Git PR 用的 Markdown 片段 |

---

## 4. Git 提交 / PR

```bash
# 干净 worktree，基于最新 upstream main
rm -rf /tmp/Embodied-AI /tmp/ea-papers
git clone --depth 1 https://github.com/Octoday-Hub/Embodied-AI.git /tmp/Embodied-AI
cd /tmp/Embodied-AI
git fetch origin main
git worktree add /tmp/ea-papers -b update/papers-<YYYYMMDD> origin/main

# 写 PR 描述（批次日期、10 篇论文表、改动文件、验收清单、飞书来源）
$EDITOR /tmp/pr_body.md

cd /tmp/feishu-paper-sync
export GITHUB_TOKEN='<Octoday-member0 PAT>'
python3 feishu_to_git_pr.py \
  --input data/papers_<YYYYMMDD>.json \
  --repo /tmp/ea-papers \
  --branch update/papers-<YYYYMMDD> \
  --title "docs: 新增 10 篇 <YYYY-MM> 具身智能论文（飞书论文库同步）" \
  --body-file /tmp/pr_body.md
```

脚本会：把中英六字段表格插到对应分类最前面 → `git diff --check` → 以 `Octoday-member0 <dev_intern@dexunit.com>` 提交 → push 到 `Octoday-member0/Embodied-AI` → 对 `Octoday-Hub/Embodied-AI:main` 开 PR。

加 `--dry-run` 只渲染校验，不提交。

禁止：直接 push 上游 `main`、在上游建分支、提交 `.env` / token / 临时文件。

---

## 5. 验收清单（脚本路径）

- [ ] 10 篇都是最近 7 天首次提交，不是 revision
- [ ] 与飞书、Git 仓库均无重复
- [ ] 标题、日期、机构、数字能在原文找到
- [ ] 飞书 10 条记录字段无空、封面有图
- [ ] 论文页导语 + 10 行表 + 5 条重点
- [ ] 首页卡片日期与新批次一致（或明确标注「待 owner 授权」）
- [ ] 中英文条目 1:1，顺序、链接一致
- [ ] PR 只改 `topics/03-papers.md` + `topics/03-papers_EN.md`
- [ ] commit 作者是 `Octoday-member0 <dev_intern@dexunit.com>`
- [ ] PR base 是 `Octoday-Hub/Embodied-AI:main`，不是直接 push

---

## 6. 常见错误

| 报错 | 原因 | 处理 |
|---|---|---|
| `91403` | 应用不是论文表可编辑协作者 | 加表协作者 |
| `1770032` | 应用不是文档可编辑协作者 | 加文档 / 首页协作者 |
| `1061004` | 封面上传无权限 | 开 `drive:drive` + 表编辑 |
| `99991672` | 应用缺 scope | 开放平台补权限 |
| `99991663` | token 失效 / secret 错误 | 重新 `token` |
| arXiv HTML `404` | 论文没有 HTML | 用 abs 页 + PDF |
| PR `not mergeable` | 上游 main 已更新 | rebase 到最新 `origin/main` 再 push |