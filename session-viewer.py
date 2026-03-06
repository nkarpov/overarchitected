#!/usr/bin/env python3
"""session-viewer.py — Claude Code session JSONL → four-column annotated viewer.

Usage:
    python session-viewer.py <session.jsonl> [-a annotations.json] [output.html]
"""

import json, sys, html, re, argparse
from pathlib import Path


# ── Noise filters ──────────────────────────────────────────────────────────────

SKIP_PATTERNS = [
    '<local-command-caveat>', '<command-name>', '<local-command-stdout>',
    '<system-reminder>', '<available-deferred-tools>',
]

def is_noise(content):
    if isinstance(content, str):
        return any(p in content for p in SKIP_PATTERNS) or not content.strip()
    if isinstance(content, list):
        if not content:
            return True
        for block in content:
            if isinstance(block, dict) and block.get('type') == 'tool_result':
                inner = block.get('content', [])
                if isinstance(inner, list) and all(
                    isinstance(c, dict) and c.get('type') == 'tool_reference'
                    for c in inner
                ):
                    return True
    return False


# ── Build display items ────────────────────────────────────────────────────────

def extract_result_text(block):
    inner = block.get('content', '')
    if isinstance(inner, list):
        return '\n'.join(
            c.get('text', '') if isinstance(c, dict) and c.get('type') != 'tool_reference'
            else ''
            for c in inner
        ).strip()
    return str(inner).strip()


def build_items(turns):
    items = []
    i = 0
    while i < len(turns):
        turn    = turns[i]
        role    = turn['type']
        content = turn.get('message', {}).get('content', '')
        ts      = turn.get('timestamp', '')

        if role == 'user':
            if isinstance(content, str) and content.strip():
                items.append({'type': 'user', 'text': content.strip(), 'ts': ts})
            elif isinstance(content, list):
                texts = [b.get('text', '') for b in content
                         if isinstance(b, dict) and b.get('type') == 'text']
                combined = '\n'.join(texts).strip()
                if combined:
                    items.append({'type': 'user', 'text': combined, 'ts': ts})
            i += 1
            continue

        if isinstance(content, str):
            if content.strip():
                items.append({'type': 'claude', 'text': content.strip(),
                              'tools': [], 'post_text': '', 'ts': ts})
            i += 1
            continue

        pre_texts, post_texts, tool_calls = [], [], []
        past_tools = False
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get('type')
            if btype == 'text':
                t = block.get('text', '').strip()
                if t:
                    (post_texts if past_tools else pre_texts).append(t)
            elif btype == 'tool_use':
                past_tools = True
                tool_calls.append({
                    'name':  block.get('name', ''),
                    'input': block.get('input', {}),
                    'id':    block.get('id', ''),
                })

        results = []
        j = i + 1
        while j < len(turns):
            nxt = turns[j]
            if nxt.get('isMeta'):
                j += 1
                continue
            nc = nxt.get('message', {}).get('content', '')
            if nxt['type'] != 'user':
                break
            if isinstance(nc, list) and any(
                isinstance(b, dict) and b.get('type') == 'tool_result' for b in nc
            ):
                for block in nc:
                    if isinstance(block, dict) and block.get('type') == 'tool_result':
                        results.append({
                            'text':     extract_result_text(block),
                            'is_error': block.get('is_error', False),
                        })
                j += 1
                break
            else:
                break

        tools = []
        for k, call in enumerate(tool_calls):
            tools.append({
                'name':   call['name'],
                'input':  call['input'],
                'result': results[k] if k < len(results) else None,
            })

        pre_text  = '\n'.join(pre_texts).strip()
        post_text = '\n'.join(post_texts).strip()
        if pre_text or tools or post_text:
            items.append({
                'type': 'claude', 'text': pre_text,
                'tools': tools, 'post_text': post_text, 'ts': ts,
            })
        i = j
    return items


# ── Text → HTML ────────────────────────────────────────────────────────────────

def text_to_html(raw):
    if not raw:
        return ''
    e = html.escape(raw)
    def fmt_code_block(m):
        lang = html.escape(m.group(1) or '')
        body = m.group(2)
        lbl  = f'<span class="code-lang">{lang}</span>' if lang else ''
        return f'<div class="code-block">{lbl}<pre><code>{body}</code></pre></div>'
    e = re.sub(r'```(\w*)\n(.*?)```', fmt_code_block, e, flags=re.DOTALL)
    e = re.sub(r'`([^`\n]+)`',        r'<code>\1</code>', e)
    e = re.sub(r'\*\*([^*\n]+)\*\*',  r'<strong>\1</strong>', e)
    e = re.sub(r'\*([^*\n]+)\*',      r'<em>\1</em>', e)
    out = []
    for para in re.split(r'\n\n+', e):
        para = para.strip()
        if not para:
            continue
        if para.startswith('<div class="code-block"') or para.startswith('<pre'):
            out.append(para)
        else:
            out.append(f'<p>{para.replace(chr(10), "<br>")}</p>')
    return '\n'.join(out)


