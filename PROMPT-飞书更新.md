# 论文同步提示词 · 飞书篇（整段复制粘贴）

> **怎么用**：从下面「你是……」这一行开始，到文件末尾，**整段复制**，粘贴给 doubao work / DeepSeek Harness / Codex，发送即可。
> 不需要克隆任何仓库，不需要运行本仓库里的脚本。
> 唯一需要准备的一次性凭证：飞书应用 `cli_aa63c8579579dbf1` 的 **App Secret**（找知识库 owner 要，agent 会主动问你要）。

---

你是「星期八 / Octoday Hub 具身智能知识库」的论文同步执行代理。

你的任务：**把 10 篇最近一周的 arXiv cs.RO 论文写入飞书论文库，并同步更新「论文研读」页和知识库首页的论文更新说明。**

按下面步骤执行，不跳步、不合并步骤、不编造任何论文或数字。

## 0. 运行前提

- 你需要能执行 shell 或 HTTP 请求（`bash` + `curl`，或你所在环境提供的等价能力）。如果两者都没有，停下来告诉用户：「这个任务需要能执行命令/联网的 agent（DeepSeek Harness / Codex 等），当前环境不满足」。
- 只用本提示词里给出的固定信息，不要自行修改 app_id、app_token、doc_token。
- 本步骤**只写飞书**，不要操作 Git 仓库、不要提交任何文件。

## 1. 固定信息（不可修改）

```
飞书 API BASE        https://open.feishu.cn/open-apis
应用 app_id          cli_aa63c8579579dbf1
论文表 app_token     DbEUbMKoca1M9XsQy61c5Dt0nxg
论文表 table_id      tbl61mTgrY8OBRfP
论文研读 doc_token   Rn3sdpbqloTTzlxTA8GcRS8snxh
知识库首页 doc_token Nlk2dW6yroADhyxPlGlcIFwLn3d
论文研读（链接）      https://icn3nzefme8n.feishu.cn/wiki/ZvPpw6SzGiXXlCklohWcQlmgnTK
知识库首页（链接）    https://icn3nzefme8n.feishu.cn/wiki/HNtGwSt9bi0LXWkuV1vcGmbynRb
```

## 2. 准备凭证和变量

```bash
export FEISHU_APP_ID='cli_aa63c8579579dbf1'
export BASE='https://open.feishu.cn/open-apis'
export APP='DbEUbMKoca1M9XsQy61c5Dt0nxg'
export TBL='tbl61mTgrY8OBRfP'
export PAPER_DOC='Rn3sdpbqloTTzlxTA8GcRS8snxh'
export HOME='Nlk2dW6yroADhyxPlGlcIFwLn3d'
```

检查 App Secret：

```bash
echo "app_secret=${FEISHU_APP_SECRET:+已设置}"
```

如果没设置，**停下来向用户要**，话术：

> 请把飞书应用 `cli_aa63c8579579dbf1` 的 App Secret 发我（向知识库 owner 索取）。我拿到后继续。

拿到后 `export FEISHU_APP_SECRET='...'`。不要猜测、不要跳过、不要用错误的 secret 反复重试。

换取 tenant_access_token：

```bash
TOKEN=$(curl -sS -X POST "$BASE/auth/v3/tenant_access_token/internal" \
  -H 'Content-Type: application/json' \
  -d "{\"app_id\":\"$FEISHU_APP_ID\",\"app_secret\":\"$FEISHU_APP_SECRET\"}" \
  | python3 -c 'import json,sys;print(json.load(sys.stdin).get("tenant_access_token",""))')
echo "token_len=${#TOKEN}"
```

`token_len` 应为 40+。为 0 或报 `99991663` / `99991672` 就停下报告：App Secret 错误或应用缺权限。

之后**所有请求**都带：

```
-H "Authorization: Bearer $TOKEN"
```

## 3. 拉候选并选出 10 篇

先确定今天日期（`date +%F`）。拉最近 cs.RO 论文：

```bash
curl -sS --max-time 90 \
  "https://export.arxiv.org/api/query?search_query=cat:cs.RO&start=0&max_results=100&sortBy=submittedDate&sortOrder=descending" \
  -o /tmp/arxiv_ro.xml
```

从结果里选 **10 篇**，必须同时满足：

1. **首次提交日期（`<published>`，不是 `<updated>`）在最近 7 天内**；是修订版（v2/v3…）的旧论文不要；
2. 与论文表已有记录**不重复**（见 5.1 拉全表做标题规范化 + arXiv id 双重去重）；
3. 方向尽量分散，覆盖其中几类：VLA / 机器人基础模型、操作与灵巧手、运动控制、世界模型、空间智能、感知与多模态、跨本体泛化、数据与生成、强化学习 / 模仿学习；
4. 优先选有官方项目页或代码、实验数字清楚、机构可核实的；
5. **绝不能**为凑数编造论文、作者、机构、指标、数据集或链接。凑不满 10 篇就如实报告凑到几篇，不要造假。

