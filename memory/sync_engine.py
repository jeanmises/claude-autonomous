#!/usr/bin/env python3
"""
Autonomous System - Memory Sync Engine
Bidirectional sync between MEMORY.md and metrics database.
"""

import re
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple


# Paths
MEMORY_FILE = Path.home() / ".claude" / "projects" / "-Users-giovanniaffinita" / "memory" / "MEMORY.md"
METRICS_DB = Path.home() / ".claude" / "autonomous" / "metrics.db"


class MemorySyncEngine:
    """Syncs memory between MEMORY.md and database."""

    def __init__(self):
        self.memory_file = MEMORY_FILE
        self.db_path = METRICS_DB

    def sync_to_db(self) -> int:
        """
        Sync MEMORY.md content to database.

        Returns:
            Number of entries synced
        """

        if not self.memory_file.exists():
            print(f"[MemorySync] MEMORY.md not found: {self.memory_file}")
            return 0

        print("[MemorySync] Reading MEMORY.md...")
        with open(self.memory_file, "r") as f:
            content = f.read()

        # Parse memory content
        entries = self._parse_memory_content(content)
        print(f"[MemorySync] Parsed {len(entries)} memory entries")

        # Sync to database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        synced = 0
        for category, key, value in entries:
            cursor.execute("""
                INSERT OR REPLACE INTO memory_context (category, key, value, last_updated)
                VALUES (?, ?, ?, ?)
            """, (category, key, value, datetime.now().isoformat()))
            synced += 1

        conn.commit()
        conn.close()

        print(f"[MemorySync] ✓ Synced {synced} entries to database")
        return synced

    def sync_from_db(self) -> Dict[str, List[Tuple[str, str]]]:
        """
        Read memory context from database.

        Returns:
            Dict of {category: [(key, value), ...]}
        """

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT category, key, value
            FROM memory_context
            ORDER BY category, key
        """)

        memory = {}
        for category, key, value in cursor.fetchall():
            if category not in memory:
                memory[category] = []
            memory[category].append((key, value))

        conn.close()

        return memory

    def _parse_memory_content(self, content: str) -> List[Tuple[str, str, str]]:
        """
        Parse MEMORY.md into structured entries.

        Returns:
            List of (category, key, value) tuples
        """

        entries = []
        current_category = "general"

        lines = content.split("\n")

        for i, line in enumerate(lines):
            # Detect category from headers
            if line.startswith("## "):
                current_category = line.replace("##", "").strip().lower().replace(" ", "_")
                continue

            # Parse key-value patterns
            # Pattern 1: **Key**: Value
            match = re.match(r'\*\*([^*]+)\*\*:\s*(.+)', line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                entries.append((current_category, key, value))
                continue

            # Pattern 2: - Key: Value
            match = re.match(r'-\s+([^:]+):\s*(.+)', line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                entries.append((current_category, key, value))
                continue

            # Pattern 3: Bold text as flag
            if line.startswith("**") and line.endswith("**"):
                key = line.strip("*").strip()
                # Look ahead for next line as value
                if i + 1 < len(lines):
                    value = lines[i + 1].strip()
                    if value:
                        entries.append((current_category, key, value))

        return entries


# CLI test
if __name__ == "__main__":
    engine = MemorySyncEngine()

    print("=" * 60)
    print("Memory Sync Engine Test")
    print("=" * 60)

    # Test 1: Sync to DB
    print("\nTest 1: Sync MEMORY.md to database")
    synced = engine.sync_to_db()
    print(f"Result: {synced} entries synced")

    # Test 2: Read from DB
    print("\nTest 2: Read memory from database")
    memory = engine.sync_from_db()
    print(f"Result: {len(memory)} categories found")

    for category, entries in memory.items():
        print(f"\n  Category: {category}")
        for key, value in entries[:3]:  # Show first 3
            print(f"    - {key}: {value[:50]}...")

    print("\n" + "=" * 60)
    if synced > 0:
        print("✓ Memory sync test PASSED")
    else:
        print("⚠ No memory entries synced (MEMORY.md might be empty)")
    print("=" * 60)
