"""Builds the neofetch-style profile card and link buttons (dark + light).

Stdlib only. Stats come from the GitHub GraphQL API; set GITHUB_TOKEN, or run
locally with `GITHUB_TOKEN=$(gh auth token) python tools/build.py`.
Edit the CONFIG block below to change what the card says.
"""
import datetime as dt
import json
import os
import urllib.request
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- CONFIG
USER = "princeali7"
TITLE = "ali@raza"
BIRTHDATE = None  # e.g. dt.date(1990, 1, 31); None = count "Uptime" from the GitHub join date
INFO = [  # (key, value); "Languages.Real" renders the sub-key dimmed
    ("OS", "macOS, iOS, Linux"),
    ("Uptime", "{uptime}"),
    ("Host", "Dubai, UAE"),
    ("Kernel", "Software Engineer @ Infinity Creatives"),
    ("IDE", "VS Code, Claude Code"),
    None,
    ("Languages.Programming", "Python, TypeScript, JavaScript"),
    ("Languages.Computer", "HTML, CSS, SQL, YAML"),
    ("Languages.Real", "English"),
    None,
    ("Focus.AI", "Agents, MCP, LLM Automation"),
    ("Focus.Web", "Next.js, Shopify, Cloudflare"),
    ("Hobbies", "Building things"),
]
CONTACT = [
    ("Email", "razaminhas11@gmail.com"),
    ("LinkedIn", "ali-raza-minhas"),
    ("GitHub", USER),
]
# Buttons under the card: (label, href). Keep README.md's links in sync with this list.
LINKS = [
    ("LINKEDIN", "https://www.linkedin.com/in/ali-raza-minhas/"),
    ("EMAIL", "mailto:razaminhas11@gmail.com"),
    ("GITHUB", f"https://github.com/{USER}"),
]
# ----------------------------------------------------------------------

THEMES = {
    "dark": dict(bg="#161b22", text="#c9d1d9", key="#F76E0A", value="#a5d6ff",
                 dim="#616e7f", border="#363c43"),
    "light": dict(bg="#f6f8fa", text="#24292f", key="#bc4c00", value="#0a3069",
                  dim="#8c959f", border="#d0d7de"),
}
FONT = "ConsolasFallback,Consolas,Menlo,'DejaVu Sans Mono',monospace"
STYLE_FONT = """@font-face {src: local('Consolas'); font-family: 'ConsolasFallback'; size-adjust: 109%;}
text, tspan {white-space: pre;}"""
CHAR_W = 0.6        # monospace advance, in em
W = 1018            # card width; GitHub's README column
M = 15              # outer margin
PANEL_FS, PANEL_LH, PANEL_COLS = 16, 20, 58
PANEL_X = W - M - PANEL_COLS * PANEL_FS * CHAR_W
ART_W = PANEL_X - M - 18


def gql(query: str) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]


