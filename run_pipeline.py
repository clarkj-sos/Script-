#!/usr/bin/env python3
"""
Faceless YouTube Automation — CLI entry point.

Usage examples:
  python run_pipeline.py generate --topic "What's inside a black hole" --niche space_science
  python run_pipeline.py batch --niche space_science --count 5
  python run_pipeline.py thumbnail --text "BLACK HOLE" --preset 1 --output thumb.jpg
  python run_pipeline.py schedule --niche space_science --count 10
  python run_pipeline.py run-scheduled
  python run_pipeline.py status
  python run_pipeline.py topics --niche space_science --count 10
  python run_pipeline.py analytics
  python run_pipeline.py config --init
  python run_pipeline.py config --show
"""
from __future__ import annotations
import argparse
import json
import sys
import traceback
from pathlib import Path

# ANSI colors
class C:
    R = "\033[0m"; B = "\033[1m"
    RED = "\033[31m"; GRN = "\033[32m"; YEL = "\033[33m"
    BLU = "\033[34m"; MAG = "\033[35m"; CYN = "\033[36m"

BANNER = f"""{C.CYN}{C.B}
╔══════════════════════════════════════════════════════════════╗
║   FACELESS YOUTUBE AUTOMATION SYSTEM  v1.0                   ║
║   script → voice → video → thumbnail → upload → analytics    ║
╚══════════════════════════════════════════════════════════════╝
{C.R}"""


def info(msg): print(f"{C.BLU}[i]{C.R} {msg}")
def ok(msg):   print(f"{C.GRN}[✓]{C.R} {msg}")
def warn(msg): print(f"{C.YEL}[!]{C.R} {msg}")
def err(msg):  print(f"{C.RED}[✗]{C.R} {msg}")


def load_config(path: str | None):
    from faceless_youtube import PipelineConfig
    if path and Path(path).exists():
        info(f"Loading config from {path}")
        return PipelineConfig.from_file(path)
    return PipelineConfig.from_env()


# ─── Commands ──────────────────────────────────────────────────

def cmd_generate(args):
    from faceless_youtube import Pipeline
    cfg = load_config(args.config)
    if args.dry_run:
        info(f"DRY-RUN: would produce video for '{args.topic}' (niche={args.niche}, style={args.style}, upload={args.upload})")
        return 0
    pipeline = Pipeline(cfg)
    result = pipeline.produce_video(
        topic=args.topic, niche=args.niche, style=args.style,
        upload=args.upload, thumbnail_preset=args.preset,
    )
    ok(f"Video produced: {result.get('video_path', 'n/a')}")
    print(json.dumps(result, indent=2, default=str))
    return 0


def cmd_batch(args):
    from faceless_youtube import Pipeline, NicheLibrary, ScriptGenerator
    cfg = load_config(args.config)
    cfg.niche = args.niche
    info(f"Generating {args.count} topics for niche '{args.niche}'")
    if cfg.openai_api_key:
        topics = ScriptGenerator(cfg).suggest_topics(args.niche, args.count)
    else:
        warn("No OpenAI key — using preset topics from niche library")
        topics = NicheLibrary().suggest_trending_topics(args.niche, args.count)
    for i, t in enumerate(topics, 1):
        print(f"  {i:2d}. {t}")
    if args.dry_run:
        return 0
    pipeline = Pipeline(cfg)
    results = pipeline.produce_batch(topics, niche=args.niche, style=args.style, upload=args.upload)
    ok(f"Produced {len(results)} videos")
    return 0


def cmd_thumbnail(args):
    from faceless_youtube import ThumbnailGenerator
    cfg = load_config(args.config)
    if args.image_backend:
        cfg.image_backend = args.image_backend
    gen = ThumbnailGenerator(cfg)
    if args.all:
        paths = gen.generate_all_presets(args.text, output_dir=args.output)
        for p in paths:
            ok(f"Generated: {p}")
    else:
        path = gen.generate(text=args.text, preset=args.preset, output_path=args.output,
                             background_image=args.background)
        ok(f"Thumbnail: {path}")
    return 0


def cmd_schedule(args):
    from faceless_youtube import ContentScheduler, NicheLibrary, ScriptGenerator
    cfg = load_config(args.config)
    sched = ContentScheduler(cfg)
    if cfg.openai_api_key:
        topics = ScriptGenerator(cfg).suggest_topics(args.niche, args.count)
    else:
        topics = NicheLibrary().suggest_trending_topics(args.niche, args.count)
    if args.dry_run:
        info("DRY-RUN: would schedule:")
        for t in topics: print(f"  - {t}")
        return 0
    items = sched.auto_schedule(topics)
    ok(f"Scheduled {len(items)} videos")
    for item in items:
        print(f"  {item.scheduled_date} — {item.topic}")
    return 0