# ── Item → HTML ────────────────────────────────────────────────────────────────

def short_tool_name(name):
    parts = name.split('__')
    return parts[-1] if len(parts) > 1 else name

def tool_preview(inp):
    for v in inp.values():
        if isinstance(v, str) and v.strip():
            return v.strip().replace('\n', ' ')[:100]
    return ''

def render_tools_block(tools):
    if not tools:
        return ''
    rows = []
    for tool in tools:
        name     = short_tool_name(tool['name'])
        prev     = tool_preview(tool['input'])
        inp_json = json.dumps(tool['input'], indent=2)
        result   = tool.get('result')
        prev_html = f'<span class="tool-preview">{html.escape(prev)}</span>' if prev else ''
        rows.append(f'''<div class="tool-pair">
  <div class="tool-name-row">
    <span class="tool-call-name">{html.escape(name)}</span>{prev_html}
  </div>
  <div class="tool-input-block">
    <details class="tool-input-details">
      <summary class="tool-input-summary">input</summary>
      <pre class="tool-input-pre">{html.escape(inp_json)}</pre>
    </details>
  </div>''')
        if result and result.get('text'):
            chars    = f"{len(result['text']):,}"
            is_error = result.get('is_error', False)
            res_html = html.escape(result['text'][:5000])
            if len(result['text']) > 5000:
                res_html += '\n… [truncated]'
            err_cls  = ' result-error' if is_error else ''
            rows.append(f'''  <div class="tool-result-row{err_cls}" onclick="toggleResult(this)">
    <span class="result-arrow">{"⚠" if is_error else "←"}</span>
    <span class="result-chars">{chars} chars</span>
    <span class="result-toggle">expand</span>
  </div>
  <pre class="tool-result-pre" hidden>{res_html}</pre>''')
        rows.append('</div>')
    return f'<div class="tools-block">{"".join(rows)}</div>'


def render_item(item, idx, chapter_classes=''):
    itype = item['type']
    ts    = item.get('ts', '')
    time  = ts[11:16] if len(ts) >= 16 else ''

    if itype == 'user':
        label   = '<span class="lbl lbl-user">user</span>'
        content = f'<div class="item-text">{text_to_html(item["text"])}</div>'
    elif itype == 'claude':
        label    = '<span class="lbl lbl-claude">claude</span>'
        pre_html  = f'<div class="item-text">{text_to_html(item["text"])}</div>' if item.get("text") else ''
        tools_html = render_tools_block(item.get('tools', []))
        post_html  = f'<div class="item-text">{text_to_html(item["post_text"])}</div>' if item.get('post_text') else ''
        content    = pre_html + tools_html + post_html
    else:
        return None

    cls = f'item item-{itype}'
    if chapter_classes:
        cls += f' {chapter_classes}'
    return f'''<div class="{cls}" id="i{idx}" data-type="{itype}">
  <div class="item-label">{label}<span class="item-time">{time}</span><span class="item-id-badge" data-ref="#i{idx}" onclick="copyRef(this)">#i{idx}</span></div>
  <div class="item-content">{content}</div>
</div>'''


# ── Load + annotations ────────────────────────────────────────────────────────

def load_turns(path):
    turns = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get('type') not in ('user', 'assistant'):
                continue
            if d.get('isMeta'):
                continue
            if is_noise(d.get('message', {}).get('content', '')):
                continue
            turns.append(d)
    return turns


def load_annotations(path):
    if not path:
        return None
    with open(path) as f:
        return json.load(f)


def compute_chapter_map(annotations, total_items):
    if not annotations:
        return {}
    cmap = {}
    for ch in annotations.get('chapters', []):
        start, end = ch['start'], ch['end']
        for i in range(start, min(end + 1, total_items)):
            classes = 'chapter-item'
            if i == start:
                classes += ' chapter-start'
            cmap[i] = classes
    return cmap