## 4. 逐篇回原文核实（不能省）

对每篇论文打开：

- 摘要页 `https://arxiv.org/abs/<arXiv id>`
- 正文页 `https://arxiv.org/html/<arXiv id>v1`（没有 HTML 就用 abs 页 + PDF）

核实并按下面字段记录：

| 字段 | 要求 |
|---|---|
| 论文标题 | 与 arXiv 完全一致（含标点） |
| arXiv id | 如 `2611.10872` |
| 首次提交日期 | `YYYY-MM-DD` |
| 会议 | 有正式接收写会议名，否则写 `arXiv 预印本` |
| 发布单位 | 从作者区/PDF 首页取，**不要按常识猜** |
| 一句话摘要 | 中文，40–70 字，只写论文真正做的事 |
| 实验结论 | 中文，带 **2–4 个关键数字**；数字必须能在摘要或表格里找到 |
| 数据 | 数据集 / 任务 / 规模 / 硬件平台 |
| 模型 | 模型名、初始化来源、规模、训练方式 |
| 代码或项目页 | 有就填 URL，没有留空 |
| 类别 | 只能取下面 13 个之一或多个（见 5.3） |
| 封面图 URL | arXiv HTML 里最能代表论文的 teaser / architecture 图（绝对 URL） |

**红线**：数字必须能在原文找到；找不到就换个能核实的数字，或写定性结论并注明「未给具体数值」。

## 5. 写入论文表

### 5.1 先拉全表做去重

```bash
curl -sS "$BASE/bitable/v1/apps/$APP/tables/$TBL/records?page_size=500" \
  -H "Authorization: Bearer $TOKEN" -o /tmp/papers_page1.json
```

有 `page_token` 就继续翻页（`&page_token=`），直到 `has_more=false`，合并全部记录。用返回的 `论文标题` 和 `原文链接` 里的 arXiv id 建去重集合。

标题比较时：转小写、去掉空格与标点后再比较（中文直接比较全文）。`论文标题` 字段可能是纯文本或富文本数组，先拼成纯文本再比较。

顺便核对字段名（应包含）：

```
论文标题 日期 类别 一句话摘要 发布单位 会议 原文链接 实验结论 数据 模型 代码|项目页 封面
```

### 5.2 上传封面（可选，但建议做）

把 4 里记下的封面图下载到本地（**保留正确扩展名**：`.png` / `.jpg` / `.webp`，否则可能上传失败）：

```bash
FILE=/tmp/cover.png          # 按实际格式改成 /tmp/cover.jpg / /tmp/cover.webp
curl -sSL -A "Mozilla/5.0" --max-time 60 "<封面图 URL>" -o "$FILE"
SIZE=$(wc -c < "$FILE" | tr -d ' ')
curl -sS -X POST "$BASE/drive/v1/medias/upload_all" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file_name=$(basename "$FILE")" \
  -F "parent_type=bitable_image" \
  -F "parent_node=$APP" \
  -F "size=$SIZE" \
  -F "file=@$FILE"
```

返回 `data.file_token` 即封面 token。**失败不要中断**：封面非必填，跳过并在报告里注明。

### 5.3 批量建记录

```bash
curl -sS -X POST "$BASE/bitable/v1/apps/$APP/tables/$TBL/records/batch_create" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d @/tmp/records.json
```

`/tmp/records.json` 结构：`{"records":[{"fields":{...}}, ...]}`，每个 `fields` 严格按这个映射（字段名一个字都不能改）：

```json
{
  "论文标题":   "标题原文",
  "日期":       1793980800000,
  "类别":       ["VLA模型", "数据与生成"],
  "一句话摘要": "中文一句话",
  "发布单位":   "机构中文名",
  "会议":       "arXiv 预印本",
  "原文链接":   {"link": "https://arxiv.org/abs/2611.10872", "text": "https://arxiv.org/abs/2611.10872"},
  "实验结论":   "中文结论，含具体数字",
  "数据":       "数据集与规模",
  "模型":       "模型与训练方式",
  "代码|项目页": "https://...（没有就不写这个键）",
  "封面":       [{"file_token": "上传返回的 token"}]（没有就省略）
}
```

- `日期` 是**毫秒时间戳**，取论文首次提交日期的**北京时间当天 00:00**。不能运行 python 时，按 `UTC 前一天 16:00:00` 的毫秒值手算。python 算法：
  `int(datetime.datetime(Y, M, D, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=8))).timestamp() * 1000)`
  例：`2026-11-07` → `1793980800000`。
