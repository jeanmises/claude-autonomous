# Claude Code Autonomous System

Sistema di autonomia per trasformare Claude Code da reattivo a proattivo con esecuzione automatica task.

## Status: Week 6 Complete ✓

**Milestone**: Web Dashboard + Full Autonomous Mode

**Completato**:
- ✓ Directory structure creata
- ✓ Metrics database (SQLite) inizializzato
- ✓ Risk Scorer implementato e testato (5/5 tests passed)
- ✓ Decision Router implementato e testato (4/4 tests passed)
- ✓ Autonomous Profile configurato
- ✓ CLI Dashboard (basic version)
- ✓ Heartbeat Engine (dry-run mode) testato
- ✓ Integration con local_vault.db verificata
- ✓ Sandbox Executor con fix automatici (Week 2)
- ✓ Production Executor con rollback (Week 3)
- ✓ Memory Sync Engine bidirezionale (Week 4)
- ✓ Launchd scheduling (15 minuti) (Week 5)
- ✓ macOS Notifications (Week 5)
- ✓ Web Dashboard Flask (Week 6)

## Quick Start

### Test Heartbeat Discovery
```bash
# Run manual heartbeat cycle (dry-run)
python3 ~/.claude/autonomous/heartbeat/engine.py --dry-run --run-once

# Check system health
python3 ~/.claude/autonomous/observability/dashboard_cli.py --health

# View stats
python3 ~/.claude/autonomous/observability/dashboard_cli.py --stats
```

### Risk Scoring
```bash
# Test risk scorer
python3 ~/.claude/autonomous/router/risk_scorer.py --test

# Score specific task
python3 ~/.claude/autonomous/router/risk_scorer.py --score task.json
```

### Decision Routing
```bash
# Test decision engine
python3 ~/.claude/autonomous/router/decision_engine.py --test

# Get decision for task
python3 ~/.claude/autonomous/router/decision_engine.py --decide task.json
```

### Kill Switch
```bash
# Emergency stop
python3 ~/.claude/autonomous/observability/dashboard_cli.py --kill

# Resume execution
python3 ~/.claude/autonomous/observability/dashboard_cli.py --resume
```

## Usage

### Daily Operations

**Start Web Dashboard**:
```bash
cd ~/.claude/autonomous/observability/dashboard_web
python3 app.py
# Access at: http://localhost:5050
```

**Monitor Execution**:
```bash
# CLI stats
python3 ~/.claude/autonomous/observability/dashboard_cli.py --stats

# Recent logs
python3 ~/.claude/autonomous/observability/dashboard_cli.py --logs

# System health
python3 ~/.claude/autonomous/observability/dashboard_cli.py --health
```

**Manual Task Execution**:
```bash
# Run single heartbeat cycle
python3 ~/.claude/autonomous/heartbeat/engine.py --run-once

# Run with live execution (not dry-run)
python3 ~/.claude/autonomous/heartbeat/engine.py --live --run-once
```

### Autonomous Mode Control

**Enable Autonomous Mode** (15-minute heartbeat):
```bash
# Load launchd agent
launchctl load ~/Library/LaunchAgents/com.claude.autonomous-heartbeat.plist

# Verify status
launchctl list | grep claude.autonomous
```

**Disable Autonomous Mode**:
```bash
# Unload launchd agent
launchctl unload ~/Library/LaunchAgents/com.claude.autonomous-heartbeat.plist

# Or use kill switch
touch ~/.claude/autonomous/KILL_SWITCH
```

**Monitor Autonomous Execution**:
```bash
# Real-time logs
tail -f ~/.claude/autonomous/logs/heartbeat-stdout.log

# Error logs
tail -f ~/.claude/autonomous/logs/heartbeat-stderr.log
```

### Rollback Operations

**List Available Snapshots**:
```bash
ls -lh ~/.claude/autonomous/snapshots/
```

