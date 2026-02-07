#!/usr/bin/env python3
"""
Autonomous System - Heartbeat Engine
Main orchestrator for autonomous task execution cycles.
"""

import json
import sqlite3
import sys
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add router and sandbox to path
sys.path.insert(0, str(Path(__file__).parent.parent / "router"))
sys.path.insert(0, str(Path(__file__).parent.parent / "sandbox"))
sys.path.insert(0, str(Path(__file__).parent))

from risk_scorer import calculate_risk_score
from decision_engine import make_decision, ActionType
from approval_parser import parse_pending_approvals
from orchestrator import SandboxOrchestrator


# Paths
WORKSPACE_ROOT = Path.home() / "Library" / "CloudStorage" / "OneDrive-SAPASPA" / "OD PARA Sales Strategy" / "Claude Workspace"
PENDING_APPROVAL = WORKSPACE_ROOT / "PENDING_APPROVAL.md"
LOCAL_VAULT_DB = WORKSPACE_ROOT / "local_vault.db"
METRICS_DB = Path.home() / ".claude" / "autonomous" / "metrics.db"
KILL_SWITCH = Path.home() / ".claude" / "autonomous" / "KILL_SWITCH"
LOG_DIR = Path.home() / ".claude" / "autonomous" / "logs"


class HeartbeatEngine:
    """Main orchestrator for autonomous execution."""

    def __init__(self, dry_run: bool = True, profile: str = "autonomous"):
        self.dry_run = dry_run
        self.profile = profile
        self.cycle_id = str(uuid.uuid4())[:8]
        self.stats = {
            "discovered": 0,
            "executed": 0,
            "failed": 0,
            "escalated": 0,
            "blocked": 0
        }

    def log(self, message: str, level: str = "INFO"):
        """Log message to console and file."""

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] [Cycle:{self.cycle_id}] {message}"

        print(log_line)

        # Log to file
        log_date = datetime.now().strftime("%Y-%m-%d")
        log_file = LOG_DIR / log_date / "heartbeat.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        with open(log_file, "a") as f:
            f.write(log_line + "\n")

    def check_kill_switch(self) -> bool:
        """Check if kill switch is active."""

        if KILL_SWITCH.exists():
            self.log("Kill switch ACTIVE - aborting cycle", "WARN")
            return True

        return False

    def discover_tasks(self) -> List[Dict[str, Any]]:
        """Discover pending tasks from PENDING_APPROVAL.md and local_vault.db."""

        tasks = []

        # Parse PENDING_APPROVAL.md using enhanced parser
        if PENDING_APPROVAL.exists():
            try:
                approval_tasks = parse_pending_approvals(PENDING_APPROVAL)
                for task in approval_tasks:
                    tasks.append(task)
                    self.log(f"Discovered task from PENDING_APPROVAL: {task['task_id']} ({task['action_type']})")
            except Exception as e:
                self.log(f"Error parsing PENDING_APPROVAL.md: {e}", "ERROR")

        # Query local_vault.db for pending tasks
        if LOCAL_VAULT_DB.exists():
            try:
                conn = sqlite3.connect(str(LOCAL_VAULT_DB))
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT id, task_type, payload
                    FROM tasks
                    WHERE status = 'pending'
                    LIMIT 10
                """)

                for row in cursor.fetchall():
                    task_id, task_type, payload_json = row
                    try:
                        payload = json.loads(payload_json) if payload_json else {}
                        task = {
                            "task_id": f"db_{task_id}",
                            "action_type": task_type,  # Map task_type to action_type
                            "payload": payload,
                            "source": "local_vault.db"
                        }
                        tasks.append(task)
                        self.log(f"Discovered task from DB: {task_id} ({task_type})")
                    except json.JSONDecodeError as e:
                        self.log(f"Invalid payload JSON in task {task_id}: {e}", "ERROR")

                conn.close()
            except sqlite3.Error as e:
                self.log(f"Database query error: {e}", "ERROR")

        self.stats["discovered"] = len(tasks)
        return tasks

    def process_task(self, task: Dict[str, Any]):
        """Process a single task through risk scoring and routing."""

        task_id = task.get("task_id", "unknown")
        action_type = task.get("action_type", "unknown")

        self.log(f"Processing task {task_id} ({action_type})")

        # Calculate risk
        risk_score, risk_level, breakdown = calculate_risk_score(task)
        self.log(f"  Risk Score: {risk_score}/100 ({risk_level.value})")

        # Make routing decision
        action, decision = make_decision(task, self.profile)
        self.log(f"  Decision: {action.value}")

        # Execute via sandbox if not dry-run
        sandbox_score = None
        sandbox_success = False

        if not self.dry_run and action in [ActionType.AUTO_EXECUTE, ActionType.CONDITIONAL_EXECUTE]:
            # Run sandbox test
            self.log(f"  Running sandbox test...", "INFO")

            try:
                target_score = decision.get("sandbox_threshold", 95)
                orchestrator = SandboxOrchestrator(task, max_iterations=5, target_score=target_score)
                sandbox_success, sandbox_score, sandbox_result = orchestrator.run()

                self.log(f"  Sandbox result: score={sandbox_score}/100, success={sandbox_success}", "INFO")
            except Exception as e:
                self.log(f"  Sandbox error: {e}", "ERROR")
                sandbox_score = 0
                sandbox_success = False

        # Update stats based on action and sandbox result
        if action == ActionType.AUTO_EXECUTE:
            if self.dry_run:
                self.stats["executed"] += 1
                self.log(f"  [DRY-RUN] Would auto-execute task {task_id}", "INFO")
            elif sandbox_success:
                self.stats["executed"] += 1
                self.log(f"  ✓ Task executed successfully (score: {sandbox_score}/100)", "INFO")
            else:
                self.stats["failed"] += 1
                self.log(f"  ✗ Task failed sandbox test (score: {sandbox_score}/100)", "WARN")

        elif action == ActionType.CONDITIONAL_EXECUTE:
            if self.dry_run:
                self.log(f"  [DRY-RUN] Would test in sandbox (threshold: {decision['sandbox_threshold']})", "INFO")
                self.stats["escalated"] += 1
            elif sandbox_success and sandbox_score >= decision["sandbox_threshold"]:
                self.stats["executed"] += 1
                self.log(f"  ✓ Task executed (score {sandbox_score} >= threshold {decision['sandbox_threshold']})", "INFO")
            else:
                self.stats["escalated"] += 1
                self.log(f"  Escalating to human (score {sandbox_score} < threshold {decision['sandbox_threshold']})", "WARN")

        elif action == ActionType.ESCALATE_HUMAN:
            self.stats["escalated"] += 1
            self.log(f"  Escalating to human approval", "WARN")
        elif action == ActionType.BLOCK:
            self.stats["blocked"] += 1
            self.log(f"  BLOCKED - Manual review required", "WARN")

        # Record in metrics DB
        if not self.dry_run:
            self._record_metrics(task, risk_score, risk_level.value, decision, sandbox_score)

    def _record_metrics(self, task: Dict[str, Any], risk_score: int, risk_level: str, decision: Dict[str, Any], sandbox_score: int = None):
        """Record execution metrics to database."""

        conn = sqlite3.connect(str(METRICS_DB))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO execution_metrics (
                task_id, task_type, risk_level, risk_score, sandbox_score,
                status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            task.get("task_id"),
            task.get("action_type"),
            risk_level,
            risk_score,
            sandbox_score,
            decision["action"],
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    def record_cycle_health(self, start_time: datetime):
        """Record heartbeat cycle health to database."""

        duration = (datetime.now() - start_time).total_seconds()

        conn = sqlite3.connect(str(METRICS_DB))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO system_health (
                heartbeat_cycle_id, tasks_discovered, tasks_executed,
                tasks_failed, tasks_escalated, cycle_duration_seconds,
                status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.cycle_id,
            self.stats["discovered"],
            self.stats["executed"],
            self.stats["failed"],
            self.stats["escalated"],
            duration,
            "success",
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    def run_cycle(self):
        """Execute one heartbeat cycle."""

        start_time = datetime.now()

        self.log("=" * 60)
        self.log("Heartbeat Cycle Starting")
        self.log(f"Mode: {'DRY-RUN' if self.dry_run else 'LIVE'}")
        self.log(f"Profile: {self.profile}")
        self.log("=" * 60)

        # Check kill switch
        if self.check_kill_switch():
            return

        # Discover tasks
        self.log("Phase 1: Task Discovery")
        tasks = self.discover_tasks()
        self.log(f"  Discovered {len(tasks)} pending tasks")

        if not tasks:
            self.log("No tasks to process - cycle complete")
            self.record_cycle_health(start_time)
            return

        # Process tasks
        self.log("\nPhase 2: Task Processing")
        for i, task in enumerate(tasks, 1):
            self.log(f"\nTask {i}/{len(tasks)}")
            try:
                self.process_task(task)
            except Exception as e:
                self.log(f"Error processing task: {e}", "ERROR")
                self.stats["failed"] += 1

        # Summary
        self.log("\n" + "=" * 60)
        self.log("Cycle Summary")
        self.log("=" * 60)
        self.log(f"Discovered: {self.stats['discovered']}")
        self.log(f"Executed: {self.stats['executed']}")
        self.log(f"Escalated: {self.stats['escalated']}")
        self.log(f"Blocked: {self.stats['blocked']}")
        self.log(f"Failed: {self.stats['failed']}")
        self.log(f"Duration: {(datetime.now() - start_time).total_seconds():.1f}s")

        # Record health
        self.record_cycle_health(start_time)


if __name__ == "__main__":
    # Default is dry-run mode; use --live to execute for real
    dry_run = "--live" not in sys.argv
    run_once = "--run-once" in sys.argv
    verbose = "--verbose" in sys.argv

    engine = HeartbeatEngine(dry_run=dry_run)

    if run_once:
        engine.run_cycle()
    else:
        print("Heartbeat engine requires --run-once flag for manual execution")
        print("For scheduled execution, use launchd (Week 5)")
        sys.exit(1)
