"""Verification that the provided example code works correctly.

Copyright (c) 2020-2021 Network To Code, LLC <info@networktocode.com>

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

from os.path import join, dirname
import subprocess

EXAMPLES = join(dirname(dirname(dirname(__file__))), "examples")


def test_example_1():
    """Test that the "example1" script runs successfully."""
    example1_dir = join(EXAMPLES, "example1")
    example1_main = join(example1_dir, "main.py")
    # Run it and make sure it doesn't raise an exception or otherwise exit with a non-zero code.
    subprocess.run(example1_main, cwd=example1_dir, check=True)


def test_example_2():
    """Test that the "example2" script runs successfully."""
    example2_dir = join(EXAMPLES, "example2")
    example2_main = join(example2_dir, "example2.py")
    # Run it and make sure it doesn't raise an exception or otherwise exit with a non-zero code.
    subprocess.run(example2_main, cwd=example2_dir, check=True)
