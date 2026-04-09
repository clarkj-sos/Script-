#!/usr/bin/env python3
"""
Fal.ai Seedance 2.0 image-to-video endpoint verification.

Run this LOCALLY (not in the sandbox — sandbox blocks fal.ai egress) with your
FAL_KEY set. It will:

  1. Try a list of candidate model IDs until one accepts the request
  2. Submit a tiny test image with a simple prompt
  3. Download the resulting video
  4. Print the EXACT response shape I need to finalize seedance_client.py

Prerequisites:
    pip install fal-client pillow httpx
    export FAL_KEY=your_fal_key_here

Usage:
    python verify_seedance.py

Optional flags:
    python verify_seedance.py --image path/to/real.jpg
    python verify_seedance.py --prompt "your prompt here"
    python verify_seedance.py --model fal-ai/exact/endpoint/id
"""
from __future__ import annotations

import argparse
import json
import os
import pprint
import sys
import tempfile
import traceback
from pathlib import Path


# ---- Candidate model IDs to try (in order) -------------------------------
# If you already know the exact ID from the fal.ai dashboard, pass --model.
CANDIDATE_MODEL_IDS = [
    "fal-ai/bytedance/seedance/v2/pro/image-to-video",
    "fal-ai/bytedance/seedance/v2/image-to-video",
    "fal-ai/bytedance/seedance-v2-pro/image-to-video",
    "fal-ai/bytedance/seedance-pro-i2v",
    "fal-ai/bytedance-seedance-v2-i2v",
    "fal-ai/bytedance/seedance-v2/image-to-video",
]