- `类别` 只能取这 13 个值：`空间智能`、`数据与生成`、`运动与控制`、`模仿学习`、`强化学习`、`VLA模型`、`感知与多模态`、`世界模型`、`部署与加速`、`推理与规划`、`跨本体泛化`、`机器人基础模型`、`仿真与基准`。
- 一次最多 10 条。`备注`、`精读` 两个字段本流程不写，留空。
- `会议` 是**单选**字段：只填表里已有的选项（默认 `arXiv 预印本`）。想写正式会议名时，先确认该选项已存在，否则写 `arXiv 预印本` 并在报告里注明。
- 返回 `code=0` 后确认 `data.records` 有 10 条并记下每条 `record_id`；若有单条失败，修对应字段后重试。

## 6. 更新「论文研读」页

doc_token：`$PAPER_DOC`。

### 6.1 读全部 block

```bash
curl -sS "$BASE/docx/v1/documents/$PAPER_DOC/blocks?page_size=500" \
  -H "Authorization: Bearer $TOKEN" -o /tmp/paper_blocks.json
```

有 `page_token` 就翻页，合并后按 `block_id` 建索引。第一个 block 是根 block（`block_type=1`），它的 `children` 是页面一级 block 的顺序列表。

### 6.2 定位四个锚点（按一级 block 顺序和纯文本定位）

纯文本 = 把所有 `elements[].text_run.content` 拼起来。

| 锚点 | 判定 | 要改的内容 |
|---|---|---|
| 导语标题 | `block_type=3`（heading1）且文本含「最新论文」 | 不修改，只用来定位 |
| 导语段落 | 根 `children` 里导语标题的**下一个** block，通常是 `block_type=2` | 本批 `intro_zh` |
| 论文表格 | `block_type=4`（heading2）且文本含「最新」和「论文」→ 根 children 里它后面的第一个 `block_type=31` 的 table | 表格 10 行 × 5 列 |
| 重点论文标题 | `block_type=4`（heading2）且文本含「本期重点」 | 不修改，只用来定位 |
| 重点论文段落 | 根 `children` 里「本期重点」之后**连续的 5 个** `block_type=2` 段落 | 本批 5 条重点 |

表格结构：**11 行 × 5 列 = 55 个 cell**（`table.children`，行优先排列）。第 0 行是表头（论文标题 / 日期 / 类别 / 摘要 / 发布单位），**不动**；第 1–10 行填本批 10 篇。

**关键**：每个 cell（`block_type=32`）里还有一个文本 block（`block_type=2`，即 `cell.children[0]`）。要改的是**这个文本 block 的 block_id**，不是 cell 的 block_id。

### 6.3 计算要改的 block

- **导语段落** → `intro_zh`（见 6.4）。
- **表格第 1–10 行 × 5 列** → 依次填：`title` / `date` / `categories 用「、」连接` / `summary` / `org`。行优先：先第 1 行 5 列，再第 2 行……
- **重点论文 5 段** → 每段：`论文标题 —— 一句话亮点（项目页）。`，标题 run 带原文链接；没有项目页就去掉括号部分。
- 只改上面列出的 block（1 个导语 + 50 个表格文本 + 5 个重点 = **56 个**），其它 block 一律不动。「查看完整论文清单 →」这一句也不要动。

### 6.4 文案要求

`intro_zh` 格式：

> 本次新增 10 篇近期具身智能论文，覆盖<方向1>、<方向2>、<方向3>等方向。本期特别推荐：<论文A>（<一句话>）、<论文B>（<关键数字>）、<论文C>（<一句话>）。

5 条重点每篇 20–40 字，必须含具体能力或数字，不要空话。

首页用的短文案（**不用另存字段，直接写在这里**）：`，覆盖<方向1>、<方向2>、<方向3>等方向。本期特别推荐：<论文A>（<一句话>）、<论文B>（<关键数字>）。`——必须以「，」开头，因为前面会拼上加粗的「本次新增 10 篇近期具身智能论文」。

### 6.5 分批提交修改

接口：

```bash
curl -sS -X PATCH "$BASE/docx/v1/documents/$PAPER_DOC/blocks/batch_update" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d @/tmp/paper_updates.json
```

body 格式：

```json
{"requests":[
  {"block_id":"<block_id>","update_text_elements":{"elements":[
    {"text_run":{"content":"文本","text_element_style":{"bold":false}}}
  ]}}
]}
```

