#!/usr/bin/env python3
"""
Feishu paper sync for the Octoday embodied-AI knowledge base.

Subcommands
-----------
  token                      verify app credentials and print tenant token status
  list                       list the newest records in 论文汇总
  preview --input batch.json validate a batch and show what would be written
  apply   --input batch.json insert records, upload covers, update 论文研读 + 首页
  verify  --input batch.json check records, paper doc, and homepage
  export  --input batch.json --out DIR
                             emit Markdown fragments for the Git PR workflow

Credentials are read from FEISHU_APP_ID / FEISHU_APP_SECRET (or a local
.env file next to this script).  No credentials are written to disk by
this tool.
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

try:
    from PIL import Image

    HAS_PIL = True
except Exception:  # pragma: no cover - optional
    HAS_PIL = False

BASE = "https://open.feishu.cn/open-apis"
HERE = Path(__file__).resolve().parent

# --- Stable IDs of the Octoday knowledge base -------------------------------
SPACE_ID = "7673448817735257310"
PAPER_APP_TOKEN = "DbEUbMKoca1M9XsQy61c5Dt0nxg"
PAPER_TABLE_ID = "tbl61mTgrY8OBRfP"
PAPER_DOC_TOKEN = "Rn3sdpbqloTTzlxTA8GcRS8snxh"   # 论文研读
HOME_DOC_TOKEN = "Nlk2dW6yroADhyxPlGlcIFwLn3d"    # 知识库首页
WIKI_ROOT = "https://icn3nzefme8n.feishu.cn/wiki/HNtGwSt9bi0LXWkuV1vcGmbynRb"

PAPER_FIELDS = [
    "论文标题", "日期", "类别", "一句话摘要", "发布单位", "会议",
    "原文链接", "实验结论", "数据", "模型", "代码|项目页", "封面",
]

CATEGORIES = [
    "空间智能", "数据与生成", "运动与控制", "模仿学习", "强化学习", "VLA模型",
    "感知与多模态", "世界模型", "部署与加速", "推理与规划", "跨本体泛化",
    "机器人基础模型", "仿真与基准",
]


# ---------------------------------------------------------------------------
# tiny HTTP client
# ---------------------------------------------------------------------------
class FeishuError(RuntimeError):
    pass


class Feishu:
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self._token: str | None = None
        self._token_exp = 0.0

    # -- auth ---------------------------------------------------------------
    def token(self) -> str:
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        data = json.dumps({"app_id": self.app_id, "app_secret": self.app_secret}).encode()
        req = urllib.request.Request(
            BASE + "/auth/v3/tenant_access_token/internal",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.load(resp)
        if payload.get("code") != 0:
            raise FeishuError(f"auth failed: {payload}")
        self._token = payload["tenant_access_token"]
        self._token_exp = time.time() + int(payload.get("expire", 7200))
        return self._token

    # -- generic ------------------------------------------------------------
    def request(self, method: str, path: str, *, params: dict | None = None,
                data: dict | None = None, timeout: int = 60) -> dict:
        url = BASE + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        body = None
        headers = {"Authorization": "Bearer " + self.token()}
        if data is not None:
            body = json.dumps(data, ensure_ascii=False).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.load(resp)
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                payload = json.loads(raw)
            except Exception:
                raise FeishuError(f"{method} {path} -> HTTP {exc.code}: {raw[:400]!r}")
        if payload.get("code") not in (0, None):
            raise FeishuError(f"{method} {path} -> {payload.get('code')}: {payload.get('msg')} ({payload.get('error')})")
        return payload

    # -- upload -------------------------------------------------------------
    def upload_image(self, data: bytes, file_name: str, parent_node: str) -> str:
        boundary = "----FeishuBoundary" + uuid.uuid4().hex
        fields = {
            "file_name": file_name,
            "parent_type": "bitable_image",
            "parent_node": parent_node,
            "size": str(len(data)),
        }
        chunks: list[bytes] = []
        for key, value in fields.items():
            chunks.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode()
            )
        ctype = mimetypes.guess_type(file_name)[0] or "image/png"
        chunks.append(
            (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
                f"filename=\"{file_name}\"\r\nContent-Type: {ctype}\r\n\r\n"
            ).encode()
            + data
            + b"\r\n"
        )
        chunks.append(f"--{boundary}--\r\n".encode())
        req = urllib.request.Request(
            BASE + "/drive/v1/medias/upload_all",
            data=b"".join(chunks),
            headers={
                "Authorization": "Bearer " + self.token(),
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.load(resp)
        if payload.get("code") != 0:
            raise FeishuError(f"upload failed: {payload}")
        return payload["data"]["file_token"]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def env_credentials() -> tuple[str, str]:
    app_id = os.getenv("FEISHU_APP_ID", "").strip()
    app_secret = os.getenv("FEISHU_APP_SECRET", "").strip()
    if (not app_id or not app_secret) and (HERE / ".env").exists():
        for line in (HERE / ".env").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip().strip("'\"")
            if key == "FEISHU_APP_ID" and not app_id:
                app_id = value
            if key == "FEISHU_APP_SECRET" and not app_secret:
                app_secret = value
    if not app_id or not app_secret:
        raise SystemExit(
            "缺少飞书应用凭据。请设置 FEISHU_APP_ID / FEISHU_APP_SECRET，"
            f"或在本目录创建 .env（不要提交到 Git）：{HERE / '.env'}"
        )
    return app_id, app_secret


def date_ms(value: str) -> int:
    """Feishu date field uses ms at local midnight (UTC+8)."""
    d = dt.date.fromisoformat(value)
    tz = dt.timezone(dt.timedelta(hours=8))
    return int(dt.datetime(d.year, d.month, d.day, tzinfo=tz).timestamp() * 1000)


def normalize_title(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[\s\-_—–:：,，.。()（）\[\]【】/]+", "", value)
    return value


def record_arxiv_id(record: dict) -> str:
    link = record.get("fields", {}).get("原文链接")
    url = link.get("link", "") if isinstance(link, dict) else (link or "")
    match = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5})", url)
    return match.group(1) if match else ""


def get_all_records(fs: Feishu) -> list[dict]:
    items: list[dict] = []
    page_token = None
    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        payload = fs.request(
            "GET",
            f"/bitable/v1/apps/{PAPER_APP_TOKEN}/tables/{PAPER_TABLE_ID}/records",
            params=params,
        )
        data = payload["data"]
        items.extend(data.get("items", []))
        if not data.get("has_more"):
            break
        page_token = data.get("page_token")
    return items


def get_doc_blocks(fs: Feishu, doc_token: str) -> tuple[list[dict], dict[str, dict]]:
    payload = fs.request(
        "GET",
        f"/docx/v1/documents/{doc_token}/blocks",
        params={"page_size": 500, "document_revision_id": -1},
    )
    items = payload["data"]["items"]
    return items, {item["block_id"]: item for item in items}


def block_text(block: dict) -> str:
    for key in ("text", "heading1", "heading2", "heading3", "heading4",
                "heading5", "bullet", "ordered", "quote", "code"):
        if key in block:
            return "".join(
                element.get("text_run", {}).get("content", "")
                for element in block[key].get("elements", [])
            )
    return ""


def text_elements(*runs: tuple[str, bool, str | None]) -> list[dict]:
    """runs: (content, bold, link_url)."""
    elements = []
    for content, bold, link in runs:
        style: dict[str, Any] = {"bold": bold}
        if link:
            style["link"] = {"url": link}
        elements.append({"text_run": {"content": content, "text_element_style": style}})
    return elements


def update_text(block_id: str, elements: list[dict]) -> dict:
    return {"block_id": block_id, "update_text_elements": {"elements": elements}}


def batch_update(fs: Feishu, doc_token: str, requests: list[dict]) -> None:
    for start in range(0, len(requests), 20):
        chunk = requests[start:start + 20]
        fs.request(
            "PATCH",
            f"/docx/v1/documents/{doc_token}/blocks/batch_update",
            data={"requests": chunk},
        )
        time.sleep(0.15)


# ---------------------------------------------------------------------------
# cover handling
# ---------------------------------------------------------------------------
def load_cover(paper: dict) -> tuple[bytes, str] | None:
    candidates: list[str] = []
    if paper.get("cover_file"):
        candidates.append(paper["cover_file"])
    if paper.get("cover"):
        candidates.append(str(HERE / "covers" / (paper["cover"] + ".png")))
        candidates.append(str(HERE / "covers" / (paper["cover"] + ".img")))
    if paper.get("cover_url"):
        candidates.append(paper["cover_url"])
    for candidate in candidates:
        path = Path(candidate)
        if path.exists() and path.is_file():
            return path.read_bytes(), path.name
        if candidate.startswith("http"):
            try:
                req = urllib.request.Request(candidate, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = resp.read()
                if data[:8] == b"\x89PNG\r\n\x1a\n" or data[:3] == b"\xff\xd8\xff":
                    return data, Path(urllib.parse.urlparse(candidate).path).name or "cover.png"
            except Exception as exc:
                print(f"  ! cover download failed: {candidate} ({exc})", file=sys.stderr)
    return None


def normalize_cover(data: bytes, name: str) -> tuple[bytes, str]:
    if not HAS_PIL:
        return data, name if name.lower().endswith(".png") else "cover.png"
    try:
        image = Image.open(io.BytesIO(data))
    except Exception:
        return data, "cover.png"
    if getattr(image, "n_frames", 1) > 1:
        image.seek(0)
    if image.mode in ("RGBA", "P", "LA"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image.convert("RGBA"), mask=image.convert("RGBA").split()[-1])
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")
    if image.width > 1400:
        height = round(image.height * 1400 / image.width)
        image = image.resize((1400, height), Image.LANCZOS)
    out = io.BytesIO()
    image.save(out, "PNG", optimize=True)
    return out.getvalue(), "cover.png"


# ---------------------------------------------------------------------------
# preview / apply
# ---------------------------------------------------------------------------
def validate_batch(batch: dict) -> list[str]:
    errors: list[str] = []
    papers = batch.get("papers", [])
    if len(papers) != 10:
        errors.append(f"papers 数量应为 10，当前 {len(papers)}")
    for index, paper in enumerate(papers, 1):
        required = ["title", "arxiv_id", "url", "date", "venue", "categories",
                    "summary", "org", "results", "data", "model", "repo_category"]
        for key in required:
            if not str(paper.get(key, "")).strip():
                errors.append(f"#{index} {paper.get('arxiv_id', '?')}: 缺少 {key}")
        if paper.get("categories"):
            unknown = [c for c in paper["categories"] if c not in CATEGORIES]
            if unknown:
                errors.append(f"#{index}: 未知类别 {unknown}")
        try:
            dt.date.fromisoformat(str(paper.get("date", "")))
        except ValueError:
            errors.append(f"#{index}: 日期格式应为 YYYY-MM-DD")
    return errors


def preview(batch: dict, fs: Feishu | None) -> int:
    errors = validate_batch(batch)
    if errors:
        print("❌ 校验未通过：")
        for error in errors:
            print("  -", error)
        return 1
    existing = get_all_records(fs) if fs else []
    titles = {normalize_title(item.get("fields", {}).get("论文标题", "")) for item in existing}
    ids = {record_arxiv_id(item) for item in existing}
    print(f"飞书现有记录：{len(existing)}")
    print(f"{'#':>2}  {'arXiv':<12} {'日期':<12} {'类别':<28} 标题")
    duplicate = 0
    for index, paper in enumerate(batch["papers"], 1):
        dup = normalize_title(paper["title"]) in titles or paper["arxiv_id"] in ids
        duplicate += int(dup)
        print(
            f"{index:>2}  {paper['arxiv_id']:<12} {paper['date']:<12} "
            f"{'、'.join(paper['categories']):<28} {paper['title'][:70]}"
            f"{'  [已存在，将跳过]' if dup else ''}"
        )
    print(f"\n新增 {len(batch['papers']) - duplicate}，跳过 {duplicate}，预计写入 {len(batch['papers']) - duplicate} 条")
    return 0


def build_fields(paper: dict, cover_token: str | None) -> dict:
    fields: dict[str, Any] = {
        "论文标题": paper["title"],
        "日期": date_ms(paper["date"]),
        "类别": paper["categories"],
        "一句话摘要": paper["summary"],
        "发布单位": paper["org"],
        "会议": paper["venue"],
        "原文链接": {"link": paper["url"], "text": paper["url"]},
        "实验结论": paper["results"],
        "数据": paper["data"],
        "模型": paper["model"],
    }
    if paper.get("code_url"):
        fields["代码|项目页"] = paper["code_url"]
    if cover_token:
        fields["封面"] = [{"file_token": cover_token}]
    return fields


def apply_batch(fs: Feishu, batch: dict, skip_home: bool = False) -> dict:
    errors = validate_batch(batch)
    if errors:
        raise SystemExit("批次校验失败：\n" + "\n".join(errors))

    existing = get_all_records(fs)
    titles = {normalize_title(item.get("fields", {}).get("论文标题", "")) for item in existing}
    ids = {record_arxiv_id(item) for item in existing}

    to_create: list[dict] = []
    skipped: list[dict] = []
    for paper in batch["papers"]:
        if normalize_title(paper["title"]) in titles or paper["arxiv_id"] in ids:
            skipped.append(paper)
            continue
        to_create.append(paper)

    print(f"现有 {len(existing)} 条；本次新增 {len(to_create)}，跳过 {len(skipped)}")

    created: list[dict] = []
    for index, paper in enumerate(to_create, 1):
        print(f"[{index}/{len(to_create)}] {paper['arxiv_id']} {paper['title'][:70]}")
        cover_token = None
        cover = load_cover(paper)
        if cover:
            data, name = normalize_cover(*cover)
            try:
                cover_token = fs.upload_image(data, f"{paper['arxiv_id']}.png", PAPER_APP_TOKEN)
                print(f"  cover -> {cover_token} ({len(data) // 1024} KB)")
            except Exception as exc:
                print(f"  ! cover upload failed: {exc}", file=sys.stderr)
        else:
            print("  ! no cover")
        payload = fs.request(
            "POST",
            f"/bitable/v1/apps/{PAPER_APP_TOKEN}/tables/{PAPER_TABLE_ID}/records",
            data={"fields": build_fields(paper, cover_token)},
        )
        record = payload["data"]["record"]
        created.append({
            "arxiv_id": paper["arxiv_id"],
            "title": paper["title"],
            "record_id": record["record_id"],
            "cover_token": cover_token,
        })
        time.sleep(0.25)

    # refresh record ids for papers that already existed
    refreshed = get_all_records(fs)
    title_to_id = {
        normalize_title(item.get("fields", {}).get("论文标题", "")): item["record_id"]
        for item in refreshed
    }
    for paper in batch["papers"]:
        if all(item["arxiv_id"] != paper["arxiv_id"] for item in created):
            rid = title_to_id.get(normalize_title(paper["title"]))
            if rid:
                created.append({
                    "arxiv_id": paper["arxiv_id"],
                    "title": paper["title"],
                    "record_id": rid,
                    "cover_token": None,
                    "existing": True,
                })

    update_paper_doc(fs, batch)
    home_updated = True
    try:
        update_homepage(fs, batch)
    except FeishuError as exc:
        if not skip_home:
            raise
        home_updated = False
        print(f"  ! 首页更新跳过（无编辑权限）：{exc}", file=sys.stderr)

    result = {
        "batch_date": batch["batch_date"],
        "applied_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "created": created,
        "skipped": [{"arxiv_id": p["arxiv_id"], "title": p["title"]} for p in skipped],
        "paper_doc": f"https://icn3nzefme8n.feishu.cn/wiki/{PAPER_DOC_TOKEN}",
        "homepage": WIKI_ROOT,
        "homepage_updated": home_updated,
    }
    out = HERE / "data" / f"applied_{batch['batch_date']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"applied manifest -> {out}")
    return result


# ---------------------------------------------------------------------------
# 论文研读 doc
# ---------------------------------------------------------------------------
def update_paper_doc(fs: Feishu, batch: dict) -> None:
    blocks, by_id = get_doc_blocks(fs, PAPER_DOC_TOKEN)
    root = blocks[0]
    root_children = root.get("children", [])
    by_position = {bid: index for index, bid in enumerate(root_children)}

    heading3 = next(
        (b for b in blocks if b.get("block_type") == 3 and "最新论文" in block_text(b)),
        None,
    )
    if not heading3:
        raise FeishuError("找不到「最新论文」标题")
    heading4 = next(
        (b for b in blocks if b.get("block_type") == 4 and "最新" in block_text(b) and "论文" in block_text(b)),
        None,
    )
    table = None
    if heading4:
        pos = by_position.get(heading4["block_id"])
        if pos is not None and pos + 1 < len(root_children):
            candidate = by_id.get(root_children[pos + 1])
            if candidate and candidate.get("block_type") == 31:
                table = candidate
    if not table:
        table = next((b for b in blocks if b.get("block_type") == 31), None)
    if not table:
        raise FeishuError("找不到论文表格")

    requests: list[dict] = []

    # 1) intro paragraph: first text block after the heading
    pos = by_position.get(heading3["block_id"])
    intro = by_id.get(root_children[pos + 1]) if pos is not None and pos + 1 < len(root_children) else None
    if intro and intro.get("block_type") == 2:
        requests.append(update_text(intro["block_id"], text_elements((batch["intro_zh"], False, None))))

    # 2) table: 10 data rows x 5 columns (row-major cell list)
    cells = table.get("children", [])
    columns = 5
    rows = len(cells) // columns
    if rows < 11:
        raise FeishuError(f"论文表格行数异常：{rows} 行 × {columns} 列")
    header = ["论文标题", "日期", "类别", "摘要", "发布单位"]
    for row_index, paper in enumerate(batch["papers"], start=1):
        values = [
            paper["title"],
            paper["date"],
            "、".join(paper["categories"]),
            paper["summary"],
            paper["org"],
        ]
        for col_index, value in enumerate(values):
            cell = by_id.get(cells[row_index * columns + col_index])
            if not cell:
                continue
            children = cell.get("children", [])
            if not children:
                continue
            target = by_id.get(children[0])
            if target:
                requests.append(update_text(target["block_id"], text_elements((value, False, None))))

    # 3) highlight paragraphs after「本期重点论文」
    highlight_heading = next(
        (b for b in blocks if b.get("block_type") == 4 and "本期重点" in block_text(b)),
        None,
    )
    if highlight_heading:
        hpos = by_position.get(highlight_heading["block_id"])
        candidates = []
        if hpos is not None:
            for bid in root_children[hpos + 1:]:
                block = by_id.get(bid)
                if not block:
                    continue
                if block.get("block_type") != 2:
                    if candidates:
                        break
                    continue
                candidates.append(block)
                if len(candidates) == len(batch["highlights"]):
                    break
        for block, item in zip(candidates, batch["highlights"]):
            paper = next((p for p in batch["papers"] if p["arxiv_id"] == item["arxiv_id"]), None)
            if not paper:
                continue
            runs = [(paper["title"], False, paper["url"]), (" —— " + item["text"], False, None)]
            if item.get("link_url"):
                runs.append(("（", False, None))
                runs.append((item.get("link_text", "项目页"), False, item["link_url"]))
                runs.append(("）。", False, None))
            else:
                runs.append(("。", False, None))
            requests.append(update_text(block["block_id"], text_elements(*runs)))

    batch_update(fs, PAPER_DOC_TOKEN, requests)
    print(f"论文页已更新：{len(requests)} 个文本块")


# ---------------------------------------------------------------------------
# homepage
# ---------------------------------------------------------------------------
def update_homepage(fs: Feishu, batch: dict) -> None:
    blocks, by_id = get_doc_blocks(fs, HOME_DOC_TOKEN)
    heading = next(
        (
            b for b in blocks
            if b.get("block_type") == 5
            and "📄" in block_text(b)
            and "论文" in block_text(b)
        ),
        None,
    )
    if not heading:
        raise FeishuError("首页找不到「📄 论文」更新卡片")
    callout_id = heading["parent_id"]
    callout = by_id[callout_id]
    children = [by_id[bid] for bid in callout.get("children", []) if bid in by_id]
    text_blocks = [b for b in children if b.get("block_type") == 2]
    if len(text_blocks) < 2:
        raise FeishuError("首页论文卡片结构异常：缺少正文或链接段落")

    requests = [update_text(heading["block_id"], text_elements((batch["homepage_title"], False, None)))]

    intro = batch["intro_short_zh"]
    head = "本次新增 10 篇近期具身智能论文"
    rest = intro[len(head):] if intro.startswith(head) else "，" + intro
    requests.append(update_text(
        text_blocks[0]["block_id"],
        text_elements((head, True, None), (rest, False, None)),
    ))
    # keep the existing link paragraph unchanged
    batch_update(fs, HOME_DOC_TOKEN, requests)
    print("首页「近期更新」论文卡片已更新")


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------
def verify_batch(fs: Feishu, batch: dict, skip_home: bool = False) -> int:
    problems: list[str] = []
    records = get_all_records(fs)
    by_title = {normalize_title(item.get("fields", {}).get("论文标题", "")): item for item in records}
    by_arxiv = {record_arxiv_id(item): item for item in records if record_arxiv_id(item)}
    print(f"飞书论文表：{len(records)} 条")
    for paper in batch["papers"]:
        record = by_title.get(normalize_title(paper["title"])) or by_arxiv.get(paper["arxiv_id"])
        if not record:
            problems.append(f"缺少记录：{paper['arxiv_id']} {paper['title']}")
            continue
        fields = record.get("fields", {})
        for key in ("论文标题", "日期", "类别", "一句话摘要", "发布单位", "会议",
                    "原文链接", "实验结论", "数据", "模型"):
            if not fields.get(key) and fields.get(key) != 0:
                problems.append(f"{paper['arxiv_id']} 字段为空：{key}")
        print(f"  ✓ {paper['arxiv_id']} {record['record_id']} 封面={'有' if fields.get('封面') else '无'}")

    blocks, by_id = get_doc_blocks(fs, PAPER_DOC_TOKEN)
    root = blocks[0]
    root_children = root.get("children", [])
    heading3 = next((b for b in blocks if b.get("block_type") == 3 and "最新论文" in block_text(b)), None)
    intro_ok = False
    if heading3:
        pos = root_children.index(heading3["block_id"])
        intro = by_id.get(root_children[pos + 1]) if pos + 1 < len(root_children) else None
        intro_ok = bool(intro and "10 篇" in block_text(intro))
    table_ok = False
    for bid in root_children:
        block = by_id.get(bid)
        if block and block.get("block_type") == 31:
            table_ok = len(block.get("children", [])) >= 55
            break
    print(f"论文页：标题={'✓' if heading3 else '✗'} 导语={'✓' if intro_ok else '✗'} 表格={'✓' if table_ok else '✗'}")
    if not intro_ok:
        problems.append("论文页导语未更新")

    if skip_home:
        print("首页：跳过（--skip-home）")
    else:
        home_blocks, home_by_id = get_doc_blocks(fs, HOME_DOC_TOKEN)
        home_heading = next(
            (
                b for b in home_blocks
                if b.get("block_type") == 5 and "📄" in block_text(b) and "论文" in block_text(b)
            ),
            None,
        )
        home_ok = bool(home_heading and batch["batch_date"][5:].replace("-", ".") in block_text(home_heading))
        print(f"首页：论文卡片={'✓' if home_ok else '✗'} 「{block_text(home_heading) if home_heading else '未找到'}」")
        if not home_ok:
            problems.append("首页论文卡片未更新")

    if problems:
        print("\n❌ 验收问题：")
        for problem in problems:
            print("  -", problem)
        return 1
    print("\n✅ 验收通过：10 条记录 + 论文页" + ("（首页已跳过）" if skip_home else " + 首页"))
    return 0


# ---------------------------------------------------------------------------
# export Markdown for Git
# ---------------------------------------------------------------------------
def html_cell(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_entry_zh(paper: dict) -> str:
    highlights = "".join(f"<li>{item}</li>" for item in paper.get("repo_highlights_zh", []))
    results = "".join(f"<li>{item}</li>" for item in paper.get("repo_results_zh", []))
    return f"""### [{paper['title']}]({paper['url']})

