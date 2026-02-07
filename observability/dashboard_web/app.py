#!/usr/bin/env python3
"""
Autonomous System - Web Dashboard
Flask web interface for monitoring autonomous execution.
"""

from flask import Flask, render_template_string, jsonify
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

app = Flask(__name__)

METRICS_DB = Path.home() / ".claude" / "autonomous" / "metrics.db"
KILL_SWITCH = Path.home() / ".claude" / "autonomous" / "KILL_SWITCH"


def get_db():
    """Get database connection."""
    return sqlite3.connect(str(METRICS_DB))


@app.route("/")
def index():
    """Main dashboard page."""
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/stats")
def api_stats():
    """API: Execution statistics."""

    conn = get_db()
    cursor = conn.cursor()

    # Last 24h stats
    since = (datetime.now() - timedelta(hours=24)).isoformat()

    cursor.execute("""
        SELECT
            COUNT(*) as total,
            AVG(sandbox_score) as avg_score,
            COUNT(CASE WHEN status LIKE '%execute%' THEN 1 END) as executed
        FROM execution_metrics
        WHERE created_at > ?
    """, (since,))

    total, avg_score, executed = cursor.fetchone()

    # Risk distribution
    cursor.execute("""
        SELECT risk_level, COUNT(*) as count
        FROM execution_metrics
        WHERE created_at > ?
        GROUP BY risk_level
    """, (since,))

    risk_dist = dict(cursor.fetchall())

    conn.close()

    return jsonify({
        "total": total or 0,
        "executed": executed or 0,
        "avg_score": round(avg_score, 1) if avg_score else 0,
        "risk_distribution": risk_dist
    })


@app.route("/api/health")
def api_health():
    """API: System health."""

    conn = get_db()
    cursor = conn.cursor()

    # Last heartbeat
    cursor.execute("""
        SELECT created_at
        FROM system_health
        ORDER BY created_at DESC
        LIMIT 1
    """)

    row = cursor.fetchone()
    last_heartbeat = row[0] if row else None

    conn.close()

    # Kill switch status
    kill_switch_active = KILL_SWITCH.exists()

    return jsonify({
        "database": METRICS_DB.exists(),
        "kill_switch": kill_switch_active,
        "last_heartbeat": last_heartbeat,
        "status": "running" if not kill_switch_active else "stopped"
    })


@app.route("/api/recent_tasks")
def api_recent_tasks():
    """API: Recent tasks."""

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT task_id, task_type, risk_score, sandbox_score, status, created_at
        FROM execution_metrics
        ORDER BY created_at DESC
        LIMIT 20
    """)

    tasks = []
    for row in cursor.fetchall():
        tasks.append({
            "task_id": row[0],
            "task_type": row[1],
            "risk_score": row[2],
            "sandbox_score": row[3],
            "status": row[4],
            "created_at": row[5]
        })

    conn.close()

    return jsonify({"tasks": tasks})


# HTML Template (embedded for simplicity)
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Autonomous System Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1a1a1a; color: #fff; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { margin-bottom: 30px; font-size: 32px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card { background: #2a2a2a; padding: 20px; border-radius: 8px; border: 1px solid #3a3a3a; }
        .card h2 { font-size: 14px; color: #888; margin-bottom: 10px; text-transform: uppercase; }
        .card .value { font-size: 36px; font-weight: bold; color: #4ade80; }
        .status { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: bold; }
        .status.running { background: #4ade80; color: #000; }
        .status.stopped { background: #ef4444; color: #fff; }
        table { width: 100%; border-collapse: collapse; background: #2a2a2a; border-radius: 8px; overflow: hidden; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #3a3a3a; }
        th { background: #333; color: #888; font-size: 12px; text-transform: uppercase; }
        .score { font-weight: bold; }
        .score.excellent { color: #4ade80; }
        .score.good { color: #fbbf24; }
        .score.poor { color: #ef4444; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Autonomous System Dashboard</h1>

        <div class="grid">
            <div class="card">
                <h2>Total Tasks (24h)</h2>
                <div class="value" id="total-tasks">-</div>
            </div>
            <div class="card">
                <h2>Executed</h2>
                <div class="value" id="executed-tasks">-</div>
            </div>
            <div class="card">
                <h2>Avg Sandbox Score</h2>
                <div class="value" id="avg-score">-</div>
            </div>
            <div class="card">
                <h2>System Status</h2>
                <span class="status" id="system-status">-</span>
            </div>
        </div>

        <div class="card">
            <h2>Recent Tasks</h2>
            <table id="tasks-table">
                <thead>
                    <tr>
                        <th>Task ID</th>
                        <th>Type</th>
                        <th>Risk</th>
                        <th>Sandbox Score</th>
                        <th>Status</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody id="tasks-body">
                    <tr><td colspan="6" style="text-align:center;color:#888;">Loading...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function updateDashboard() {
            // Fetch stats
            fetch('/api/stats')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('total-tasks').textContent = data.total;
                    document.getElementById('executed-tasks').textContent = data.executed;
                    document.getElementById('avg-score').textContent = data.avg_score + '/100';
                });

            // Fetch health
            fetch('/api/health')
                .then(r => r.json())
                .then(data => {
                    const statusEl = document.getElementById('system-status');
                    statusEl.textContent = data.status.toUpperCase();
                    statusEl.className = 'status ' + data.status;
                });

            // Fetch recent tasks
            fetch('/api/recent_tasks')
                .then(r => r.json())
                .then(data => {
                    const tbody = document.getElementById('tasks-body');
                    tbody.innerHTML = '';

                    data.tasks.forEach(task => {
                        const row = tbody.insertRow();
                        row.innerHTML = `
                            <td>${task.task_id}</td>
                            <td>${task.task_type}</td>
                            <td>${task.risk_score}</td>
                            <td><span class="score ${task.sandbox_score >= 95 ? 'excellent' : task.sandbox_score >= 90 ? 'good' : 'poor'}">${task.sandbox_score || 'N/A'}</span></td>
                            <td>${task.status}</td>
                            <td>${new Date(task.created_at).toLocaleTimeString()}</td>
                        `;
                    });

                    if (data.tasks.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#888;">No tasks yet</td></tr>';
                    }
                });
        }

        // Update every 5 seconds
        updateDashboard();
        setInterval(updateDashboard, 5000);
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    print("Starting Autonomous System Web Dashboard")
    print("=" * 60)
    print("Access at: http://localhost:5050")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5050, debug=False)
