#!/usr/bin/env python3
"""Génère dark_mode.svg et light_mode.svg (profil GitHub façon neofetch).

Usage : GITHUB_TOKEN=xxx python3 generate.py
"""
import datetime as dt
import json
import os
import urllib.request
from html import escape

# ─── Configuration ─────────────────────────────────────────────────────────
USER = "cmer81"
HEADER = "cmer@cmer81"
UPTIME_SINCE = dt.date(2013, 7, 22)  # remplace par ta date de naissance

# Sections : (titre de section ou None, [(clé, valeur), ...])
SECTIONS = [
    (None, [
        ("OS", "Linux"),
        ("Uptime", "{uptime}"),
        ("Host", "The Void"),
        ("Kernel", "Software Engineer"),
        ("IDE", "VS Code, Claude Code"),
    ]),
    (None, [
        ("Languages.Programming", "TypeScript, Python, Rust, Go"),
        ("Languages.Infra", "Shell, Docker, Terraform (HCL)"),
        ("Languages.Real", "French, English"),
    ]),
    (None, [
        ("Hobbies.Software", "Self-hosting, AI, Open source"),
        ("Hobbies.Hardware", "Home Assistant, Weather stations"),
    ]),
    ("Contact", [
        ("GitHub", f"github.com/{USER}"),
        ("Discord", "Cmer"),
    ]),
]

WIDTH = 60  # largeur du bloc d'infos, en caractères

THEMES = {
    "dark": dict(bg="#161b22", text="#c9d1d9", key="#ffa657", value="#a5d6ff",
                 dots="#616e7f", art="#c9d1d9", add="#3fb950", border="#30363d"),
    "light": dict(bg="#f6f8fa", text="#24292f", key="#953800", value="#0a3069",
                  dots="#c2cfde", art="#24292f", add="#1a7f37", border="#d0d7de"),
}


# ─── Données GitHub ────────────────────────────────────────────────────────
def graphql(query, variables=None):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def fetch_stats():
    repos, stars, cursor = 0, 0, None
    while True:
        u = graphql("""query($login:String!,$cursor:String){user(login:$login){
            createdAt followers{totalCount}
            repositoriesContributedTo(contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY]){totalCount}
            repositories(ownerAffiliations:OWNER,first:100,after:$cursor){
              totalCount pageInfo{hasNextPage endCursor} nodes{stargazerCount}}}}""",
                    {"login": USER, "cursor": cursor})["user"]
        repos = u["repositories"]["totalCount"]
        stars += sum(n["stargazerCount"] for n in u["repositories"]["nodes"])
        if not u["repositories"]["pageInfo"]["hasNextPage"]:
            break
        cursor = u["repositories"]["pageInfo"]["endCursor"]

    # Les commits ne sont exposés que par fenêtres d'un an maximum
    commits = 0
    start = dt.datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00"))
    now = dt.datetime.now(dt.timezone.utc)
    while start < now:
        end = min(start + dt.timedelta(days=365), now)
        c = graphql("""query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){
            contributionsCollection(from:$from,to:$to){totalCommitContributions restrictedContributionsCount}}}""",
                    {"login": USER, "from": start.isoformat(), "to": end.isoformat()})
        cc = c["user"]["contributionsCollection"]
        commits += cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
        start = end

    return dict(repos=repos, contributed=u["repositoriesContributedTo"]["totalCount"],
                stars=stars, followers=u["followers"]["totalCount"], commits=commits)


def uptime(since):
    today = dt.date.today()
    years = today.year - since.year
    months = today.month - since.month
    days = today.day - since.day
    if days < 0:
        months -= 1
        prev_month = today.replace(day=1) - dt.timedelta(days=1)
        days += prev_month.day
    if months < 0:
        years -= 1
        months += 12
    plural = lambda n, w: f"{n} {w}{'s' if n > 1 else ''}"
    return f"{plural(years, 'year')}, {plural(months, 'month')}, {plural(days, 'day')}"


# ─── Rendu SVG ─────────────────────────────────────────────────────────────
def span(text, cls):
    return f'<tspan class="{cls}">{escape(text)}</tspan>'


def entry(key, value, width=WIDTH, lead=True):
    """'. Key: ........ value' aligné sur `width` caractères."""
    prefix = ". " if lead else ""
    dots = width - len(prefix) - len(key) - len(": ") - len(value) - 1
    return (span(prefix, "dots") + span(key, "key") + ":" +
            span(" " + "." * max(dots, 1) + " ", "dots") + span(value, "value"))


def header(title, width=WIDTH):
    fill = width - len(title) - 2
    return title + " " + span("—" * (fill - 2) + "-—-", "dots")


def build_info(stats):
    lines = [header(HEADER)]
    for title, items in SECTIONS:
        if title:
            lines.append("")
            lines.append(span("- ", "dots") + header(title, WIDTH - 2))
        elif len(lines) > 1:
            lines.append("")
        for k, v in items:
            lines.append(entry(k, v.format(uptime=uptime(UPTIME_SINCE))))

    half = 33
    lines += ["", span("- ", "dots") + header("GitHub Stats", WIDTH - 2)]
    repos = f"{stats['repos']} {{Contributed: {stats['contributed']}}}"
    lines.append(entry("Repos", repos, half) + " | " + entry("Stars", str(stats["stars"]), WIDTH - half - 3, lead=False))
    lines.append(entry("Commits", f"{stats['commits']:,}", half) + " | " + entry("Followers", str(stats["followers"]), WIDTH - half - 3, lead=False))
    return lines


def render(theme, art, info):
    c = THEMES[theme]
    art_fs, art_lh = 8, 9.4
    info_fs, info_lh = 16, 20
    art_w = 480
    pad = 20
    info_x = pad + art_w + 30
    width = info_x + int(WIDTH * info_fs * 0.6) + pad
    height = max(len(art) * art_lh, len(info) * info_lh) + 2 * pad

    out = [f'<?xml version="1.0" encoding="UTF-8"?>',
           f'<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,\'Courier New\',monospace" '
           f'width="{width}px" height="{height:.0f}px">',
           "<style>",
           f".key{{fill:{c['key']}}} .value{{fill:{c['value']}}} .dots{{fill:{c['dots']}}} .add{{fill:{c['add']}}}",
           "text,tspan{white-space:pre}",
           "</style>",
           f'<rect width="{width}px" height="{height:.0f}px" fill="{c["bg"]}" rx="15"/>',
           f'<text x="{pad}" y="{pad}" fill="{c["art"]}" font-size="{art_fs}px" xml:space="preserve">']
    for i, line in enumerate(art):
        out.append(f'<tspan x="{pad}" y="{pad + (i + 1) * art_lh:.1f}" textLength="{art_w}" '
                   f'lengthAdjust="spacingAndGlyphs">{escape(line)}</tspan>')
    out.append("</text>")
    out.append(f'<text x="{info_x}" y="{pad}" fill="{c["text"]}" font-size="{info_fs}px" xml:space="preserve">')
    for i, line in enumerate(info):
        out.append(f'<tspan x="{info_x}" y="{pad + (i + 1) * info_lh}">{line}</tspan>')
    out.append("</text>")
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "ascii_art.txt"), encoding="utf-8") as f:
        art = f.read().rstrip("\n").split("\n")
    info = build_info(fetch_stats())
    for theme in THEMES:
        with open(os.path.join(here, f"{theme}_mode.svg"), "w", encoding="utf-8") as f:
            f.write(render(theme, art, info))


if __name__ == "__main__":
    main()