def cmd_run_scheduled(args):
    from faceless_youtube import Pipeline
    cfg = load_config(args.config)
    pipeline = Pipeline(cfg)
    if args.dry_run:
        due = pipeline.scheduler.run_due()
        info(f"DRY-RUN: {len(due)} item(s) due")
        for d in due: print(f"  - {d.topic} (scheduled: {d.scheduled_date})")
        return 0
    results = pipeline.run_scheduled()
    ok(f"Processed {len(results)} scheduled items")
    return 0


def cmd_status(args):
    from faceless_youtube import Pipeline
    cfg = load_config(args.config)
    pipeline = Pipeline(cfg)
    s = pipeline.status()
    print(json.dumps(s, indent=2, default=str))
    return 0


def cmd_topics(args):
    from faceless_youtube import ScriptGenerator, NicheLibrary
    cfg = load_config(args.config)
    cfg.niche = args.niche
    if cfg.openai_api_key:
        topics = ScriptGenerator(cfg).suggest_topics(args.niche, args.count)
    else:
        warn("No OpenAI key — using preset topics from niche library")
        topics = NicheLibrary().get_topics(args.niche)[:args.count]
    print(f"\n{C.B}Topic ideas for {args.niche}:{C.R}")
    for i, t in enumerate(topics, 1): print(f"  {i:2d}. {t}")
    return 0


def cmd_analytics(args):
    from faceless_youtube import AnalyticsTracker
    cfg = load_config(args.config)
    tracker = AnalyticsTracker(cfg)
    print(tracker.generate_report())
    return 0


def cmd_config(args):
    from faceless_youtube import PipelineConfig
    if args.init:
        cfg = PipelineConfig()
        path = args.path or "faceless_config.json"
        cfg.save(path)
        ok(f"Default config written to {path}")
        warn("Edit it to add your API keys before running the pipeline")
        return 0
    if args.show:
        cfg = load_config(args.path)
        print(json.dumps({k: v for k, v in cfg.__dict__.items()}, indent=2, default=str))
        return 0
    err("Specify --init or --show")
    return 1


# ─── Argparse setup ─────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="run_pipeline.py",
        description="Faceless YouTube Automation System")
    p.add_argument("--config", help="Path to JSON config file")
    p.add_argument("--dry-run", action="store_true", help="Show what would happen without executing")
    sub = p.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="Generate a single video")
    g.add_argument("--topic", required=True)
    g.add_argument("--niche", default="space_science")
    g.add_argument("--style", default="documentary",
                   choices=["documentary", "listicle", "explainer", "storytelling", "mystery"])
    g.add_argument("--upload", action="store_true")
    g.add_argument("--preset", type=int, default=1)
    g.set_defaults(func=cmd_generate)

    b = sub.add_parser("batch", help="Generate N videos for a niche")
    b.add_argument("--niche", default="space_science")
    b.add_argument("--count", type=int, default=5)
    b.add_argument("--style", default="documentary")
    b.add_argument("--upload", action="store_true")
    b.set_defaults(func=cmd_batch)

    t = sub.add_parser("thumbnail", help="Generate a thumbnail")
    t.add_argument("--text", required=True)
    t.add_argument("--preset", type=int, default=1, choices=[1, 2, 3, 4, 5, 6])
    t.add_argument("--output")
    t.add_argument("--background", help="Path to a local background image")
    t.add_argument("--image-backend", choices=["none", "fal"],
                   help="Override config.image_backend (fal = nano-banana-2 via fal.ai)")
    t.add_argument("--all", action="store_true", help="Generate all 6 presets")
    t.set_defaults(func=cmd_thumbnail)

    s = sub.add_parser("schedule", help="Schedule videos for production")
    s.add_argument("--niche", default="space_science")
    s.add_argument("--count", type=int, default=10)
    s.set_defaults(func=cmd_schedule)

    rs = sub.add_parser("run-scheduled", help="Process due scheduled items")
    rs.set_defaults(func=cmd_run_scheduled)

    st = sub.add_parser("status", help="Show pipeline status")
    st.set_defaults(func=cmd_status)

    tp = sub.add_parser("topics", help="Suggest topics for a niche")
    tp.add_argument("--niche", default="space_science")
    tp.add_argument("--count", type=int, default=10)
    tp.set_defaults(func=cmd_topics)

    a = sub.add_parser("analytics", help="Show performance report")
    a.set_defaults(func=cmd_analytics)

    c = sub.add_parser("config", help="Manage config file")
    c.add_argument("--init", action="store_true")
    c.add_argument("--show", action="store_true")
    c.add_argument("--path")
    c.set_defaults(func=cmd_config)

    return p


def main() -> int:
    print(BANNER)
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except KeyboardInterrupt:
        warn("Interrupted by user")
        return 130
    except Exception as e:
        err(f"{type(e).__name__}: {e}")
        if "--debug" in sys.argv:
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
