#!/usr/bin/env python
"""Main executable for DiffSync "example1".

Copyright (c) 2021 Network To Code, LLC <info@networktocode.com>

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
import pprint

from diffsync.logging import enable_console_logging

from backends import BackendA
from backends import BackendB


def main():
    """Demonstrate DiffSync behavior using the example backends provided."""
    parser = argparse.ArgumentParser("example4")
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

    print("Getting diffs from Backend A to Backend B...")
    diff_a_b = backend_a.diff_to(backend_b)
    print(diff_a_b.str())

    print("Diffs can also be represented as a dictionary...")
    pprint.pprint(diff_a_b.dict(), width=120)

    print("Syncing changes from Backend A to Backend B...")
    backend_a.sync_to(backend_b)
    print("Getting updated diffs from Backend A to Backend B...")
    print(backend_a.diff_to(backend_b).str())


if __name__ == "__main__":
    main()
