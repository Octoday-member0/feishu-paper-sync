# 论文入库提示词 · Git 篇（整段复制粘贴）

> **怎么用**：飞书论文库更新完成后，从下面「你是……」这一行开始，到文件末尾，**整段复制**，粘贴给 Codex / DeepSeek Harness，发送即可。
> 默认行为：从飞书论文多维表格读取**最近一批**论文，按 `Octoday-Hub/Embodied-AI` 仓库既有格式生成中英双份条目，插入 `topics/03-papers.md` 与 `topics/03-papers_EN.md`，整理成**一次 commit**。
> 默认**只提交到本地分支，不推送**；只有你明确说「推送」或「开 PR」时才 push / 开 PR。
> 需要飞书应用 `cli_aa63c8579579dbf1` 的 App Secret（和飞书篇用的是同一个；agent 会主动问你要）。

---

你是 `Octoday-Hub/Embodied-AI` 仓库的论文入库执行代理。任务：**从飞书论文多维表格读取最近一批论文，按仓库既有格式生成中英双份条目，插入 `topics/03-papers.md` 与 `topics/03-papers_EN.md`，整理成一次 commit。**

不跳步、不编造，失败如实报告。

## 0. 运行前提

- 你需要能执行 shell（`git`、`curl`、`python3`）并能读 arXiv 网页；没有就停下说明环境不满足。
- 只用本提示词给出的固定信息，不要改 app_id / app_token / table_id。
- **默认不 push、不建 PR**；见第 7 步。

## 1. 固定信息（不可修改）

```
飞书 API BASE        https://open.feishu.cn/open-apis
应用 app_id          cli_aa63c8579579dbf1
论文表 app_token     DbEUbMKoca1M9XsQy61c5Dt0nxg
论文表 table_id      tbl61mTgrY8OBRfP
Git 上游仓库          https://github.com/Octoday-Hub/Embodied-AI
Git 个人 Fork         Octoday-member0/Embodied-AI
目标文件              topics/03-papers.md、topics/03-papers_EN.md
提交身份              Octoday-member0 <dev_intern@dexunit.com>
```

## 2. 准备凭证和变量

```bash
export FEISHU_APP_ID='cli_aa63c8579579dbf1'
export BASE='https://open.feishu.cn/open-apis'
export APP='DbEUbMKoca1M9XsQy61c5Dt0nxg'
export TBL='tbl61mTgrY8OBRfP'
echo "app_secret=${FEISHU_APP_SECRET:+已设置}"
```

没设置就**停下来向用户要**：

> 请把飞书应用 `cli_aa63c8579579dbf1` 的 App Secret 发我（向知识库 owner 索取）。拿到后我继续。

换 token：

```bash
TOKEN=$(curl -sS -X POST "$BASE/auth/v3/tenant_access_token/internal" \
  -H 'Content-Type: application/json' \
  -d "{\"app_id\":\"$FEISHU_APP_ID\",\"app_secret\":\"$FEISHU_APP_SECRET\"}" \
  | python3 -c 'import json,sys;print(json.load(sys.stdin).get("tenant_access_token",""))')
```

`token_len` 应为 40+，否则报告 App Secret / 权限问题并停止。

## 3. 拉飞书论文表，确定「最近一批」

### 3.1 读全表

```bash
curl -sS "$BASE/bitable/v1/apps/$APP/tables/$TBL/records?page_size=500" \
  -H "Authorization: Bearer $TOKEN" -o /tmp/papers_page1.json
```

有 `page_token` 就继续翻页（`&page_token=`），直到 `has_more=false`，合并全部记录。

字段解析注意：

- `日期`：毫秒时间戳，按**北京时间**（UTC+8）取日期；
- `原文链接`：形如 `{"link": "...", "text": "..."}`，取 `link`；
- `类别`：数组，如 `["VLA模型","数据与生成"]`；
- `封面`：附件数组，本步骤用不到；
- `备注`、`精读`：本步骤用不到。

### 3.2 选定本批范围

按优先级：

1. 用户明确给了 arXiv id 列表或批次日期 → 用用户的；
2. 否则取表里**最新批次**：先取 `日期` 最大的那一天，取该天全部记录（通常 10 条）；不足 10 条就往前一天补，直到凑满 10 条或没有更多；
3. 再按 `日期` 倒序排，最多取 10 条。

