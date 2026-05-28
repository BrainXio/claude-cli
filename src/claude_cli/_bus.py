#!/usr/bin/env python3
"""Bus tool for inter-agent communication during unattended monitoring.

Commands:
    read [N]              Read last N messages (default 10)
    write <json>          Write a JSON message to the bus
    metrics [N]           Check last N hook metrics entries (default 50)
    heartbeat <name>      Post a status heartbeat
    sessions              List unique active sessions from last 60 min
"""

import json
import sys
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

from ._config import INTER_SESSION_BUS

BUS_FILE = INTER_SESSION_BUS


def cmd_read(n=10):
    """Read last N messages from the bus."""
    if not BUS_FILE.exists():
        return []
    with open(BUS_FILE) as f:
        lines = f.readlines()
    return [json.loads(line) for line in lines[-n:]]


def cmd_write(msg_json):
    """Write a JSON message to the bus."""
    msg = json.loads(msg_json)
    if "ts" not in msg:
        msg["ts"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    BUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BUS_FILE, "a") as f:
        f.write(json.dumps(msg, sort_keys=True) + "\n")
    return msg


def cmd_metrics(n=50):
    """Check last N hook metrics entries for failures."""
    results = {}
    for mf in Path.home().rglob("hook_metrics.jsonl"):
        try:
            with open(mf) as f:
                lines = f.readlines()
            entries = [json.loads(line) for line in lines[-n:] if line.strip()]
            failures = [e for e in entries if e.get("failure") is True]
            over_2s = [
                e
                for e in entries
                if isinstance(e.get("duration_ms"), (int, float))
                and e["duration_ms"] > 2000
            ]
            results[str(mf.relative_to(Path.home()))] = {
                "total_entries": len(entries),
                "failures": len(failures),
                "over_2s": len(over_2s),
                "clean": len(failures) == 0 and len(over_2s) == 0,
            }
        except (json.JSONDecodeError, OSError):
            results[str(mf.relative_to(Path.home()))] = {"error": "unreadable"}
    return results


def cmd_heartbeat(session_name):
    """Post a status heartbeat to the bus."""
    metrics = cmd_metrics(50)
    all_clean = all(m.get("clean", False) for m in metrics.values())
    summary = "; ".join(
        f"{k}: {v['failures']} fail, {v['over_2s']} slow"
        for k, v in metrics.items()
        if "error" not in v
    )
    content = f"Session {session_name} alive. Metrics: {summary}. Clean: {all_clean}."
    msg = cmd_write(
        json.dumps(
            {
                "from": session_name,
                "to": "all",
                "type": "status",
                "id": f"{session_name[:3].lower()}-{datetime.now(timezone.utc).strftime('%H%M')}",
                "content": content,
            }
        )
    )
    return msg


def cmd_sessions():
    """List unique active sessions from the last 60 minutes."""
    if not BUS_FILE.exists():
        return {}
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=60)
    sessions = {}
    with open(BUS_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                ts_str = msg.get("ts", "")
                if ts_str.startswith("$("):
                    continue
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    continue
                if ts >= cutoff:
                    sender = msg.get("from", "unknown")
                    sessions[sender] = {
                        "last_seen": ts_str,
                        "last_message": msg.get("content", "")[:80],
                    }
            except json.JSONDecodeError:
                continue
    return sessions


def main():
    parser = argparse.ArgumentParser(description="Inter-agent bus communication tool")
    sub = parser.add_subparsers(dest="command")

    p_read = sub.add_parser("read", help="Read last N messages")
    p_read.add_argument("n", nargs="?", type=int, default=10)

    p_write = sub.add_parser("write", help="Write a JSON message")
    p_write.add_argument("json", help="JSON message string")

    p_metrics = sub.add_parser("metrics", help="Check hook metrics")
    p_metrics.add_argument("n", nargs="?", type=int, default=50)

    p_hb = sub.add_parser("heartbeat", help="Post a status heartbeat")
    p_hb.add_argument("name", help="Session name")

    sub.add_parser("sessions", help="List active sessions")

    args = parser.parse_args()

    if args.command == "read":
        messages = cmd_read(args.n)
        print(json.dumps(messages, indent=2))

    elif args.command == "write":
        result = cmd_write(args.json)
        print(json.dumps(result, indent=2))

    elif args.command == "metrics":
        result = cmd_metrics(args.n)
        print(json.dumps(result, indent=2))

    elif args.command == "heartbeat":
        result = cmd_heartbeat(args.name)
        print(f"Heartbeat posted: {result['id']}")

    elif args.command == "sessions":
        result = cmd_sessions()
        if result:
            print("Active sessions (last 60 min):")
            for name, info in sorted(result.items()):
                print(f"  {name}: last seen {info['last_seen']}")
        else:
            print("No active sessions found.")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