def render_annotation_column(annotations):
    if not annotations:
        return '<div style="padding:30px;color:var(--muted);font-size:0.88rem;">No annotations loaded.</div>'
    parts = []
    title   = annotations.get('title', '')
    summary = annotations.get('summary', '')
    if title:
        parts.append(f'''<div class="anno-title-block">
  <h3 class="anno-title">{html.escape(title)}</h3>
  <p class="anno-summary">{html.escape(summary)}</p>
</div>''')
    for ci, ch in enumerate(annotations.get('chapters', [])):
        parts.append(f'''<div class="anno-chapter" id="ch{ci}" data-chapter="{ci}" data-start="{ch.get('start',0)}" data-end="{ch.get('end',0)}">
  <h3 class="anno-heading">{html.escape(ch.get('heading',''))}<span class="anno-id-badge" data-ref="#ch{ci}" onclick="copyRef(this)">#ch{ci}</span></h3>
  <p class="anno-text">{html.escape(ch.get('annotation',''))}</p>
</div>''')
    return '\n'.join(parts)


# ── Generate HTML ──────────────────────────────────────────────────────────────

def generate(path, annotations_path=None):
    turns       = load_turns(path)
    items       = build_items(turns)
    annotations = load_annotations(annotations_path)
    sid         = Path(path).stem
    chapter_map = compute_chapter_map(annotations, len(items))

    rows, map_data = [], []
    for idx, item in enumerate(items):
        ch_cls = chapter_map.get(idx, '')
        row = render_item(item, idx, ch_cls)
        if row is None:
            continue
        rows.append(row)
        n_tools  = len(item.get('tools', []))
        text_len = len(item.get('text', '') or '') + len(item.get('post_text', '') or '')
        map_data.append({
            'type': item['type'], 'len': max(text_len + n_tools * 200, 20),
            'tools': n_tools, 'ch': 1 if ch_cls else 0,
        })

    session_html    = '\n'.join(rows)
    annotation_html = render_annotation_column(annotations)
    map_json        = json.dumps(map_data)
    anno_title      = html.escape(annotations.get('title', 'Session')) if annotations else 'Session'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{anno_title}</title>
<style>
:root {{
  --bg:        #F9F7F4;
  --bg-essay:  #FFFFFF;
  --bg-anno:   #F5F2EE;
  --bg-map:    #EDE9E3;
  --text:      #0B2026;
  --muted:     #8a8a8a;
  --border:    #E0DCD6;

  --c-user:    #4462c9;
  --c-claude:  #4a5a52;
  --c-tool:    #7a3f30;
  --c-error:   #EB1600;

  --m-user:    #C5D0EE;
  --m-claude:  #C8CEC9;
  --m-tool:    #EDCFC8;

  --base:       17px;
  --xs:         0.68rem;

  --map-w:      60px;
  --handle-w:   4px;
}}

* {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  font-family: 'DM Sans', system-ui, -apple-system, sans-serif;
  font-size: var(--base);
  background: var(--bg);
  color: var(--text);
  display: flex;
  height: 100vh;
  overflow: hidden;
  line-height: 1.6;
}}

/* ── Drag handles ── */
.rh {{
  width: var(--handle-w);
  flex-shrink: 0;
  background: var(--border);
  cursor: col-resize;
  transition: background 0.15s;
  z-index: 20;
}}
.rh:hover, .rh.dragging {{ background: var(--c-user); opacity: 0.5; }}

/* ── Col headers ── */
.col-header {{
  padding: 16px 24px 12px;
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 10;
  background: inherit;
}}
.col-header h1, .col-header h2 {{
  font-size: var(--xs);
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
}}
.col-meta {{
  font-size: var(--xs);
  color: var(--muted);
  margin-top: 2px;
}}

/* ─────────────────────────────
   Col 1 — Essay (your writing)
───────────────────────────── */
#essay {{
  flex: 1;
  min-width: 150px;
  overflow-y: auto;
  background: var(--bg-essay);
  display: flex;
  flex-direction: column;
}}

#essay-rendered {{
  flex: 1;
  padding: 30px 32px;
  min-height: 200px;
  cursor: text;
  font-size: 1rem;
  line-height: 1.85;
  color: var(--text);
}}
#essay-rendered:empty::before {{
  content: 'Click here to start writing your essay...';
  color: var(--muted);
  font-style: italic;
  opacity: 0.6;
}}
#essay-rendered h1 {{ font-size: 1.5rem; font-weight: 700; margin: 0.8em 0 0.4em; }}
#essay-rendered h2 {{ font-size: 1.2rem; font-weight: 700; margin: 0.8em 0 0.4em; }}
#essay-rendered h3 {{ font-size: 1.05rem; font-weight: 700; margin: 0.8em 0 0.3em; }}
#essay-rendered p {{ margin-bottom: 0.8em; }}
#essay-rendered p:last-child {{ margin-bottom: 0; }}
#essay-rendered blockquote {{
  border-left: 3px solid var(--border);
  padding-left: 16px;
  color: var(--muted);
  margin: 0.6em 0;
}}
#essay-rendered strong {{ font-weight: 600; }}
#essay-rendered em {{ font-style: italic; }}
#essay-rendered code {{
  font-family: 'Fira Code', ui-monospace, monospace;
  font-size: 0.85em;
  background: rgba(0,0,0,0.06);
  padding: 1px 5px;
  border-radius: 3px;
}}
#essay-rendered hr {{
  border: none;
  border-top: 1px solid var(--border);
  margin: 1.5em 0;
}}

