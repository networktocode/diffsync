"""
(c) 2020 Network To Code

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


def intersection(lst1, lst2):
    lst3 = [value for value in lst1 if value in lst2]
    return lst3


class OrderedDefaultDict(OrderedDict):
    def __init__(self, dict_type):
        self.factory = dict_type

    def __missing__(self, key):
        self[key] = value = self.factory()
        return value
