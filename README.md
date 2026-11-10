# feishu-paper-sync

One-paste automation for the **星期八 / Octoday Hub 具身智能知识库**:

1. pick 10 recent arXiv `cs.RO` papers;
2. insert them into the Feishu **论文汇总** bitable (with covers);
3. refresh the **论文研读** page (intro + 10-row table + highlights);
4. refresh the **知识库首页** “近期更新 → 📄 论文” card;
5. optionally turn the same batch into one commit on
   `Octoday-Hub/Embodied-AI` via an `Octoday-member0` fork PR.

The tool is a thin, deterministic I/O layer.  The agent (DeepSeek Harness /
Codex) is responsible for reading papers and writing accurate metadata; the
script handles Feishu/Git API calls and verification.

---

## 1. One-time setup

### 1.1 Feishu app

Create an internal app at <https://open.feishu.cn/app>, then enable:

| Scope | Why |
|---|---|
| `wiki:wiki:readonly` | read the wiki tree |
| `docx:document` | read/write the two docs |
| `bitable:app` | read/write 论文汇总 records |
| `drive:drive` | upload cover images |

### 1.2 Grant the app edit access (required)

The app must be an **editor** collaborator, otherwise record creation returns
`91403 Forbidden` and doc updates return `1770032 forBidden`.

1. Open the knowledge base:
   <https://icn3nzefme8n.feishu.cn/wiki/HNtGwSt9bi0LXWkuV1vcGmbynRb>
2. Top-right `···` → **添加协作者** → search the app name → **可编辑**.
3. Also add the app to the **论文汇总** bitable
   (<https://icn3nzefme8n.feishu.cn/wiki/HzXtwhSWYir13zkExiEcFYXNnKc>)
   with **可编辑** rights.
4. If your tenant supports adding apps to a wiki space, adding it once at the
   space level covers all child nodes.

> **首页特别注意**：首页文档可能由另一位管理员持有，且分享权限只给
> `full_access` 成员。如果 `apply` 在首页步骤报 `1770032`，说明当前应用
> 无法编辑首页；请让首页 owner 把应用加为「可编辑」。临时可以先用
> `apply --skip-home` 完成论文表和论文页，权限恢复后再运行
> `home --input ...` 只补首页。

### 1.3 Credentials

```bash
export FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
export FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Or create `.env` next to the script (never commit it):

```dotenv
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 1.4 Git identity for the PR phase

```bash
export GITHUB_TOKEN=ghp_...      # Octoday-member0 PAT, admin on the fork
```

The token only needs `repo` scope.  Commit identity is forced to
`Octoday-member0 <dev_intern@dexunit.com>` by `feishu_to_git_pr.py`.

---

## 2. Quick start

```bash
git clone https://github.com/Octoday-member0/feishu-paper-sync.git
cd feishu-paper-sync

python3 feishu_paper_sync.py token
mkdir -p data
cp examples/papers_20261110.json data/
python3 feishu_paper_sync.py preview --input data/papers_20261110.json
python3 feishu_paper_sync.py apply   --input data/papers_20261110.json
python3 feishu_paper_sync.py verify  --input data/papers_20261110.json
```

`apply` is idempotent: records already present (same normalized title or same
arXiv id) are skipped, while the docs/homepage are refreshed.

### Subcommands

| Command | Purpose |
|---|---|
| `token` | verify app credentials |
| `list` | show the newest 20 records |
| `preview --input` | validate a batch + show dedupe result |
| `apply --input` | upload covers, create records, update 论文研读 + 首页, then verify |
| `apply --input --skip-home` | same, but tolerate a missing homepage edit permission |
| `home --input` | only refresh the homepage paper card (for a later retry) |
| `verify --input` | check records / paper page / homepage |
| `verify --input --skip-home` | skip the homepage check |
| `export --input --out` | emit Markdown fragments for the Git PR |

---

## 3. Batch format

`data/papers_20261110.json` is the reference example.  Each paper needs:

```json
{
  "title": "...",
  "arxiv_id": "2611.10872",
  "url": "https://arxiv.org/abs/2611.10872",
  "date": "2026-11-07",
  "venue": "NeurIPS 2026",
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

`repo_category` is one of:
`embodied-foundation-models`, `manipulation`, `locomotion`, `navigation`,
`simulators`, `datasets`, `benchmarks`, `survey`.

The top-level batch also carries `batch_date`, `homepage_title`, `intro_zh`,
`intro_short_zh`, and `highlights` (5 items with `arxiv_id`, `text`,
`link_text`, `link_url`).

---

## 4. Git phase

```bash
# clean worktree based on the latest upstream main
cd /path/to/Embodied-AI
git fetch origin main
git worktree add ../ea-papers -b update/papers-YYYYMMDD origin/main

cd /path/to/feishu-paper-sync
python3 feishu_to_git_pr.py \
  --input data/papers_20261110.json \
  --repo ../ea-papers \
  --branch update/papers-20261110 \
  --title "docs: 新增 10 篇 2026-11 具身智能论文（飞书论文库同步）" \
  --body-file /tmp/pr_body.md
```

It inserts the bilingual six-field HTML tables at the top of each category,
runs `git diff --check`, commits as `Octoday-member0`, pushes to
`Octoday-member0/Embodied-AI`, and opens a PR against
`Octoday-Hub/Embodied-AI:main`.

Use `--dry-run` to render and check without committing.

---

## 5. What can go wrong

| Symptom | Fix |
|---|---|
| `91403 Forbidden` on records | app is not an editor of the bitable |
| `1770032 forBidden` on docs | app is not an editor of the wiki/doc |
| `403` on cover upload | add `drive:drive` scope + bitable edit |
| `99991672` scope error | enable the missing scope in the app console |
| `1063001` permission member | add the app through the Feishu UI, not the API |

The script never writes credentials to disk.  Keep `.env` and `GITHUB_TOKEN`
out of Git.