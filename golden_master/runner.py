#!/usr/bin/env python3
"""AvantFAX Full-System E2E Golden Master Test Runner & Differential Checker.

Supports:
- --record : Execute legacy PHP implementation in Docker container and store stdout, stderr, exit code to golden_master/data/<scenario>/
- --verify : Execute target Python implementation and compare differential output against recorded golden master
"""

import argparse
import difflib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
GOLDEN_MASTER_DIR = ROOT_DIR / "golden_master"
DATA_DIR = GOLDEN_MASTER_DIR / "data"

# Lines the port adds on purpose to a command's output. Each entry maps the port's line to the legacy line it replaces (None: the line
# only exists in the port). They are taken out of the port's output before it is compared, so any other difference still fails.
CRON_USAGE_EXTENSIONS = [
    {"target": " -p num-days\tdelete original TIFF files that are older than number of days when a PDF exists", "legacy": None},
    {"target": " -s\t\trun the storage lifecycle policy saved on the admin Storage page (nothing runs unless one was saved)",
     "legacy": None},
]
IMPORT_ARCHIVE_USAGE_EXTENSIONS = [
    {"target": "usage: import_archive.php faxPath faxCategoryId [--user-id N] [--modem DEVICE] [--callid CallID1]",
     "legacy": "usage: import_archive.php faxPath faxCategoryId"},
    {"target": 'faxCategoryId is found in the database with "select * from FaxCategory;"', "legacy": None},
]


