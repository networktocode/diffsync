"""Utility functions for DiffSync library.

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

from collections import OrderedDict
from typing import List


def intersection(lst1, lst2) -> List:
    """Calculate the intersection of two lists, with ordering based on the first list."""
    lst3 = [value for value in lst1 if value in lst2]
    return lst3


def symmetric_difference(lst1, lst2) -> List:
    """Calculate the symmetric difference of two lists."""
    return sorted(set(lst1) ^ set(lst2))


class OrderedDefaultDict(OrderedDict):
    """A combination of collections.OrderedDict and collections.DefaultDict behavior."""

    def __init__(self, dict_type):
        """Create a new OrderedDefaultDict."""
        self.factory = dict_type
        super().__init__(self)

    def __missing__(self, key):
        """When trying to access a nonexistent key, initialize the key value based on the internal factory."""
        self[key] = value = self.factory()
        return value
