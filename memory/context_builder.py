#!/usr/bin/env python3
"""
Autonomous System - Context Builder
Builds workspace context for informed decision-making.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

METRICS_DB = Path.home() / ".claude" / "autonomous" / "metrics.db"
WORKSPACE_DB = Path.home() / "Library" / "CloudStorage" / "OneDrive-SAPASPA" / "OD PARA Sales Strategy" / "Claude Workspace" / "local_vault.db"


class ContextBuilder:
    """Builds execution context from workspace state."""

    def build_context(self, days: int = 7) -> str:
        """Build markdown context for last N days."""

        context_parts = [
            "# Workspace Context",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            ""
        ]

        # Recent task stats
        context_parts.extend(self._build_task_stats(days))

        # Entity stats
        context_parts.extend(self._build_entity_stats())

        # Memory highlights
        context_parts.extend(self._build_memory_highlights())

        return "\n".join(context_parts)

    def _build_task_stats(self, days: int) -> list:
        """Build recent task statistics."""

        conn = sqlite3.connect(str(METRICS_DB))
        cursor = conn.cursor()

        since = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute("""
            SELECT COUNT(*),
                   AVG(sandbox_score),
                   COUNT(CASE WHEN status LIKE '%execute%' THEN 1 END)
            FROM execution_metrics
            WHERE created_at > ?
        """, (since,))

        total, avg_score, executed = cursor.fetchone()
        conn.close()

        return [
            f"\n## Recent Activity ({days} days)",
            f"- Total tasks: {total or 0}",
            f"- Avg sandbox score: {avg_score:.1f}/100" if avg_score else "- No scores yet",
            f"- Executed: {executed or 0}"
        ]

    def _build_entity_stats(self) -> list:
        """Build entity statistics."""

        try:
            conn = sqlite3.connect(str(WORKSPACE_DB))
            cursor = conn.cursor()

            cursor.execute("SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type")
            stats = cursor.fetchall()
            conn.close()

            lines = ["\n## Workspace Entities"]
            for entity_type, count in stats:
                lines.append(f"- {entity_type}: {count}")

            return lines
        except:
            return ["\n## Workspace Entities", "- (Unable to read)"]

    def _build_memory_highlights(self) -> list:
        """Build memory highlights."""

        conn = sqlite3.connect(str(METRICS_DB))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT category, COUNT(*)
            FROM memory_context
            GROUP BY category
        """)

        stats = cursor.fetchall()
        conn.close()

        lines = ["\n## Memory Context"]
        for category, count in stats:
            lines.append(f"- {category}: {count} entries")

        return lines if stats else ["\n## Memory Context", "- (No memory loaded)"]


if __name__ == "__main__":
    builder = ContextBuilder()
    context = builder.build_context(days=7)
    print(context)