def fetch_stats() -> dict:
    u = gql(f"""{{ user(login: "{USER}") {{
        createdAt followers {{ totalCount }}
        repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]) {{ totalCount }}
        repositories(ownerAffiliations: OWNER, first: 100, isFork: false) {{
            totalCount nodes {{ stargazerCount }} }} }} }}""")["user"]
    # shortcut: stars only cover the first 100 repos, page through if you pass that
    joined = dt.datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00"))
    now = dt.datetime.now(dt.timezone.utc)
    # contributionsCollection spans at most a year, so ask for each year in one query.
    years = " ".join(
        f'y{y}: contributionsCollection(from: "{max(joined, dt.datetime(y, 1, 1, tzinfo=dt.timezone.utc)).isoformat()}", '
        f'to: "{min(now, dt.datetime(y, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc)).isoformat()}") '
        "{ totalCommitContributions restrictedContributionsCount }"
        for y in range(joined.year, now.year + 1)
    )
    c = gql(f'{{ user(login: "{USER}") {{ {years} }} }}')["user"]
    return {
        "joined": joined.date().isoformat(),
        "repos": u["repositories"]["totalCount"],
        "contrib": u["repositoriesContributedTo"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
        "commits": sum(v["totalCommitContributions"] for v in c.values()),
        "private": sum(v["restrictedContributionsCount"] for v in c.values()),
        "followers": u["followers"]["totalCount"],
    }


def uptime(start: dt.date, today: dt.date) -> str:
    months = (today.year - start.year) * 12 + today.month - start.month - (today.day < start.day)
    ay, am = divmod(start.month - 1 + months, 12)
    am += 1
    ay += start.year
    last = (dt.date(ay + am // 12, am % 12 + 1, 1) - dt.timedelta(days=1)).day
    d = (today - dt.date(ay, am, min(start.day, last))).days  # anchor clamps Jan 31 -> Feb 28
    y, m = divmod(months, 12)
    plural = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"
    return f"{plural(y, 'year')}, {plural(m, 'month')}, {plural(d, 'day')}"


def row(key: str, value: str) -> list[tuple[str, str]]:
    """'. Key: ....... value' as (css class, text) spans, padded to PANEL_COLS."""
    main, _, sub = key.partition(".")
    head = [("key", main)] + ([("dim", "."), ("key", sub)] if sub else []) + [("text", ":")]
    used = 2 + len(key) + 1 + 1 + len(value)  # ". " + key + ":" + " " + value
    dots = " " + "." * max(PANEL_COLS - used - 2, 1) + " "
    return [("text", ". ")] + head + [("dim", dots), ("value", value)]


def rule(label: str = "") -> list[tuple[str, str]]:
    text = f"- {label} -" if label else ""
    return [("text", text), ("dim", "—" * (PANEL_COLS - len(text)))]


def panel_rows(s: dict) -> list:
    start = BIRTHDATE or dt.date.fromisoformat(s["joined"])
    rows = [[("title", TITLE), ("cursor", "_")], rule()]
    for item in INFO:
        rows.append([] if item is None else row(item[0], item[1].format(uptime=uptime(start, dt.date.today()))))
    rows += [[], rule("Contact")] + [row(k, v) for k, v in CONTACT]
    rows += [[], rule("GitHub Stats")]
    rows.append(row("Repos", f"{s['repos']} (Contributed: {s['contrib']}) | Stars: {s['stars']}"))
    rows.append(row("Commits", f"{s['commits']:,} (+{s['private']:,} private) | Followers: {s['followers']}"))
    return rows


def card(theme: str, s: dict) -> str:
    t = THEMES[theme]
    rows = panel_rows(s)
    h = 2 * M + len(rows) * PANEL_LH + 10
    art = (ROOT / f"assets/ascii-art{'-light' if theme == 'light' else ''}.txt").read_text().splitlines()
    cols = max(len(line) for line in art)
    fs = min(ART_W / (cols * CHAR_W), (h - 2 * M) / (len(art) * 1.11))
    art_y = (h - len(art) * fs * 1.11) / 2 + fs
    art_x = M + (ART_W - cols * fs * CHAR_W) / 2
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h:.0f}" viewBox="0 0 {W} {h:.0f}" font-family="{FONT}">',
        f"<style>{STYLE_FONT}",
        *(f".{k} {{fill: {t[k]};}}" for k in ("text", "key", "value", "dim")),
        f".title {{fill: {t['key']}; font-weight: bold;}}",
        f".cursor {{fill: {t['key']}; animation: blink 1.06s steps(1) infinite;}}",
        "@keyframes blink {50% {opacity: 0;}}",
        "</style>",
        f'<rect width="{W}" height="{h:.0f}" fill="{t["bg"]}" rx="15"/>',
        f'<text font-size="{fs:.2f}px" fill="{t["text"]}">',
        *(f'<tspan x="{art_x:.1f}" y="{art_y + i * fs * 1.11:.2f}">{escape(line)}</tspan>' for i, line in enumerate(art)),
        "</text>",
        f'<text font-size="{PANEL_FS}px" class="text">',
    ]
    for i, spans in enumerate(rows):
        if spans:
            body = "".join(f'<tspan class="{c}">{escape(txt)}</tspan>' for c, txt in spans)
            out.append(f'<tspan x="{PANEL_X:.1f}" y="{M + 20 + i * PANEL_LH}">{body}</tspan>')
    out += ["</text>", "</svg>"]
    return "\n".join(out) + "\n"


def button(theme: str, label: str, n: int) -> str:
    """One pixel-framed button; README shows n of them side by side at 1/n width."""
    t = THEMES[theme]
    w, h, gap = W / n, 60, 14
    x0, bw = gap / 2, w - gap
    step = lambda x, y, ww, hh, p=3: (f"M{x + p} {y}h{ww - 2 * p}v{p}h{p}v{hh - 2 * p}h{-p}v{p}"
                                      f"h{-(ww - 2 * p)}v{-p}h{-p}v{-(hh - 2 * p)}h{p}z")
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.1f}" height="{h}" viewBox="0 0 {w:.1f} {h}" font-family="{FONT}">',
        f"<style>{STYLE_FONT}",
        f".cursor {{animation: blink 1.06s steps(1) infinite;}} @keyframes blink {{50% {{opacity: 0;}}}}</style>",
        f'<path d="{step(x0, 0, bw, h)}" fill="{t["border"]}" shape-rendering="crispEdges"/>',
        f'<path d="{step(x0 + 3, 3, bw - 6, h - 6)}" fill="{t["bg"]}" shape-rendering="crispEdges"/>',
        f'<rect x="{x0 + 6}" y="{h - 6}" width="{bw - 12}" height="3" fill="{t["key"]}"/>',
        f'<text x="{x0 + bw / 2:.1f}" y="{h / 2 + 6}" font-size="18px" text-anchor="middle" fill="{t["text"]}">'
        f'<tspan fill="{t["key"]}">&gt; </tspan>{escape(label)}<tspan class="cursor" fill="{t["key"]}">_</tspan></text>',
        "</svg>",
    ]) + "\n"


def main() -> None:
    cache = ROOT / "cache/stats.json"
    if os.environ.get("GITHUB_TOKEN"):
        s = fetch_stats()
        cache.parent.mkdir(exist_ok=True)
        cache.write_text(json.dumps(s, indent=2) + "\n")
    else:
        s = json.loads(cache.read_text())  # offline rebuild from the last fetch
    for theme in THEMES:
        (ROOT / f"{theme}_mode.svg").write_text(card(theme, s))
        for label, _ in LINKS:
            (ROOT / f"link_{label.lower()}_{theme}.svg").write_text(button(theme, label, len(LINKS)))


if __name__ == "__main__":
    assert uptime(dt.date(2015, 1, 10), dt.date(2026, 11, 9)) == "11 years, 9 months, 30 days"
    assert uptime(dt.date(2020, 3, 31), dt.date(2021, 3, 1)) == "0 years, 11 months, 1 day"
    main()
