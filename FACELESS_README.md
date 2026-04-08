# Faceless YouTube Automation System

End-to-end pipeline that generates faceless YouTube videos: script → voiceover → thumbnail → video assembly → SEO → upload → analytics.

## Architecture

```
faceless_youtube/
├── __init__.py              Package exports
├── config.py                PipelineConfig dataclass (env + JSON)
├── script_generator.py      OpenAI gpt-4o script generation (structured JSON)
├── thumbnail_generator.py   PIL-based thumbnails (6 Stride presets)
├── fal_image_client.py      Optional fal.ai nano-banana-2 wrapper
├── tts_engine.py            ElevenLabs / edge-tts / gTTS
├── video_assembler.py       FFmpeg slideshow + Ken Burns + subtitles + music
├── seo_optimizer.py         Title/description/tags optimization
├── uploader.py              YouTube Data API v3 upload + thumbnail
├── scheduler.py             Content queue with auto-scheduling
├── analytics.py             Performance tracking
├── niche_library.py         8 pre-built niches with topics
└── pipeline.py              Main orchestrator

run_pipeline.py              CLI entry point
faceless_requirements.txt    Python dependencies
```

## Optional: AI-generated thumbnail backgrounds (nano-banana-2)

The thumbnail generator can call [fal.ai](https://fal.ai)'s `fal-ai/nano-banana-2`
(Google Gemini image gen) to produce a cinematic background per thumbnail,
on top of which the 6 Stride presets overlay their typography. If the key is
missing, the library is not installed, or the request fails, it **silently
falls back** to the solid-color preset background — thumbnails always render.

```bash
pip install fal-client                  # optional dep
export FAL_KEY="your-fal-api-key"
export IMAGE_BACKEND=fal                # enable globally
# or per-command:
python run_pipeline.py thumbnail --text "BLACK HOLE WARNING" --image-backend fal
```

Config equivalents:

| env var         | config field    | default                 |
|-----------------|-----------------|-------------------------|
| `FAL_KEY`       | `fal_api_key`   | `None`                  |
| `IMAGE_BACKEND` | `image_backend` | `"none"` (solid colors) |
| `IMAGE_MODEL`   | `image_model`   | `"fal-ai/nano-banana-2"`|

## Six Thumbnail Presets (from the Stride doc)

1. **BLACK HOLE WARNING** — high urgency, orange/black, Anton font
2. **WHAT'S INSIDE** — mysterious, teal/midnight, Bebas Neue
3. **NO ESCAPE** — aggressive, crimson/violet, Impact
4. **THE VOID** — minimalist, gold/black, League Gothic
5. **COSMIC MONSTER** — dramatic, neon purple/orange, Barlow
6. **GRAVITY GONE WILD** — sci-fi, cyan/navy, Eurostile

## Setup

```bash
# 1. Install Python deps
pip install -r faceless_requirements.txt

# 2. Install FFmpeg (required for video assembly)
# Ubuntu/Debian:  sudo apt install ffmpeg
# macOS:          brew install ffmpeg
# Windows:        https://ffmpeg.org/download.html

# 3. Set environment variables
export OPENAI_API_KEY="sk-..."
export ELEVENLABS_API_KEY="..."          # optional, falls back to edge-tts
export YOUTUBE_CLIENT_ID="..."
export YOUTUBE_CLIENT_SECRET="..."
export YOUTUBE_REFRESH_TOKEN="..."

# 4. Initialize config (optional — env vars work too)
python run_pipeline.py config --init
```

## Usage

```bash
# Suggest topic ideas
python run_pipeline.py topics --niche space_science --count 10

# Generate ONE video (no upload)
python run_pipeline.py generate \
  --topic "What's actually inside a black hole" \
  --niche space_science \
  --style documentary \
  --preset 1

# Generate AND upload
python run_pipeline.py generate \
  --topic "The dark side of the Moon" \
  --niche space_science \
  --upload

# Generate all 6 thumbnails for A/B testing
python run_pipeline.py thumbnail --text "BLACK HOLE" --all --output ./thumbnails

# Batch produce 5 videos for a niche
python run_pipeline.py batch --niche space_science --count 5 --upload

# Schedule 10 videos across upcoming upload slots
python run_pipeline.py schedule --niche space_science --count 10

# Process all due scheduled items (run via cron)
python run_pipeline.py run-scheduled

# Show pipeline status + queue
python run_pipeline.py status

# Performance report
python run_pipeline.py analytics
```

## Niches available

`space_science` · `ancient_history` · `ocean_mysteries` · `true_crime` ·
`psychology` · `technology` · `mythology` · `nature_wildlife`

Each niche ships with 10 ready-to-use topics, default style, recommended
thumbnail preset, and target audience config.

## Cron schedule

```cron
# Process scheduled videos every 30 minutes
*/30 * * * * cd /path/to/repo && python run_pipeline.py run-scheduled >> logs/cron.log 2>&1

# Daily analytics report
0 9 * * * cd /path/to/repo && python run_pipeline.py analytics > reports/daily.md
```

## Notes

- **First run**: use `--dry-run` on every command to see what would happen.
- **Privacy**: defaults to `private` for safety. Set `PRIVACY_STATUS=public` or use the config file when ready.
- **Quota**: each YouTube upload costs 1,600 units (default daily quota: 10,000). Plan accordingly.
- **TTS fallback**: ElevenLabs is best quality but paid. `edge-tts` is free and good. `gTTS` is the universal fallback.
- **Stock footage**: the pipeline uses placeholder images by default. Wire up your own asset source (Pexels API, Pixabay, local library) in `pipeline.py`.

## Built from the Stride content

The 6 thumbnail presets are direct implementations of the design concepts
shared in the original Stride document — colors, fonts, and style notes
ported faithfully into the `ThumbnailGenerator`.