def make_test_image(path: Path) -> None:
    """Create a 1024x576 test image with readable text."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("ERROR: Pillow not installed. Run: pip install pillow")
        sys.exit(1)

    img = Image.new("RGB", (1024, 576), (18, 24, 48))
    draw = ImageDraw.Draw(img)
    # Draw some simple geometric content so Seedance has something to animate
    draw.ellipse((412, 188, 612, 388), fill=(255, 180, 60), outline=(255, 255, 255), width=4)
    draw.rectangle((0, 520, 1024, 576), fill=(8, 12, 24))
    draw.text((20, 535), "seedance api verification", fill=(200, 200, 200))
    img.save(path, "JPEG", quality=90)


def try_model(model_id: str, image_url: str, prompt: str) -> dict | None:
    """Attempt one model ID. Returns the raw response dict on success, None on failure."""
    import fal_client

    # Different Seedance builds use slightly different field names. Start with
    # the most common shape; if it errors with "unknown field" we will log it.
    arguments = {
        "image_url": image_url,
        "prompt": prompt,
        "duration": 5,
        "aspect_ratio": "16:9",
        "resolution": "1080p",
    }

    print(f"\n── Trying model: {model_id}")
    print(f"   Arguments: {json.dumps(arguments, indent=2)}")

    try:
        result = fal_client.subscribe(
            model_id,
            arguments=arguments,
            with_logs=True,
            on_queue_update=lambda update: print(f"   queue: {type(update).__name__}"),
        )
        print(f"   ✓ Accepted")
        return result
    except Exception as exc:
        msg = str(exc)
        # Truncate huge tracebacks in the summary line
        print(f"   ✗ Failed: {type(exc).__name__}: {msg[:200]}")
        return None


def download_video(url: str, out_path: Path) -> int:
    """Download the generated video via httpx. Returns byte count."""
    try:
        import httpx
    except ImportError:
        print("(skipping download — httpx not installed)")
        return 0
    with httpx.stream("GET", url, follow_redirects=True, timeout=120.0) as r:
        r.raise_for_status()
        total = 0
        with open(out_path, "wb") as f:
            for chunk in r.iter_bytes(chunk_size=65536):
                f.write(chunk)
                total += len(chunk)
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify fal.ai Seedance 2.0 endpoint")
    parser.add_argument("--image", help="Path to seed image (default: generate a tiny test image)")
    parser.add_argument("--prompt", default="slow cinematic zoom in, dramatic lighting, 4k",
                        help="Prompt for the video generation")
    parser.add_argument("--model", help="Exact model ID (skips candidate loop)")
    parser.add_argument("--out", default="seedance_verification_output.mp4",
                        help="Where to save the downloaded video")
    args = parser.parse_args()

    # ---- Preflight ------------------------------------------------------
    api_key = os.environ.get("FAL_KEY") or os.environ.get("FAL_API_KEY")
    if not api_key:
        print("ERROR: FAL_KEY environment variable not set.")
        print("       export FAL_KEY=your_key_here")
        return 1
    os.environ["FAL_KEY"] = api_key  # fal_client reads this

    try:
        import fal_client  # noqa: F401
    except ImportError:
        print("ERROR: fal-client not installed. Run: pip install fal-client")
        return 1

    # ---- Upload (or make) the seed image -------------------------------
    import fal_client

    if args.image:
        image_path = Path(args.image)
        if not image_path.exists():
            print(f"ERROR: image not found: {image_path}")
            return 1
    else:
        image_path = Path(tempfile.gettempdir()) / "seedance_verify_seed.jpg"
        make_test_image(image_path)
        print(f"Generated test image: {image_path}")

    print(f"\n→ Uploading seed image to fal.ai…")
    try:
        image_url = fal_client.upload_file(str(image_path))
        print(f"   image_url: {image_url}")
    except Exception as exc:
        print(f"ERROR: image upload failed: {type(exc).__name__}: {exc}")
        return 1

    # ---- Try each candidate ID until one works -------------------------
    model_ids = [args.model] if args.model else CANDIDATE_MODEL_IDS
    result = None
    winning_model = None
    for mid in model_ids:
        result = try_model(mid, image_url, args.prompt)
        if result is not None:
            winning_model = mid
            break

    if result is None:
        print("\n✗ All candidate model IDs failed.")
        print("  Check https://fal.ai/models (search for 'seedance') for the exact route.")
        print("  Then re-run with: python verify_seedance.py --model fal-ai/<exact/id>")
        return 2

    # ---- Print the full response shape ---------------------------------
    print("\n" + "=" * 70)
    print("  SUCCESS — paste everything between the === markers back to me")
    print("=" * 70)
    print(f"\nWinning model_id: {winning_model}")
    print(f"\nPrompt used: {args.prompt!r}")
    print(f"\nFull response (JSON):")
    try:
        print(json.dumps(result, indent=2, default=str))
    except Exception:
        pprint.pprint(result)

    # ---- Map out the response schema -----------------------------------
    print(f"\nTop-level keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
    if isinstance(result, dict):
        for k, v in result.items():
            print(f"  result[{k!r}] → {type(v).__name__}", end="")
            if isinstance(v, dict):
                print(f" with keys {list(v.keys())}")
            elif isinstance(v, list):
                print(f" of len {len(v)}" + (f" first={type(v[0]).__name__}" if v else ""))
            else:
                # truncate long strings
                s = repr(v)
                print(f" = {s[:100]}{'…' if len(s) > 100 else ''}")

    # ---- Find the video URL in the response ----------------------------
    video_url = None
    if isinstance(result, dict):
        # Most common: result["video"]["url"]
        v = result.get("video")
        if isinstance(v, dict):
            video_url = v.get("url")
        elif isinstance(v, str):
            video_url = v
        # Alternates: result["url"], result["output"]["url"]
        video_url = video_url or result.get("url")
        out = result.get("output")
        if not video_url and isinstance(out, dict):
            video_url = out.get("url")
        if not video_url and isinstance(out, list) and out:
            if isinstance(out[0], dict):
                video_url = out[0].get("url")

    if video_url:
        print(f"\n✓ Detected video URL: {video_url}")
        out_path = Path(args.out).resolve()
        try:
            n = download_video(video_url, out_path)
            print(f"  Downloaded {n:,} bytes → {out_path}")
        except Exception as exc:
            print(f"  (download failed: {exc})")
    else:
        print("\n⚠ Could not auto-locate a video URL in the response.")
        print("  Please tell me which field holds the MP4 URL.")

    # ---- Print the exact info I need ----------------------------------
    print("\n" + "=" * 70)
    print("  WHAT TO PASTE BACK TO ME")
    print("=" * 70)
    print("""
1. The `Winning model_id` line above
2. The full JSON response (everything under "Full response (JSON):")
3. The exact path to the MP4 URL inside the response
   (e.g. result["video"]["url"] or result["output"][0]["url"])
4. Any arguments you had to tweak (did `duration`, `aspect_ratio`, or
   `resolution` get rejected? any other required fields?)
5. Approximate cost of this one call if shown in the fal.ai dashboard
""")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
