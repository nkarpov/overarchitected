#!/usr/bin/env python3
"""Build OverArchitected blog from markdown episodes to HTML."""

import os
import re
import yaml
import html as html_mod
from pathlib import Path

ROOT = Path(__file__).parent
EPISODES_DIR = ROOT / "episodes"
DIST_DIR = ROOT / "dist"


def parse_frontmatter(text):
    """Split YAML frontmatter from markdown body."""
    if text.startswith("---"):
        _, fm, body = text.split("---", 2)
        return yaml.safe_load(fm), body.strip()
    return {}, text.strip()


def timestamp_to_seconds(ts):
    """Convert 'M:SS' or 'H:MM:SS' to seconds."""
    parts = ts.split(":")
    parts = [int(p) for p in parts]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def inline_md(text):
    """Convert inline markdown (bold, italic, links, code) to HTML."""
    # code spans first (so bold/italic don't interfere)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # italic
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)
    return text


def parse_body(md_body):
    """Parse markdown body into a list of blocks.

    Returns list of dicts with type: 'intro' | 'heading' | 'machine' | 'human' | 'divider'
    Convention: blockquotes (> ...) = machine (Opus), regular paragraphs = human (Nick)
    """
    blocks = []
    lines = md_body.split("\n")
    i = 0
    seen_first_heading = False

    while i < len(lines):
        line = lines[i]

        # Heading
        if line.startswith("## "):
            seen_first_heading = True
            blocks.append({"type": "heading", "text": line[3:].strip()})
            i += 1
            continue

        # Blockquote block (machine)
        if line.startswith("> "):
            quote_lines = []
            while i < len(lines) and (lines[i].startswith("> ") or lines[i] == ">"):
                stripped = lines[i][2:] if lines[i].startswith("> ") else ""
                quote_lines.append(stripped)
                i += 1
            # Parse the quote content into paragraphs, preserving code blocks
            raw = "\n".join(quote_lines)
            # Check for code block inside quote
            if "```" in raw:
                pre_code = re.search(r'```\n?(.*?)```', raw, re.DOTALL)
                code_html = ""
                if pre_code:
                    code_text = html_mod.escape(pre_code.group(1).rstrip())
                    # color the arrows
                    code_text = re.sub(r'(→|←|-)', r'<span class="arrow">\1</span>', code_text)
                    code_html = f"<pre>{code_text}</pre>"
                blocks.append({"type": "machine", "html": code_html, "is_code": True})
            else:
                paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
                html_parts = []
                for p in paragraphs:
                    p_html = inline_md(html_mod.escape(p))
                    # unescape our generated HTML tags
                    p_html = p_html.replace("&lt;strong&gt;", "<strong>").replace("&lt;/strong&gt;", "</strong>")
                    p_html = p_html.replace("&lt;em&gt;", "<em>").replace("&lt;/em&gt;", "</em>")
                    p_html = p_html.replace("&lt;code&gt;", "<code>").replace("&lt;/code&gt;", "</code>")
                    p_html = p_html.replace("&lt;a ", "<a ").replace("&lt;/a&gt;", "</a>")
                    # fix target attribute
                    p_html = re.sub(r'&lt;a href=&quot;(.+?)&quot; target=&quot;_blank&quot;&gt;', r'<a href="\1" target="_blank">', p_html)
                    html_parts.append(f"<p>{p_html}</p>")
                blocks.append({"type": "machine", "html": "\n    ".join(html_parts), "is_code": False})
            continue

        # Blank line
        if line.strip() == "":
            i += 1
            continue

        # Regular text (human / intro)
        para_lines = []
        while i < len(lines) and lines[i].strip() != "" and not lines[i].startswith("## ") and not lines[i].startswith("> "):
            para_lines.append(lines[i])
            i += 1
        text = " ".join(para_lines)
        if not seen_first_heading:
            blocks.append({"type": "intro", "html": f"<p>{inline_md(html_mod.escape(text))}</p>"})
        else:
            blocks.append({"type": "human", "html": f"<p>{inline_md(html_mod.escape(text))}</p>"})
        continue

    return blocks


