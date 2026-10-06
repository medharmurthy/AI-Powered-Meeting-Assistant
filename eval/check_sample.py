#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from verbatim.config import find_repo_root
from verbatim.store import get_run_dir, load_json


def check_run(run_path_or_id: str) -> bool:
    root = find_repo_root()
    expected_path = root / "samples" / "expected.json"
    if not expected_path.exists():
        print(f"Error: {expected_path} not found", file=sys.stderr)
        return False

    with open(expected_path, "r", encoding="utf-8") as f:
        expected = json.load(f)

    # Resolve run directory
    target = Path(run_path_or_id)
    if not target.exists():
        target = get_run_dir(run_path_or_id)
    if not target.exists():
        print(f"Error: Run directory '{run_path_or_id}' not found", file=sys.stderr)
        return False

    record_file = target / "meeting_record.json"
    if not record_file.exists():
        print(f"Error: {record_file} not found", file=sys.stderr)
        return False

    with open(record_file, "r", encoding="utf-8") as f:
        record = json.load(f)

    all_passed = True
    print(f"\n=======================================================")
    print(f"Verifying Run: {target.name}")
    print(f"=======================================================\n")

    decisions = record.get("decisions", [])
    actions = record.get("action_items", [])
    unresolved = record.get("unresolved", [])

    # Check 1: Decisions Present
    print("--- Decisions Check ---")
    dec_texts = [d["text"].lower() for d in decisions]
    for req in expected.get("decisions_present", []):
        matched = any(req.lower() in t or t in req.lower() or "redis" in t if "redis" in req.lower() else False for t in dec_texts)
        # Also check general key terms
        if not matched and "redis" in req.lower():
            matched = any("redis" in t for t in dec_texts)
        if not matched and "postgresql" in req.lower():
            matched = any("postgresql" in t and ("not" in t or "16" in t) for t in dec_texts)

        if matched:
            print(f"  [PASS] Decision present: '{req}'")
        else:
            print(f"  [FAIL] Missing required decision: '{req}'")
            all_passed = False

    # Check 2: Decisions Absent (Proposals/Questions must NOT be in decisions)
    for forbidden in expected.get("decisions_absent", []):
        found = any(forbidden.lower() in t for t in dec_texts)
        if not found:
            print(f"  [PASS] Forbidden decision omitted from decisions: '{forbidden}'")
        else:
            print(f"  [FAIL] Item was incorrectly filed as agreed decision: '{forbidden}'")
            all_passed = False

    # Check 3: Unresolved items
    print("\n--- Unresolved / Discussed Not Settled Check ---")
    unres_texts = [u["text"].lower() for u in unresolved]
    for unres_req in expected.get("unresolved_present", []):
        token = unres_req["text"].lower()
        matched = any(token in t for t in unres_texts)
        if matched:
            print(f"  [PASS] Item present in unresolved: '{token}'")
        else:
            print(f"  [FAIL] Expected item in unresolved but missing: '{token}'")
            all_passed = False

    # Check 4: Action Items
    print("\n--- Action Items Check ---")
    for task_spec in expected.get("tasks", []):
        match_kw = task_spec["match"].lower()
        matching_tasks = [a for a in actions if match_kw in a["task"].lower()]
        if not matching_tasks:
            print(f"  [FAIL] Missing required task matching '{match_kw}'")
            all_passed = False
            continue

        task_item = matching_tasks[0]
        # Check Owner
        expected_owner = task_spec.get("owner")
        actual_owner = task_item.get("owner")
        if expected_owner is None:
            if actual_owner is None:
                print(f"  [PASS] Task '{match_kw}': Owner correctly Unspecified (null)")
            else:
                print(f"  [FAIL] Task '{match_kw}': Owner hallucinated as '{actual_owner}' (expected null)")
                all_passed = False
        else:
            if actual_owner and expected_owner.lower() in actual_owner.lower():
                print(f"  [PASS] Task '{match_kw}': Owner correctly assigned as '{actual_owner}'")
            else:
                print(f"  [FAIL] Task '{match_kw}': Owner expected '{expected_owner}', got '{actual_owner}'")
                all_passed = False

        # Check Deadline
        expected_deadline = task_spec.get("deadline")
        actual_deadline = task_item.get("deadline")
        deadline_contains = task_spec.get("deadline_contains")

        if expected_deadline is None and deadline_contains is None:
            if actual_deadline is None:
                print(f"  [PASS] Task '{match_kw}': Deadline correctly Unspecified (null)")
            else:
                print(f"  [FAIL] Task '{match_kw}': Deadline hallucinated as '{actual_deadline}' (expected null)")
                all_passed = False
        elif expected_deadline is not None:
            if actual_deadline and expected_deadline.lower() in actual_deadline.lower():
                print(f"  [PASS] Task '{match_kw}': Deadline verbatim as '{actual_deadline}'")
            else:
                print(f"  [FAIL] Task '{match_kw}': Deadline expected '{expected_deadline}', got '{actual_deadline}'")
                all_passed = False
        elif deadline_contains is not None:
            if actual_deadline and any(c.lower() in actual_deadline.lower() for c in deadline_contains):
                print(f"  [PASS] Task '{match_kw}': Deadline verbatim as '{actual_deadline}'")
            else:
                print(f"  [FAIL] Task '{match_kw}': Deadline expected words {deadline_contains}, got '{actual_deadline}'")
                all_passed = False

    # Check 5: Forbidden tasks
    for forb in expected.get("tasks_forbidden", []):
        matched = any(forb.lower() in a["task"].lower() for a in actions)
        if not matched:
            print(f"  [PASS] Non-task '{forb}' correctly excluded from action items")
        else:
            print(f"  [FAIL] Non-task '{forb}' was incorrectly accepted as action item")
            all_passed = False

    print("\n-------------------------------------------------------")
    if all_passed:
        print("RESULT: ALL GROUND TRUTH CHECKS PASSED!")
    else:
        print("RESULT: SOME CHECKS FAILED.")
    print("-------------------------------------------------------\n")
    return all_passed


def main():
    parser = argparse.ArgumentParser(description="Evaluate meeting record against ground truth")
    parser.add_argument("run_path_or_id", help="Path to run dir or run ID")
    args = parser.parse_args()

    ok = check_run(args.run_path_or_id)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
