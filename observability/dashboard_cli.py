#!/usr/bin/env python3
"""
Autonomous System - CLI Dashboard
Command-line interface for monitoring and control.
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional


DB_PATH = Path.home() / ".claude" / "autonomous" / "metrics.db"
KILL_SWITCH = Path.home() / ".claude" / "autonomous" / "KILL_SWITCH"


def get_stats(hours: int = 24) -> dict:
    """Get execution statistics for last N hours."""

    if not DB_PATH.exists():
        return {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "rolled_back": 0,
            "avg_execution_time": 0,
            "avg_sandbox_score": 0
        }

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    since = datetime.now() - timedelta(hours=hours)

    # Overall stats
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN status = 'rolled_back' THEN 1 ELSE 0 END) as rolled_back,
            AVG(execution_time_seconds) as avg_exec_time,
            AVG(sandbox_score) as avg_sandbox_score
        FROM execution_metrics
        WHERE created_at > ?
    """, (since.isoformat(),))

    row = cursor.fetchone()

    stats = {
        "total": row[0] or 0,
        "successful": row[1] or 0,
        "failed": row[2] or 0,
        "rolled_back": row[3] or 0,
        "avg_execution_time": round(row[4], 1) if row[4] else 0,
        "avg_sandbox_score": round(row[5], 1) if row[5] else 0
    }

    # Risk distribution
    cursor.execute("""
        SELECT risk_level, COUNT(*) as count
        FROM execution_metrics
        WHERE created_at > ?
        GROUP BY risk_level
    """, (since.isoformat(),))

    stats["risk_distribution"] = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()
    return stats


def get_health() -> dict:
    """Get system health status."""

    health = {
        "database": DB_PATH.exists(),
        "kill_switch": KILL_SWITCH.exists(),
        "last_heartbeat": None
    }

    if health["database"]:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT created_at
            FROM system_health
            ORDER BY created_at DESC
            LIMIT 1
        """)

        row = cursor.fetchone()
        if row:
            health["last_heartbeat"] = row[0]

        conn.close()

    return health


def get_recent_logs(lines: int = 20) -> list:
    """Get recent log entries."""

    log_dir = Path.home() / ".claude" / "autonomous" / "logs"
    today_log = log_dir / datetime.now().strftime("%Y-%m-%d") / "execution.log"

    if not today_log.exists():
        return []

    with open(today_log, "r") as f:
        all_lines = f.readlines()
        return all_lines[-lines:]


def activate_kill_switch():
    """Activate kill switch to stop autonomous execution."""

    KILL_SWITCH.parent.mkdir(parents=True, exist_ok=True)
    KILL_SWITCH.touch()

    print("=" * 60)
    print("KILL SWITCH ACTIVATED")
    print("=" * 60)
    print(f"\nKill switch file created: {KILL_SWITCH}")
    print("\nAutonomous execution will stop at next heartbeat check.")
    print("\nTo resume, delete the kill switch file:")
    print(f"  rm {KILL_SWITCH}")


def deactivate_kill_switch():
    """Deactivate kill switch to resume autonomous execution."""

    if KILL_SWITCH.exists():
        KILL_SWITCH.unlink()
        print("✓ Kill switch deactivated. Autonomous execution will resume.")
    else:
        print("Kill switch was not active.")


def print_stats(hours: int = 24):
    """Print execution statistics."""

    stats = get_stats(hours)

    print("=" * 60)
    print(f"Execution Stats (Last {hours}h)")
    print("=" * 60)

    print(f"\nTotal Tasks: {stats['total']}")

    if stats['total'] > 0:
        success_pct = (stats['successful'] / stats['total']) * 100
        print(f"Successful: {stats['successful']} ({success_pct:.1f}%)")
        print(f"Failed: {stats['failed']}")
        print(f"Rolled Back: {stats['rolled_back']}")

        print(f"\nAvg Execution Time: {stats['avg_execution_time']:.1f}s")
        print(f"Avg Sandbox Score: {stats['avg_sandbox_score']:.1f}/100")

        if stats['risk_distribution']:
            print(f"\nRisk Distribution:")
            for level, count in sorted(stats['risk_distribution'].items()):
                print(f"  {level}: {count}")
    else:
        print("No tasks executed in this time period.")


def print_health():
    """Print system health status."""

    health = get_health()

    print("=" * 60)
    print("System Health")
    print("=" * 60)

    print(f"\nDatabase: {'✓ OK' if health['database'] else '✗ NOT FOUND'}")
    print(f"Kill Switch: {'⚠ ACTIVE' if health['kill_switch'] else '✓ Inactive'}")

    if health['last_heartbeat']:
        last_beat = datetime.fromisoformat(health['last_heartbeat'])
        minutes_ago = (datetime.now() - last_beat).total_seconds() / 60
        print(f"Last Heartbeat: {minutes_ago:.1f} minutes ago")

        if minutes_ago > 20:
            print("  ⚠ Warning: No heartbeat in >20 minutes")
    else:
        print("Last Heartbeat: Never")


def print_logs(lines: int = 20):
    """Print recent log entries."""

    logs = get_recent_logs(lines)

    print("=" * 60)
    print(f"Recent Logs (last {len(logs)} lines)")
    print("=" * 60)

    if logs:
        for line in logs:
            print(line.rstrip())
    else:
        print("\nNo logs found for today.")


def print_usage():
    """Print usage instructions."""

    print("""
Autonomous System - CLI Dashboard

Usage:
  dashboard_cli.py --stats [hours]    Show execution statistics (default: 24h)
  dashboard_cli.py --health           Show system health status
  dashboard_cli.py --logs [lines]     Show recent log entries (default: 20)
  dashboard_cli.py --kill             Activate kill switch (stop execution)
  dashboard_cli.py --resume           Deactivate kill switch (resume execution)
  dashboard_cli.py --help             Show this help message

Examples:
  dashboard_cli.py --stats             # Last 24h stats
  dashboard_cli.py --stats 168         # Last 7 days stats
  dashboard_cli.py --logs 50           # Last 50 log lines
  dashboard_cli.py --kill              # Emergency stop
""")


if __name__ == "__main__":
    if len(sys.argv) == 1 or "--help" in sys.argv:
        print_usage()
        sys.exit(0)

    if "--stats" in sys.argv:
        idx = sys.argv.index("--stats")
        hours = int(sys.argv[idx + 1]) if len(sys.argv) > idx + 1 and sys.argv[idx + 1].isdigit() else 24
        print_stats(hours)

    elif "--health" in sys.argv:
        print_health()

    elif "--logs" in sys.argv:
        idx = sys.argv.index("--logs")
        lines = int(sys.argv[idx + 1]) if len(sys.argv) > idx + 1 and sys.argv[idx + 1].isdigit() else 20
        print_logs(lines)

    elif "--kill" in sys.argv:
        activate_kill_switch()

    elif "--resume" in sys.argv:
        deactivate_kill_switch()

    else:
        print_usage()
        sys.exit(1)