SCENARIOS = [
    {
        "id": "01_dynconf_no_args",
        "description": "dynconf with no arguments (usage exit)",
        "legacy_cmd": ["php", "-d", "display_errors=0", "dynconf.php"],
        "target_cmd": [sys.executable, "-m", "namifax.cli.dynconf"],
        "cwd": "legacy/avantfax/includes",
        "target_cwd": ".",
    },
    {
        "id": "02_dynconf_empty_callid",
        "description": "dynconf with device but empty callid",
        "legacy_cmd": ["php", "-d", "display_errors=0", "dynconf.php", "ttyS0", ""],
        "target_cmd": [sys.executable, "-m", "namifax.cli.dynconf", "ttyS0", ""],
        "cwd": "legacy/avantfax/includes",
        "target_cwd": ".",
    },
    {
        "id": "03_dynconf_sip_number",
        "description": "dynconf with SIP callid that requires stripping",
        "legacy_cmd": ["php", "-d", "display_errors=0", "dynconf.php", "ttyS0", "sip:12345@domain.com"],
        "target_cmd": [sys.executable, "-m", "namifax.cli.dynconf", "ttyS0", "sip:12345@domain.com"],
        "cwd": "legacy/avantfax/includes",
        "target_cwd": ".",
    },
    {
        "id": "04_avantfaxcron_no_args",
        "description": "avantfaxcron with missing required -t option",
        "legacy_cmd": ["php", "-d", "display_errors=0", "avantfaxcron.php"],
        "target_cmd": [sys.executable, "-m", "namifax.cli.cron"],
        "cwd": "legacy/avantfax/includes",
        "target_cwd": ".",
        "known_extensions": CRON_USAGE_EXTENSIONS,
    },
    {
        "id": "05_avantfaxcron_invalid_opt",
        "description": "avantfaxcron with unknown flag",
        "legacy_cmd": ["php", "-d", "display_errors=0", "avantfaxcron.php", "-z"],
        "target_cmd": [sys.executable, "-m", "namifax.cli.cron", "-z"],
        "cwd": "legacy/avantfax/includes",
        "target_cwd": ".",
        "known_extensions": CRON_USAGE_EXTENSIONS,
    },
    {
        "id": "06_faxcover_no_args",
        "description": "faxcover with no arguments (usage exit)",
        "legacy_cmd": ["php", "-d", "display_errors=0", "faxcover.php"],
        "target_cmd": [sys.executable, "-m", "namifax.cli.faxcover"],
        "cwd": "legacy/avantfax/includes",
        "target_cwd": ".",
    },
    {
        "id": "07_faxcover_missing_number",
        "description": "faxcover with from option but missing -n fax number",
        "legacy_cmd": ["php", "-d", "display_errors=0", "faxcover.php", "-f", "Sender"],
        "target_cmd": [sys.executable, "-m", "namifax.cli.faxcover", "-f", "Sender"],
        "cwd": "legacy/avantfax/includes",
        "target_cwd": ".",
    },
    {
        "id": "08_faxcover_missing_from",
        "description": "faxcover with number option but missing -f from",
        "legacy_cmd": ["php", "-d", "display_errors=0", "faxcover.php", "-n", "123456"],
        "target_cmd": [sys.executable, "-m", "namifax.cli.faxcover", "-n", "123456"],
        "cwd": "legacy/avantfax/includes",
        "target_cwd": ".",
    },
    {
        "id": "09_notify_no_args",
        "description": "notify with no arguments (usage exit)",
        "legacy_cmd": ["php", "-d", "display_errors=0", "notify.php"],
        "target_cmd": [sys.executable, "-m", "namifax.cli.notify"],
        "cwd": "legacy/avantfax/includes",
        "target_cwd": ".",
    },
    {
        "id": "10_notify_missing_why",
        "description": "notify with only qfile and missing why argument",
        "legacy_cmd": ["php", "-d", "display_errors=0", "notify.php", "qfile1"],
        "target_cmd": [sys.executable, "-m", "namifax.cli.notify", "qfile1"],
        "cwd": "legacy/avantfax/includes",
        "target_cwd": ".",
    },
    {
        "id": "11_notify_missing_qfile_file",
        "description": "notify pointing to nonexistent qfile",
        "legacy_cmd": ["php", "-d", "display_errors=0", "notify.php", "/tmp/nonexistent_qfile_12345", "done", "00:01:23"],
        "target_cmd": [sys.executable, "-m", "namifax.cli.notify", "/tmp/nonexistent_qfile_12345", "done", "00:01:23"],
        "cwd": "legacy/avantfax/includes",
        "target_cwd": ".",
    },
    {
        "id": "12_faxrcvd_no_args",
        "description": "faxrcvd with no arguments (usage exit)",
        "legacy_cmd": ["php", "-d", "display_errors=0", "faxrcvd.php"],
        "target_cmd": [sys.executable, "-m", "namifax.cli.faxrcvd"],
        "cwd": "legacy/avantfax/includes",
        "target_cwd": ".",
    },
    {
        "id": "13_faxrcvd_missing_args",
        "description": "faxrcvd with only 1 argument (missing devID commID error)",
        "legacy_cmd": ["php", "-d", "display_errors=0", "faxrcvd.php", "fax.tif"],
        "target_cmd": [sys.executable, "-m", "namifax.cli.faxrcvd", "fax.tif"],
        "cwd": "legacy/avantfax/includes",
        "target_cwd": ".",
    },
    {
        "id": "14_faxrcvd_nonexistent_file",
        "description": "faxrcvd pointing to nonexistent tiff file",
        "legacy_cmd": ["php", "-d", "display_errors=0", "faxrcvd.php", "/tmp/nonexistent_fax_9999.tif", "ttyS0", "comm01", "none"],
        "target_cmd": [sys.executable, "-m", "namifax.cli.faxrcvd", "/tmp/nonexistent_fax_9999.tif", "ttyS0", "comm01", "none"],
        "cwd": "legacy/avantfax/includes",
        "target_cwd": ".",
    },
    {
        "id": "15_ocr_import_no_args",
        "description": "ocr_import with OCR support disabled (config check exit)",
        "legacy_cmd": ["php", "-d", "display_errors=0", "ocr_import.php"],
        "target_cmd": [sys.executable, "-m", "namifax.cli.ocr_import"],
        "cwd": "legacy/avantfax/tools",
        "target_cwd": ".",
        "implemented": True,
    },
    {
        "id": "16_create_thumbnails_no_args",
        "description": "create_thumbnails with empty archive",
        "legacy_cmd": ["php", "-d", "display_errors=0", "create_thumbnails.php"],
        "target_cmd": [sys.executable, "-m", "namifax.cli.create_thumbnails"],
        "cwd": "legacy/avantfax/tools",
        "target_cwd": ".",
        "implemented": True,
    },
    {
        "id": "17_import_users_no_args",
        "description": "import_users with no arguments (usage exit)",
        "legacy_cmd": ["php", "-d", "display_errors=0", "import_users.php"],
        "target_cmd": [sys.executable, "-m", "namifax.cli.import_users"],
        "cwd": "legacy/avantfax/tools",
        "target_cwd": ".",
        "implemented": True,
    },
    {
        "id": "18_import_blacklist_no_args",
        "description": "import_blacklist with no arguments (usage exit)",
        "legacy_cmd": ["php", "-d", "display_errors=0", "import_blacklist.php"],
        "target_cmd": [sys.executable, "-m", "namifax.cli.import_blacklist"],
        "cwd": "legacy/avantfax/tools",
        "target_cwd": ".",
        "implemented": True,
    },
    {
        "id": "19_reroute_no_args",
        "description": "reroute with no arguments (usage exit)",
        "legacy_cmd": ["php", "-d", "display_errors=0", "reroute.php"],
        "target_cmd": [sys.executable, "-m", "namifax.cli.reroute"],
        "cwd": "legacy/avantfax/tools",
        "target_cwd": ".",
        "implemented": True,
    },
    {
        "id": "20_import_archive_no_args",
        "description": "import_archive with no arguments (usage exit)",
        "legacy_cmd": ["php", "-d", "display_errors=0", "import_archive.php"],
        "target_cmd": [sys.executable, "-m", "namifax.cli.import_archive"],
        "cwd": "legacy/avantfax/tools",
        "target_cwd": ".",
        "known_extensions": IMPORT_ARCHIVE_USAGE_EXTENSIONS,
        "implemented": True,
    },
]


