#!/usr/bin/env python3
"""
Turn a Feishu paper batch into one commit + PR on Octoday-Hub/Embodied-AI.

The batch JSON is the same file consumed by feishu_paper_sync.py.  It must
contain the repo_* fields (repo_category, repo_highlights, repo_results,
data_model_zh/en, one_line_en, org_en) so the zh/en HTML tables can be
rendered without guessing.

Usage
-----
  export GITHUB_TOKEN=...                 # Octoday-member0 PAT
  python3 feishu_to_git_pr.py \
      --input data/papers_20261110.json \
      --repo ../worktree/Embodied-AI \
      --branch update/papers-20261110 \
      --title "docs: 新增 10 篇 2026-11 具身智能论文（飞书论文库同步）" \
      --body-file /tmp/pr_body.md

The target worktree must be clean and based on the latest origin/main.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import feishu_paper_sync as sync

HEADINGS = {
    "embodied-foundation-models": "Embodied Foundation Models",
    "manipulation": "Manipulation & Teleoperation",
    "locomotion": "Locomotion",
    "navigation": "Navigation & Spatial Intelligence",
    "simulators": "Simulators & Sim2Real",
    "datasets": "Datasets",
    "benchmarks": "Benchmarks & Evaluation",
    "survey": "Survey",
}

FORK = "Octoday-member0/Embodied-AI"
UPSTREAM = "Octoday-Hub/Embodied-AI"
FORK_URL = f"https://github.com/{FORK}.git"


def run(cmd: list[str], cwd: Path, env: dict | None = None) -> str:
    result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"command failed: {' '.join(cmd)}\n{result.stdout}\n{result.stderr}")
    return result.stdout.strip()


def check_clean(repo: Path) -> None:
    if not (repo / ".git").exists():
        raise SystemExit(f"不是 Git 仓库：{repo}")
    dirty = run(["git", "status", "--porcelain"], repo)
    if dirty:
        raise SystemExit(f"工作区不干净，请先清理：\n{dirty}")
    branch = run(["git", "branch", "--show-current"], repo)
    print(f"worktree={repo} branch={branch} head={run(['git', 'rev-parse', '--short', 'HEAD'], repo)}")


def insert_entries(repo: Path, batch: dict) -> None:
    groups: dict[str, list[dict]] = {}
    for paper in batch["papers"]:
        category = paper.get("repo_category")
        if category not in HEADINGS:
            raise SystemExit(f"未知 repo_category：{category}")
        groups.setdefault(category, []).append(paper)

    for lang, filename in (("zh", "topics/03-papers.md"), ("en", "topics/03-papers_EN.md")):
        path = repo / filename
        text = path.read_text(encoding="utf-8")
        for category, papers in groups.items():
            heading = HEADINGS[category]
            marker = f"## {heading}\n\n"
            if marker not in text:
                raise SystemExit(f"{filename} 缺少分类：{heading}")
            entry = "\n".join(
                sync.render_entry_zh(p) if lang == "zh" else sync.render_entry_en(p)
                for p in papers
            ).strip()
            text = text.replace(marker, marker + entry + "\n\n", 1)
        path.write_text(text, encoding="utf-8")
        print(f"inserted {sum(len(v) for v in groups.values())} entries into {filename}")


def repo_checks(repo: Path, batch: dict) -> None:
    run(["git", "diff", "--check"], repo)
    for filename in ("topics/03-papers.md", "topics/03-papers_EN.md"):
        text = (repo / filename).read_text(encoding="utf-8")
        detailed = len(re.findall(r"^### \[", text, re.M))
        summaries = len(re.findall(r"^- \*\*\[arXiv", text, re.M))
        for paper in batch["papers"]:
            if text.count(paper["arxiv_id"]) != 1:
                raise SystemExit(f"{filename}: {paper['arxiv_id']} 出现次数不为 1")
        print(f"{filename}: detailed={detailed} summaries={summaries}")


def create_pr(batch: dict, branch: str, title: str, body: str, token: str, draft: bool = False) -> str:
    payload = json.dumps({
        "title": title,
        "head": f"{FORK.split('/')[0]}:{branch}",
        "base": "main",
        "body": body,
        "draft": draft,
    }).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{UPSTREAM}/pulls",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "ignore")
        raise SystemExit(f"创建 PR 失败：HTTP {exc.code}\n{raw}")
    return data["html_url"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="batch JSON")
    parser.add_argument("--repo", required=True, help="clean worktree based on origin/main")
    parser.add_argument("--branch", required=True, help="branch to push to the Octoday-member0 fork")
    parser.add_argument("--title", required=True)
    parser.add_argument("--body-file", required=True)
    parser.add_argument("--dry-run", action="store_true", help="render + checks, do not commit/push/PR")
    parser.add_argument("--draft", action="store_true")
    args = parser.parse_args()

    batch = json.loads(Path(args.input).read_text(encoding="utf-8"))
    errors = sync.validate_batch(batch)
    if errors:
        raise SystemExit("批次校验失败：\n" + "\n".join(errors))

    repo = Path(args.repo).resolve()
    check_clean(repo)
    insert_entries(repo, batch)
    repo_checks(repo, batch)

    if args.dry_run:
        print("dry-run: changes left in the worktree, nothing committed")
        return 0

    run(["git", "add", "topics/03-papers.md", "topics/03-papers_EN.md"], repo)
    run([
        "git", "-c", "user.name=Octoday-member0", "-c", "user.email=dev_intern@dexunit.com",
        "commit", "-m", args.title,
    ], repo)
    print(run(["git", "log", "--oneline", "-1"], repo))

    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        raise SystemExit("缺少 GITHUB_TOKEN（Octoday-member0 PAT）")
    push_url = f"https://Octoday-member0:{token}@github.com/{FORK}.git"
    run(["git", "push", push_url, f"HEAD:refs/heads/{args.branch}"], repo)
    print(f"pushed to fork: {FORK}:{args.branch}")

    body = Path(args.body_file).read_text(encoding="utf-8")
    url = create_pr(batch, args.branch, args.title, body, token, args.draft)
    print(f"PR: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())