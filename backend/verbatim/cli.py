from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sys
import time

from verbatim.config import find_repo_root, get_config, load_config
from verbatim.errors import PipelineError
from verbatim.ingest import process_audio_file, validate_file_extension
from verbatim.refine import refine_transcript
from verbatim.stt import format_time, transcribe_audio
from verbatim.store import (
    create_run,
    get_run_dir,
    load_json,
    load_meta,
    save_meta,
)


def main():
    parser = argparse.ArgumentParser(description="Verbatim CLI runner")
    parser.add_argument("file", help="Path to input audio/video recording")
    parser.add_argument(
        "--stage",
        choices=["stt", "refine", "document", "all"],
        default="stt",
        help="Stage to execute (default: stt)",
    )
    parser.add_argument(
        "--profile",
        choices=["lite", "standard", "quality"],
        help="Profile override",
    )
    parser.add_argument(
        "--glossary",
        nargs="*",
        default=[],
        help="Glossary terms to listen for",
    )
    parser.add_argument(
        "--participants",
        nargs="*",
        default=[],
        help="Participants in the meeting",
    )
    parser.add_argument(
        "--model",
        help="STT model name override (e.g. tiny, distil-large-v3)",
    )

    args = parser.parse_args()

    if args.profile:
        os.environ["VERBATIM_PROFILE"] = args.profile
        load_config(reload=True)

    cfg = get_config()
    input_path = Path(args.file).resolve()
    if not input_path.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    print(f"Verbatim CLI | File: {input_path.name} | Profile: {cfg.active_profile}")

    # Validate extension
    try:
        ext = validate_file_extension(input_path.name, cfg.limits.allowed_ext)
    except PipelineError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Ingest file
    run_id = create_run(filename=input_path.name)
    run_dir = get_run_dir(run_id)
    dest_original = run_dir / f"original.{ext}"
    shutil.copy2(input_path, dest_original)

    # Parse glossary & participants
    glossary = []
    for g in args.glossary:
        glossary.extend([x.strip() for x in g.split(",") if x.strip()])
    participants = []
    for p in args.participants:
        participants.extend([x.strip() for x in p.split(",") if x.strip()])

    save_meta(
        run_id,
        {
            "glossary": glossary,
            "participants": participants,
        },
    )

    print(f"Ingesting {input_path.name} (run_id: {run_id})...")
    try:
        ingest_res = process_audio_file(run_id, dest_original)
        print(f"Audio ready: duration {ingest_res['duration']:.2f}s, RMS {ingest_res['rms_dbfs']:.1f} dBFS")
    except PipelineError as e:
        print(f"Ingest failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Run STT stage
    if args.stage in ("stt", "refine", "all"):
        print("\n--- Transcription ---")
        t_start = time.time()

        def on_progress(done: float, total: float, label: str):
            pass

        try:
            raw_transcript = transcribe_audio(
                run_id=run_id,
                model_override=args.model,
                progress_callback=on_progress,
            )
            for seg in raw_transcript.segments:
                start_str = format_time(seg.start)
                end_str = format_time(seg.end)
                print(f"[{start_str} - {end_str}] {seg.text}")

            t_elapsed = time.time() - t_start
            print(
                f"\nSTT completed in {t_elapsed:.2f}s "
                f"({len(raw_transcript.segments)} segments, model: {raw_transcript.model}, device: {raw_transcript.device})"
            )
        except PipelineError as e:
            print(f"Transcription failed: {e}", file=sys.stderr)
            sys.exit(1)

    # Run Refine stage
    if args.stage in ("refine", "all"):
        print("\n--- Refinement ---")
        t_ref_start = time.time()
        try:
            refined = refine_transcript(run_id=run_id)
            print(f"Domain: {refined.profile.domain} | Topic: {refined.profile.topic}")
            print(f"Likely terms: {', '.join(refined.profile.likely_terms[:10])}...")
            applied_cnt = sum(1 for c in refined.corrections if c.status == "applied")
            blocked_cnt = sum(1 for c in refined.corrections if c.status == "blocked")
            print(f"Corrections: {applied_cnt} applied, {blocked_cnt} blocked")
            for c in refined.corrections:
                flag = "[APPLIED]" if c.status == "applied" else f"[BLOCKED: {c.block_reason}]"
                print(f"  {flag} Line {c.segment_id}: '{c.original}' -> '{c.corrected}' ({c.reason})")
            t_ref_elapsed = time.time() - t_ref_start
            print(f"Refinement completed in {t_ref_elapsed:.2f}s (model: {refined.model})")
        except PipelineError as e:
            print(f"Refinement failed: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