def fix_escaped_html(text):
    """After html.escape + inline_md, fix the double-escaped tags."""
    text = re.sub(r'&lt;(/?(?:strong|em|code|a|pre|span))([^&]*?)&gt;', r'<\1\2>', text)
    text = text.replace('&amp;quot;', '"')
    text = text.replace('&quot;', '"')
    text = text.replace("&amp;#", "&#")
    return text


def build_section_meta(sections, heading):
    """Find matching section metadata from frontmatter."""
    for s in sections:
        if s["heading"] == heading:
            return s
    return None


def render_episode(meta, blocks):
    """Render an episode to HTML."""
    sections = meta.get("sections", [])
    youtube_id = meta.get("youtube_id")
    feat_num = 0

    body_parts = []

    # Intro paragraphs
    intro_html = []
    i = 0
    while i < len(blocks) and blocks[i]["type"] == "intro":
        intro_html.append(blocks[i]["html"])
        i += 1

    if intro_html:
        body_parts.append(f'<div class="intro">\n  {"".join(intro_html)}\n</div>')

    # Remaining blocks
    current_heading = None
    while i < len(blocks):
        block = blocks[i]

        if block["type"] == "heading":
            if current_heading:
                body_parts.append("</div>\n<hr class='divider'>")

            heading_text = block["text"]
            section_meta = build_section_meta(sections, heading_text)

            # Determine if numbered feature or standalone section
            is_feature = section_meta and section_meta.get("docs")
            if is_feature or (section_meta and heading_text not in ("The Thumb Incident", "The Final Architecture", "The Rating")):
                if heading_text not in ("The Final Architecture", "The Rating"):
                    feat_num += 1

            heading_html = heading_text
            if feat_num > 0 and heading_text not in ("The Thumb Incident", "The Final Architecture", "The Rating"):
                heading_html = f'<span class="feat-num">{feat_num:02d}</span> {heading_text}'

            body_parts.append(f'<div class="section">')
            body_parts.append(f'  <h2>{heading_html}</h2>')

            # Release notes
            if section_meta and section_meta.get("docs"):
                links = "\n    ".join(
                    f'<a href="{d["url"]}" target="_blank">{d["label"]}</a>'
                    for d in section_meta["docs"]
                )
                body_parts.append(f'''  <div class="release-notes">
    <div class="rn-label">Read the docs</div>
    <div class="rn-links">
    {links}
    </div>
  </div>''')

            # Video
            if section_meta and section_meta.get("timestamp"):
                ts = section_meta["timestamp"]
                secs = timestamp_to_seconds(ts)
                if youtube_id:
                    body_parts.append(f'''  <div class="video-wrap">
    <iframe src="https://www.youtube.com/embed/{youtube_id}?start={secs}&rel=0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
  </div>''')
                else:
                    body_parts.append(f'''  <div class="video-wrap placeholder" data-start="{secs}">
    <span>&#9654; Watch from <span class="timestamp">{ts}</span></span>
  </div>''')

            current_heading = heading_text
            i += 1
            continue

        if block["type"] == "machine":
            if block.get("is_code"):
                body_parts.append(f'  <div class="architecture">\n    {block["html"]}\n  </div>')
            else:
                body_parts.append(f'  <div class="machine">\n    {block["html"]}\n  </div>')
            i += 1
            continue

        if block["type"] == "human":
            body_parts.append(f'  <div class="human">\n    {block["html"]}\n  </div>')
            i += 1
            continue

        i += 1

    if current_heading:
        body_parts.append("</div>")

    body = "\n\n".join(body_parts)
    body = fix_escaped_html(body)
    return body


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  :root {{
    --bg: #fafafa; --surface: #fff; --border: #e5e5e5;
    --text: #1a1a1a; --text-muted: #717171;
    --accent: #6e56cf; --accent-dim: rgba(110, 86, 207, 0.08);
    --machine-bg: #f5f3ff; --machine-border: #e4dffc; --machine-text: #555;
    --human-text: #1a1a1a;
  }}
  body {{ font-family: 'Inter', -apple-system, sans-serif; background: var(--bg); color: var(--text); line-height: 1.7; -webkit-font-smoothing: antialiased; }}
  .container {{ max-width: 720px; margin: 0 auto; padding: 3rem 1.5rem 6rem; }}
  header {{ margin-bottom: 3rem; padding-bottom: 2rem; border-bottom: 1px solid var(--border); }}
  header h1 {{ font-size: 2rem; font-weight: 700; letter-spacing: -0.03em; margin-bottom: 0.75rem; }}
  header .subtitle {{ color: var(--text-muted); font-size: 0.95rem; }}
  .intro {{ font-size: 1.05rem; margin-bottom: 3rem; padding-bottom: 2rem; border-bottom: 1px solid var(--border); line-height: 1.8; }}
  .intro p + p {{ margin-top: 1rem; }}
  .section {{ margin-bottom: 3rem; }}
  .section h2 {{ font-size: 1.25rem; font-weight: 600; letter-spacing: -0.02em; margin-bottom: 1rem; }}
  .section h2 .feat-num {{ color: var(--accent); font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; font-weight: 500; margin-right: 0.4rem; }}
  .release-notes {{ margin-bottom: 1.25rem; padding: 0.75rem 1rem; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; }}
  .release-notes .rn-label {{ font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem; }}
  .release-notes .rn-label::before {{ content: '\\1F4C4 '; }}
  .release-notes .rn-links {{ display: flex; flex-wrap: wrap; gap: 0.5rem; }}
  .release-notes a {{ font-size: 0.82rem; font-weight: 500; color: var(--accent); text-decoration: none; padding: 0.2em 0.6em; background: var(--accent-dim); border-radius: 4px; transition: background 0.15s; }}
  .release-notes a:hover {{ background: rgba(110, 86, 207, 0.18); text-decoration: underline; }}
  .release-notes a::after {{ content: ' \\2197'; font-size: 0.7em; }}
  .video-wrap {{ position: relative; width: 100%; padding-bottom: 56.25%; margin-bottom: 1.25rem; border-radius: 8px; overflow: hidden; background: #000; }}
  .video-wrap iframe {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none; }}
  .video-wrap.placeholder {{ padding-bottom: 0; height: 56px; background: var(--surface); border: 1px dashed var(--border); display: flex; align-items: center; justify-content: center; cursor: pointer; }}
  .video-wrap.placeholder span {{ font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--text-muted); }}
  .video-wrap.placeholder .timestamp {{ color: var(--accent); font-weight: 500; }}
  .machine {{ position: relative; background: var(--machine-bg); border: 1px solid var(--machine-border); border-radius: 8px; padding: 1.25rem 1.5rem; margin-bottom: 1.25rem; font-size: 0.9rem; color: var(--machine-text); line-height: 1.7; }}
  .machine::before {{ content: 'OPUS'; position: absolute; top: -0.55rem; left: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; font-weight: 500; letter-spacing: 0.12em; color: var(--accent); background: var(--machine-bg); padding: 0 0.5rem; }}
  .machine p + p {{ margin-top: 0.75rem; }}
  .machine strong {{ color: #333; font-weight: 500; }}
  .machine code {{ font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; background: rgba(0,0,0,0.04); padding: 0.15em 0.4em; border-radius: 3px; }}
  .human {{ font-size: 1.05rem; color: var(--human-text); line-height: 1.8; padding: 0 0.25rem; }}
  .human::before {{ content: 'Nick \\2014'; display: block; font-size: 0.8rem; font-weight: 600; color: var(--text-muted); margin-bottom: 0.3rem; }}
  .human strong {{ font-weight: 600; }}
  .architecture {{ background: var(--machine-bg); border: 1px solid var(--machine-border); border-radius: 8px; padding: 1.5rem; position: relative; }}
  .architecture::before {{ content: 'OPUS'; position: absolute; top: -0.55rem; left: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; font-weight: 500; letter-spacing: 0.12em; color: var(--accent); background: var(--machine-bg); padding: 0 0.5rem; }}
  .architecture pre {{ font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: var(--machine-text); line-height: 1.8; overflow-x: auto; white-space: pre; }}
  .architecture pre .arrow {{ color: var(--accent); }}
  hr.divider {{ border: none; border-top: 1px solid var(--border); margin: 2.5rem 0; }}
  footer {{ margin-top: 4rem; padding-top: 2rem; border-top: 1px solid var(--border); text-align: center; color: var(--text-muted); font-size: 0.85rem; }}
  footer a {{ color: var(--accent); text-decoration: none; }}
  footer a:hover {{ text-decoration: underline; }}
  @media (max-width: 600px) {{
    .container {{ padding: 2rem 1rem 4rem; }}
    header h1 {{ font-size: 1.5rem; }}
    .machine {{ padding: 1rem 1.15rem; }}
    .human {{ font-size: 1rem; }}
    .architecture pre {{ font-size: 0.7rem; }}
  }}
</style>
</head>
<body>
<div class="container">
<header>
  <h1>{title}</h1>
  <div class="subtitle">{subtitle}</div>
</header>

{body}

<footer>
  <p>Hated this podcast? Why not replace us with an RSS feed: <a href="https://docs.databricks.com/aws/en/release-notes/">Databricks Release Notes</a></p>
</footer>
</div>
</body>
</html>"""


INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OverArchitected</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Inter', -apple-system, sans-serif; background: #fafafa; color: #1a1a1a; line-height: 1.7; -webkit-font-smoothing: antialiased; }}
  .container {{ max-width: 720px; margin: 0 auto; padding: 3rem 1.5rem 6rem; }}
  h1 {{ font-size: 2rem; font-weight: 700; letter-spacing: -0.03em; margin-bottom: 0.5rem; }}
  .tagline {{ color: #717171; font-size: 0.95rem; margin-bottom: 3rem; padding-bottom: 2rem; border-bottom: 1px solid #e5e5e5; }}
  .episode {{ display: block; padding: 1.25rem 1.5rem; margin-bottom: 1rem; background: #fff; border: 1px solid #e5e5e5; border-radius: 8px; text-decoration: none; color: inherit; transition: border-color 0.15s, box-shadow 0.15s; }}
  .episode:hover {{ border-color: #6e56cf; box-shadow: 0 2px 8px rgba(110, 86, 207, 0.1); }}
  .episode .ep-title {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 0.25rem; }}
  .episode .ep-date {{ font-size: 0.8rem; font-family: 'JetBrains Mono', monospace; color: #6e56cf; }}
</style>
</head>
<body>
<div class="container">
  <h1>OverArchitected</h1>
  <div class="tagline">New Databricks features, shoehorned into one architecture to see if it's actually realistic.</div>
  {episodes}
</div>
</body>
</html>"""


def build():
    DIST_DIR.mkdir(exist_ok=True)

    episode_dirs = sorted(EPISODES_DIR.iterdir())
    index_entries = []

    for ep_dir in episode_dirs:
        md_file = ep_dir / "index.md"
        if not md_file.exists():
            continue

        slug = ep_dir.name  # e.g. "2026-03"
        raw = md_file.read_text()
        meta, body_md = parse_frontmatter(raw)
        blocks = parse_body(body_md)
        body_html = render_episode(meta, blocks)

        page_html = TEMPLATE.format(
            title=meta.get("title", "OverArchitected"),
            subtitle=meta.get("subtitle", ""),
            body=body_html,
        )

        out_dir = DIST_DIR / slug
        out_dir.mkdir(exist_ok=True)
        (out_dir / "index.html").write_text(page_html)
        print(f"  Built {slug}/index.html")

        index_entries.append({
            "slug": slug,
            "title": meta.get("title", slug),
            "date": str(meta.get("date", "")),
        })

    # Build index
    episodes_html = "\n  ".join(
        f'<a class="episode" href="{e["slug"]}/">\n'
        f'    <div class="ep-title">{e["title"]}</div>\n'
        f'    <div class="ep-date">{e["date"]}</div>\n'
        f'  </a>'
        for e in reversed(index_entries)
    )
    index_html = INDEX_TEMPLATE.format(episodes=episodes_html)
    (DIST_DIR / "index.html").write_text(index_html)
    print("  Built index.html")
    print(f"Done. {len(index_entries)} episode(s) in dist/")


if __name__ == "__main__":
    build()
