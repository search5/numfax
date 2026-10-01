#!/usr/bin/env python3
"""Batch apply strict form structures and dynamic states to golden master contracts."""

import json
from pathlib import Path

GOLDEN_WEB_DIR = Path(__file__).parent / "web"
LIVE_STRUCTURES_FILE = Path(__file__).parent / "live_form_structures.json"

DYNAMIC_STATE_DEFS = {
    "W01_login_get": {
        "login_focus": {
            "trigger_selector": "#username",
            "affected_inputs": ["username", "password"]
        }
    },
    "W09_sendfax_form": {
        "coverpage_options": {
            "trigger_selector": "#coverpage",
            "affected_inputs": ["whichcover", "comments"]
        },
        "scheduling_options": {
            "trigger_selector": "details > summary",
            "affected_inputs": ["priority", "numtries", "notify_requeue"]
        },
        "file_attachment": {
            "trigger_selector": "#file",
            "affected_inputs": ["file"]
        }
    },
    "W19_admin_users": {
        "superuser_rights": {
            "trigger_selector": "input[name='superuser']",
            "affected_inputs": ["didrouting[]", "modemdevs[]", "faxcats[]"]
        }
    },
    "W64_admin_user_edit": {
        "superuser_rights": {
            "trigger_selector": "input[name='superuser']",
            "affected_inputs": ["didrouting[]", "modemdevs[]", "faxcats[]"]
        },
        "delete_action": {
            "trigger_selector": "button[name='delete']",
            "affected_inputs": ["uid"]
        }
    },
    "W57_admin_did_edit": {
        "delete_rule": {
            "trigger_selector": "button[name='delete']",
            "affected_inputs": ["didr_id"]
        }
    },
    "W58_admin_modem_edit": {
        "save_device": {
            "trigger_selector": "button[type='submit']",
            "affected_inputs": ["device"]
        }
    },
    "W59_admin_barcode_edit": {
        "delete_rule": {
            "trigger_selector": "button[name='delete']",
            "affected_inputs": ["barcode_id"]
        }
    },
    "W60_admin_cover_edit": {
        "delete_template": {
            "trigger_selector": "button[name='delete']",
            "affected_inputs": ["cover_id"]
        }
    },
    "W61_admin_dynconf_edit": {
        "delete_rule": {
            "trigger_selector": "button[name='delete']",
            "affected_inputs": ["dynconf_id"]
        }
    },
    "W62_admin_fax2email_edit": {
        "delete_mapping": {
            "trigger_selector": "button[name='delete']",
            "affected_inputs": ["abook_id"]
        }
    },
    "W63_admin_category_edit": {
        "delete_category": {
            "trigger_selector": "button[name='delete']",
            "affected_inputs": ["catid"]
        }
    },
    "W65_addressbook_edit_selected": {
        "delete_company": {
            "trigger_selector": "button[name='delete']",
            "affected_inputs": ["abook_id"]
        }
    },
    "W66_distrolist_edit_selected": {
        "delete_list": {
            "trigger_selector": "button[name='delete']",
            "affected_inputs": ["dl_id"]
        }
    },
    "W67_emailbook_edit_selected": {
        "delete_contact": {
            "trigger_selector": "button[name='delete']",
            "affected_inputs": ["abookemail_id"]
        }
    }
}

def apply_strict_contracts():
    if not LIVE_STRUCTURES_FILE.exists():
        print(f"Error: {LIVE_STRUCTURES_FILE} not found")
        return

    live_specs = json.loads(LIVE_STRUCTURES_FILE.read_text(encoding="utf-8"))
    updated = 0

    for s_id, spec in live_specs.items():
        contract_file = GOLDEN_WEB_DIR / s_id / "contract.json"
        if not contract_file.exists():
            continue

        contract = json.loads(contract_file.read_text(encoding="utf-8"))
        contract["form_structure"] = spec
        
        if s_id in DYNAMIC_STATE_DEFS:
            contract["dynamic_states"] = DYNAMIC_STATE_DEFS[s_id]

        contract_file.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        updated += 1

    print(f"Successfully applied strict form contracts & dynamic states to {updated} scenarios.")

if __name__ == "__main__":
    apply_strict_contracts()