#essay-source {{
  width: 100%;
  flex: 1;
  padding: 30px 32px;
  border: none;
  outline: none;
  resize: none;
  font-family: 'Fira Code', ui-monospace, monospace;
  font-size: 0.88rem;
  line-height: 1.7;
  color: var(--text);
  background: var(--bg-essay);
  tab-size: 2;
}}

.essay-mode-toggle {{
  font-size: var(--xs);
  color: var(--muted);
  cursor: pointer;
  float: right;
  opacity: 0.6;
  user-select: none;
}}
.essay-mode-toggle:hover {{ opacity: 1; }}

/* ─────────────────────────────
   Col 2 — Annotation (Claude)
───────────────────────────── */
#annotation {{
  flex: 1;
  min-width: 150px;
  overflow-y: scroll;
  background: var(--bg-anno);
}}

.anno-title-block {{
  padding: 24px 24px 20px;
  border-bottom: 1px solid var(--border);
}}
.anno-title {{
  font-size: 1rem;
  font-weight: 700;
  color: var(--text);
  line-height: 1.4;
  margin-bottom: 10px;
}}
.anno-summary {{
  font-size: 0.82rem;
  color: var(--muted);
  line-height: 1.75;
}}
.anno-chapter {{
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background 0.1s;
}}
.anno-chapter:hover {{ background: rgba(0,0,0,0.025); }}
.anno-chapter.is-active {{ background: rgba(68, 98, 201, 0.04); }}
.anno-heading {{
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--c-user);
  margin-bottom: 8px;
  letter-spacing: 0.02em;
}}
.anno-text {{
  font-size: 0.85rem;
  line-height: 1.8;
  color: var(--text);
}}

/* ─────────────────────────────
   Col 3 — Session
───────────────────────────── */
#session {{
  flex: 1;
  min-width: 200px;
  overflow-y: scroll;
  overflow-x: hidden;
  background: var(--bg);
}}

.item {{
  border-bottom: 1px solid var(--border);
  opacity: 0.3;
  transition: opacity 0.15s;
  padding: 8px 16px;
}}
.item:hover {{ opacity: 0.5; background: rgba(0,0,0,0.01); }}
.item.chapter-item {{ opacity: 0.75; }}
.item.chapter-item:hover {{ opacity: 0.9; }}
.item.chapter-start {{
  opacity: 0.9;
  border-top: 2px solid var(--c-user);
}}

.item-label {{
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 4px;
}}
.lbl {{
  font-size: var(--xs);
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}}
.lbl-user   {{ color: var(--c-user);   }}
.lbl-claude {{ color: var(--c-claude); }}
.item-time {{
  font-size: calc(var(--xs) * 0.85);
  color: var(--muted);
  opacity: 0.5;
  font-variant-numeric: tabular-nums;
}}
.item-content {{ min-width: 0; overflow: hidden; }}

.item-text p {{
  font-size: 0.82rem;
  line-height: 1.65;
  margin-bottom: 0.5em;
}}
.item-text p:last-child {{ margin-bottom: 0; }}
.item-text code {{
  font-family: 'Fira Code', ui-monospace, monospace;
  font-size: 0.8em;
  background: rgba(0,0,0,0.06);
  padding: 1px 4px;
  border-radius: 3px;
}}
.item-text strong {{ font-weight: 600; }}

.code-block {{
  margin: 6px 0;
  border-radius: 5px;
  overflow: hidden;
  background: #1e1e2e;
}}
.code-lang {{
  display: block;
  font-size: var(--xs);
  color: #6c7086;
  padding: 4px 12px 2px;
  font-family: monospace;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}}
.code-block pre {{
  padding: 8px 12px;
  font-family: 'Fira Code', ui-monospace, monospace;
  font-size: 0.75rem;
  color: #cdd6f4;
  overflow-x: auto;
  line-height: 1.5;
  max-width: 100%;
}}
pre {{ max-width: 100%; }}

