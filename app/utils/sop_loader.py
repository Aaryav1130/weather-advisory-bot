"""SOP (Standard Operating Procedure) loader.

Loads policies from the YAML file at startup. Policies are decoupled from
application code so they can be added or modified without any code changes.
This is a hard requirement — during the live review, an 11th SOP will be
added on the spot by simply editing the YAML file.
"""

from pathlib import Path
from typing import Any

import yaml


# Path to SOPs file (relative to project root)
SOPS_FILE_PATH = Path(__file__).parent.parent.parent / "sops" / "policies.yaml"


def load_sops(filepath: str | Path | None = None) -> list[dict[str, Any]]:
    """Load all SOPs from the YAML policies file.

    Args:
        filepath: Optional custom path to the YAML file.
                  Defaults to sops/policies.yaml in the project root.

    Returns:
        List of SOP dictionaries.

    Raises:
        FileNotFoundError: If the YAML file doesn't exist.
        yaml.YAMLError: If the YAML file is malformed.
    """
    path = Path(filepath) if filepath else SOPS_FILE_PATH

    if not path.exists():
        raise FileNotFoundError(f"SOPs file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "sops" not in data:
        return []

    return data["sops"]


def format_sops_for_prompt(sops: list[dict[str, Any]]) -> str:
    """Format all SOPs into a structured string for the LLM system prompt.

    This ensures the LLM knows exactly which policies exist and can
    cite them by ID in its responses.
    """
    lines = [
        "=== STANDARD OPERATING PROCEDURES (SOPs) ===",
        "You MUST follow these policies. Every answer must cite the applicable SOP by ID.",
        "If no SOP applies, say so explicitly. Never invent advice beyond these policies.",
        "",
    ]

    for sop in sops:
        lines.append(f"--- {sop['id']}: {sop['name']} ---")
        lines.append(f"  Category: {sop['category']}")
        lines.append(f"  Severity: {sop['severity']}")
        lines.append(f"  Description: {sop['description'].strip()}")

        # Format condition
        condition = sop.get("condition", {})
        if "parameter" in condition:
            lines.append(
                f"  Trigger: {condition['parameter']} {condition.get('operator', '')} "
                f"{condition.get('threshold', '')} {condition.get('unit', '')}"
            )
        elif "parameters" in condition:
            logic = condition.get("logic", "AND")
            triggers = []
            for p in condition["parameters"]:
                triggers.append(
                    f"{p['parameter']} {p.get('operator', '')} "
                    f"{p.get('threshold', '')} {p.get('unit', '')}"
                )
            lines.append(f"  Trigger: {f' {logic} '.join(triggers)}")
        elif condition.get("type") == "holistic":
            lines.append(f"  Trigger: Holistic assessment — {condition.get('description', '').strip()}")

        if "activity_keywords" in condition:
            lines.append(f"  Activity Keywords: {', '.join(condition['activity_keywords'])}")

        lines.append(f"  Guidance: {sop['guidance'].strip()}")
        lines.append("")

    return "\n".join(lines)


def get_sop_by_id(sops: list[dict[str, Any]], sop_id: str) -> dict[str, Any] | None:
    """Look up an SOP by its ID."""
    for sop in sops:
        if sop["id"] == sop_id:
            return sop
    return None