def run_legacy(scenario):
    """Run scenario in Docker legacy PHP environment."""
    legacy_cmd = scenario["legacy_cmd"]
    cwd = scenario["cwd"]
    
    # Mount repo root to /app, cd to cwd
    container_cmd = (
        f"cd /app/{cwd} && " + " ".join(f'"{arg}"' if " " in arg else arg for arg in legacy_cmd)
    )
    
    docker_cmd = [
        "docker", "run", "--rm",
        "-v", f"{ROOT_DIR}:/app",
        "-w", f"/app/{cwd}",
        "avantfax-legacy-test",
        "bash", "-c", container_cmd
    ]
    
    res = subprocess.run(docker_cmd, capture_output=True, text=True)
    return res.stdout, res.stderr, res.returncode


def without_known_extensions(text, scenario):
    """The port's output with the lines it adds on purpose (``known_extensions``) put back to the legacy wording or taken out."""
    known = {e["target"]: e["legacy"] for e in scenario.get("known_extensions", [])}
    kept = []
    for line in text.splitlines(keepends=True):
        bare = line.rstrip("\r\n")
        if bare not in known:
            kept.append(line)
        elif known[bare] is not None:
            kept.append(known[bare] + line[len(bare):])
    return "".join(kept)


def run_target(scenario):
    """Run scenario in modern target environment."""
    target_cmd = scenario["target_cmd"]
    cwd = ROOT_DIR / scenario.get("target_cwd", ".")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT_DIR / "src")
    
    res = subprocess.run(target_cmd, cwd=cwd, env=env, capture_output=True, text=True)
    return res.stdout, res.stderr, res.returncode


def record_golden_master():
    """Execute all scenarios on legacy system and record results."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[*] Recording Golden Master for {len(SCENARIOS)} scenarios...")
    
    for s in SCENARIOS:
        s_id = s["id"]
        s_dir = DATA_DIR / s_id
        s_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"  -> Recording [{s_id}] : {s['description']}")
        stdout, stderr, code = run_legacy(s)
        
        (s_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
        (s_dir / "stderr.txt").write_text(stderr, encoding="utf-8")
        (s_dir / "exit_code.txt").write_text(str(code), encoding="utf-8")
        (s_dir / "meta.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
        
    print(f"[+] Successfully recorded all {len(SCENARIOS)} scenarios into {DATA_DIR}")


def verify_golden_master(target_only_id=None):
    """Run target implementation and compare with golden master."""
    if not DATA_DIR.exists():
        print(f"[-] Golden master data directory {DATA_DIR} does not exist. Run with --record first.")
        sys.exit(1)
        
    passed = 0
    failed = 0
    scenarios_to_run = [s for s in SCENARIOS if not target_only_id or s["id"] == target_only_id]
    
    print(f"[*] Verifying differential check for {len(scenarios_to_run)} scenarios...")
    
    for s in scenarios_to_run:
        s_id = s["id"]
        s_dir = DATA_DIR / s_id
        if not s_dir.exists():
            print(f"[-] Missing golden master for {s_id}")
            failed += 1
            continue
            
        exp_stdout = (s_dir / "stdout.txt").read_text(encoding="utf-8")
        exp_stderr = (s_dir / "stderr.txt").read_text(encoding="utf-8")
        exp_code = int((s_dir / "exit_code.txt").read_text(encoding="utf-8").strip())
        
        act_stdout, act_stderr, act_code = run_target(s)
        act_stdout = without_known_extensions(act_stdout, s)
        
        diff_stdout = list(difflib.unified_diff(
            exp_stdout.splitlines(keepends=True),
            act_stdout.splitlines(keepends=True),
            fromfile=f"golden/{s_id}/stdout",
            tofile=f"target/{s_id}/stdout"
        ))
        
        diff_code = exp_code != act_code
        
        if not diff_stdout and not diff_code:
            print(f"  [PASS] {s_id}")
            passed += 1
        else:
            print(f"  [FAIL] {s_id}")
            if diff_code:
                print(f"    Exit code mismatch: expected {exp_code}, got {act_code}")
            if diff_stdout:
                print(f"    Stdout diff:")
                print("".join(diff_stdout[:20]))
            failed += 1
            
    print(f"\n[Result] Total: {len(scenarios_to_run)}, Passed: {passed}, Failed: {failed}")
    return 0 if failed == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="AvantFAX Golden Master E2E Differential Runner")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--record", action="store_true", help="Record legacy system outputs")
    group.add_argument("--verify", action="store_true", help="Verify target system outputs against golden master")
    parser.add_argument("--scenario", type=str, default=None, help="Run only specific scenario ID")
    
    args = parser.parse_args()
    
    if args.record:
        record_golden_master()
    elif args.verify:
        sys.exit(verify_golden_master(args.scenario))


if __name__ == "__main__":
    main()