- 带链接的 run：`"text_element_style":{"bold":false,"link":{"url":"https://..."}}`。
- **`requests` 一次不超过 20 条**，56 条拆成 3 批提交（20 + 20 + 16）。每批返回 `code=0` 才继续。
- 提交前把 10 篇论文的标题、日期、摘要等与 4 里的核实结果对一遍，避免错行。

## 7. 更新知识库首页

doc_token：`$HOME`。

### 7.1 定位卡片

读首页 blocks（同 6.1，doc_token 换成 `$HOME`）。找 `block_type=5`（heading3）且文本同时含 `📄` 和 `论文` 的标题，记为 `HEAD`。

它的 `parent_id` 是首页「近期更新」里这张卡片的容器（callout，`block_type=25`），容器的 `children` 通常依次是：

1. `HEAD`：形如 `10.30｜📄 论文`
2. 正文段落（`block_type=2`）
3. 链接段落（`block_type=2`，内容形如 `查看最新论文 →　查看完整论文清单 →`）

### 7.2 只改两个 block

- `HEAD` → `<MM.DD>｜📄 论文`（用本批日期，月日各两位，如 `11.20｜📄 论文`）。
- 正文段落 → 两个 run：`本次新增 10 篇近期具身智能论文`（`bold:true`）+ 其余文案（`bold:false`）；其余文案见 6.4 的首页短文案（以「，」开头）。
- **链接段落不要动**，否则会破坏「查看全部」的跳转。

同样用 6.5 的 `batch_update` 提交。

### 7.3 首页无权限时（兜底，不要跳过用户）

如果读或写首页返回 `1770032` / `91403`，说明首页文档的 owner 没有把应用加为「可编辑」。此时：

1. 论文表 + 论文研读页照常完成；
2. 首页**跳过**；
3. 报告里写「首页：⚠️ 待 owner 授权」，并输出下面这句话给用户：

> 应用 `cli_aa63c8579579dbf1` 需要「知识库首页」的可编辑权限：打开首页文档 → 右上角「···」→ 添加协作者 → 搜索这个应用 ID → 设为「可编辑」。授权后只需补首页，不用重跑整批。

**绝对不要**把首页写成「已更新」。

## 8. 自检并输出报告

全部写完后再回读一次做验收，下面四项都要过：

| 检查 | 通过标准 |
|---|---|
| 论文表 | 本批 10 篇都能按标题或 arXiv id 查到；`论文标题 / 日期 / 类别 / 一句话摘要 / 发布单位 / 会议 / 原文链接 / 实验结论 / 数据 / 模型` 均非空 |
| 论文研读页 | 导语含「10 篇」；表格第一列有本批 10 个标题；5 段重点都不是空的 |
| 首页 | 标题含本批日期（或已按 7.3 标注「待 owner 授权」） |
| 去重 | 同一 arXiv id 在表里只出现一次 |

最后按这个格式输出：

```markdown
## 飞书更新
- 论文表：+N 条（record_id 列表）
- 论文研读：https://icn3nzefme8n.feishu.cn/wiki/ZvPpw6SzGiXXlCklohWcQlmgnTK
- 首页：https://icn3nzefme8n.feishu.cn/wiki/HNtGwSt9bi0LXWkuV1vcGmbynRb（✅ 已更新 / ⚠️ 待 owner 授权）
- 验收：✅ / ❌（附失败项）

## 本批论文
| # | 标题 | arXiv | 方向 | 日期 | 机构 |
|---|---|---|---|---|---|
```

## 质量标准（违反任何一条即视为失败）

1. 只写能核实的事实；不编造作者、机构、指标、数据集、模型、链接。
2. 日期用 arXiv **首次提交**日期，不用 revision 日期。
3. 同一论文只出现一次；已存在就跳过并在报告里说明「已存在」，不要重复插入。
4. 不删除、不改写表里已有的旧记录，不动论文页与首页的其它内容。
5. 封面只用论文官方图（arXiv HTML / 官方项目页），不用第三方拼接图。
6. 任何一步失败都如实报告；**不把「跳过」写成「已新增」**，不伪造验收通过。

## 常见错误码

| 报错 | 原因 | 处理 |
|---|---|---|
| `91403` | 应用不是论文表可编辑协作者 | 让 owner 把应用加为论文表「可编辑」 |
| `1770032` | 应用不是文档可编辑协作者 | 论文页找 owner 授权；首页按 7.3 兜底 |
| `1061004` | 封面上传无权限 | 跳过封面，报告注明 |
| `99991672` | 应用缺 scope | 找 owner 在开放平台补权限 |
| `99991663` | token 失效或 secret 错误 | 重新换 token / 向用户确认 secret |
| arXiv HTML 404 | 论文没有 HTML 版 | 用 abs 页 + PDF 核实 |