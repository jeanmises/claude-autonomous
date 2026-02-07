#!/usr/bin/env python3
"""
Autonomous System - Notification System
macOS native notifications for autonomous events.
"""

import subprocess
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

METRICS_DB = Path.home() / ".claude" / "autonomous" / "metrics.db"


class Notifier:
    """Sends macOS notifications for autonomous events."""

    def __init__(self):
        self.enabled = True

    def notify(self, title: str, message: str, sound: str = "default") -> bool:
        """
        Send macOS notification.

        Args:
            title: Notification title
            message: Notification message
            sound: Sound name (default, glass, submarine, etc.)

        Returns:
            True if sent successfully
        """

        if not self.enabled:
            return False

        try:
            # Use osascript for native macOS notifications
            script = f'''
            display notification "{message}" with title "{title}" sound name "{sound}"
            '''

            result = subprocess.run(
                ["/usr/bin/osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                self._log_notification(title, message)
                return True
            else:
                print(f"[Notifier] Failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"[Notifier] Error: {e}")
            return False

    def notify_task_completed(self, task_id: str, score: int):
        """Notify task completion."""
        return self.notify(
            "Task Completed",
            f"Task {task_id} executed successfully (score: {score}/100)",
            sound="Glass"
        )

    def notify_task_failed(self, task_id: str, reason: str):
        """Notify task failure."""
        return self.notify(
            "Task Failed",
            f"Task {task_id} failed: {reason[:50]}...",
            sound="Basso"
        )

    def notify_high_risk_escalated(self, task_id: str, risk_score: int):
        """Notify HIGH risk escalation."""
        return self.notify(
            "High Risk Task",
            f"Task {task_id} escalated (risk: {risk_score}/100)",
            sound="Submarine"
        )

    def notify_system_error(self, error: str):
        """Notify system error."""
        return self.notify(
            "System Error",
            f"Autonomous system error: {error[:50]}...",
            sound="Funk"
        )

    def _log_notification(self, title: str, message: str):
        """Log notification to database."""

        try:
            conn = sqlite3.connect(str(METRICS_DB))
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO user_notifications (notification_type, severity, title, message, delivered, created_at, delivered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("system", "info", title, message, 1, datetime.now().isoformat(), datetime.now().isoformat()))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Notifier] Log error: {e}")


# CLI test
if __name__ == "__main__":
    notifier = Notifier()

    print("Testing macOS Notification System")
    print("=" * 60)

    # Test 1: Simple notification
    print("\nTest 1: Simple notification")
    success = notifier.notify("Test Notification", "This is a test from autonomous system")
    print(f"Result: {'✓ Sent' if success else '✗ Failed'}")

    # Test 2: Task completed
    print("\nTest 2: Task completed notification")
    success = notifier.notify_task_completed("test_task_1", 98)
    print(f"Result: {'✓ Sent' if success else '✗ Failed'}")

    # Test 3: Task failed
    print("\nTest 3: Task failed notification")
    success = notifier.notify_task_failed("test_task_2", "Database connection timeout")
    print(f"Result: {'✓ Sent' if success else '✗ Failed'}")

    print("\n" + "=" * 60)
    print("Check your macOS notifications to verify!")
