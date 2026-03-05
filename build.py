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

            # Add data-start for PiP scroll-seek
            start_attr = ""
            if youtube_id and section_meta and section_meta.get("timestamp"):
                start_attr = f' data-start="{timestamp_to_seconds(section_meta["timestamp"])}"'
            body_parts.append(f'<div class="section"{start_attr}>')
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
  body {{ font-family: 'DM Sans', Arial, sans-serif; background: var(--bg); color: var(--text); line-height: 1.7; -webkit-font-smoothing: antialiased; }}
  .container {{ max-width: 720px; margin: 0 auto; padding: 3rem 1.5rem 6rem; }}
  header {{ margin-bottom: 3rem; padding-bottom: 2rem; border-bottom: 1px solid var(--border); }}
  header h1 {{ font-size: 2rem; font-weight: 700; letter-spacing: -0.03em; margin-bottom: 0.75rem; }}
  header .subtitle {{ color: var(--text-muted); font-size: 0.95rem; }}
  .intro {{ font-size: 1.05rem; margin-bottom: 3rem; padding-bottom: 2rem; border-bottom: 1px solid var(--border); line-height: 1.8; }}
  .intro p + p {{ margin-top: 1rem; }}
  .section {{ margin-bottom: 3rem; }}
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
  .machine strong {{ color: #0B2026; font-weight: 500; }}
  .machine code {{ font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; background: rgba(0,0,0,0.04); padding: 0.15em 0.4em; border-radius: 3px; }}
  .human {{ font-size: 1.05rem; color: var(--human-text); line-height: 1.8; padding: 0 0.25rem; }}
  .human::before {{ content: 'Nick \\2014'; display: block; font-size: 0.8rem; font-weight: 600; color: var(--text-muted); margin-bottom: 0.3rem; }}
  .human strong {{ font-weight: 600; }}
  .architecture {{ background: var(--machine-bg); border: 1px solid var(--machine-border); border-radius: var(--radius); padding: 1.5rem; position: relative; }}
  .architecture::before {{ content: 'CLAUDE OPUS 4.6'; position: absolute; top: -0.65rem; left: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.6rem; font-weight: 500; letter-spacing: 0.1em; color: var(--accent); background: var(--bg); border: 1px solid var(--machine-border); padding: 0.15rem 0.6rem; border-radius: 99px; }}
  .architecture pre {{ font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: var(--machine-text); line-height: 1.8; overflow-x: auto; white-space: pre; }}
  .architecture pre .arrow {{ color: var(--accent); }}
  hr.divider {{ border: none; border-top: 1px solid var(--border); margin: 2.5rem 0; }}
  footer {{ margin-top: 4rem; padding-top: 2rem; border-top: 1px solid var(--border); text-align: center; color: var(--text-muted); font-size: 0.85rem; }}
  footer a {{ color: var(--accent); text-decoration: none; }}
  footer a:hover {{ text-decoration: underline; }}

  /* PiP Video Player */
  .pip {{ position: fixed; bottom: 1.5rem; right: 1.5rem; z-index: 1000; width: 360px; min-width: 260px; max-width: 640px; background: #000; border-radius: var(--radius); overflow: hidden; box-shadow: 0 8px 32px rgba(0,0,0,0.25); transition: opacity 0.3s, transform 0.3s; }}
  .pip.dragging {{ transition: none; user-select: none; }}
  .pip.hidden {{ opacity: 0; transform: translateY(1rem); pointer-events: none; }}
  .pip-header {{ display: flex; align-items: center; justify-content: space-between; padding: 0.4rem 0.75rem; background: var(--text); cursor: grab; }}
  .pip-header:active {{ cursor: grabbing; }}
  .pip-resize {{ position: absolute; top: 0; left: 0; width: 20px; height: 20px; cursor: nw-resize; z-index: 2; }}
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

{pip_block}
</body>
</html>"""


PIP_BLOCK = """<!-- PiP Video Player -->
<div class="pip hidden" id="pip">
  <div class="pip-resize" id="pip-resize"></div>
  <div class="pip-header" id="pip-drag">
    <span class="pip-section" id="pip-section">Loading...</span>
    <div class="pip-controls">
      <button class="pip-btn" id="pip-playpause" title="Play/Pause">&#9654;</button>
      <button class="pip-btn pip-size-toggle" id="pip-size-toggle" title="Toggle size" style="display:none;">&#8596;</button>
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

var PAD = 24; // min distance from any window edge
var player, isReady = false, currentStart = 0;
var pip = document.getElementById('pip');
var pipSection = document.getElementById('pip-section');
var pipPlaypause = document.getElementById('pip-playpause');
var pipClose = document.getElementById('pip-close');
var pipReopen = document.getElementById('pip-reopen');
var pipDrag = document.getElementById('pip-drag');
var pipResize = document.getElementById('pip-resize');
var pipSizeToggle = document.getElementById('pip-size-toggle');

var overlay = document.createElement('div');
overlay.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;z-index:3;display:none;';
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

function onYouTubeIframeAPIReady() {{
  player = new YT.Player('pip-player', {{
    videoId: '{youtube_id}',
    playerVars: {{ rel: 0, modestbranding: 1, playsinline: 1, autoplay: 1, mute: 1 }},
    events: {{
      onReady: function() {{
        isReady = true;
        pip.classList.remove('hidden');
        document.body.classList.add('pip-visible');
        if (isMobile()) {{ pipSizeToggle.style.display = 'inline'; pipResize.style.display = 'none'; }}
        // Switch to absolute and clamp to respect padding
        setTimeout(function() {{
          switchToAbsolute();
          applyPos(parseFloat(pip.style.left), parseFloat(pip.style.top));
        }}, 50);
        player.playVideo();
      }},
      onStateChange: function(e) {{
        pipPlaypause.innerHTML = (e.data === YT.PlayerState.PLAYING) ? '\u23F8' : '\u25B6';
      }}
    }}
  }});
}}

pipPlaypause.addEventListener('click', function() {{
  if (!isReady) return;
  if (player.getPlayerState() === YT.PlayerState.PLAYING) player.pauseVideo();
  else player.playVideo();
}});

pipClose.addEventListener('click', function() {{
  pip.classList.add('hidden');
  document.body.classList.remove('pip-visible');
  pipReopen.style.display = 'block';
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
  overlay.style.display = 'block';
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
  overlay.style.display = 'none';

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

// --- RESIZE (desktop only) ---
var isResizing = false, resStartX, resStartY, resStartW, resStartRect;

pipResize.addEventListener('mousedown', function(e) {{
  if (isMobile()) return;
  e.preventDefault();
  e.stopPropagation();
  isResizing = true;
  pip.classList.add('dragging');
  overlay.style.display = 'block';
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
    overlay.style.display = 'none';
  }}
}});

// --- Keep pip in viewport on window resize ---
window.addEventListener('resize', function() {{
  if (pip.classList.contains('hidden') || pip.style.right !== 'auto') return;
  // Mobile size toggle visibility
  if (isMobile()) {{ pipSizeToggle.style.display = 'inline'; pipResize.style.display = 'none'; }}
  else {{ pipSizeToggle.style.display = 'none'; pipResize.style.display = ''; }}
  var w = pip.offsetWidth;
  var maxW = window.innerWidth - PAD * 2;
  if (w > maxW) {{ w = Math.max(160, maxW); pip.style.width = w + 'px'; }}
  var rect = pip.getBoundingClientRect();
  applyPos(rect.left, rect.top);
}});

// --- Scroll-seek ---
var sections = document.querySelectorAll('.section[data-start]');
var observer = new IntersectionObserver(function(entries) {{
  entries.forEach(function(entry) {{
    if (entry.isIntersecting) {{
      var start = parseInt(entry.target.dataset.start);
      var heading = entry.target.querySelector('h2');
      if (heading && isReady && start !== currentStart) {{
        currentStart = start;
        player.seekTo(start, true);
        pipSection.textContent = heading.textContent.replace(/^\d{{2}}\s*/, '');
      }}
    }}
  }});
}}, {{ rootMargin: '-20% 0px -60% 0px', threshold: 0 }});

sections.forEach(function(s) {{ observer.observe(s); }});
</script>"""


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

        page_html = TEMPLATE.format(
            title=meta.get("title", "OverArchitected"),
            subtitle=meta.get("subtitle", ""),
            body=body_html,
            pip_block=pip_block,
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