**Manual Rollback**:
```bash
python3 ~/.claude/autonomous/production/rollback_manager.py --rollback [snapshot_id]
```

**Verify Rollback**:
```bash
python3 ~/.claude/autonomous/production/rollback_manager.py --verify [snapshot_id]
```

### Memory Sync

**Trigger Manual Sync** (MEMORY.md ↔ database):
```bash
python3 ~/.claude/autonomous/memory/sync_engine.py --sync
```

**Build Context Snapshot**:
```bash
python3 ~/.claude/autonomous/memory/context_builder.py --build --output /tmp/context.md
cat /tmp/context.md
```

### Testing & Validation

**Run Week-Specific Tests**:
```bash
# Week 1: Foundation
python3 /tmp/test_week1_complete.py

# Week 2: Sandbox
python3 /tmp/test_week2_complete.py

# Week 3: Production
python3 /tmp/test_week3_complete.py

# Week 4: Memory
python3 /tmp/test_week4_complete.py

# Week 5: Autonomous
python3 /tmp/test_week5_complete.py

# Week 6: Web Dashboard
python3 /tmp/test_week6_complete.py
```

**End-to-End Integration Test**:
```bash
cd "/Users/giovanniaffinita/Library/CloudStorage/OneDrive-SAPASPA/OD PARA Sales Strategy/Claude Workspace"
python3 tests/test_autonomous_e2e.py
```

## Architecture (Full System)

```
~/.claude/autonomous/
├── heartbeat/
│   └── engine.py                    # Main orchestrator (Week 1)
├── router/
│   ├── risk_scorer.py               # Risk scoring 0-100 (Week 1)
│   ├── decision_engine.py           # Routing logic (Week 1)
│   └── profiles/
│       └── autonomous.json          # Auto-execution rules (Week 1)
├── sandbox/
│   ├── executor.py                  # Isolated testing (Week 2)
│   ├── score_calculator.py          # Validation scoring (Week 2)
│   ├── fix_generator.py             # LLM-powered fixes (Week 2)
│   └── orchestrator.py              # Fix iteration loop (Week 2)
├── production/
│   ├── executor.py                  # Safe execution (Week 3)
│   ├── snapshot_manager.py          # Pre-exec backups (Week 3)
│   ├── rollback_manager.py          # Auto-rollback (Week 3)
│   └── validation/
│       ├── pre_flight.py            # Pre-checks (Week 3)
│       └── post_flight.py           # Post-validation (Week 3)
├── memory/
│   ├── sync_engine.py               # MEMORY.md ↔ DB (Week 4)
│   └── context_builder.py           # Workspace context (Week 4)
├── observability/
│   ├── dashboard_cli.py             # CLI monitoring (Week 1)
│   ├── dashboard_web/
│   │   └── app.py                   # Flask web UI (Week 6)
│   └── alerts/
│       └── notifier.py              # macOS notifications (Week 5)
├── scripts/
│   └── init_metrics_db.py           # Database setup (Week 1)
├── logs/
│   ├── heartbeat-stdout.log         # Launchd stdout (Week 5)
│   ├── heartbeat-stderr.log         # Launchd stderr (Week 5)
│   └── [date]/
│       └── heartbeat.log            # Manual execution logs
├── snapshots/                       # Rollback backups (Week 3)
│   └── [snapshot_id]/
│       ├── local_vault.db
│       └── metadata.json
└── metrics.db                       # SQLite metrics store (Week 1)

~/Library/LaunchAgents/
└── com.claude.autonomous-heartbeat.plist  # 15-min scheduling (Week 5)
```

## Risk Levels

| Level | Score | Action | Description |
|-------|-------|--------|-------------|
| **LOW** | 0-30 | Auto-execute | Read-only queries, safe operations |
| **MEDIUM** | 31-60 | Conditional execute | DB writes, file operations (sandbox score ≥90) |
| **HIGH** | 61-85 | Human escalation | High-impact operations |
| **CRITICAL** | 86-100 | Hard block | Email, payments, deletions |

