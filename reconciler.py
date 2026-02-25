#!/usr/bin/env python3
"""Q-F5 Sentinel: F5 Big-IP configuration drift auditor.

This script compares a declarative desired-state YAML file against an actual-state
JSON payload (mocking F5 iControl REST output), reports drift, and simulates
telemetry + change-management integrations.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

try:
    from rich.console import Console
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


LOGGER = logging.getLogger("q_f5_sentinel")


def configure_logging() -> None:
    """Set clean, interview-friendly log formatting."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def load_yaml(path: Path) -> dict[str, Any]:
    """Load desired state from YAML (Source of Truth)."""
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected top-level mapping in {path}")
    return data


def fetch_f5_actual_state(path: Path) -> dict[str, Any]:
    """Simulate fetching F5 config over iControl REST.

    In production, replace this with requests.get(...) to your F5 endpoint.
    """
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected top-level object in {path}")
    return data


def compare_states(
    desired: Any, actual: Any, path: str = "root"
) -> list[dict[str, Any]]:
    """Reconciliation loop: recursively compare desired vs actual.

    Reconciliation is safer than "push-only" automation in high-uptime
    environments because it validates reality first. That avoids accidental
    outages from blindly overwriting production devices that may have critical
    in-flight operational changes.
    """
    drifts: list[dict[str, Any]] = []

    if isinstance(desired, dict) and isinstance(actual, dict):
        all_keys = sorted(set(desired.keys()) | set(actual.keys()))
        for key in all_keys:
            child_path = f"{path}.{key}"
            if key not in desired:
                drifts.append(
                    {
                        "path": child_path,
                        "status": "unexpected_key",
                        "desired": None,
                        "actual": actual[key],
                    }
                )
            elif key not in actual:
                drifts.append(
                    {
                        "path": child_path,
                        "status": "missing_key",
                        "desired": desired[key],
                        "actual": None,
                    }
                )
            else:
                drifts.extend(compare_states(desired[key], actual[key], child_path))
        return drifts

    if desired != actual:
        drifts.append(
            {
                "path": path,
                "status": "value_mismatch",
                "desired": desired,
                "actual": actual,
            }
        )
    return drifts


def build_splunk_payload(device_id: str, drifts: list[dict[str, Any]]) -> dict[str, Any]:
    """Build telemetry payload for Splunk ingestion."""
    return {
        "event_type": "f5_config_drift",
        "device_id": device_id,
        "drift_detected": bool(drifts),
        "drift_count": len(drifts),
        "drifts": drifts,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


def send_to_splunk(payload: dict[str, Any]) -> None:
    """Mock Splunk submission: log the event payload as JSON."""
    LOGGER.info("Splunk payload: %s", json.dumps(payload, indent=2))


def open_servicenow_change(
    device_id: str, drifts: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Mock ServiceNow POST call to open a change request for human approval."""
    if not drifts:
        LOGGER.info("No drift detected. ServiceNow change request not required.")
        return None

    change_payload = {
        "short_description": f"F5 config drift detected on {device_id}",
        "description": "Q-F5 Sentinel found drift; approval required before remediation.",
        "category": "Network",
        "type": "Normal",
        "priority": "2",
        "cmdb_ci": device_id,
        "u_drift_details": drifts,
    }

    LOGGER.warning(
        "ServiceNow POST (simulated) to /api/now/table/change_request: %s",
        json.dumps(change_payload, indent=2),
    )
    return change_payload


def print_diff_report(drifts: list[dict[str, Any]]) -> None:
    """Render a clean console report (rich table when available)."""
    if not drifts:
        LOGGER.info("Desired and actual states are aligned. No configuration drift.")
        return

    if RICH_AVAILABLE:
        table = Table(title="Q-F5 Sentinel Drift Report")
        table.add_column("Path", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Desired", style="green")
        table.add_column("Actual", style="red")
        for drift in drifts:
            table.add_row(
                drift["path"],
                drift["status"],
                str(drift["desired"]),
                str(drift["actual"]),
            )
        Console().print(table)
    else:
        LOGGER.info("Drift report:")
        for drift in drifts:
            LOGGER.info(
                "path=%s status=%s desired=%s actual=%s",
                drift["path"],
                drift["status"],
                drift["desired"],
                drift["actual"],
            )


def main() -> None:
    configure_logging()
    project_root = Path(__file__).parent
    desired = load_yaml(project_root / "gold_standard.yaml")
    actual = fetch_f5_actual_state(project_root / "f5_actual_state.json")

    drifts = compare_states(desired, actual, path="virtual_server_root")
    print_diff_report(drifts)

    splunk_payload = build_splunk_payload(device_id="f5-bigip-a1", drifts=drifts)
    send_to_splunk(splunk_payload)
    open_servicenow_change(device_id="f5-bigip-a1", drifts=drifts)


if __name__ == "__main__":
    main()
