# kzhou003.github.io

我所有 GitHub Pages 站点的目录页：<https://kzhou003.github.io/>

目录由 `scripts/build_directory.py` 自动生成，列出 `kzhou003` 名下所有开启了 Pages 的公开仓库，按最近更新排序。链接文字取自站点的 `<title>`，说明文字取自仓库的 GitHub 描述。

## 更新时机

- 每天定时重新生成一次。
- 推送到 `main` 时重新生成。
- 想立刻更新时，运行：

```bash
gh workflow run pages.yml -R kzhou003/kzhou003.github.io
```

## 隐藏某个站点

把仓库名加到 `scripts/build_directory.py` 的 `EXCLUDE` 里，然后推送。
