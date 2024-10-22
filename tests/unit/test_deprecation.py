"""Unit tests for the DiffSync deprecation warning.

Copyright (c) 2020-2024 Network To Code, LLC <info@networktocode.com>

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

import pytest

from diffsync import DiffSync


def test_diffsync_deprecation_warning():
    """Test that `DiffSync` causes a deprecation warning."""
    with pytest.deprecated_call():

        class TestAdapter(DiffSync):  # pylint:disable=missing-class-docstring
            pass

        TestAdapter()
