# kzhou003.github.io

我所有站点和学习仓库的分类目录：<https://kzhou003.github.io/>

目录由 `scripts/build_directory.py` 按 `sites.json` 自动生成。同一分类内按最近更新排序。开了 Pages 的仓库链接到网站，标题取自页面的 `<title>`；其他仓库链接到 GitHub。说明文字优先用 `sites.json` 里的 `description`，没有时用仓库的 GitHub 描述。

## 更新时机

- 每天定时重新生成一次。
- 推送到 `main` 时重新生成。
- 想立刻更新时，运行：

```bash
gh workflow run pages.yml -R kzhou003/kzhou003.github.io
```

## 维护目录

都改 `sites.json`，然后推送：

- **归类或添加仓库**：把仓库加到对应分类的 `repos` 里。没开 Pages 的仓库也可以加。
- **新的 Pages 站点**：没有归类时会自动出现在“未分类”，之后再挪到对应分类。
- **隐藏站点**：把仓库名加到 `hidden` 里。
- **增加分类**：在 `categories` 里加一项，页面按这里的顺序显示。
