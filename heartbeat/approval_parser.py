#!/usr/bin/env python3
"""
Autonomous System - Enhanced PENDING_APPROVAL.md Parser
Handles real-world approval formats.
"""

import json
import re
from typing import List, Dict, Any
from pathlib import Path


def parse_pending_approvals(file_path: Path) -> List[Dict[str, Any]]:
    """
    Parse PENDING_APPROVAL.md and extract approved actions.

    Handles two formats:
    1. JSON payload format (Azione #5 style)
    2. Bash command format (Azione #6 style)

    Args:
        file_path: Path to PENDING_APPROVAL.md

    Returns:
        List of approved task dictionaries
    """

    if not file_path.exists():
        return []

    with open(file_path, "r") as f:
        content = f.read()

    tasks = []

    # Split by actions (## Azione #N)
    action_pattern = r'## Azione #(\d+)[^\n]*\n(.*?)(?=## Azione #|\Z)'
    actions = re.findall(action_pattern, content, re.DOTALL)

    for action_id, action_content in actions:
        # Check if approved
        if not _is_approved(action_content):
            continue

        # Extract action type
        action_type = _extract_action_type(action_content)

        # Try to extract JSON payload
        json_payload = _extract_json_payload(action_content)

        if json_payload:
            # JSON format found
            task = {
                "task_id": f"approval_{action_id}",
                "action_type": action_type or json_payload.get("platform", "unknown").lower(),
                "payload": json_payload,
                "source": "PENDING_APPROVAL.md",
                "approval_format": "json"
            }
            tasks.append(task)
        else:
            # Bash command format (or other)
            bash_commands = _extract_bash_commands(action_content)

            if bash_commands:
                task = {
                    "task_id": f"approval_{action_id}",
                    "action_type": action_type or "execute_script",
                    "payload": {
                        "commands": bash_commands,
                        "description": _extract_description(action_content)
                    },
                    "source": "PENDING_APPROVAL.md",
                    "approval_format": "bash"
                }
                tasks.append(task)

    return tasks


def _is_approved(content: str) -> bool:
    """Check if action is approved."""

    # Check for various approval patterns
    patterns = [
        r'\[x\]\s+\*\*APPROVA',           # [x] **APPROVA**
        r'\[X\]\s+\*\*APPROVA',           # [X] **APPROVA**
        r'\[x\]\s+APPROVA',               # [x] APPROVA
        r'✓\s+APPROVA',                   # ✓ APPROVA
    ]

    for pattern in patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return True

    return False


def _extract_action_type(content: str) -> str:
    """Extract action type from content."""

    # Look for **Tipo**: pattern
    match = re.search(r'\*\*Tipo\*\*:\s*`?([^`\n]+)`?', content)
    if match:
        return match.group(1).strip()

    return None


def _extract_json_payload(content: str) -> Dict[str, Any]:
    """Extract JSON payload from markdown code block."""

    # Look for ```json ... ```
    match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    return None


def _extract_bash_commands(content: str) -> List[str]:
    """Extract bash commands from markdown code block."""

    # Look for ```bash ... ```
    match = re.search(r'```bash\s*(.*?)\s*```', content, re.DOTALL)
    if match:
        commands = match.group(1).strip().split('\n')
        # Filter out comments and empty lines
        return [
            cmd.strip()
            for cmd in commands
            if cmd.strip() and not cmd.strip().startswith('#')
        ]

    return []


def _extract_description(content: str) -> str:
    """Extract action description."""

    # Look for first paragraph after action header
    lines = content.split('\n')
    description_lines = []

    in_description = False
    for line in lines:
        if '**Tipo**:' in line or '**Descrizione**:' in line:
            in_description = True
            continue
        if in_description and line.strip() and not line.startswith('#'):
            description_lines.append(line.strip())
            if len(description_lines) >= 3:  # Max 3 lines
                break
        if in_description and line.startswith('###'):
            break

    return ' '.join(description_lines[:3])


# Test function
def test_parser():
    """Test parser with real PENDING_APPROVAL.md."""

    workspace = Path.home() / "Library" / "CloudStorage" / "OneDrive-SAPASPA" / "OD PARA Sales Strategy" / "Claude Workspace"
    approval_file = workspace / "PENDING_APPROVAL.md"

    print("=" * 60)
    print("PENDING_APPROVAL.md Parser Test")
    print("=" * 60)

    if not approval_file.exists():
        print(f"✗ File not found: {approval_file}")
        return False

    tasks = parse_pending_approvals(approval_file)

    print(f"\nFile: {approval_file}")
    print(f"Tasks discovered: {len(tasks)}")

    for i, task in enumerate(tasks, 1):
        print(f"\n--- Task {i} ---")
        print(f"ID: {task['task_id']}")
        print(f"Type: {task['action_type']}")
        print(f"Format: {task['approval_format']}")

        if task['approval_format'] == 'json':
            print(f"Payload keys: {list(task['payload'].keys())}")
        elif task['approval_format'] == 'bash':
            print(f"Commands: {len(task['payload']['commands'])} found")
            print(f"First command: {task['payload']['commands'][0][:80]}...")

    print("\n" + "=" * 60)
    print(f"✓ Parser test complete - {len(tasks)} approved tasks found")
    print("=" * 60)

    return True


if __name__ == "__main__":
    import sys

    if "--test" in sys.argv:
        test_parser()
    else:
        print("Usage: approval_parser.py --test")
