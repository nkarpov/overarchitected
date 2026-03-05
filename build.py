#!/usr/bin/env python3
"""Build OverArchitected blog from markdown episodes to HTML."""

import os
import re
import shutil
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

    # Build Table of Contents
    toc_items = []
    toc_num = 0
    skip_headings = ("The Thumb Incident", "The Final Architecture", "The Rating")
    for b in blocks:
        if b["type"] == "heading" and b["text"] not in skip_headings:
            toc_num += 1
            sm = build_section_meta(sections, b["text"])
            tag_html = ""
            if sm and sm.get("tag"):
                tag_html = f' <span class="toc-tag">{sm["tag"]}</span>'
            slug = f'section-{toc_num}'
            toc_items.append(f'<a href="#{slug}"><span class="toc-num">{toc_num:02d}</span>{b["text"]}{tag_html}</a>')
    if toc_items:
        body_parts.append('<div class="toc">\n  <div class="toc-title">In this month&#39;s episode</div>\n  ' + '\n  '.join(toc_items) + '\n</div>')

    # Remaining blocks
    toc_feat_num = 0
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
            section_id = ""
            if feat_num > 0 and heading_text not in ("The Thumb Incident", "The Final Architecture", "The Rating"):
                toc_feat_num += 1
                section_id = f' id="section-{toc_feat_num}"'
                tag_html = ""
                if section_meta and section_meta.get("tag"):
                    tag_html = f' <span class="feat-tag">{section_meta["tag"]}</span>'
                heading_html = f'<span class="feat-num">{feat_num:02d}</span> {heading_text}{tag_html}'

            # Add data-start for PiP scroll-seek
            start_attr = ""
            if youtube_id and section_meta and section_meta.get("timestamp"):
                start_attr = f' data-start="{timestamp_to_seconds(section_meta["timestamp"])}"'
            body_parts.append(f'<div class="section"{start_attr}{section_id}>')
            body_parts.append(f'  <h2>{heading_html}</h2>')

            # Release notes - stored for inclusion inside machine block
            release_notes_html = ""
            if section_meta and section_meta.get("docs"):
                links = "\n      ".join(
                    f'<a href="{d["url"]}" target="_blank">{d["label"]}</a>'
                    for d in section_meta["docs"]
                )
                release_notes_html = f'''\n    <div class="release-notes-inner">
      <div class="rn-label">📄 Read the docs</div>
      <div class="rn-links">
      {links}
      </div>
    </div>'''

            # Video — only show inline placeholders when no youtube_id (PiP handles it otherwise)
            if not youtube_id and section_meta and section_meta.get("timestamp"):
                ts = section_meta["timestamp"]
                secs = timestamp_to_seconds(ts)
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
                body_parts.append(f'  <div class="machine">\n    {block["html"]}{release_notes_html}\n  </div>')
                release_notes_html = ""  # only attach to first machine block per section
            i += 1
            continue

        if block["type"] == "human":
            body_parts.append(f'  <div class="human">\n    <div class="human-label"><img src="/images/nick_LI.jpeg" alt="Nick"> Director\'s Commentary (Nick)</div>\n    {block["html"]}\n  </div>')
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
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,400;0,500;0,700;1,400&family=JetBrains+Mono:wght@400;500&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  :root {{
    --bg: #F9F7F4; --surface: #fff; --border: #e0ddd8;
    --text: #0B2026; --text-muted: #5a6670;
    --accent: #EB1600; --accent-dim: rgba(235, 22, 0, 0.06);
    --accent-cyan: #40d1f5; --accent-blue: #4462c9;
    --machine-bg: #eef1f8; --machine-border: #d4dbe8; --machine-text: #4a5568;
    --human-text: #0B2026;
    --radius: 4px;
  }}
  html {{ font-size: 110%; }}
  body {{ font-family: 'DM Sans', Arial, sans-serif; background: var(--bg); color: var(--text); line-height: 1.7; -webkit-font-smoothing: antialiased; }}
  .container {{ max-width: 720px; margin: 0 auto; padding: 3rem 1.5rem 6rem; }}
  header {{ margin-bottom: 3rem; padding-bottom: 2rem; border-bottom: 1px solid var(--border); }}
  header h1 {{ font-size: 2rem; font-weight: 700; letter-spacing: -0.03em; margin-bottom: 0.75rem; }}
  header .subtitle {{ color: var(--text-muted); font-size: 0.95rem; }}
  .intro {{ font-size: 1.05rem; margin-bottom: 3rem; padding-bottom: 2rem; border-bottom: 1px solid var(--border); line-height: 1.8; }}
  .info-callout {{ background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 0.85rem 1.15rem; margin-bottom: 2.5rem; font-size: 0.85rem; color: var(--text-muted); line-height: 1.65; }}
  .info-callout strong {{ color: var(--text); font-weight: 600; }}
  .intro p + p {{ margin-top: 1rem; }}
  .toc {{ margin-bottom: 2.5rem; padding-bottom: 2rem; border-bottom: 1px solid var(--border); }}
  .toc-title {{ font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.6rem; }}
  .toc a {{ display: block; font-size: 0.88rem; color: var(--text); text-decoration: none; padding: 0.25rem 0; transition: color 0.15s; }}
  .toc a:hover {{ color: var(--accent); }}
  .toc .toc-num {{ color: var(--accent); font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; font-weight: 500; margin-right: 0.35rem; }}
  .toc .toc-tag {{ font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; font-weight: 500; color: var(--text-muted); background: var(--surface); border: 1px solid var(--border); padding: 0.1em 0.45em; border-radius: 3px; margin-left: 0.4rem; vertical-align: 1px; }}
  .section {{ margin-bottom: 3rem; }}
  .feat-tag {{ font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; font-weight: 500; color: var(--surface); background: var(--accent); padding: 0.15em 0.5em; border-radius: 3px; margin-left: 0.5rem; vertical-align: 2px; }}
  .section h2 {{ font-size: 1.25rem; font-weight: 600; letter-spacing: -0.02em; margin-bottom: 1rem; }}
  .section h2 .feat-num {{ color: var(--accent); font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; font-weight: 500; margin-right: 0.4rem; }}
  .release-notes {{ margin-bottom: 1.25rem; padding: 0.75rem 1rem; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); }}
  .release-notes .rn-label {{ font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem; }}
  .release-notes .rn-label::before {{ content: '\\1F4C4 '; }}
  .release-notes .rn-links {{ display: flex; flex-wrap: wrap; gap: 0.5rem; }}
  .release-notes a {{ font-size: 0.82rem; font-weight: 500; color: var(--accent-blue); text-decoration: none; padding: 0.2em 0.6em; background: var(--accent-dim); border-radius: 4px; transition: background 0.15s; }}
  .release-notes a:hover {{ background: rgba(68, 98, 201, 0.14); text-decoration: underline; }}
  .release-notes a::after {{ content: ' \\2197'; font-size: 0.7em; }}
  .video-wrap.placeholder {{ height: 56px; background: var(--surface); border: 1px dashed var(--border); border-radius: var(--radius); display: flex; align-items: center; justify-content: center; margin-bottom: 1.25rem; }}
  .video-wrap.placeholder span {{ font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: var(--text-muted); }}
  .video-wrap.placeholder .timestamp {{ color: var(--accent); font-weight: 500; }}
  .machine {{ position: relative; background: var(--machine-bg); border: 1px solid var(--machine-border); border-radius: var(--radius); padding: 1.25rem 1.5rem; margin-bottom: 1.25rem; font-size: 0.9rem; color: var(--machine-text); line-height: 1.7; }}
  .machine::before {{ content: 'CLAUDE OPUS 4.6'; position: absolute; top: -0.65rem; left: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; font-weight: 500; letter-spacing: 0.1em; color: var(--accent); background: var(--bg); border: 1px solid var(--machine-border); padding: 0.15rem 0.6rem; border-radius: 99px; }}
  .machine p + p {{ margin-top: 0.75rem; }}
  .release-notes-inner {{ margin-top: 1rem; padding-top: 0.85rem; border-top: 1px solid var(--machine-border); }}
  .release-notes-inner .rn-label {{ font-size: 0.7rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.35rem; }}
  .release-notes-inner .rn-label {{ font-size: 0.7rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.35rem; }}
  .release-notes-inner .rn-links {{ display: flex; flex-wrap: wrap; gap: 0.4rem; }}
  .release-notes-inner a {{ font-size: 0.78rem; font-weight: 500; color: var(--accent-blue); text-decoration: none; padding: 0.15em 0.5em; background: rgba(68, 98, 201, 0.08); border-radius: 3px; transition: background 0.15s; }}
  .release-notes-inner a:hover {{ background: rgba(68, 98, 201, 0.16); text-decoration: underline; }}
  .release-notes-inner a::after {{ content: " ↗"; font-size: 0.65em; }}
  .machine strong {{ color: #2a3a3f; font-weight: 500; font-size: 0.92rem; }}
  .machine p > strong:first-child {{ color: #0B2026; font-weight: 700; }}
  .machine code {{ font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; background: rgba(0,0,0,0.04); padding: 0.15em 0.4em; border-radius: 3px; }}
  .human {{ font-size: 1.05rem; color: var(--human-text); line-height: 1.8; padding: 0 0.25rem; }}
  .human-label {{ display: flex; align-items: center; gap: 0.4rem; font-size: 0.8rem; font-weight: 600; color: var(--text-muted); margin-bottom: 0.3rem; }}
  .human-label img {{ width: 24px; height: 24px; border-radius: 50%; object-fit: cover; }}
  .human strong {{ font-weight: 600; }}
  .architecture {{ background: var(--machine-bg); border: 1px solid var(--machine-border); border-radius: var(--radius); padding: 1.5rem; position: relative; }}
  .architecture::before {{ content: 'CLAUDE OPUS 4.6'; position: absolute; top: -0.65rem; left: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; font-weight: 500; letter-spacing: 0.1em; color: var(--accent); background: var(--bg); border: 1px solid var(--machine-border); padding: 0.15rem 0.6rem; border-radius: 99px; }}
  .architecture pre {{ font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: var(--machine-text); line-height: 1.8; overflow-x: auto; white-space: pre; }}
  .architecture pre .arrow {{ color: var(--accent); }}
  hr.divider {{ border: none; border-top: 1px solid var(--border); margin: 2.5rem 0; }}
  .ep-nav {{ display: flex; justify-content: space-between; align-items: center; margin-top: 3rem; padding-top: 2rem; border-top: 1px solid var(--border); font-size: 0.85rem; }}
  .ep-nav a {{ color: var(--text-muted); text-decoration: none; transition: color 0.15s; }}
  .ep-nav a:hover {{ color: var(--accent); }}
  .ep-nav .ep-nav-label {{ font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; display: block; margin-bottom: 0.15rem; }}
  footer {{ margin-top: 4rem; padding-top: 2rem; border-top: 1px solid var(--border); text-align: center; color: var(--text-muted); font-size: 0.85rem; }}
  footer a {{ color: var(--accent); text-decoration: none; }}
  footer a:hover {{ text-decoration: underline; }}

  /* Sidebar video layout (wide screens) */
  .layout {{ display: flex; justify-content: center; gap: 3rem; max-width: 1400px; margin: 0 auto; padding: 0 1.5rem; }}
  .layout .container {{ padding-left: 0; padding-right: 0; margin: 0; flex: 1; min-width: 0; }}
  
  .video-sidebar {{ width: 520px; flex-shrink: 0; }}
  .video-sidebar .video-sticky {{ position: sticky; top: calc(50vh - 150px); width: 100%; }}
  .video-sidebar .video-frame {{ position: relative; width: 100%; padding-bottom: 56.25%; background: #000; border-radius: var(--radius) var(--radius) 0 0; overflow: hidden; }}
  .video-sidebar .video-frame iframe {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none; }}
  .video-sidebar .video-bar {{ display: flex; align-items: center; justify-content: space-between; padding: 0.5rem 0.6rem; background: var(--text); border-radius: 0 0 var(--radius) var(--radius); }}
  .video-sidebar .vs-section {{ font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: #fff; opacity: 0.7; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; margin-right: 0.5rem; }}
  .video-sidebar .vs-controls {{ display: flex; gap: 0.35rem; flex-shrink: 0; }}
  .video-sidebar .vs-btn {{ background: none; border: none; color: #fff; opacity: 0.6; cursor: pointer; font-size: 0.85rem; padding: 0.1rem 0.3rem; line-height: 1; transition: opacity 0.15s; }}
  .video-sidebar .vs-btn:hover {{ opacity: 1; }}
  .vs-nav {{ display: flex; align-items: center; justify-content: center; width: 36px; height: 36px; margin: 0.4rem auto; background: none; border: none; color: var(--text-muted); cursor: pointer; transition: color 0.15s, opacity 0.15s; opacity: 0; pointer-events: none; }}
  .vs-nav.visible {{ opacity: 0.5; pointer-events: auto; }}
  .vs-nav:hover {{ opacity: 1; color: var(--accent); }}

  @media (max-width: 1100px) {{
    .layout {{ display: block; padding: 0; }}
    .layout .container {{ padding: 3rem 1.5rem 6rem; max-width: 720px; margin: 0 auto; }}
    .video-sidebar {{ display: none; }}
  }}
  @media (min-width: 1101px) {{
    .pip:not(.detached) {{ display: none !important; }}
    .pip-toggle:not(.detached) {{ display: none !important; }}
  }}

  @keyframes pip-shake {{
    0%, 100% {{ transform: translateX(0); }}
    15% {{ transform: translateX(-6px) rotate(-2deg); }}
    30% {{ transform: translateX(5px) rotate(1.5deg); }}
    45% {{ transform: translateX(-4px) rotate(-1deg); }}
    60% {{ transform: translateX(3px) rotate(0.5deg); }}
    75% {{ transform: translateX(-2px); }}
  }}
  .pip.shake {{ animation: pip-shake 0.5s ease; }}
  .video-sticky.shake {{ animation: pip-shake 0.5s ease; }}

  /* PiP Video Player */
  .pip {{ position: fixed; bottom: 1.5rem; right: 1.5rem; z-index: 1000; width: 360px; min-width: 260px; max-width: 640px; background: #000; border-radius: var(--radius); overflow: hidden; box-shadow: 0 8px 32px rgba(0,0,0,0.25); transition: opacity 0.3s, transform 0.3s; }}
  .pip.dragging {{ transition: none; user-select: none; }}
  .pip.hidden {{ opacity: 0; transform: translateY(1rem); pointer-events: none; }}
  .pip-header {{ display: flex; align-items: center; justify-content: space-between; padding: 0.4rem 0.75rem; background: var(--text); cursor: grab; }}
  .pip-header:active {{ cursor: grabbing; }}
  .pip-resize {{ position: absolute; top: 0; left: 0; width: 20px; height: 20px; cursor: nw-resize; z-index: 4; }}
  .pip-resize::after {{ content: ''; position: absolute; top: 4px; left: 4px; width: 8px; height: 8px; border-top: 2px solid rgba(255,255,255,0.25); border-left: 2px solid rgba(255,255,255,0.25); }}
  .pip-section {{ font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: #fff; opacity: 0.7; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; margin-right: 0.5rem; }}
  .pip-controls {{ display: flex; gap: 0.35rem; flex-shrink: 0; }}
  .pip-btn {{ background: none; border: none; color: #fff; opacity: 0.6; cursor: pointer; font-size: 0.85rem; padding: 0.1rem 0.3rem; line-height: 1; transition: opacity 0.15s; }}
  .pip-btn:hover {{ opacity: 1; }}
  .pip-video {{ position: relative; width: 100%; padding-bottom: 56.25%; }}
  .pip-video iframe {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none; }}
  .pip-toggle {{ position: fixed; bottom: 1.5rem; right: 1.5rem; z-index: 999; width: 48px; height: 48px; border-radius: 50%; background: var(--accent); color: #fff; border: none; cursor: pointer; font-size: 1.2rem; box-shadow: 0 4px 16px rgba(0,0,0,0.15); display: none; transition: transform 0.15s; }}
  .pip-toggle:hover {{ transform: scale(1.1); }}

  @media (max-width: 600px) {{
    .container {{ padding: 2rem 1rem 4rem; }}
    header h1 {{ font-size: 1.5rem; }}
    .machine {{ padding: 1rem 1.15rem; }}
    .human {{ font-size: 1rem; }}
    .architecture pre {{ font-size: 0.7rem; }}
    .pip {{ width: 65vw; min-width: 160px; }}
    .pip-toggle {{ bottom: 0.75rem; right: 0.75rem; width: 40px; height: 40px; font-size: 1rem; }}
  }}
</style>
</head>
<body>
<div class="layout">
<div class="container">
<header>
  <h1><a href="/" style="color:inherit;text-decoration:none;">{title}</a></h1>
  <div class="subtitle">{subtitle}</div>
</header>

<div class="info-callout">
  <strong>Welcome to OverArchitected with Nick &amp; Holly &mdash; web edition!</strong>
  <br><br>
  Every month we pick our favorite Databricks features and try to shoehorn them into one architecture. This page recaps each feature we covered &mdash; with the <a href="#" id="pip-shake-trigger" style="color:var(--accent);text-decoration:none;font-weight:600;">episode video &#x2198;</a> queued up to jump between sections as you scroll.
  <br><br>
  For the web edition, each feature summary is augmented by <strong>Claude Opus 4.6</strong> from the raw episode transcript, and each one is followed by unfiltered <strong>Director&rsquo;s Commentary</strong>.
</div>

{body}

{ep_nav}

<footer>
  <p>Hated this podcast? Why not replace us with an RSS feed: <a href="https://docs.databricks.com/aws/en/release-notes/">Databricks Release Notes</a></p>
</footer>
</div>

{video_sidebar}
</div>

{pip_block}
</body>
</html>"""


PIP_BLOCK = """<!-- PiP Video Player -->
<div class="pip hidden" id="pip">
  <div class="pip-resize" id="pip-resize"></div>
  <div class="pip-header" id="pip-drag">
    <span class="pip-section" id="pip-section">Loading...</span>
    <div class="pip-controls">
      <button class="pip-btn" id="pip-mute" title="Unmute">&#128263;</button>
      <button class="pip-btn" id="pip-playpause" title="Play/Pause">&#9654;</button>
      <button class="pip-btn pip-size-toggle" id="pip-size-toggle" title="Toggle size" style="display:none;">&#8596;</button>
      <button class="pip-btn" id="pip-dock" title="Dock to sidebar" style="display:none;">&#x2926;</button>
      <button class="pip-btn" id="pip-close" title="Minimize">&times;</button>
    </div>
  </div>
  <div class="pip-video">
    <div id="pip-player"></div>
  </div>
</div>
<button class="pip-toggle" id="pip-reopen" title="Show video">&#9654;</button>

<script>
var tag = document.createElement('script');
tag.src = 'https://www.youtube.com/iframe_api';
document.head.appendChild(tag);

var PAD = 24;
var player, sidebarPlayer, activePlayer, isReady = false, currentStart = 0;
var isWide = window.innerWidth > 1100;
var sidebarMode = isWide;
var pip = document.getElementById('pip');
var pipSection = document.getElementById('pip-section');
var pipPlaypause = document.getElementById('pip-playpause');
var pipMute = document.getElementById('pip-mute');
var pipClose = document.getElementById('pip-close');
var pipReopen = document.getElementById('pip-reopen');
var pipDrag = document.getElementById('pip-drag');
var pipResize = document.getElementById('pip-resize');
var pipSizeToggle = document.getElementById('pip-size-toggle');
var DRAG_THRESHOLD = 5; // px movement before it counts as drag vs click

var overlay = document.createElement('div');
overlay.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;z-index:3;';
pip.appendChild(overlay);

function isMobile() {{ return window.innerWidth <= 600; }}

function clamp(x, y, w) {{
  var h = pip.offsetHeight;
  x = Math.max(PAD, Math.min(window.innerWidth - w - PAD, x));
  y = Math.max(PAD, Math.min(window.innerHeight - h - PAD, y));
  return [x, y];
}}

function applyPos(x, y) {{
  var c = clamp(x, y, pip.offsetWidth);
  pip.style.left = c[0] + 'px';
  pip.style.top = c[1] + 'px';
}}

var vsSection = document.getElementById('vs-section');
var vsMute = document.getElementById('vs-mute');
var vsPlaypause = document.getElementById('vs-playpause');
var vsDetach = document.getElementById('vs-detach');

function makePlayerOpts(elId) {{
  return {{
    videoId: '{youtube_id}',
    playerVars: {{ rel: 0, modestbranding: 1, playsinline: 1, autoplay: 1, mute: 1 }},
    events: {{
      onReady: function(event) {{
        isReady = true;
        var thisPlayer = event.target;
        if (sidebarMode && thisPlayer === sidebarPlayer) {{
          activePlayer = sidebarPlayer;
          activePlayer.playVideo();
        }} else if (!sidebarMode && thisPlayer === player) {{
          activePlayer = player;
          pip.classList.remove('hidden');
          document.body.classList.add('pip-visible');
          if (isMobile()) {{ pipSizeToggle.style.display = 'inline'; pipResize.style.display = 'none'; }}
    if (pipDock) pipDock.style.display = (window.innerWidth > 1100) ? 'inline' : 'none';
          setTimeout(function() {{ switchToAbsolute(); applyPos(parseFloat(pip.style.left), parseFloat(pip.style.top)); }}, 50);
          activePlayer.playVideo();
        }}
      }},
      onStateChange: function(e) {{
        var icon = (e.data === YT.PlayerState.PLAYING) ? '\u23F8' : '\u25B6';
        pipPlaypause.innerHTML = icon;
        if (vsPlaypause) vsPlaypause.innerHTML = icon;
      }}
    }}
  }};
}}

function onYouTubeIframeAPIReady() {{
  if (document.getElementById('sidebar-player')) {{
    sidebarPlayer = new YT.Player('sidebar-player', makePlayerOpts('sidebar-player'));
  }}
  if (document.getElementById('pip-player')) {{
    player = new YT.Player('pip-player', makePlayerOpts('pip-player'));
  }}
  activePlayer = sidebarMode ? sidebarPlayer : player;
}}

function togglePlay() {{
  if (!isReady || !activePlayer) return;
  if (activePlayer.getPlayerState() === YT.PlayerState.PLAYING) activePlayer.pauseVideo();
  else activePlayer.playVideo();
}}
pipPlaypause.addEventListener('click', togglePlay);
if (vsPlaypause) vsPlaypause.addEventListener('click', togglePlay);

function toggleMute() {{
  if (!isReady || !activePlayer) return;
  if (activePlayer.isMuted()) {{
    activePlayer.unMute();
    activePlayer.setVolume(80);
    pipMute.innerHTML = '&#128266;';
    if (vsMute) vsMute.innerHTML = '&#128266;';
  }} else {{
    activePlayer.mute();
    pipMute.innerHTML = '&#128265;';
    if (vsMute) vsMute.innerHTML = '&#128265;';
  }}
}}
pipMute.addEventListener('click', toggleMute);
if (vsMute) vsMute.addEventListener('click', toggleMute);

pipClose.addEventListener('click', function() {{
  pip.classList.add('hidden');
  document.body.classList.remove('pip-visible');
  pipReopen.style.display = 'block';
  if (isReady && activePlayer) activePlayer.pauseVideo();
}});

pipReopen.addEventListener('click', function() {{
  pip.classList.remove('hidden');
  document.body.classList.add('pip-visible');
  pipReopen.style.display = 'none';
}});

// --- Mobile size toggle (65% <-> 95%) ---
var mobileSmall = true;
pipSizeToggle.addEventListener('click', function() {{
  mobileSmall = !mobileSmall;
  var w = mobileSmall ? 0.65 : 1.0;
  if (!mobileSmall) {{ pip.style.width = (window.innerWidth - PAD * 2) + 'px'; var rect = pip.getBoundingClientRect(); applyPos(rect.left, rect.top); return; }}
  pip.style.width = (window.innerWidth * w) + 'px';
  var rect = pip.getBoundingClientRect();
  applyPos(rect.left, rect.top);
}});

// --- Switch to absolute positioning ---
function switchToAbsolute() {{
  var rect = pip.getBoundingClientRect();
  pip.style.left = rect.left + 'px';
  pip.style.top = rect.top + 'px';
  pip.style.right = 'auto';
  pip.style.bottom = 'auto';
}}

// --- DRAG with velocity tracking ---
var isDragging = false, dragX, dragY;
var velX = 0, velY = 0, lastMoveX = 0, lastMoveY = 0, lastMoveTime = 0;

function onDragStart(cx, cy) {{
  isDragging = true;
  pip.classList.add('dragging');
  // overlay active
  var rect = pip.getBoundingClientRect();
  dragX = cx - rect.left;
  dragY = cy - rect.top;
  velX = 0; velY = 0;
  lastMoveX = cx; lastMoveY = cy;
  lastMoveTime = Date.now();
  switchToAbsolute();
  cancelMomentum();
}}

function onDragMove(cx, cy) {{
  if (!isDragging) return;
  var now = Date.now();
  var dt = Math.max(1, now - lastMoveTime);
  velX = (cx - lastMoveX) / dt * 16; // normalize to ~frame
  velY = (cy - lastMoveY) / dt * 16;
  lastMoveX = cx; lastMoveY = cy;
  lastMoveTime = now;
  applyPos(cx - dragX, cy - dragY);
}}

var momentumId = null;
function cancelMomentum() {{
  if (momentumId) {{ cancelAnimationFrame(momentumId); momentumId = null; }}
}}

function onDragEnd() {{
  if (!isDragging) return;
  isDragging = false;
  pip.classList.remove('dragging');
  // overlay active

  // If velocity is meaningful, start momentum
  var speed = Math.sqrt(velX * velX + velY * velY);
  if (speed > 2) {{
    startMomentum();
  }}
}}

function startMomentum() {{
  var friction = 0.92;
  var bounce = -0.5;
  var x = parseFloat(pip.style.left);
  var y = parseFloat(pip.style.top);
  var w = pip.offsetWidth;
  var h = pip.offsetHeight;

  function frame() {{
    velX *= friction;
    velY *= friction;

    x += velX;
    y += velY;

    // Bounce off edges
    if (x < PAD) {{ x = PAD; velX *= bounce; }}
    if (x > window.innerWidth - w - PAD) {{ x = window.innerWidth - w - PAD; velX *= bounce; }}
    if (y < PAD) {{ y = PAD; velY *= bounce; }}
    if (y > window.innerHeight - h - PAD) {{ y = window.innerHeight - h - PAD; velY *= bounce; }}

    pip.style.left = x + 'px';
    pip.style.top = y + 'px';

    if (Math.abs(velX) > 0.3 || Math.abs(velY) > 0.3) {{
      momentumId = requestAnimationFrame(frame);
    }} else {{
      momentumId = null;
    }}
  }}
  cancelMomentum();
  momentumId = requestAnimationFrame(frame);
}}

// Mouse
pipDrag.addEventListener('mousedown', function(e) {{
  if (e.target.closest('.pip-btn')) return;
  e.preventDefault();
  onDragStart(e.clientX, e.clientY);
}});
document.addEventListener('mousemove', function(e) {{ onDragMove(e.clientX, e.clientY); }});
document.addEventListener('mouseup', onDragEnd);

// Touch
pipDrag.addEventListener('touchstart', function(e) {{
  if (e.target.closest('.pip-btn')) return;
  e.preventDefault();
  var t = e.touches[0];
  if (isMobile()) pip.style.width = pip.getBoundingClientRect().width + 'px';
  onDragStart(t.clientX, t.clientY);
}});
document.addEventListener('touchmove', function(e) {{
  if (isDragging) {{ var t = e.touches[0]; onDragMove(t.clientX, t.clientY); }}
}});
document.addEventListener('touchend', onDragEnd);

// --- VIDEO AREA: drag vs click-through ---
var overlayStartX, overlayStartY, overlayMoved;

overlay.addEventListener('mousedown', function(e) {{
  e.preventDefault();
  overlayStartX = e.clientX;
  overlayStartY = e.clientY;
  overlayMoved = false;
  onDragStart(e.clientX, e.clientY);
}});

overlay.addEventListener('mousemove', function(e) {{
  if (!isDragging) return;
  var dx = e.clientX - overlayStartX;
  var dy = e.clientY - overlayStartY;
  if (Math.sqrt(dx*dx + dy*dy) > DRAG_THRESHOLD) overlayMoved = true;
}});

overlay.addEventListener('mouseup', function(e) {{
  if (!overlayMoved) {{
    // It was a click, not a drag — pass through to YouTube
    onDragEnd();
    overlay.style.pointerEvents = 'none';
    var el = document.elementFromPoint(e.clientX, e.clientY);
    if (el) el.click();
    setTimeout(function() {{ overlay.style.pointerEvents = ''; }}, 100);
  }}
}});

overlay.addEventListener('touchstart', function(e) {{
  var t = e.touches[0];
  overlayStartX = t.clientX;
  overlayStartY = t.clientY;
  overlayMoved = false;
  if (isMobile()) pip.style.width = pip.getBoundingClientRect().width + 'px';
  onDragStart(t.clientX, t.clientY);
}}, {{ passive: false }});

overlay.addEventListener('touchmove', function(e) {{
  if (!isDragging) return;
  var t = e.touches[0];
  var dx = t.clientX - overlayStartX;
  var dy = t.clientY - overlayStartY;
  if (Math.sqrt(dx*dx + dy*dy) > DRAG_THRESHOLD) {{ overlayMoved = true; e.preventDefault(); }}
  onDragMove(t.clientX, t.clientY);
}}, {{ passive: false }});

overlay.addEventListener('touchend', function(e) {{
  if (!overlayMoved) {{
    // Tap, not drag — pass through
    onDragEnd();
    overlay.style.pointerEvents = 'none';
    var el = document.elementFromPoint(overlayStartX, overlayStartY);
    if (el) el.click();
    setTimeout(function() {{ overlay.style.pointerEvents = ''; }}, 300);
  }} else {{
    onDragEnd();
  }}
}});

// --- RESIZE (desktop only) ---
var isResizing = false, resStartX, resStartY, resStartW, resStartRect;

pipResize.addEventListener('mousedown', function(e) {{
  if (isMobile()) return;
  e.preventDefault();
  e.stopPropagation();
  isResizing = true;
  pip.classList.add('dragging');
  // overlay active
  switchToAbsolute();
  resStartX = e.clientX;
  resStartY = e.clientY;
  resStartW = pip.offsetWidth;
  resStartRect = pip.getBoundingClientRect();
}});

document.addEventListener('mousemove', function(e) {{
  if (!isResizing) return;
  var rect = resStartRect;
  var cx = rect.left + rect.width / 2;
  var cy = rect.top + rect.height / 2;
  var anchorRight = cx > window.innerWidth / 2;
  var anchorBottom = cy > window.innerHeight / 2;

  var dx = e.clientX - resStartX;
  var dy = e.clientY - resStartY;
  var delta = Math.abs(dx) > Math.abs(dy) ? dx : dy * (16/9);
  var sign = (anchorRight || anchorBottom) ? -1 : 1;
  var newW = Math.max(260, Math.min(640, resStartW + delta * sign));

  pip.style.width = newW + 'px';

  var newLeft = anchorRight ? (rect.right - newW) : rect.left;
  var newTop = rect.top;
  if (anchorBottom) {{
    var newH = newW * 9 / 16 + 30;
    newTop = rect.bottom - newH;
  }}
  var c = clamp(newLeft, newTop, newW);
  pip.style.left = c[0] + 'px';
  pip.style.top = c[1] + 'px';
}});

document.addEventListener('mouseup', function() {{
  if (isResizing) {{
    isResizing = false;
    pip.classList.remove('dragging');
    // overlay active
  }}
}});

// --- Handle breakpoint crossing ---
var lastWasWide = isWide;
function checkBreakpoint() {{
  var nowWide = window.innerWidth > 1100;
  if (nowWide === lastWasWide) return;
  lastWasWide = nowWide;
  if (nowWide && !sidebarMode) return; // was detached, stay in PiP
  if (!nowWide) {{
    // Went narrow — activate PiP
    pip.classList.remove('hidden');
    document.body.classList.add('pip-visible');
    if (isMobile()) {{ pipSizeToggle.style.display = 'inline'; pipResize.style.display = 'none'; }}
    if (pipDock) pipDock.style.display = (window.innerWidth > 1100) ? 'inline' : 'none';
    // Sync time from sidebar
    if (player && sidebarPlayer && sidebarPlayer.getCurrentTime) {{
      var t = sidebarPlayer.getCurrentTime();
      var wasMuted = sidebarPlayer.isMuted();
      sidebarPlayer.pauseVideo();
      player.seekTo(t, true);
      player.playVideo();
      if (!wasMuted) {{ player.unMute(); player.setVolume(80); }}
    }}
    activePlayer = player;
    setTimeout(function() {{ switchToAbsolute(); applyPos(parseFloat(pip.style.left), parseFloat(pip.style.top)); }}, 50);
  }} else {{
    // Went wide — activate sidebar
    pip.classList.add('hidden');
    document.body.classList.remove('pip-visible');
    if (sidebarPlayer) {{
      if (player && player.getCurrentTime) {{
        var t = player.getCurrentTime();
        sidebarPlayer.seekTo(t, true);
        sidebarPlayer.playVideo();
        if (player && !player.isMuted()) {{ sidebarPlayer.unMute(); sidebarPlayer.setVolume(80); }}
      }}
      activePlayer = sidebarPlayer;
      sidebarMode = true;
    }}
  }}
}}

// --- Keep pip in viewport on window resize ---
window.addEventListener('resize', function() {{
  checkBreakpoint();
  if (pip.classList.contains('hidden') || pip.style.right !== 'auto') return;
  // Mobile size toggle visibility
  if (isMobile()) {{ pipSizeToggle.style.display = 'inline'; pipResize.style.display = 'none'; }}
    if (pipDock) pipDock.style.display = (window.innerWidth > 1100) ? 'inline' : 'none';
  else {{ pipSizeToggle.style.display = 'none'; pipResize.style.display = ''; }}
  var w = pip.offsetWidth;
  var maxW = window.innerWidth - PAD * 2;
  if (w > maxW) {{ w = Math.max(160, maxW); pip.style.width = w + 'px'; }}
  var rect = pip.getBoundingClientRect();
  applyPos(rect.left, rect.top);
}});

// --- Dock: PiP -> sidebar ---
var pipDock = document.getElementById('pip-dock');
if (pipDock) {{
  // Show dock button only on wide screens
  if (isWide) pipDock.style.display = 'inline';
  pipDock.addEventListener('click', function() {{
    if (!sidebarPlayer) return;
    // Sync time to sidebar
    var t = player ? player.getCurrentTime() : 0;
    var wasMuted = player ? player.isMuted() : true;
    if (player) player.pauseVideo();
    
    sidebarPlayer.seekTo(t, true);
    sidebarPlayer.playVideo();
    if (!wasMuted) {{ sidebarPlayer.unMute(); sidebarPlayer.setVolume(80); }}
    
    activePlayer = sidebarPlayer;
    sidebarMode = true;
    
    // Hide PiP, show sidebar
    pip.classList.add('hidden');
    pip.classList.remove('detached');
    document.body.classList.remove('pip-visible');
    var sb = document.querySelector('.video-sidebar');
    if (sb) sb.style.display = '';
  }});
}}

// --- Detach: sidebar -> PiP ---
if (vsDetach) vsDetach.addEventListener('click', function() {{
  sidebarMode = false;
  // Create PiP player if it doesn't exist
  if (!player) {{
    player = new YT.Player('pip-player', makePlayerOpts('pip-player'));
  }}
  // Sync time
  var t = sidebarPlayer ? sidebarPlayer.getCurrentTime() : 0;
  var wasMuted = sidebarPlayer ? sidebarPlayer.isMuted() : true;
  if (sidebarPlayer) sidebarPlayer.pauseVideo();

  // Show PiP
  pip.classList.add('detached');
  pip.classList.remove('hidden');
  document.body.classList.add('pip-visible');
  setTimeout(function() {{
    switchToAbsolute();
    applyPos(parseFloat(pip.style.left), parseFloat(pip.style.top));
    if (player && player.seekTo) {{
      player.seekTo(t, true);
      player.playVideo();
      if (!wasMuted) {{ player.unMute(); player.setVolume(80); }}
    }}
    activePlayer = player;
  }}, 500);

  // Hide sidebar
  var sb = document.querySelector('.video-sidebar');
  if (sb) sb.style.display = 'none';
}});

// --- Smooth scroll ToC to center sections ---
document.querySelectorAll('.toc a[href^="#"]').forEach(function(link) {{
  link.addEventListener('click', function(e) {{
    e.preventDefault();
    var target = document.querySelector(this.getAttribute('href'));
    if (!target) return;
    var rect = target.getBoundingClientRect();
    var offset = window.pageYOffset + rect.top - (window.innerHeight / 2) + (rect.height / 2);
    window.scrollTo({{ top: Math.max(0, offset), behavior: 'smooth' }});
  }});
}});

// --- Shake the PiP to draw attention ---
document.addEventListener('click', function(e) {{
  var link = e.target.closest('#pip-shake-trigger');
  if (link) {{
    e.preventDefault();
    var target;
    if (sidebarMode) {{
      target = document.querySelector('.video-sticky');
    }} else {{
      target = pip;
      if (pip.classList.contains('hidden')) {{
        pip.classList.remove('hidden');
        document.body.classList.add('pip-visible');
        pipReopen.style.display = 'none';
      }}
    }}
    if (target) {{
      target.classList.remove('shake');
      void target.offsetWidth;
      target.classList.add('shake');
      setTimeout(function() {{ target.classList.remove('shake'); }}, 600);
    }}
  }}
}});

// --- Scroll-seek ---
var sections = document.querySelectorAll('.section[data-start]');
var observer = new IntersectionObserver(function(entries) {{
  entries.forEach(function(entry) {{
    if (entry.isIntersecting) {{
      var start = parseInt(entry.target.dataset.start);
      var heading = entry.target.querySelector('h2');
      if (heading && isReady && start !== currentStart && !videoScrolling) {{
        currentStart = start;
        if (activePlayer) activePlayer.seekTo(start, true);
        var stext = heading.textContent.replace(/^\d{{2}}\s*/, '');
        pipSection.textContent = stext;
        if (vsSection) vsSection.textContent = stext;
      }}
    }}
  }});
}}, {{ rootMargin: '-20% 0px -60% 0px', threshold: 0 }});

sections.forEach(function(s) {{ observer.observe(s); }});

// --- Reverse sync: video progress scrolls the page ---
var videoScrolling = false; // flag to prevent feedback loop
var reverseStart = -1;

// Build sorted list of section timestamps
var sectionList = [];
sections.forEach(function(s) {{
  sectionList.push({{ el: s, start: parseInt(s.dataset.start) }});
}});
sectionList.sort(function(a, b) {{ return a.start - b.start; }});

// Override observer to skip when video is driving the scroll
var origObserverCallback = observer;
// Actually, just use the videoScrolling flag in the existing observer
// Patch: wrap the seek call to check flag

setInterval(function() {{
  if (!isReady || !activePlayer || !activePlayer.getCurrentTime) return;
  if (isDragging || isResizing) return;
  var state = activePlayer.getPlayerState();
  if (state !== YT.PlayerState.PLAYING) return;

  var t = activePlayer.getCurrentTime();
  // Find which section we're in
  var targetSection = null;
  for (var j = sectionList.length - 1; j >= 0; j--) {{
    if (t >= sectionList[j].start) {{
      targetSection = sectionList[j];
      break;
    }}
  }}
  if (!targetSection || targetSection.start === reverseStart) return;
  reverseStart = targetSection.start;

  // Check if this section is already mostly visible
  var rect = targetSection.el.getBoundingClientRect();
  var inView = rect.top > 0 && rect.top < window.innerHeight * 0.6;
  if (inView) return;

  // Scroll to center the section
  videoScrolling = true;
  var offset = window.pageYOffset + rect.top - (window.innerHeight / 2) + (rect.height / 2);
  window.scrollTo({{ top: Math.max(0, offset), behavior: 'smooth' }});
  setTimeout(function() {{ videoScrolling = false; }}, 1000);
}}, 500);

// --- Section nav buttons (sidebar) ---
var navUp = document.getElementById('vs-nav-up');
var navDown = document.getElementById('vs-nav-down');
var currentSectionIdx = -1;

function updateNavButtons() {{
  if (!navUp || !navDown) return;
  navUp.classList.toggle('visible', currentSectionIdx > 0);
  navDown.classList.toggle('visible', currentSectionIdx < sectionList.length - 1);
}}

function scrollToSection(idx) {{
  if (idx < 0 || idx >= sectionList.length) return;
  currentSectionIdx = idx;
  var el = sectionList[idx].el;
  var rect = el.getBoundingClientRect();
  var offset = window.pageYOffset + rect.top - (window.innerHeight / 2) + (rect.height / 2);
  window.scrollTo({{ top: Math.max(0, offset), behavior: 'smooth' }});
  updateNavButtons();
}}

if (navUp) navUp.addEventListener('click', function() {{ scrollToSection(currentSectionIdx - 1); }});
if (navDown) navDown.addEventListener('click', function() {{ scrollToSection(currentSectionIdx + 1); }});

// Track current section from observer
var origObsCb = observer;
var sectionObserver2 = new IntersectionObserver(function(entries) {{
  entries.forEach(function(entry) {{
    if (entry.isIntersecting) {{
      for (var k = 0; k < sectionList.length; k++) {{
        if (sectionList[k].el === entry.target) {{
          currentSectionIdx = k;
          updateNavButtons();
          break;
        }}
      }}
    }}
  }});
}}, {{ rootMargin: '-20% 0px -60% 0px', threshold: 0 }});
sections.forEach(function(s) {{ sectionObserver2.observe(s); }});

// Reset index when scrolled above all sections
window.addEventListener('scroll', function() {{
  if (sectionList.length && sectionList[0].el.getBoundingClientRect().top > window.innerHeight * 0.5) {{
    currentSectionIdx = -1;
    updateNavButtons();
  }}
}});
updateNavButtons();
</script>"""


VIDEO_SIDEBAR = """<div class="video-sidebar">
  <div class="video-sticky">
    <button class="vs-nav vs-nav-up" id="vs-nav-up" title="Previous section"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" fill="currentColor" width="18" height="18"><path d="M256 512A256 256 0 1 0 256 0a256 256 0 1 0 0 512zm11.3-395.3l112 112c4.6 4.6 5.9 11.5 3.5 17.4s-8.3 9.9-14.8 9.9l-64 0 0 96c0 17.7-14.3 32-32 32l-32 0c-17.7 0-32-14.3-32-32l0-96-64 0c-6.5 0-12.3-3.9-14.8-9.9s-1.1-12.9 3.5-17.4l112-112c6.2-6.2 16.4-6.2 22.6 0z"/></svg></button>
    <div class="video-frame">
      <div id="sidebar-player"></div>
    </div>
    <div class="video-bar">
      <span class="vs-section" id="vs-section">Loading...</span>
      <div class="vs-controls">
        <button class="vs-btn" id="vs-mute" title="Unmute">&#128263;</button>
        <button class="vs-btn" id="vs-playpause" title="Play/Pause">&#9654;</button>
        <button class="vs-btn" id="vs-detach" title="Detach to PiP">&#x2922;</button>
      </div>
    </div>
    <button class="vs-nav vs-nav-down" id="vs-nav-down" title="Next section"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" fill="currentColor" width="18" height="18"><path d="M256 0a256 256 0 1 0 0 512A256 256 0 1 0 256 0zM244.7 395.3l-112-112c-4.6-4.6-5.9-11.5-3.5-17.4s8.3-9.9 14.8-9.9l64 0 0-96c0-17.7 14.3-32 32-32l32 0c17.7 0 32 14.3 32 32l0 96 64 0c6.5 0 12.3 3.9 14.8 9.9s1.1 12.9-3.5 17.4l-112 112c-6.2 6.2-16.4 6.2-22.6 0z"/></svg></button>
  </div>
</div>"""



INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OverArchitected</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,400;0,500;0,700;1,400&family=JetBrains+Mono:wght@400;500&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'DM Sans', Arial, sans-serif; background: #F9F7F4; color: #0B2026; line-height: 1.7; -webkit-font-smoothing: antialiased; }}
  .container {{ max-width: 720px; margin: 0 auto; padding: 3rem 1.5rem 6rem; }}
  h1 {{ font-size: 2rem; font-weight: 700; letter-spacing: -0.03em; margin-bottom: 0.5rem; }}
  .tagline {{ color: #5a6670; font-size: 0.95rem; margin-bottom: 3rem; padding-bottom: 2rem; border-bottom: 1px solid #e0ddd8; }}
  .episode {{ display: block; padding: 1.25rem 1.5rem; margin-bottom: 1rem; background: #fff; border: 1px solid #e0ddd8; border-radius: 4px; text-decoration: none; color: inherit; transition: border-color 0.15s, box-shadow 0.15s; }}
  .episode:hover {{ border-color: #EB1600; box-shadow: 0 2px 8px rgba(235, 22, 0, 0.1); }}
  .episode .ep-title {{ font-size: 1.1rem; font-weight: 600; margin-bottom: 0.25rem; }}
  .episode .ep-date {{ font-size: 0.8rem; font-family: 'JetBrains Mono', monospace; color: #EB1600; }}
</style>
</head>
<body>
<div class="layout">
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

        slug = ep_dir.name
        raw = md_file.read_text()
        meta, body_md = parse_frontmatter(raw)
        blocks = parse_body(body_md)
        body_html = render_episode(meta, blocks)

        youtube_id = meta.get("youtube_id")
        pip_block = ""
        if youtube_id:
            pip_block = PIP_BLOCK.format(youtube_id=youtube_id)

        # Episode navigation — will be filled in second pass
        ep_nav_html = "<!-- EP_NAV_PLACEHOLDER -->"

        video_sidebar = ""
        if youtube_id:
            video_sidebar = VIDEO_SIDEBAR

        page_html = TEMPLATE.format(
            title=meta.get("title", "OverArchitected"),
            subtitle=meta.get("subtitle", ""),
            body=body_html,
            pip_block=pip_block,
            ep_nav=ep_nav_html,
            video_sidebar=video_sidebar,
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

    # Second pass: generate prev/next navigation
    for idx, entry in enumerate(index_entries):
        slug = entry["slug"]
        prev_link = ""
        next_link = ""
        if idx > 0:
            p = index_entries[idx - 1]
            prev_link = f'<a href="/{p["slug"]}/"><span class="ep-nav-label">&larr; Previous</span>{p["title"]}</a>'
        if idx < len(index_entries) - 1:
            n = index_entries[idx + 1]
            next_link = f'<a href="/{n["slug"]}/"><span class="ep-nav-label">Next &rarr;</span>{n["title"]}</a>'
        if prev_link or next_link:
            nav_html = f'<div class="ep-nav">{prev_link or "<span></span>"}{next_link or "<span></span>"}</div>'
            out_path = DIST_DIR / slug / "index.html"
            html = out_path.read_text()
            html = html.replace("<!-- EP_NAV_PLACEHOLDER -->", nav_html)
            out_path.write_text(html)

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

    # Copy images
    images_src = ROOT / "images"
    if images_src.exists():
        images_dst = DIST_DIR / "images"
        if images_dst.exists():
            shutil.rmtree(images_dst)
        shutil.copytree(images_src, images_dst)
        print("  Copied images/")

    # CNAME for custom domain
    (DIST_DIR / "CNAME").write_text("overarchitected.com")
    print("  Built CNAME")
    print(f"Done. {len(index_entries)} episode(s) in dist/")


if __name__ == "__main__":
    build()
