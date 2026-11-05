# kzhou003.github.io

我的知识图谱，把所有学习站点和仓库连成一张地图：<https://kzhou003.github.io/>

页面分为五个区域，顺序是 Adhoc Drills、Deep Drills、Overviews、Dev Skills 和 Awesome Lists。节点之间的连线表示内容上的真实关联，点击节点可以看到每条关联的原因。页面下方还有一份完整的静态目录，方便手机浏览和无障碍访问。

## 文件结构

| 文件 | 作用 |
| --- | --- |
| `sites.json` | 作者信息、区域、节点和知识关联，日常维护只改这里 |
| `site/template.html` | 页面的样式和图谱交互 |
| `scripts/build_directory.py` | 读取 GitHub 数据，生成最终页面 |

本地预览：

```bash
python3 scripts/build_directory.py _site && open _site/index.html
```

## 更新时机

- 每天定时重新生成一次。
- 推送到 `main` 时重新生成。
- 想立刻更新时，运行：

```bash
gh workflow run pages.yml -R kzhou003/kzhou003.github.io
```

## 维护图谱

都改 `sites.json`，然后推送：

- **添加仓库**：加到对应区域的 `repos` 里，没开 Pages 的仓库也可以加。
- **添加子节点**：在仓库的 `children` 里加一项，填写 `id`、`title`、`description` 和 `url`。
- **添加知识关联**：在 `links` 里加一项，`reason` 写明两者的具体关系。
- **隐藏站点**：把仓库名加到 `hidden` 里。
- **修正 license**：GitHub 识别不出时，在仓库条目里填写 `license`。

新的 Pages 站点没有归类时，会自动出现在“未分类”区域。

## 配色

页面有两套配色，用左上角的按钮切换，选择会保存在浏览器里：

- **深色**：默认配色，接近 Obsidian。
- **Latte**：浅色，取自 [kuanzhou.online](https://kuanzhou.online/) 的配色。链接加上 `?theme=latte` 可以直接打开，比如 <https://kzhou003.github.io/?theme=latte>。

每个区域在 `sites.json` 里有 `color`（深色）和 `colorLight`（Latte）两个颜色。两套颜色都用校验脚本检查过：地图上相邻的区域都能分清，包括色盲视觉下。调整颜色或区域位置时，要重新检查相邻的两个区域。

## License

本仓库代码采用 [MIT License](LICENSE)。图谱链接到的各个项目，license 以其仓库为准。
