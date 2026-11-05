---
name: update-knowledge-graph
description: Update and maintain Kuan Zhou's knowledge graph at https://kzhou003.github.io/ (repo kzhou003/kzhou003.github.io). Adds knowledge links between nodes, child topic nodes for drills and overviews, region assignments, and descriptions, then validates and publishes the site. Use this whenever the user wants to update the knowledge base, 知识图谱, knowledge graph, or 目录页, add a new repo, note, drill, or overview to it, connect topics, 补知识关联, 加子节点, or asks why something is missing or stale on kzhou003.github.io, even if they do not name this skill.
---

# 更新知识图谱

这个 skill 维护 <https://kzhou003.github.io/>。网站大部分内容自动更新，你的工作是补上需要判断的部分：**知识关联**和**子节点**。这些内容都是公开发布的，读者会把每条连线当成事实，所以宁可少连，也不要连没有依据的线。

## 自动化做了什么

每 30 分钟，GitHub Actions 重建整个网站，指纹和线上不同时才部署。下面这些不用动手：

- 已收录仓库的 README 页面、页面标题、描述、license 和更新日期
- `adhoc-lean-grills` 目录页上的新笔记，自动成为子节点（标记了 `autoChildren`）
- 新仓库按名称归类：`awesome-*`、`*-drills`、`*-overview`、`*-skills`。没开 Pages 时发布 README
- 其他名称的 Pages 站点进入“未分类”

用户问“为什么还没更新”时，先判断是不是还在等下一轮，再运行 `gh workflow run pages.yml -R kzhou003/kzhou003.github.io` 触发一次，不要去改配置。

## 流程

### 1. 同步并审计

```bash
cd ~/development/kzhou003.github.io   # 不存在时 clone git@github.com:kzhou003/kzhou003.github.io.git
git pull --ff-only
GITHUB_TOKEN=$(gh auth token) python3 .claude/skills/update-knowledge-graph/scripts/audit_graph.py
```

审计会列出配置错误和待补内容。工作区有不相关的改动时，先告诉用户，不要混进这次提交。

### 2. 确定范围

用户点名了内容，就只做那部分。用户只说“更新一下”，就处理审计的错误和待补内容，优先顺序是：未分类站点、新收录仓库、孤立仓库、缺子节点的仓库。

不要顺手重组现有结构，也不要为了补齐数字硬加内容。“没有知识关联的子节点”一项不需要清零。

### 3. 读真实内容

判断之前先读两边的内容，不要只看仓库名和描述：

```bash
curl -s https://kzhou003.github.io/<仓库名>/ | grep -oE '<(section|h[12])[^>]* id="[^"]*"' # 网站的章节锚点
gh api repos/kzhou003/<仓库名>/readme -H 'Accept: application/vnd.github.raw'             # README
```

README 发布的页面，锚点就是 GitHub 的标题 slug。

### 4. 改 `sites.json`

日常只需要改这个文件。

**子节点**写在仓库条目的 `children` 里：

```json
{"id": "gpu-flashinfer", "title": "FlashInfer", "description": "对着官方 API 实现并对拍，最后做贡献实战", "url": "https://kzhou003.github.io/gpu-kernel-drills/#F1"}
```

- 对应这个站点真实的一个主线或章节，不是随便抽的关键词。一个仓库 2 到 9 个，太多图谱会挤。
- `id` 全图唯一，用小写短横线，带仓库前缀，比如 `gpu-`、`ov-`。不要改已有 `id`，`links` 靠它引用。
- `title` 控制在 12 个字以内，这是图上的标签。
- `url` 尽量精确到章节锚点。
- `description` 一句话，写这部分具体讲什么，内容来自原文。

**知识关联**写在 `links` 里：

```json
{"source": "ov-omni", "target": "nano-orch", "reason": "Omni 的多 stage 架构：概览讲取舍，练习写实现"}
```

每条关联要满足：

