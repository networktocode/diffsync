#!/usr/bin/env python
"""Example 2 - simple pair of DiffSync adapters and a callback function to report progress.

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

import random

from diffsync import Adapter, DiffSyncModel
from diffsync.logging import enable_console_logging


class Number(DiffSyncModel):
    """Simple model that consists only of a number."""

    _modelname = "number"
    _identifiers = ("number",)

    number: int


class Adapter1(Adapter):
    """DiffSync adapter that contains a number of Numbers constructed in order."""

    number = Number

    top_level = ["number"]

    def load(self, count):  # pylint: disable=arguments-differ
        """Construct Numbers from 1 to count."""
        for i in range(count):
            self.add(Number(number=i + 1))


class Adapter2(Adapter):
    """DiffSync adapter that contains a number of Numbers spread randomly across a range."""

    number = Number

    top_level = ["number"]

    def load(self, count):  # pylint: disable=arguments-differ
        """Construct count numbers in the range (1 - 2*count)."""
        prev = 0
        for i in range(count):  # pylint: disable=unused-variable
            num = prev + random.randint(1, 2)  # noqa: S311
            self.add(Number(number=num))
            prev = num


def print_callback(stage, current, total):
    """Callback for DiffSync; stage is "diff"/"sync", current is records processed to date, total is self-evident."""
    print(f"{stage}: Processed {current:>3}/{total} records.")


def main():
    """Create instances of DiffSync1 and DiffSync2 and sync them with a progress-reporting callback function."""
    enable_console_logging(verbosity=0)  # Show WARNING and ERROR logs only

    # Create a DiffSync1 instance and load it with records numbered 1-100
    ds1 = Adapter1()
    ds1.load(count=100)

    # Create a DiffSync2 instance and load it with 100 random records in the range 1-200
    ds2 = Adapter2()
    ds2.load(count=100)

    # Identify and attempt to resolve the differences between the two,
    # periodically invoking print_callback() as DiffSync progresses
    ds1.sync_to(ds2, callback=print_callback)


if __name__ == "__main__":
    main()