选定后**先把清单打印出来核对**（标题 / arXiv id / 日期 / 机构），再进入下一步。

同时做仓库去重（见 5.1）：已存在于仓库的论文跳过，记录「已存在」。

需要的飞书字段：

```
论文标题  日期  类别  一句话摘要  发布单位  会议  原文链接  实验结论  数据  模型  代码|项目页
```

> 注意：飞书表**没有**英文内容，也没有「特点」字段，这两部分要读 arXiv 原文补，见第 4 步。

## 4. 判定仓库分类

每篇论文归入且仅归入一个分类（按论文主题判断）：

| repo_category | 仓库中对应标题 |
|---|---|
| `embodied-foundation-models` | `## Embodied Foundation Models` |
| `manipulation` | `## Manipulation & Teleoperation` |
| `locomotion` | `## Locomotion` |
| `navigation` | `## Navigation & Spatial Intelligence` |
| `simulators` | `## Simulators & Sim2Real` |
| `datasets` | `## Datasets` |
| `benchmarks` | `## Benchmarks & Evaluation` |
| `survey` | `## Survey` |

判定倾向：VLA / 通用策略 / 基础模型 → 第一个；抓取、灵巧手、遥操作 → 第二个；腿足步态 → 第三个；SLAM / 建图 / 空间智能 → 第四个；仿真器 / Sim2Real → 第五个；数据集 → 第六个；基准与评测 → 第七个；综述 → 第八个。

## 5. 补齐缺失内容（必须回原文）

对每篇论文打开 `https://arxiv.org/abs/<arXiv id>`（有 HTML 就开 `https://arxiv.org/html/<arXiv id>v1`），补齐：

- **一句话英文**（`one_line_en`）：对应中文「一句话摘要」的英文改写；
- **机构英文名**（`org_en`）；
- **特点（中文 2–4 条）**：论文的关键设计点，每条 20–40 字；关键数字可用 `<strong>数字</strong>`；
- **实验结论（中文 2–4 条）**：把飞书「实验结论」拆条，数字加粗；
- **英文 highlights（2–4 条）**、**英文 results（2–4 条）**、**英文 data / models 一句话**（`data_model_en`）；
- **发布时间**：中文 `YYYY 年 M 月`，英文 `Month YYYY`（如 `November 2026`）；
- **中文 data / models 一句话**（`data_model_zh`）：由飞书「数据」「模型」合并。

**红线**：不编造数字、机构、指标。英文是翻译与改写，不是另起事实。

## 6. 写入仓库

### 6.1 准备干净的 worktree

```bash
rm -rf /tmp/Embodied-AI /tmp/ea-papers
git clone --depth 1 https://github.com/Octoday-Hub/Embodied-AI.git /tmp/Embodied-AI
cd /tmp/Embodied-AI
git fetch origin main
git worktree add /tmp/ea-papers -b update/papers-<YYYYMMDD> origin/main
cd /tmp/ea-papers
```

`<YYYYMMDD>` 用本批日期（如 `20261120`）。

### 6.2 先查重

```bash
grep -Fn "<arXiv id>" topics/03-papers.md topics/03-papers_EN.md
```

任一文件里已出现该 id，就跳过这篇并记录「已存在」。

### 6.3 插入位置

每个分类的结构是：

```
<a id="embodied-foundation-models" name="embodied-foundation-models"></a>

## Embodied Foundation Models

### [已有的详细条目]
...
```

**新条目插在 `## <分类标题>\n\n` 之后**，即成为该分类第一条。一次插入多篇时按 arXiv 日期倒序排。

**不要**新增或改动「速览列表」里 `- **[arXiv ...](...)**` 那种单行条目，也不要动 Table of Contents。只改 `topics/03-papers.md` 和 `topics/03-papers_EN.md` 两个文件。

### 6.4 中文条目模板（严格照抄结构）

