"""Main executable for DSync "example1"."""
# pylint: disable=wrong-import-order

import argparse

from dsync import Diff
from dsync.logging import enable_console_logging

from backend_a import BackendA
from backend_b import BackendB
from backend_c import BackendC


class MyDiff(Diff):
    """Custom Diff class to control the order of the site objects."""

    @classmethod
    def order_children_site(cls, children):
        """Return the site children ordered in alphabetical order."""
        keys = sorted(children.keys(), reverse=False)
        for key in keys:
            yield children[key]


def main():
    """Demonstrate DSync behavior using the example backends provided."""
    parser = argparse.ArgumentParser("example1")
    parser.add_argument("--verbosity", "-v", default=0, action="count")
    args = parser.parse_args()
    enable_console_logging(verbosity=args.verbosity)

    print("Initializing and loading Backend A...")
    backend_a = BackendA(name="Backend-A")
    backend_a.load()
    backend_a.print_detailed()

    print("Initializing and loading Backend B...")
    backend_b = BackendB(name="Backend-B")
    backend_b.load()
    backend_b.print_detailed()

    print("Initializing and loading Backend C...")
    backend_c = BackendC()
    backend_c.load()
    backend_c.print_detailed()

    print("Getting diffs from Backend A to Backend B...")
    diff_a_b = backend_a.diff_to(backend_b, diff_class=MyDiff)
    diff_a_b.print_detailed()

    print("Syncing changes from Backend A to Backend B...")
    backend_a.sync_to(backend_b)
    print("Getting updated diffs from Backend A to Backend B...")
    backend_a.diff_to(backend_b).print_detailed()


if __name__ == "__main__":
    main()