.tools-block {{
  margin: 8px 0;
  padding-left: 14px;
  border-left: 2px solid var(--border);
}}
.tool-pair {{ margin-bottom: 8px; }}
.tool-pair:last-child {{ margin-bottom: 0; }}
.tool-name-row {{
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 2px;
}}
.tool-call-name {{
  font-size: var(--xs);
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--c-tool);
  flex-shrink: 0;
}}
.tool-preview {{
  font-family: 'Fira Code', ui-monospace, monospace;
  font-size: 0.72rem;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
  flex: 1;
}}
.tool-input-block {{ margin-bottom: 3px; }}
.tool-input-details summary.tool-input-summary {{
  font-size: var(--xs);
  color: var(--muted);
  cursor: pointer;
  list-style: none;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  opacity: 0.5;
}}
.tool-input-summary::-webkit-details-marker {{ display: none; }}
.tool-input-summary::before {{ content: '▶'; font-size: 0.5rem; }}
.tool-input-details[open] .tool-input-summary::before {{ content: '▼'; }}
.tool-input-pre {{
  margin-top: 5px;
  padding: 8px 12px;
  background: #1e1e2e;
  border-radius: 4px;
  font-family: 'Fira Code', ui-monospace, monospace;
  font-size: 0.72rem;
  color: #cdd6f4;
  overflow-x: auto;
  line-height: 1.5;
}}
.tool-result-row {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--xs);
  color: var(--muted);
  cursor: pointer;
  opacity: 0.6;
  user-select: none;
}}
.tool-result-row:hover {{ opacity: 1; }}
.result-error {{ color: var(--c-error); }}
.result-arrow {{ font-size: 0.65em; }}
.result-chars {{ font-variant-numeric: tabular-nums; }}
.result-toggle {{
  font-size: calc(var(--xs) * 0.82);
  border: 1px solid currentColor;
  border-radius: 3px;
  padding: 0 3px;
  opacity: 0.5;
}}
.tool-result-pre {{
  margin-top: 5px;
  padding: 8px 12px;
  background: #1a1f2e;
  border-radius: 4px;
  font-family: 'Fira Code', ui-monospace, monospace;
  font-size: 0.72rem;
  color: #9ba8c0;
  overflow-x: auto;
  line-height: 1.5;
  white-space: pre;
}}

/* ─────────────────────────────
   Col 4 — Minimap
───────────────────────────── */
#minimap {{
  width: var(--map-w);
  flex-shrink: 0;
  background: var(--bg-map);
  border-left: 1px solid var(--border);
  cursor: pointer;
  user-select: none;
  overflow: hidden;
}}
#minimap-canvas {{ display: block; width: 100%; height: 100%; }}

/* ── Cross-references ── */
.xref {{
  color: var(--c-user);
  text-decoration: none;
  border-bottom: 1px dashed var(--c-user);
  cursor: pointer;
  transition: opacity 0.15s;
}}
.xref:hover {{ opacity: 0.7; }}

/* Flash on referenced target */
.xref-target-flash {{
  background: rgba(68, 98, 201, 0.2) !important;
  opacity: 1 !important;
}}

/* Item ID badge on hover */
.item-id-badge {{
  display: none;
  font-size: 0.6rem;
  font-family: 'Fira Code', ui-monospace, monospace;
  color: var(--c-user);
  background: rgba(68, 98, 201, 0.08);
  padding: 1px 5px;
  border-radius: 3px;
  cursor: pointer;
  user-select: none;
  margin-left: auto;
}}
.item:hover .item-id-badge,
.anno-chapter:hover .anno-id-badge {{ display: inline-block; }}
.item-id-badge:hover, .anno-id-badge:hover {{ background: rgba(68, 98, 201, 0.18); }}

.anno-id-badge {{
  display: none;
  font-size: 0.6rem;
  font-family: 'Fira Code', ui-monospace, monospace;
  color: var(--c-user);
  background: rgba(68, 98, 201, 0.08);
  padding: 1px 5px;
  border-radius: 3px;
  cursor: pointer;
  user-select: none;
  float: right;
}}

/* Copied tooltip */
.copy-toast {{
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--text);
  color: var(--bg);
  font-size: 0.75rem;
  padding: 6px 14px;
  border-radius: 4px;
  opacity: 0;
  transition: opacity 0.2s;
  pointer-events: none;
  z-index: 100;
}}
.copy-toast.show {{ opacity: 1; }}
</style>
</head>
<body>

<!-- Col 1: Essay -->
<div id="essay">
  <div class="col-header">
    <span class="essay-mode-toggle" id="essay-toggle">edit</span>
    <h1>Essay</h1>
  </div>
  <div id="essay-rendered"></div>
  <textarea id="essay-source" hidden placeholder="Write in markdown..."></textarea>
