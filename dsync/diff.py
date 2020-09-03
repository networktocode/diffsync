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

from .utils import intersection, OrderedDefaultDict


class Diff:
    """
    Diff Object, designed to store multiple DiffElement object and aorganized them in group
    """

    def __init__(self):
        self.childs = OrderedDefaultDict(dict)

    def add(self, group: str, element):
        """
        Save a new DiffElement per group, 
        if an element with the same name already exist it will be replaced

        Args:
            group: (string) Group name to store the element
            element: (DiffElement) element to store
        """
        name = element.name
        self.childs[group][name] = element

    def groups(self):
        return self.childs.keys()

    def has_diffs(self) -> bool:
        """Indicate if at least one of the childs element contains some diff

        Returns:
            bool: True if at least one child element contains some diff
        """
        status = False
        for group in self.groups():
            for child in self.childs[group].values():
                if child.has_diffs():
                    status = True

        return status

    def get_childs(self):

        for group in self.groups():
            for child in self.childs[group].values():
                yield child

    def print_detailed(self, indent: int = 0):
        """Print all diffs to screen for all child elements

        Args:
            indent (int, optional): Indentation to use when printing to screen. Defaults to 0.
        """
        margin = " " * indent
        for group in self.groups():
            print(f"{margin}{group}")
            for child in self.childs[group].values():
                if child.has_diffs():
                    child.print_detailed(indent + 2)


class DiffElement:
    """ 
    DiffElement object, designed to represent an item/object
    """

    def __init__(self, obj_type: str, name: str, keys: dict):
        """ """
        if not isinstance(obj_type, str):
            raise ValueError(f"obj_type must be a string (not {type(obj_type)})")

        if not isinstance(name, str):
            raise ValueError(f"name must be a string (not {type(name)})")

        self.type = obj_type
        self.name = name
        self.keys = keys
        self.source_attrs = None
        self.dest_attrs = None
        self.childs = Diff()

    # def __str__(self):
    #     """ """

    #     if self.missing_remote and self.missing_local:
    #         return f"{self.type}:{self.name} MISSING BOTH"
    #     if self.missing_remote:
    #         return f"{self.type}:{self.name} MISSING REMOTE"
    #     if self.missing_local:
    #         return f"{self.type}:{self.name} MISSING LOCAL"
    #     if not self.has_diffs():
    #         return f"{self.type}:{self.name} NO DIFF"

    #     return f"{self.type}:{self.name} {self.nbr_diffs()} DIFFs"

    def add_attrs(self, source: dict = None, dest: dict = None):
        """
        Add an item
        """

        if source != None:
            self.source_attrs = source

        if dest != None:
            self.dest_attrs = dest

    def get_attrs_keys(self):
        """
        Return the list of shared attrs between source and dest
        if source_attrs is not defined return dest
        if dest is not defined, return source
        if both are defined, return the intersection of both
        """

        if self.source_attrs is None and self.dest_attrs is None:
            return None
        elif self.source_attrs is None and self.dest_attrs:
            return self.dest_attrs.keys()
        elif self.source_attrs and self.dest_attrs is None:
            return self.source_attrs.keys()
        else:
            return intersection(self.dest_attrs.keys(), self.source_attrs.keys())

    def add_child(self, element):
        """
        Attach a child object of type DiffElement
        Childs are saved in a Diff object and are organized by type and name

        Args:
          element: DiffElement
        """
        self.childs.add(group=element.type, element=element)

    def get_childs(self):
        return self.childs.get_childs()

    def has_diffs(self, include_childs: bool = True) -> bool:
        """
        return true if the object has some diffs,
        by default it recursively checks all childs as well

        Args:
          include_childs: Default value = True

        Returns:
            bool
        """

        status = False

        if not (self.source_attrs == self.dest_attrs):
            status = True

        if not include_childs:
            return status

        if self.childs.has_diffs():
            status = True

        return status

    def print_detailed(self, indent: int = 0):
        """
        Print status on screen for current object and all childs
        
        Args:
          indent: Default value = 0
        """

        margin = " " * indent

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

        self.childs.print_detailed(indent + 2)