- 两端都读到了依据，能指出具体内容。比如同一个项目或技术、一边讲原理一边动手实现、一方由另一方产出。
- 优先连最具体的节点。能连子节点就不连仓库。
- 优先跨区域，这才是图谱的价值。同一仓库内部不用连。
- `reason` 是一句具体的话，让读者知道这两个放在一起能得到什么。

| 不合格 | 问题 | 合格 |
| --- | --- | --- |
| 都和 AI 相关 | 对任意两个节点都成立 | RL rollout 的推理视角，与后训练领域的全景地图 |
| 相关内容 | 没有信息 | 同一个编译器：一边写 kernel，一边读 IR 和 pass |
| 都提到了 KV cache | 只是关键词相同 | continuous batching、抢占和 KV 管理，从概念落到实现 |

找不到依据就不连，在结果里说明这个节点暂时孤立。新节点通常有 1 到 3 条关联就够了。现有的关联只有在来源已经消失、内容已变或用户要求时才删除，并在报告里说明。

**其他字段：**

| 需求 | 做法 |
| --- | --- |
| 归类新仓库 | 加到对应区域的 `repos`：`{"repo": "名称"}` |
| 发布没开 Pages 的仓库的 README | 条目加 `"readmePage": true` |
| 改图上的标题、说明或 license | 条目加 `title`、`description`、`license` |
| 给自动发现的笔记写说明 | 把它写进 `children`，`url` 保持一致，自动发现就不会重复添加 |
| 不展示某个仓库 | 名称加到 `hidden` |

归类时，五个区域的含义是：Adhoc Drills 是日常学习整理，Deep Drills 是深度练习与开源贡献，Overviews 是查漏补缺和面试准备，Dev Skills 是开发用的 skills，Awesome Lists 是阅读与跟踪。

不要修改其他仓库的内容。区域颜色和位置也别动，除非用户要求，因为配色是按地图相邻关系校验过的，规则见仓库 README 的“配色”。

### 5. 校验

```bash
GITHUB_TOKEN=$(gh auth token) python3 .claude/skills/update-knowledge-graph/scripts/audit_graph.py
GITHUB_TOKEN=$(gh auth token) python3 scripts/build_directory.py _site
```

审计要报告“配置有效”。这一步只能发现结构问题，所以提交前再自查一遍：每条新关联的 `reason` 能否在两端原文里找到依据。

加了较多节点时，打开 `_site/index.html` 看看标签是否重叠。

### 6. 发布

用户调用这个 skill 就是要更新线上图谱，所以校验通过后直接提交并推送到 `main`。用户说“先看看”或“不要发布”时，停在这里，把改动列给他确认。

```bash
git add sites.json
git commit
git push
gh run watch "$(gh run list -R kzhou003/kzhou003.github.io --event push --limit 1 --json databaseId --jq '.[0].databaseId')" -R kzhou003/kzhou003.github.io --exit-status
```

部署完成约一分钟后，确认线上已更新：

```bash
curl -s "https://kzhou003.github.io/?t=$(date +%s)" | grep -c '新节点的标题'
```

### 7. 汇报

用中文简短列出：

- 新增的子节点，以及它们的区域和仓库
- 新增的知识关联，每条写清两端和原因
- 删除或修改的内容及原因
- 部署结果和线上验证结果
- 暂时孤立的节点，以及审计里没处理的项

## 排查

| 现象 | 处理 |
| --- | --- |
| 更新迟迟不出现 | 看 `gh run list -R kzhou003/kzhou003.github.io`。`deploy` 显示 skipped，说明指纹没变，内容其实已是最新 |
| 定时任务不跑了 | `gh api repos/kzhou003/kzhou003.github.io/actions/workflows/pages.yml --jq .state`，不是 `active` 时用 `gh workflow enable pages.yml -R kzhou003/kzhou003.github.io` 恢复 |
| 审计报“锚点不存在” | 源站改了结构。重新读章节，更新 `url` |
| 审计报“不是公开仓库或不存在” | 仓库改名、删除或转为私有。确认后更新条目，并处理相关的 `links` |
| 新节点标签拥挤 | 减少子节点，或把标题缩短 |
