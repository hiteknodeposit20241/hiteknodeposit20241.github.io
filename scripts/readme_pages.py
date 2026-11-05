"""Turn a README rendered by the GitHub API into a page on this site."""
import html
import re

HEADING_RE = re.compile(
    r'<(h[1-6])([^>]*)>(.*?)</h[1-6]><a id="user-content-([^"]+)"[^>]*>.*?</a>', re.S
)
MATH_RE = re.compile(r"(<math-renderer[^>]*>)(.*?)(</math-renderer>)", re.S)
RAW_MATH_RE = re.compile(r"\$\$.+?\$\$", re.S)
RELATIVE_URL_RE = re.compile(r'\b(href|src)="(?!https?:|mailto:|#|//)([^"]*)"')


def restore_math(body, markdown):
    """Use the README's own TeX, because the API drops backslashes like \\! and escapes twice."""
    blocks = MATH_RE.findall(body)
    originals = RAW_MATH_RE.findall(markdown)
    sources = iter(originals if len(originals) == len(blocks) else [])

    def rewrite(match):
        source = next(sources, html.unescape(html.unescape(match[2])))
        return f"{match[1]}{html.escape(source, quote=False)}{match[3]}"

    return MATH_RE.sub(rewrite, body)


def clean_headings(body):
    """Put each anchor on its heading, so in-page links work without GitHub's script."""
    return HEADING_RE.sub(lambda m: f'<{m[1]} id="{m[4]}">{m[3]}</{m[1]}>', body)


def absolute_links(body, repo):
    """Point links to repo files at GitHub, since only the README is published here."""
    base = f"{repo['full_name']}/blob/{repo['default_branch']}"

    def rewrite(match):
        attr, path = match[1], match[2].removeprefix("./")
        if attr == "src":
            url = f"https://raw.githubusercontent.com/{repo['full_name']}/{repo['default_branch']}/{path}"
        else:
            url = f"https://github.com/{base}/{path}"
        return f'{attr}="{url}"'

    return RELATIVE_URL_RE.sub(rewrite, body)


def write_readme_page(page, rendered, markdown, repo, node, region, output):
    body = absolute_links(clean_headings(restore_math(rendered, markdown)), repo)
    values = {
        "__TITLE__": html.escape(node["title"]),
        "__DESCRIPTION__": html.escape(node["description"], quote=True),
        "__REGION_ID__": region["id"],
        "__REGION__": html.escape(region["title"]),
        "__LICENSE__": html.escape(node["license"]),
        "__UPDATED__": node["updated"],
        "__REPO_URL__": html.escape(repo["html_url"], quote=True),
    }
    for key, value in values.items():
        page = page.replace(key, value)
    target = output / repo["name"]
    target.mkdir(parents=True, exist_ok=True)
    # The README goes in last, so its text is never treated as a placeholder.
    (target / "index.html").write_text(page.replace("__README__", body), encoding="utf-8")
