#!/usr/bin/env python3
"""
Autonomous System - Metrics Database Initializer
Creates SQLite database for tracking execution metrics, system health, and notifications.
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime

DB_PATH = Path.home() / ".claude" / "autonomous" / "metrics.db"


def init_database():
    """Initialize metrics database with required tables."""

    # Ensure parent directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Execution metrics table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS execution_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            task_type TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            risk_score INTEGER NOT NULL,
            sandbox_score INTEGER,
            status TEXT NOT NULL,
            execution_time_seconds REAL,
            iterations_count INTEGER DEFAULT 1,
            error_message TEXT,
            snapshot_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)

    # System health table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_health (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            heartbeat_cycle_id TEXT NOT NULL,
            tasks_discovered INTEGER DEFAULT 0,
            tasks_executed INTEGER DEFAULT 0,
            tasks_failed INTEGER DEFAULT 0,
            tasks_escalated INTEGER DEFAULT 0,
            avg_risk_score REAL,
            cycle_duration_seconds REAL,
            status TEXT NOT NULL,
            error_details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # User notifications table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notification_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            task_id TEXT,
            delivered BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            delivered_at TIMESTAMP
        )
    """)

    # Memory context table (for MEMORY.md sync)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory_context (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(category, key)
        )
    """)

    # Create indexes for common queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_execution_created
        ON execution_metrics(created_at DESC)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_execution_status
        ON execution_metrics(status)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_health_created
        ON system_health(created_at DESC)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_notifications_undelivered
        ON user_notifications(delivered, created_at DESC)
    """)

    conn.commit()
    conn.close()

    print(f"✓ Metrics database initialized: {DB_PATH}")
    print(f"  - execution_metrics table created")
    print(f"  - system_health table created")
    print(f"  - user_notifications table created")
    print(f"  - memory_context table created")
    print(f"  - Indexes created")


def verify_database():
    """Verify database structure."""
    if not DB_PATH.exists():
        print(f"✗ Database not found: {DB_PATH}")
        return False

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Check tables
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table'
        ORDER BY name
    """)

    tables = [row[0] for row in cursor.fetchall()]
    expected_tables = [
        'execution_metrics',
        'memory_context',
        'system_health',
        'user_notifications'
    ]

    missing = set(expected_tables) - set(tables)
    if missing:
        print(f"✗ Missing tables: {missing}")
        conn.close()
        return False

    print(f"✓ Database structure verified")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  - {table}: {count} rows")

    conn.close()
    return True


if __name__ == "__main__":
    import sys

    if "--verify" in sys.argv:
        success = verify_database()
        sys.exit(0 if success else 1)
    else:
        init_database()
        verify_database()
