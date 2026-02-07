# Claude Code Autonomous System

Sistema di autonomia per trasformare Claude Code da reattivo a proattivo con esecuzione automatica task.

## Status: Week 3 Complete ✓

**Milestone**: Production Execution with Rollback

**Completato**:
- ✓ Directory structure creata
- ✓ Metrics database (SQLite) inizializzato
- ✓ Risk Scorer implementato e testato (5/5 tests passed)
- ✓ Decision Router implementato e testato (4/4 tests passed)
- ✓ Autonomous Profile configurato
- ✓ CLI Dashboard (basic version)
- ✓ Heartbeat Engine (dry-run mode) testato
- ✓ Integration con local_vault.db verificata

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

## Architecture (Week 1)

```
~/.claude/autonomous/
├── heartbeat/
│   └── engine.py           # Main orchestrator (dry-run mode)
├── router/
│   ├── risk_scorer.py      # Risk scoring (0-100)
│   ├── decision_engine.py  # Routing logic
│   └── profiles/
│       └── autonomous.json # Auto-execution rules
├── observability/
│   └── dashboard_cli.py    # CLI monitoring
├── scripts/
│   └── init_metrics_db.py  # Database setup
├── logs/
│   └── [date]/
│       └── heartbeat.log   # Execution logs
└── metrics.db              # SQLite metrics store
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

## Next: Week 2

**Obiettivo**: Sandbox Execution

**Tasks**:
1. Sandbox executor (isolated environment)
2. Score calculator (95/100 target)
3. Fix generator (LLM-powered error fixes)
4. Iteration loop (max 5 attempts)

**Deliverable**: Working sandbox with automatic fix iterations

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

**Version**: 1.0 (Week 1 Complete)
**Last Updated**: 2026-02-07
**Status**: Foundation complete, ready for Week 2