## Integration Points

### Local Vault DB
- **Path**: `/Users/giovanniaffinita/Library/CloudStorage/OneDrive-SAPASPA/OD PARA Sales Strategy/Claude Workspace/local_vault.db`
- **Table**: `tasks` (status='pending')
- **Schema**: `id, task_type, status, assigned_agent, payload, result`

### PENDING_APPROVAL.md
- **Path**: Same workspace root
- **Pattern**: `[x] **APPROVA**` followed by JSON action block
- **Parser**: Extracts approved actions for execution

## Week 1 Test Results

**Risk Scorer**: 5/5 tests passed
- LOW: Simple DB query (score 0)
- LOW: File write workdir (score 29)
- MEDIUM: DB update (score 38)
- CRITICAL: Send email (score 86)
- CRITICAL: Delete DB (score 86)

**Decision Router**: 4/4 tests passed
- AUTO_EXECUTE: LOW risk queries
- CONDITIONAL_EXECUTE: MEDIUM risk (sandbox threshold check)
- ESCALATE_HUMAN: MEDIUM risk below threshold
- BLOCK: CRITICAL risk

**Heartbeat Engine**: ✓ Working
- Task discovery from local_vault.db
- Risk scoring
- Routing decisions
- Metrics recording
- Health tracking

**CLI Dashboard**: ✓ Working
- System health monitoring
- Execution statistics
- Recent logs viewer
- Kill switch control

## All Weeks Complete ✓

**Week 1**: Foundation (risk scoring, decision routing, metrics DB)
**Week 2**: Sandbox Execution (isolated testing, automatic fixes)
**Week 3**: Production + Rollback (safe deployment, automatic restore)
**Week 4**: Memory Enhancement (MEMORY.md sync, context injection)
**Week 5**: Autonomous Mode (launchd scheduling, macOS notifications)
**Week 6**: Optimization + Web Dashboard (Flask UI, performance tuning)

**System Ready**: Full autonomous mode operational

## Configuration

### Autonomous Profile
- **LOW risk**: Auto-execute with sandbox validation (threshold: 95)
- **MEDIUM risk**: Conditional execute (sandbox ≥90)
- **HIGH risk**: Human escalation
- **CRITICAL risk**: Hard block

### Limits
- Max concurrent tasks: 3
- Max sandbox iterations: 5
- Execution timeout: 600s

## Troubleshooting

### No tasks discovered
```bash
# Check local_vault.db
cd "/Users/giovanniaffinita/Library/CloudStorage/OneDrive-SAPASPA/OD PARA Sales Strategy/Claude Workspace"
sqlite3 local_vault.db "SELECT * FROM tasks WHERE status='pending';"

# Check PENDING_APPROVAL.md
grep -A 10 "APPROVA" PENDING_APPROVAL.md
```

### Database errors
```bash
# Verify metrics database
python3 ~/.claude/autonomous/scripts/init_metrics_db.py --verify

# Recreate if corrupted
rm ~/.claude/autonomous/metrics.db
python3 ~/.claude/autonomous/scripts/init_metrics_db.py
```

### Logs not appearing
```bash
# Check log directory
ls -lh ~/.claude/autonomous/logs/$(date +%Y-%m-%d)/

# Manual log tail
tail -f ~/.claude/autonomous/logs/$(date +%Y-%m-%d)/heartbeat.log
```

## Support

- **Issues**: GitHub (when repo available)
- **Documentation**: This README + inline code comments
- **Implementation Plan**: See original 6-week plan document

---

**Version**: 1.6 (All Weeks Complete)
**Last Updated**: 2026-02-07
**Status**: Production-ready, full autonomous mode operational
**Test Scores**: Week 1 (100/100), Week 2 (100/100), Week 3 (100/100), Week 4 (98.8/100), Week 5 (100/100), Week 6 (95+/100)