```html
### [<标题>](<原文链接>)

<table style="width:100%;table-layout:fixed" width="100%">
<tbody>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">一句话摘要</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640"><一句话摘要></td></tr>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">发布时间</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640"><YYYY 年 M 月></td></tr>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">机构</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640"><发布单位></td></tr>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">特点</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640"><ul><li>…</li><li>…</li></ul></td></tr>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">实验结论</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640"><ul><li>…</li><li>…</li></ul></td></tr>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">数据 / 模型</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640"><数据 + 模型 合并一句话></td></tr>
</tbody>
</table>
```

### 6.5 英文条目模板（严格照抄结构）

```html
### [<Title>](<原文链接>)

<table style="width:100%;table-layout:fixed" width="100%">
<tbody>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">One-line summary</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640"><one_line_en></td></tr>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">Release date</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640"><Month YYYY></td></tr>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">Organization</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640"><org_en></td></tr>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">Highlights</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640"><ul><li>…</li><li>…</li></ul></td></tr>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">Results</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640"><ul><li>…</li><li>…</li></ul></td></tr>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">Data / Models</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640"><data_model_en></td></tr>
</tbody>
</table>
```

> 正文里的 HTML 特殊字符要转义（`&` → `&amp;`、`<` → `&lt;`、`>` → `&gt;`）；`<strong>`、`<ul>`、`<li>`、`<a>` 这些结构标签保留。

## 7. 校验、提交、按需推送

### 7.1 校验

```bash
cd /tmp/ea-papers
git diff --check
git diff --stat
```

逐项确认：

1. 每篇论文的 arXiv id 在 `03-papers.md` 和 `03-papers_EN.md` 里**各出现且仅出现 1 次**；
2. 中英条目数量 1:1，标题与链接一一对应；
3. `git diff --stat` **只**出现 `topics/03-papers.md` 和 `topics/03-papers_EN.md`；
4. 没有删除或改写其它既有条目；
5. 表格结构完整：每篇 1 个 `<table>`，6 个 `<tr>`，`<tbody>`/`</table>` 闭合。

任何一项不过，修好再继续。

### 7.2 提交（只产生 1 个 commit）

```bash
cd /tmp/ea-papers
git add topics/03-papers.md topics/03-papers_EN.md
git -c user.name='Octoday-member0' -c user.email='dev_intern@dexunit.com' \
  commit -m "docs: 新增 N 篇 <YYYY-MM> 具身智能论文（飞书论文库同步）"
```

要求：**只产生 1 个 commit**；作者是 `Octoday-member0 <dev_intern@dexunit.com>`；commit message 写清 N 篇、月份、来源是飞书论文库。

### 7.3 只有用户明确要求时才推送 / 开 PR

```bash
# 需要 Octoday-member0 的 PAT 或已登录 gh
git push https://<TOKEN>@github.com/Octoday-member0/Embodied-AI.git update/papers-<YYYYMMDD>
GITHUB_TOKEN=<TOKEN> gh pr create --repo Octoday-Hub/Embodied-AI \
  --base main --head Octoday-member0:update/papers-<YYYYMMDD> \
  --title "docs: 新增 N 篇 <YYYY-MM> 具身智能论文（飞书论文库同步）" \
  --body-file /tmp/pr_body.md
```

PR 描述至少包含：本批论文表（标题 / arXiv / 分类 / 日期）、改动文件、校验结果、飞书来源链接。

**禁止**：直接 push 上游 `main`、在上游建分支、提交 `.env` / token / 临时文件。

## 8. 输出报告

```markdown
## Git 入库
- 分支：update/papers-<YYYYMMDD>
- commit：<sha>（作者 Octoday-member0 <dev_intern@dexunit.com>）
- 改动：topics/03-papers.md +N 条 / topics/03-papers_EN.md +N 条
- 分类分布：<分类>×n …
- 校验：✅ / ❌（附失败项）
- 推送：未推送（默认）/ 已推送 fork / PR <url>

## 本批论文
| # | 标题 | arXiv | 分类 | 日期 |
|---|---|---|---|---|

## 跳过
- <arXiv id> 已存在于仓库
```

## 质量标准

1. 只写能核实的事实，不编造数字与机构。
2. 中文条目与英文条目是同一篇论文，信息必须一致。
3. 一次只提交这一批，不夹带其它改动。
4. 失败如实报告，不把「跳过」写成「已新增」。
5. 默认只 commit，不擅自 push 或开 PR。