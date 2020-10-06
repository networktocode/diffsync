"""Diff and DiffElement classes for DSync.

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

from functools import total_ordering
from typing import Iterator, Optional

from .utils import intersection, OrderedDefaultDict


class Diff:
    """Diff Object, designed to store multiple DiffElement object and organize them in a group."""

    def __init__(self):
        """Initialize a new, empty Diff object."""
        self.children = OrderedDefaultDict(dict)
        """DefaultDict for storing DiffElement objects.

        `self.children[group][unique_id] == DiffElement(...)`
        """

    def add(self, group: str, element: "DiffElement"):
        """Save a new DiffElement per group; if an element with the same name already exists it will be replaced.

        Args:
            group: (string) Group name to store the element
            element: (DiffElement) element to store
        """
        # TODO: why is group an argument, why not just use element.obj_type?
        # TODO: element.name is usually a DSyncModel.shortname() -- i.e., NOT guaranteed globally unique!!
        name = element.name

        # TODO: shouldn't it be an error if the element already exists, like in DSync.add()?
        self.children[group][name] = element

    def groups(self):
        """Get the list of all group keys in self.children."""
        return self.children.keys()

    def has_diffs(self) -> bool:
        """Indicate if at least one of the child elements contains some diff.

        Returns:
            bool: True if at least one child element contains some diff
        """
        for group in self.groups():
            for child in self.children[group].values():
                if child.has_diffs():
                    return True

        return False

    def get_children(self) -> Iterator["DiffElement"]:
        """Iterate over all child elements in all groups in self.children."""
        for group in self.groups():
            for child in self.children[group].values():
                yield child

    def print_detailed(self, indent: int = 0):
        """Print all diffs to screen for all child elements.

        Args:
            indent (int, optional): Indentation to use when printing to screen. Defaults to 0.
        """
        margin = " " * indent
        for group in self.groups():
            print(f"{margin}{group}")
            for child in self.children[group].values():
                if child.has_diffs():
                    child.print_detailed(indent + 2)


@total_ordering
class DiffElement:
    """DiffElement object, designed to represent a single item/object that may or may not have any diffs."""

    # TODO: make this a Pydantic.BaseModel subclass?

    def __init__(self, obj_type: str, name: str, keys: dict):
        """Instantiate a DiffElement.

        Args:
            obj_type (str): Name of the object type being described, as in DSyncModel.get_type().
            name (str): Human-readable name of the object being described, as in DSyncModel.get_shortname()
                        TODO: name is not guaranteed globally unique?
            keys (dict): Primary keys and values uniquely describing this object, as in DSyncModel.get_identifiers().

        TODO: refactor so it just takes a DSyncModel as its only input parameter instead?
        """
        if not isinstance(obj_type, str):
            raise ValueError(f"obj_type must be a string (not {type(obj_type)})")

        if not isinstance(name, str):
            raise ValueError(f"name must be a string (not {type(name)})")

        self.type = obj_type
        self.name = name
        self.keys = keys
        self.source_attrs: Optional[dict] = None
        self.dest_attrs: Optional[dict] = None
        self.child_diff = Diff()

    def __lt__(self, other):
        """Logical ordering of DiffElements.

        Other comparison methods (__gt__, __le__, __ge__, etc.) are created by our use of the @total_ordering decorator.
        """
        return (self.type, self.name) < (other.type, other.name)

    def __eq__(self, other):
        """Logical equality of DiffElements.

        Other comparison methods (__gt__, __le__, __ge__, etc.) are created by our use of the @total_ordering decorator.
        """
        if not isinstance(other, DiffElement):
            return NotImplemented
        return (
            self.type == other.type
            and self.name == other.name
            and self.keys == other.keys
            and self.source_attrs == other.source_attrs
            and self.dest_attrs == other.dest_attrs
            # TODO self.child_diff == other.child_diff
        )

    def __str__(self):
        """Basic string representation of a DiffElement."""
        return f"{self.type} : {self.name} : {self.keys} : {self.source_attrs} : {self.dest_attrs}"

    # TODO: separate into set_source_attrs() and set_dest_attrs() methods, or just use direct property access instead?
    def add_attrs(self, source: Optional[dict] = None, dest: Optional[dict] = None):
        """Set additional attributes of a source and/or destination item that may result in diffs."""
        # TODO: should source_attrs and dest_attrs be "write-once" properties, or is it OK to overwrite them once set?
        if source is not None:
            self.source_attrs = source

        if dest is not None:
            self.dest_attrs = dest

    def get_attrs_keys(self):
        """Return the list of shared attrs between source and dest, or the attrs of source or diff if only one is present.

        - If source_attrs is not defined return dest
        - If dest is not defined, return source
        - If both are defined, return the intersection of both

        TODO: this obscures the difference between "source/dest does not exist at all" and
        "source/dest exists but does not have any attrs defined beyond the base `keys`" - this seems problematic.
        """
        if self.source_attrs is None and self.dest_attrs is None:
            return None
        if self.source_attrs is None and self.dest_attrs:
            return self.dest_attrs.keys()
        if self.source_attrs and self.dest_attrs is None:
            return self.source_attrs.keys()
        return intersection(self.dest_attrs.keys(), self.source_attrs.keys())

    def add_child(self, element: "DiffElement"):
        """Attach a child object of type DiffElement.

        Childs are saved in a Diff object and are organized by type and name.

        Args:
          element: DiffElement
        """
        self.child_diff.add(group=element.type, element=element)

    def get_children(self) -> Iterator["DiffElement"]:
        """Iterate over all child DiffElements of this one."""
        yield from self.child_diff.get_children()

    def has_diffs(self, include_children: bool = True) -> bool:
        """Check whether this element (or optionally any of its children) has some diffs.

        Args:
          include_children: If True, recursively check children for diffs as well.
        """
        if self.source_attrs != self.dest_attrs:
            return True

        if include_children:
            if self.child_diff.has_diffs():
                return True

        return False

    def print_detailed(self, indent: int = 0):
        """Print status on screen for current object and all children.

        Args:
          indent: Default value = 0
        """
        margin = " " * indent

        # TODO: this obscures the difference between "source/dest does not exist" and
        # "source/dest exists but has no specific `attrs` defined."

        # if self.missing_remote and self.missing_local:
        #     print(f"{margin}{self.type}: {self.name} MISSING BOTH")
        if self.source_attrs is None:
            print(f"{margin}{self.type}: {self.name} MISSING in SOURCE")
        elif self.dest_attrs is None:
            print(f"{margin}{self.type}: {self.name} MISSING in DEST")
        else:
            print(f"{margin}{self.type}: {self.name}")
            # Currently we assume that source and dest have the same attrs,
            # need to account for that
            for attr in self.get_attrs_keys():
                if self.source_attrs.get(attr, None) != self.dest_attrs.get(attr, None):
                    print(f"{margin}  {attr}   S({self.source_attrs[attr]})   D({self.dest_attrs[attr]})")

        self.child_diff.print_detailed(indent + 2)
