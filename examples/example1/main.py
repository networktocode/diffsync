"""Main executable for DSync "example1"."""
# pylint: disable=wrong-import-order

import argparse

from dsync.logging import enable_console_logging

from backend_a import BackendA
from backend_b import BackendB
from backend_c import BackendC


def main():
    """Demonstrate DSync behavior using the example backends provided."""
    parser = argparse.ArgumentParser("example1")
    parser.add_argument("--verbosity", "-v", default=0, action="count")
    args = parser.parse_args()
    enable_console_logging(verbosity=args.verbosity)

    print("Initializing and loading Backend A...")
    backend_a = BackendA(name="Backend-A")
    backend_a.load()

    print("Initializing and loading Backend B...")
    backend_b = BackendB(name="Backend-B")
    backend_b.load()

    print("Initializing and loading Backend C...")
    backend_c = BackendC()
    backend_c.load()

    print("Getting diffs from Backend A to Backend B...")
    diff_a_b = backend_a.diff_to(backend_b)
    diff_a_b.print_detailed()

    print("Syncing changes from Backend A to Backend B...")
    backend_a.sync_to(backend_b)
    print("Getting updated diffs from Backend A to Backend B...")
    backend_a.diff_to(backend_b).print_detailed()


if __name__ == "__main__":
    main()
