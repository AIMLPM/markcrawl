# Recipe: Capturing game dashboards

Goal: build a corpus of rendered game-dashboard screenshots (player stats,
leaderboards, meta charts, esports tables) plus their text content.

Two independent pipelines — pick one or combine:

1. **[Web sources](#1-web-sources-markcrawl)** — MarkCrawl handles discovery,
   crawl, and screenshot capture end-to-end.
2. **[Video sources](#2-video-sources-yt-dlp--ffmpeg)** — gamer YouTube
   videos, handled with `yt-dlp` + `ffmpeg`. MarkCrawl is *not* involved.

---

## 1. Web sources (MarkCrawl)

### 1a. Install with JS-rendering support

Screenshots require Playwright.

```bash
pip install 'markcrawl[js]'
playwright install chromium
```

### 1b. Discover URLs

Three options, all emit URLs to stdout so they pipe into the crawler.

```bash
# Use the bundled curated pack (no network calls, no API keys)
markcrawl discover --pack game-dashboards

# List available packs
markcrawl discover --list-packs

# (Coming soon) Search API providers — reserved flag:
# markcrawl discover --provider brave "valorant dashboard screenshot"
```

The `game-dashboards` pack covers tracker sites (tracker.gg, steamcharts,
steamdb), per-game stat aggregators (dotabuff, u.gg, blitz.gg), esports
wikis (liquipedia, hltv), and dev patch notes.  Edit
`markcrawl/seeds/game-dashboards.txt` or write your own pack file.

### 1c. Crawl and screenshot

```bash
# One-liner: discover, crawl every seed, capture full-page screenshots
markcrawl discover --pack game-dashboards | \
  markcrawl --seed-file - --out ./dashboards \
    --screenshot --max-pages-per-site 5 --show-progress
```

Output layout:

```
dashboards/
├── steamcharts.com/
│   ├── pages.jsonl           # one row per page, "screenshot" field references the PNG
│   ├── screenshots/
│   │   └── top-abc123.png    # full-page, 1920x{variable-height}
│   └── <slug>__<hash>.md     # markdown extraction of the page
├── steamdb.info/
│   └── ...
└── tracker.gg/
    └── ...
```

### 1d. Useful tweaks

**Crop to a specific element** (e.g. only the dashboard region, skip the nav):

```bash
markcrawl --seed-file seeds.txt --out ./out \
  --screenshot --screenshot-selector ".dashboard-main"
```

**Longer wait for slow-rendering charts**:

```bash
# Default is 1500ms after networkidle; bump for heavy canvas dashboards
markcrawl --seed-file seeds.txt --out ./out \
  --screenshot --screenshot-wait-ms 4000
```

**Smaller files**:

```bash
markcrawl --seed-file seeds.txt --out ./out \
  --screenshot --screenshot-format jpeg
```

**Viewport-only (not full-page)**:

```bash
markcrawl --seed-file seeds.txt --out ./out \
  --screenshot --no-screenshot-full-page --screenshot-viewport 1440x900
```

**Also download inline `<img>` images** (logos, champion portraits):

```bash
markcrawl --seed-file seeds.txt --out ./out \
  --screenshot --download-images --min-image-size 20000
```

### 1e. Flatten all screenshots into one directory

Post-processing if you want a flat dataset:

```bash
find dashboards -path '*/screenshots/*.png' -print0 | \
  xargs -0 -I{} cp {} ./all-screenshots/
```

---

## 2. Video sources (`yt-dlp` + `ffmpeg`)

Lots of dashboards live inside gamer videos — streamers reviewing post-game
screens, coaches analysing stats, guides walking through UI.  MarkCrawl
cannot extract frames from video; use `yt-dlp` and `ffmpeg` for this step.

### 2a. Install

```bash
pipx install yt-dlp          # or: pip install yt-dlp
brew install ffmpeg          # macOS; apt install ffmpeg on Debian/Ubuntu
```

### 2b. Discover and download videos

```bash
# Search YouTube and grab the top 20 results as 480p mp4
yt-dlp "ytsearch20:valorant dashboard review" \
  --write-info-json --write-subs --sub-lang en \
  -f "bv*[height<=480]+ba/b[height<=480]" \
  -o "videos/%(channel)s/%(title).80s [%(id)s].%(ext)s"
```

Adjust the search query to your game: `"apex legends stats breakdown"`,
`"league of legends scoreboard analysis"`, `"dota 2 post game review"`, etc.

### 2c. Extract frames

```bash
# One frame every 10 seconds from every downloaded video
for vid in videos/**/*.mp4; do
  base=$(basename "$vid" .mp4)
  mkdir -p "frames/$base"
  ffmpeg -i "$vid" -vf "fps=1/10" "frames/$base/%04d.png"
done
```

Tune `fps=1/10` to taste — lower (e.g. `fps=1/30`) for long videos, higher
for short clips.

### 2d. Filter frames for "dashboard-ness"

You now have thousands of frames.  Most aren't dashboards.  Filtering options:

- **CLIP embeddings + prompt**: embed each frame and score against prompts like
  `"a game dashboard with stats and charts"` / `"gameplay footage"` — keep
  frames above a threshold.  See `openai-clip` or `open_clip_torch`.
- **OCR + keyword match**: run `tesseract` on each frame, keep frames whose
  text contains `"KDA"`, `"winrate"`, `"damage"`, `"score"`, etc.
- **Manual review**: if you only have a few videos, just flip through the
  frame dirs.

These filtering steps are outside MarkCrawl's scope — but the output (a folder
of PNGs) is the same shape as what you'd get from the web pipeline, so
downstream tooling can treat them identically.

---

## Combining both pipelines

If you want one flat corpus of dashboard screenshots regardless of source,
point both pipelines at the same root:

```bash
# Web
markcrawl discover --pack game-dashboards | \
  markcrawl --seed-file - --out ./corpus/web --screenshot --max-pages-per-site 5

# Video (after frame filtering)
cp -r filtered-frames/*.png ./corpus/video/
```

Each `pages.jsonl` under `./corpus/web/*/` gives you structured metadata
(URL, title, citation, crawl timestamp) alongside every screenshot.  Video
frames won't have that metadata unless you carry through the `yt-dlp`
`.info.json` — see `yt-dlp --write-info-json` above.
