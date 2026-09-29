"""avantfax.cli.reroute

Reroute modem or DID routing contact email matching legacy tools/reroute.php and specs/38-tools-batch.md.
"""

from __future__ import annotations

import os
import sys

from avantfax.services.did import DIDRouting
from avantfax.services.modem import FaxModem


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    if len(args) < 2:
        print("Usage: reroute.php [device | DIDnum] email-address")
        return 0

    device = args[0]
    email = args[1]
    enable_did = os.environ.get("ENABLE_DID_ROUTING", "0") in ("1", "true", "True")

    if not enable_did:
        modem = FaxModem()
        if not modem.load_device(device):
            print(f'Error loading device "{device}"; is it configured with AvantFAX?')
            return 1
        modem.set_contact(email)
    else:
        didr = DIDRouting()
        if not didr.load_route(device):
            print(f'Error loading DID route for "{device}"; is it configured with AvantFAX?')
            return 1
        didr.set_contact(email)

    return 0


if __name__ == "__main__":
    sys.exit(main())
