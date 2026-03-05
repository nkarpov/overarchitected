# OverArchitected

Companion blog for the [OverArchitected](https://www.youtube.com/playlist?list=PLTPXxbhUt-YVmQhBv7kb12GBAhepCpAWu) podcast with Nick Karpov and Holly Smith — where we talk about new Databricks features and shoehorn them into one architecture to see if it's actually realistic.

**Live site:** [nickkarpov.com/overarchitected](https://www.nickkarpov.com/overarchitected/)

## How the blog works

Each episode transcript gets fed to Claude Opus, which produces unedited summaries. Nick responds to each summary with unedited human commentary. The machine does the recap, the human does the opinion. Neither side is edited — what you see is what was written.

## Repo structure

```
overarchitected/
├── build.py                      # Markdown → HTML generator (only dep: pyyaml)
├── episodes/
│   └── 2026-03/
│       └── index.md              # Source of truth for March 2026 episode
├── .github/
│   └── workflows/
│       └── deploy.yml            # Build + deploy to GitHub Pages on push
├── dist/                         # Generated output (gitignored)
│   ├── index.html                # Episode listing page
│   └── 2026-03/
│       └── index.html            # Built episode page
└── README.md
```

## Adding a new episode

### 1. Create the episode folder

```
mkdir episodes/YYYY-MM
```

### 2. Create `episodes/YYYY-MM/index.md`

The file has two parts: YAML frontmatter for metadata, and markdown for content.

#### Frontmatter

```yaml
---
title: "OverArchitected: April 2026"
date: 2026-04-01
subtitle: "Nick Karpov & Holly Smith"
youtube_id: null  # Set to YouTube video ID once published, e.g. "dQw4w9WgXcQ"
sections:
  - heading: "Feature Name Here"       # Must match the ## heading exactly
    timestamp: "3:45"                  # M:SS or H:MM:SS — maps to video start time
    docs:
      - label: "short description"
        url: "https://docs.databricks.com/..."
  - heading: "Another Feature"
    timestamp: "12:30"
    docs: []                           # No docs links for this section
---
```

**Fields:**
- `title` — Page title and `<h1>`
- `date` — Used for ordering on the index page
- `subtitle` — Shown under the title (typically "Nick Karpov & Holly Smith")
- `youtube_id` — When `null`, video sections render as timestamp placeholders. Set to the YouTube video ID and all sections auto-embed with the correct start time
- `sections` — Maps each `## heading` to its video timestamp and release note links. The `heading` value must match the `##` heading in the markdown body exactly

#### Markdown body

The content uses two conventions:

- **Blockquotes (`> ...`)** = Claude Opus output (machine). Rendered in a styled card with a `CLAUDE OPUS 4.6` pill label
- **Regular paragraphs** = Nick's commentary (human). Rendered as body text with a `Nick —` label

```markdown
## Feature Name Here

> Machine-generated summary goes here. This was written by Claude Opus
> and not edited. Multiple paragraphs in the blockquote are fine.
>
> **In the architecture:** How this feature fits the episode's architecture.

Your human commentary goes here. Completely unedited, stream of consciousness,
whatever you want to say.

## Another Feature

> Another machine summary.

Another human response.
```

**Special sections:**
- `## The Final Architecture` — put a fenced code block inside a blockquote for the ASCII architecture diagram. It renders in a special monospace card with colored arrows
- `## The Rating` — closing scores, rendered as a machine block
- Sections without a matching `sections:` entry in frontmatter still render, they just won't have video/docs links

### 3. Build locally

```bash
pip install pyyaml   # only dependency
python build.py
```

Output goes to `dist/`. Open `dist/YYYY-MM/index.html` to preview the episode, or `dist/index.html` for the listing page.

### 4. Push to deploy

```bash
git add episodes/YYYY-MM/index.md
git commit -m "Add YYYY-MM episode"
git push
```

The GitHub Action builds and deploys to GitHub Pages automatically. The site is live at `nickkarpov.com/overarchitected/` within a couple minutes.

## Workflow for writing an episode

1. Get the episode transcript (we use Riverside, transcript lives in a Google Doc)
2. Feed the transcript to Claude Opus — have it summarize each feature section
3. Respond to each summary conversationally (don't edit the machine output)
4. Assemble into `index.md` with frontmatter (release note links come from the show notes doc)
5. Set timestamps from the transcript (approximate is fine — they map to video start times)
6. Build, preview, push

## Design

- **Brand:** Follows [Databricks brand guidelines](https://brand.databricks.com/) — DM Sans typeface, `#F9F7F4` warm background, `#EB1600` red accent, `#0B2026` text, `#4462c9` blue for doc links
- **Machine blocks:** Light blue-gray cards with `CLAUDE OPUS 4.6` pill label, muted text
- **Human blocks:** Full-contrast body text with `Nick —` label
- **Release notes:** Bordered card with "READ THE DOCS" header and linked pills (↗)
- **Video:** YouTube embeds with per-section start times (or timestamp placeholders when `youtube_id` is null)
- **Responsive:** Scales down for mobile

The template and all styles live inline in `build.py` (in the `TEMPLATE` and `INDEX_TEMPLATE` strings). No external CSS files.

## Modifying the design

All HTML/CSS is in `build.py`:

- `TEMPLATE` — the episode page template (CSS variables at the top of the `<style>` block)
- `INDEX_TEMPLATE` — the episode listing page
- `render_episode()` — turns parsed markdown blocks into HTML
- `parse_body()` — the markdown parser (handles headings, blockquotes, paragraphs, code blocks)

To change colors, fonts, or spacing, edit the `:root` CSS variables in `TEMPLATE`. To change the structure of how blocks render, modify `render_episode()`.

## Dependencies

- Python 3.x
- `pyyaml` (only external dependency)
- GitHub Pages (deployment)
