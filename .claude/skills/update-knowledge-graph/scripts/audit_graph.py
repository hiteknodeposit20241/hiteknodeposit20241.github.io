#!/usr/bin/env python3
"""Audit the knowledge graph: report config errors and work that needs judgment.

Usage: python3 audit_graph.py [--config path/to/sites.json]

Set GITHUB_TOKEN to raise the API rate limit. Exits 1 when there are errors.
"""
import argparse
import collections
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))

import build_directory as bd  # noqa: E402


def fetch_full(url):
    """Fetch a whole page, since anchors can sit past the build script's read limit."""
    request = urllib.request.Request(url, headers={"User-Agent": "graph-audit"})
    try:
        with urllib.request.urlopen(request, timeout=30) as resp:
            return resp.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError):
        return None


def check_config(config, repos):
    errors = []
    ids = collections.Counter()
    known_regions = {category["id"] for category in config["categories"]}
    for category in config["categories"]:
        for entry in category["repos"]:
            ids[entry["repo"]] += 1
            if entry["repo"] not in repos:
                errors.append(f'repo 不是公开仓库或不存在: {entry["repo"]}')
            for child in entry.get("children", []):
                ids[child["id"]] += 1
                for key in ("title", "description", "url"):
                    if not child.get(key):
                        errors.append(f'子节点 {child["id"]} 缺少 {key}')
    errors += [f"id 重复: {name}" for name, count in ids.items() if count > 1]
    errors += [
        f'autoRules 指向不存在的区域: {rule["category"]}'
        for rule in config["autoRules"] if rule["category"] not in known_regions
    ]
    return errors


def check_links(config, graph):
    errors = []
    nodes = {node["id"]: node for node in graph["nodes"]}
    seen = set()
    for link in config["links"]:
        source, target = link["source"], link["target"]
        label = f"{source} -> {target}"
        if source not in nodes or target not in nodes:
            errors.append(f"关联指向不存在的节点: {label}")
            continue
        pair = frozenset((source, target))
        if source == target:
            errors.append(f"关联连到了自己: {label}")
        if pair in seen:
            errors.append(f"关联重复: {label}")
        seen.add(pair)
        if nodes[source].get("parent") == target or nodes[target].get("parent") == source:
            errors.append(f"关联重复了仓库和子节点的从属关系: {label}")
        if len(link.get("reason", "").strip()) < 8:
            errors.append(f"关联缺少具体原因: {label}")
    return errors


def check_urls(graph):
    errors = []
    pages = {}
    for node in graph["nodes"]:
        base, _, anchor = node["url"].partition("#")
        if base not in pages:
            pages[base] = fetch_full(base)
        body = pages[base]
        if body is None:
            errors.append(f'链接打不开: {node["id"]} {node["url"]}')
        elif anchor and not re.search(rf"""\bid=["']{re.escape(anchor)}["']""", body):
            errors.append(f'锚点不存在: {node["id"]} {node["url"]}')
    return errors


def find_gaps(config, listed_children, listed_repos, graph):
    nodes = graph["nodes"]
    linked = collections.Counter()
    for link in graph["links"]:
        linked[link["source"]] += 1
        linked[link["target"]] += 1
    children = collections.defaultdict(list)
    for node in nodes:
        if node.get("parent"):
            children[node["parent"]].append(node)

    gaps = collections.OrderedDict()
    hubs = [node for node in nodes if node["hub"]]
    gaps["未写进 sites.json 的自动收录仓库（需要补说明、子节点和关联）"] = [
        node["id"] for node in hubs if node["id"] not in listed_repos
    ]
    gaps["未分类的站点（需要归类或隐藏）"] = [node["id"] for node in hubs if node["region"] == "other"]
    gaps["自动发现、还没有说明的子节点"] = [
        node["id"] for node in nodes if node.get("parent") and node["id"] not in listed_children
    ]
    gaps["没有说明的仓库"] = [node["id"] for node in hubs if not node["description"]]
    gaps["Drills / Overviews 里没有子节点的仓库"] = [
        node["id"] for node in hubs if node["region"] in ("deep", "overview") and not children[node["id"]]
    ]
    gaps["完全孤立的仓库（自身和子节点都没有知识关联）"] = [
        node["id"] for node in hubs
        if not linked[node["id"]] and not any(linked[child["id"]] for child in children[node["id"]])
    ]
    gaps["没有知识关联的子节点（不必全部补齐）"] = [
        node["id"] for node in nodes if node.get("parent") and not linked[node["id"]]
    ]
    return gaps


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, default=bd.CONFIG)
    config = json.loads(parser.parse_args().config.read_text(encoding="utf-8"))

    listed_repos = {entry["repo"] for category in config["categories"] for entry in category["repos"]}
    listed_children = {
        child["id"]
        for category in config["categories"] for entry in category["repos"]
        for child in entry.get("children", [])
    }
    repos = bd.public_repos()
    errors = check_config(config, repos)
    # An invalid rule is already an error above, and it would stop the remaining checks.
    regions = {category["id"] for category in config["categories"]}
    config["autoRules"] = [rule for rule in config["autoRules"] if rule["category"] in regions]
    bd.apply_auto_rules(config, repos)
    graph = bd.build_graph(config, repos)
    errors += check_links(config, graph)
    errors += check_urls(graph)

    hubs = sum(node["hub"] for node in graph["nodes"])
    print(f'图谱: {hubs} 个仓库, {len(graph["nodes"]) - hubs} 个子节点, {len(graph["links"])} 条知识关联\n')
    print(f"错误 ({len(errors)})")
    for error in errors:
        print(f"  - {error}")
    print("\n待补内容")
    for title, items in find_gaps(config, listed_children, listed_repos, graph).items():
        print(f"  {title}: {', '.join(items) if items else '无'}")
    print("\n结果:", "有错误，先修复" if errors else "配置有效")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
