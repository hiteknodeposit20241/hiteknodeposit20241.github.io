# kzhou003.github.io

我的知识图谱，把所有学习站点和仓库连成一张地图：<https://kzhou003.github.io/>

页面分为五个区域，顺序是 Adhoc Drills、Deep Drills、Overviews、Dev Skills 和 Awesome Lists。节点之间的连线表示内容上的真实关联，点击节点可以看到每条关联的原因。页面下方还有一份完整的静态目录，方便手机浏览和无障碍访问。

## 文件结构

| 文件 | 作用 |
| --- | --- |
| `sites.json` | 作者信息、区域、节点和知识关联，日常维护只改这里 |
| `site/template.html` | 图谱页面的样式和交互 |
| `site/readme.html` | README 页面的模板 |
| `site/theme.css`、`site/theme-boot.html`、`site/theme-toggle.js` | 两种页面共用的配色和切换逻辑 |
| `scripts/build_directory.py` | 读取 GitHub 数据，生成最终页面 |
| `scripts/readme_pages.py` | 把 README 处理成站内页面 |

本地预览：

```bash
python3 scripts/build_directory.py _site && open _site/index.html
```

## 自动更新

每 30 分钟完整重建一次，把结果和线上的 `fingerprint.txt` 对比，有变化才部署。推送到本仓库时立刻部署。想马上检查一次，运行：

```bash
gh workflow run pages.yml -R kzhou003/kzhou003.github.io
```

下面这些都不用改配置：

| 变化 | 结果 |
| --- | --- |
| 已收录仓库的 README、页面标题、描述、license 或更新日期变了 | 页面和图谱自动同步 |
| `adhoc-lean-grills` 里加了新笔记 | 自动成为 Adhoc Drills 的子节点 |
| 新建 `awesome-*` 仓库 | 进入 Awesome Lists，没开 Pages 时发布它的 README |
| 新建 `*-drills`、`*-overview`、`*-skills` 仓库 | 进入 Deep Drills、Overviews、Dev Skills，规则同上 |
| 其他名称的仓库开了 Pages | 进入“未分类” |
| 仓库删除、改为私有或开了 Pages | 自动移除或换成它自己的网站 |

fork 和已归档的仓库不会被规则收录。规则在 `sites.json` 的 `autoRules` 里。

## 手动维护

这些内容需要判断，改 `sites.json` 后推送：

- **知识关联**：在 `links` 里加一项，`reason` 写明两者的具体关系。新节点没有关联时只连到所属仓库。
- **子节点**：除了 `autoChildren` 的仓库，其他仓库的子主题写在 `children` 里，填写 `id`、`title`、`description` 和 `url`。
- **隐藏站点**：把仓库名加到 `hidden` 里。
- **归类或发布 README**：把仓库加到对应区域的 `repos` 里，加上 `"readmePage": true` 就会发布到 `https://kzhou003.github.io/<仓库名>/`，不用改动那个仓库。README 里指向仓库文件的链接仍然打开 GitHub。
- **修正说明或 license**：在仓库条目里填写 `description` 或 `license`。
- **增加区域**：在 `categories` 里加一项，页面按这里的顺序显示。

## 配色

页面有两套配色，用左上角的按钮切换，选择会保存在浏览器里：

- **深色**：默认配色，接近 Obsidian。
- **Latte**：浅色，取自 [kuanzhou.online](https://kuanzhou.online/) 的配色。链接加上 `?theme=latte` 可以直接打开，比如 <https://kzhou003.github.io/?theme=latte>。

每个区域在 `sites.json` 里有 `color`（深色）和 `colorLight`（Latte）两个颜色。两套颜色都用校验脚本检查过：地图上相邻的区域都能分清，包括色盲视觉下。调整颜色或区域位置时，要重新检查相邻的两个区域。

## License

本仓库代码采用 [MIT License](LICENSE)。图谱链接到的各个项目，license 以其仓库为准。