<table style="width:100%;table-layout:fixed" width="100%">
<tbody>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">一句话摘要</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640">{html_cell(paper['summary'])}</td></tr>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">发布时间</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640">{paper['date'][:4]} 年 {int(paper['date'][5:7])} 月</td></tr>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">机构</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640">{html_cell(paper['org'])}</td></tr>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">特点</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640"><ul>{highlights}</ul></td></tr>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">实验结论</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640"><ul>{results}</ul></td></tr>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">数据 / 模型</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640">{html_cell(paper['data_model_zh'])}</td></tr>
</tbody>
</table>
"""


def render_entry_en(paper: dict) -> str:
    highlights = "".join(f"<li>{item}</li>" for item in paper.get("repo_highlights", []))
    results = "".join(f"<li>{item}</li>" for item in paper.get("repo_results", []))
    month = dt.date.fromisoformat(paper["date"]).strftime("%B %Y")
    return f"""### [{paper['title']}]({paper['url']})

<table style="width:100%;table-layout:fixed" width="100%">
<tbody>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">One-line summary</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640">{html_cell(paper['one_line_en'])}</td></tr>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">Release date</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640">{month}</td></tr>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">Organization</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640">{html_cell(paper['org_en'])}</td></tr>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">Highlights</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640"><ul>{highlights}</ul></td></tr>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">Results</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640"><ul>{results}</ul></td></tr>
<tr><td style="width:110px;min-width:110px;max-width:110px" width="110">Data / Models</td><td style="word-wrap:break-word;width:640px;min-width:640px;max-width:640px" width="640">{html_cell(paper['data_model_en'])}</td></tr>
</tbody>
</table>
"""


def export_markdown(batch: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    groups: dict[str, list[dict]] = {}
    for paper in batch["papers"]:
        groups.setdefault(paper["repo_category"], []).append(paper)
    for category, papers in groups.items():
        zh = "\n".join(render_entry_zh(p) for p in papers)
        en = "\n".join(render_entry_en(p) for p in papers)
        (out_dir / f"{category}.zh.md").write_text(zh, encoding="utf-8")
        (out_dir / f"{category}.en.md").write_text(en, encoding="utf-8")
    manifest = {
        "batch_date": batch["batch_date"],
        "categories": {k: [p["arxiv_id"] for p in v] for k, v in groups.items()},
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"exported {len(batch['papers'])} entries -> {out_dir}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def load_batch(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("token")
    sub.add_parser("list")

    for name in ("preview", "apply", "verify", "export", "home"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--input", required=True)
        if name == "export":
            cmd.add_argument("--out", default=str(HERE / "data" / "export"))
        if name in ("apply", "verify"):
            cmd.add_argument("--skip-home", action="store_true", help="首页无编辑权限时跳过首页步骤")

    args = parser.parse_args()

    if args.command == "token":
        app_id, app_secret = env_credentials()
        fs = Feishu(app_id, app_secret)
        token = fs.token()
        print(f"app_id={app_id} token_len={len(token)} status=ok")
        return 0

    app_id, app_secret = env_credentials()
    fs = Feishu(app_id, app_secret)

    if args.command == "list":
        records = get_all_records(fs)
        records.sort(key=lambda item: item.get("fields", {}).get("日期", 0), reverse=True)
        for item in records[:20]:
            fields = item.get("fields", {})
            print(f"{item['record_id']}  {fields.get('日期', '')}  {fields.get('论文标题', '')[:90]}")
        print(f"total={len(records)}")
        return 0

    batch = load_batch(args.input)
    if args.command == "preview":
        return preview(batch, fs)
    if args.command == "apply":
        apply_batch(fs, batch, skip_home=args.skip_home)
        return verify_batch(fs, batch, skip_home=args.skip_home)
    if args.command == "verify":
        return verify_batch(fs, batch, skip_home=args.skip_home)
    if args.command == "home":
        update_homepage(fs, batch)
        return 0
    if args.command == "export":
        export_markdown(batch, Path(args.out))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())