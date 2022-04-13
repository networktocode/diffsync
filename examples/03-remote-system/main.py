#!/usr/bin/env python
"""Main executable for DiffSync "example3"."""
import sys
import argparse

from local_adapter import LocalAdapter
from nautobot_adapter import NautobotAdapter
from diff import AlphabeticalOrderDiff

from diffsync.enum import DiffSyncFlags
from diffsync.logging import enable_console_logging


def main():
    """Demonstrate DiffSync behavior using the example backends provided."""
    parser = argparse.ArgumentParser("example3")
    parser.add_argument("--verbosity", "-v", default=0, action="count")
    parser.add_argument("--diff", action="store_true")
    parser.add_argument("--sync", action="store_true")
    args = parser.parse_args()
    enable_console_logging(verbosity=args.verbosity)

    if not args.sync and not args.diff:
        sys.exit("please select --diff or --sync")

    print("Initializing and loading Local Data ...")
    local = LocalAdapter()
    local.load()

    print("Initializing and loading Nautobot Data ...")
    nautobot = NautobotAdapter()
    nautobot.load()

    # If a Region exists in Nautobot (the "destination") but not in the local data, skip it, rather than deleting it
    flags = DiffSyncFlags.SKIP_UNMATCHED_DST

    if args.diff:
        print("Calculating the Diff between the local adapter and Nautobot ...")
        diff = nautobot.diff_from(local, flags=flags, diff_class=AlphabeticalOrderDiff)
        print(diff.str())

    if args.sync:
        if not args.diff:
            diff = None
        print("Updating the list of countries in Nautobot ...")
        nautobot.sync_from(local, flags=flags, diff_class=AlphabeticalOrderDiff, diff=diff)


if __name__ == "__main__":
    main()
