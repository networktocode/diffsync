#!/usr/bin/env python
"""Main executable for DiffSync "example1".

Copyright (c) 2020 Network To Code, LLC <info@networktocode.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
# pylint: disable=wrong-import-order

import argparse

from diffsync import Diff
from diffsync.logging import enable_console_logging

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
    """Demonstrate DiffSync behavior using the example backends provided."""
    parser = argparse.ArgumentParser("example1")
    parser.add_argument("--verbosity", "-v", default=0, action="count")
    args = parser.parse_args()
    enable_console_logging(verbosity=args.verbosity)

    print("Initializing and loading Backend A...")
    backend_a = BackendA(name="Backend-A")
    backend_a.load()
    print(backend_a.str())

    print("Initializing and loading Backend B...")
    backend_b = BackendB(name="Backend-B")
    backend_b.load()
    print(backend_b.str())

    print("Initializing and loading Backend C...")
    backend_c = BackendC()
    backend_c.load()
    print(backend_c.str())

    print("Getting diffs from Backend A to Backend B...")
    diff_a_b = backend_a.diff_to(backend_b, diff_class=MyDiff)
    print(diff_a_b.str())

    print("Syncing changes from Backend A to Backend B...")
    backend_a.sync_to(backend_b)
    print("Getting updated diffs from Backend A to Backend B...")
    print(backend_a.diff_to(backend_b).str())


if __name__ == "__main__":
    main()
