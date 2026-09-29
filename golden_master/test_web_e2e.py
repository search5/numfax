import json
from pathlib import Path
import pytest
from golden_master.web_runner import GOLDEN_WEB_DIR, run_web_verification

SCENARIO_DIRS = sorted([p.name for p in GOLDEN_WEB_DIR.iterdir() if p.is_dir()]) if GOLDEN_WEB_DIR.exists() else []


@pytest.mark.parametrize("scenario_id", SCENARIO_DIRS)
def test_web_golden_master_scenario(scenario_id):
    """Verify individual web E2E Golden Master scenario differential check."""
    meta_path = GOLDEN_WEB_DIR / scenario_id / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if not meta.get("implemented", True):
            pytest.xfail(f"Golden Master contract extracted; target implementation pending for {scenario_id}")

    res = run_web_verification(target_scenario=scenario_id)
    assert res == 0, f"Web Golden Master scenario {scenario_id} failed differential verification!"

