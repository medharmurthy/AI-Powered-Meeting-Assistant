from __future__ import annotations

import argparse
import json
import sys
import time

from verbatim.config import get_config
from verbatim.document.stage import document_meeting
from verbatim.store import get_run_dir, list_runs, load_json


def main():
    parser = argparse.ArgumentParser(description="Verbatim Phase 4 Document Stage Runner")
    parser.add_argument("run_id", help="Run ID to document (e.g. 20261005-...)")
    args = parser.parse_args()

    cfg = get_config()
    run_dir = get_run_dir(args.run_id)
    if not run_dir.exists():
        print(f"Error: Run directory {args.run_id} does not exist", file=sys.stderr)
        sys.exit(1)

    print(f"Executing Phase 4 Documentation on Run ID: {args.run_id}")
    print(f"Profile: {cfg.active_profile} | Documenter model: {cfg.active_profile_config.documenter.model}")

    t0 = time.time()
    try:
        record = document_meeting(args.run_id)
        elapsed = time.time() - t0
        print(f"\nDocumentation stage completed in {elapsed:.2f}s!")
        print(f"Title: {record.title}")
        print(f"Summary: {record.summary}")
        print(f"Attendees: {', '.join(record.attendees)}")
        print(f"\nMinutes Topics ({len(record.minutes)}):")
        for topic in record.minutes:
            print(f"  • {topic.title} ({len(topic.points)} points)")
        print(f"\nDecisions ({len(record.decisions)}):")
        for d in record.decisions:
            print(f"  [{d.id}] {d.text} (lines: {d.segment_ids})")
        print(f"\nAction Items ({len(record.action_items)}):")
        for a in record.action_items:
            owner_str = a.owner or "Unspecified"
            deadline_str = a.deadline or "Unspecified"
            print(f"  [{a.id}] {a.task} | Owner: {owner_str} | Deadline: {deadline_str} (lines: {a.segment_ids})")
        print(f"\nDiscussed, Not Settled ({len(record.unresolved)}):")
        for u in record.unresolved:
            print(f"  [{u.id}] ({u.kind}) {u.text} (lines: {u.segment_ids})")
        if record.dropped:
            print(f"\nDropped/Filtered Items ({len(record.dropped)}):")
            for dr in record.dropped:
                print(f"  [{dr.section}] '{dr.text}' -> Reason: {dr.reason}")

        output_file = run_dir / "meeting_record.json"
        print(f"\nOutput saved to: {output_file}")
    except Exception as e:
        print(f"Failed to document meeting: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