</div>
<div class="rh" id="rh1"></div>

<!-- Col 2: Annotation -->
<div id="annotation">
  <div class="col-header">
    <h2>Annotation</h2>
  </div>
  {annotation_html}
</div>
<div class="rh" id="rh2"></div>

<!-- Col 3: Session -->
<div id="session">
  <div class="col-header">
    <h1>Session</h1>
    <div class="col-meta">{html.escape(sid[:8])} · {len(rows)} items</div>
  </div>
  {session_html}
</div>

<!-- Col 4: Minimap -->
<div id="minimap"><canvas id="minimap-canvas"></canvas></div>

<script>
// ── Essay editor ─────────────────────────────────────────────────────────────

const essayRendered = document.getElementById('essay-rendered');
const essaySource   = document.getElementById('essay-source');
const essayToggle   = document.getElementById('essay-toggle');
const STORAGE_KEY   = 'session-essay-' + '{html.escape(sid[:8])}';
let essayMode = 'read';  // 'read' | 'write'

// Minimal markdown → HTML
function renderMd(src) {{
  if (!src.trim()) return '';
  let h = src;
  // Escape HTML
  h = h.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  // Headings
  h = h.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  h = h.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  h = h.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  // Blockquotes
  h = h.replace(/^&gt; (.+)$/gm, '<blockquote><p>$1</p></blockquote>');
  // HR
  h = h.replace(/^---$/gm, '<hr>');
  // Bold / italic / code
  h = h.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  h = h.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  h = h.replace(/`([^`]+)`/g, '<code>$1</code>');
  // Cross-reference links: [text](#i42) or [text](#ch3)
  h = h.replace(/\[([^\]]+)\]\(#(i\d+)\)/g, '<a class="xref xref-session" data-target="$2" href="#">$1</a>');
  h = h.replace(/\[([^\]]+)\]\(#(ch\d+)\)/g, '<a class="xref xref-anno" data-target="$2" href="#">$1</a>');
  // Paragraphs: double newline
  h = h.split(/\\n\\n+/).map(block => {{
    block = block.trim();
    if (!block) return '';
    if (block.startsWith('<h') || block.startsWith('<blockquote') || block.startsWith('<hr')) return block;
    return '<p>' + block.replace(/\\n/g, '<br>') + '</p>';
  }}).join('\\n');
  return h;
}}

function showRead() {{
  essayMode = 'read';
  const md = essaySource.value;
  essayRendered.innerHTML = renderMd(md);
  essayRendered.hidden = false;
  essaySource.hidden = true;
  essayToggle.textContent = 'edit';
  localStorage.setItem(STORAGE_KEY, md);
}}

function showWrite() {{
  essayMode = 'write';
  essayRendered.hidden = true;
  essaySource.hidden = false;
  essaySource.focus();
  essayToggle.textContent = 'preview';
}}

// Toggle
essayToggle.addEventListener('click', () => {{
  if (essayMode === 'read') showWrite();
  else showRead();
}});

// Click rendered → edit (but not on cross-reference links)
essayRendered.addEventListener('click', e => {{
  if (e.target.closest('.xref')) return;
  showWrite();
}});

// Escape → preview
essaySource.addEventListener('keydown', e => {{
  if (e.key === 'Escape') showRead();
  // Tab inserts spaces
  if (e.key === 'Tab') {{
    e.preventDefault();
    const s = essaySource.selectionStart;
    essaySource.value = essaySource.value.substring(0, s) + '  ' + essaySource.value.substring(essaySource.selectionEnd);
    essaySource.selectionStart = essaySource.selectionEnd = s + 2;
  }}
}});

// Load saved essay
const saved = localStorage.getItem(STORAGE_KEY);
if (saved) {{
  essaySource.value = saved;
  essayRendered.innerHTML = renderMd(saved);
}}

// ── Minimap ──────────────────────────────────────────────────────────────────

const ITEMS  = {map_json};
const main   = document.getElementById('session');
const canvas = document.getElementById('minimap-canvas');
const ctx    = canvas.getContext('2d');

const CAT_COLOR = {{ 'user': '#C5D0EE', 'claude': '#C8CEC9' }};
const TOOL_COLOR = '#EDCFC8';
const MIN_BAR = 2, GAP = 1;

function setupCanvas() {{
  canvas.width  = canvas.offsetWidth  * devicePixelRatio;
  canvas.height = canvas.offsetHeight * devicePixelRatio;
  ctx.scale(devicePixelRatio, devicePixelRatio);
}}

function blendColor(a, b, t) {{
  const pa = parseInt, pc = (c, s, l) => pa(c.slice(s, l), 16);
  const r1=pc(a,1,3), g1=pc(a,3,5), b1=pc(a,5,7);
  const r2=pc(b,1,3), g2=pc(b,3,5), b2=pc(b,5,7);
  const r=Math.round(r1+(r2-r1)*t), g=Math.round(g1+(g2-g1)*t), bv=Math.round(b1+(b2-b1)*t);
  return '#'+[r,g,bv].map(v=>v.toString(16).padStart(2,'0')).join('');
}}

function draw() {{
  const W = canvas.offsetWidth, H = canvas.offsetHeight;
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = '#EDE9E3';
  ctx.fillRect(0, 0, W, H);
  if (!ITEMS.length) return;

  const n = ITEMS.length;
  const fixedH = n * MIN_BAR + (n - 1) * GAP;
  const extraH = Math.max(0, H - fixedH);
  const logTotal = ITEMS.reduce((s, it) => s + Math.log(1 + it.len), 0);

  let y = 0;
  ITEMS.forEach(it => {{
    const share = logTotal > 0 ? Math.log(1 + it.len) / logTotal : 1 / n;
    const barH = MIN_BAR + share * extraH;
    const base = CAT_COLOR[it.type] || '#C8CEC9';
    const color = it.tools > 0 ? blendColor(base, TOOL_COLOR, Math.min(it.tools / 4, 0.8)) : base;
    ctx.globalAlpha = it.ch ? 1 : 0.4;
    ctx.fillStyle = it.ch ? blendColor(color, '#4462c9', 0.3) : color;
    ctx.fillRect(5, y, W - 10, Math.max(barH - GAP, 1));
    ctx.globalAlpha = 1;
    y += barH;
  }});

  const scrollable = main.scrollHeight - main.clientHeight;
  const ratio = scrollable > 0 ? main.scrollTop / scrollable : 0;
  const vpH = (main.clientHeight / main.scrollHeight) * H;
  const vpY = ratio * (H - vpH);
  ctx.fillStyle = 'rgba(0,0,0,0.07)';
  ctx.fillRect(0, vpY, W, vpH);
  ctx.strokeStyle = 'rgba(0,0,0,0.22)';
  ctx.lineWidth = 1;
  ctx.strokeRect(0.5, vpY + 0.5, W - 1, vpH - 1);
}}

main.addEventListener('scroll', draw, {{ passive: true }});

function minimapScroll(clientY) {{
  const rect = canvas.getBoundingClientRect();
  const ratio = Math.max(0, Math.min(1, (clientY - rect.top) / rect.height));
  main.scrollTo({{ top: ratio * (main.scrollHeight - main.clientHeight) }});
}}
canvas.addEventListener('mousedown', e => {{
  minimapScroll(e.clientY);
  const move = ev => minimapScroll(ev.clientY);
  const up = () => {{ window.removeEventListener('mousemove', move); window.removeEventListener('mouseup', up); }};
  window.addEventListener('mousemove', move);
  window.addEventListener('mouseup', up);
}});

// ── Column resize ────────────────────────────────────────────────────────────

function makeResizable(handleId, targetId, minW, maxW) {{
  const handle = document.getElementById(handleId);
  const target = document.getElementById(targetId);
  handle.addEventListener('mousedown', e => {{
    e.preventDefault();
    const startX = e.clientX, startW = target.offsetWidth;
    handle.classList.add('dragging');
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    const move = ev => {{
      target.style.width = Math.max(minW, Math.min(maxW, startW + ev.clientX - startX)) + 'px';
      setupCanvas(); draw();
    }};
    const up = () => {{
      handle.classList.remove('dragging');
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', up);
    }};
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
  }});
}}

makeResizable('rh1', 'essay',      200, 800);
makeResizable('rh2', 'annotation', 150, 600);
// session is flex:1, resizing essay/annotation implicitly resizes it

// ── Tool result toggle ───────────────────────────────────────────────────────

function toggleResult(row) {{
  const pre = row.nextElementSibling;
  if (!pre) return;
  const open = !pre.hidden;
  pre.hidden = open;
  const btn = row.querySelector('.result-toggle');
  if (btn) btn.textContent = open ? 'expand' : 'collapse';
}}

// ── Annotation: click → scroll session ───────────────────────────────────────

const annoCol = document.getElementById('annotation');

document.querySelectorAll('.anno-chapter').forEach(ch => {{
  ch.addEventListener('click', () => {{
    const target = document.getElementById('i' + ch.dataset.start);
    if (target) main.scrollTo({{ top: target.offsetTop - 60, behavior: 'smooth' }});
  }});
}});

// Scroll sync: session drives annotation
main.addEventListener('scroll', () => {{
  const sRatio = main.scrollTop / (main.scrollHeight - main.clientHeight || 1);
  annoCol.scrollTop = sRatio * (annoCol.scrollHeight - annoCol.clientHeight || 1);
}}, {{ passive: true }});

// Active chapter tracking
function updateActiveChapter() {{
  const chapters = document.querySelectorAll('.anno-chapter');
  const scrollMid = main.scrollTop + main.clientHeight * 0.3;
  let active = null;
  chapters.forEach(ch => {{
    const startEl = document.getElementById('i' + ch.dataset.start);
    const endEl   = document.getElementById('i' + ch.dataset.end);
    if (startEl && endEl && startEl.offsetTop <= scrollMid && endEl.offsetTop + endEl.offsetHeight >= main.scrollTop) active = ch;
    ch.classList.remove('is-active');
  }});
  if (active) active.classList.add('is-active');
}}
main.addEventListener('scroll', updateActiveChapter, {{ passive: true }});

// ── Cross-references: click link in essay → scroll & flash target ─────────────

document.addEventListener('click', e => {{
  const xref = e.target.closest('.xref');
  if (!xref) return;
  e.preventDefault();
  e.stopPropagation();
  const targetId = xref.dataset.target;
  const targetEl = document.getElementById(targetId);
  if (!targetEl) return;

  // Determine which column to scroll
  const isSession = targetId.startsWith('i');
  const col = isSession ? main : annoCol;

  // Center the item in the column viewport, clamped to valid scroll range
  const scrollTop = Math.max(0, Math.min(
    targetEl.offsetTop - col.clientHeight / 2 + targetEl.offsetHeight / 2,
    col.scrollHeight - col.clientHeight
  ));
  col.scrollTo({{ top: scrollTop, behavior: 'smooth' }});

  // Flash 3 times AFTER scroll finishes
  let fired = false;
  const flashIt = () => {{
    if (fired) return;
    fired = true;
    let flashes = 0;
    const doFlash = () => {{
      targetEl.classList.add('xref-target-flash');
      setTimeout(() => {{
        targetEl.classList.remove('xref-target-flash');
        flashes++;
        if (flashes < 3) setTimeout(doFlash, 200);
      }}, 300);
    }};
    doFlash();
  }};

  // Wait for scroll to fully settle
  const startScroll = col.scrollTop;
  if (Math.abs(scrollTop - startScroll) < 2) {{
    // Already there, flash immediately
    flashIt();
  }} else {{
    // Poll until we arrive at the target scroll position
    const check = () => {{
      if (Math.abs(col.scrollTop - scrollTop) < 2) flashIt();
      else requestAnimationFrame(check);
    }};
    requestAnimationFrame(check);
  }}
}});

// ── Copy reference badge ──────────────────────────────────────────────────────

const toast = document.createElement('div');
toast.className = 'copy-toast';
toast.textContent = 'Copied!';
document.body.appendChild(toast);

function copyRef(badge) {{
  event.stopPropagation();
  const ref = badge.dataset.ref;
  navigator.clipboard.writeText(ref).then(() => {{
    toast.textContent = 'Copied ' + ref;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 1200);
  }});
}}

// j/k navigation
document.addEventListener('keydown', e => {{
  if (essayMode === 'write') return;
  if (e.key !== 'j' && e.key !== 'k') return;
  const userItems = Array.from(document.querySelectorAll('.item-user'));
  const mid = main.scrollTop + main.clientHeight / 2;
  let target;
  if (e.key === 'j') target = userItems.find(el => el.offsetTop > mid + 10);
  else {{ const above = userItems.filter(el => el.offsetTop < mid - 10); target = above[above.length - 1]; }}
  if (target) main.scrollTo({{ top: target.offsetTop - 60, behavior: 'smooth' }});
}});

// ── Init ─────────────────────────────────────────────────────────────────────
window.addEventListener('resize', () => {{ setupCanvas(); draw(); }});
window.addEventListener('load',   () => {{ setupCanvas(); draw(); updateActiveChapter(); }});
</script>
</body>
</html>'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Claude Code session viewer')
    parser.add_argument('session', help='Path to session JSONL file')
    parser.add_argument('output', nargs='?', help='Output HTML file (stdout if omitted)')
    parser.add_argument('-a', '--annotations', help='Path to annotations JSON file')
    args = parser.parse_args()

    result = generate(args.session, args.annotations)
    if args.output:
        Path(args.output).write_text(result)
        print(f'Written → {args.output}', file=sys.stderr)
    else:
        print(result)
