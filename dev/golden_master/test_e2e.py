"""Pytest integration for AvantFAX Golden Master E2E Differential Tests."""

import subprocess
import sys
from pathlib import Path
import pytest

from golden_master.runner import SCENARIOS, verify_golden_master

@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_e2e_differential(scenario):
    """Verify each scenario output matches golden master data."""
    scenario_id = scenario["id"]
    if not scenario.get("implemented", True):
        pytest.xfail(f"Golden Master contract extracted; target implementation pending for {scenario_id}")

    exit_code = verify_golden_master(target_only_id=scenario_id)
    assert exit_code == 0, f"Scenario {scenario_id} failed differential verification against golden master"
