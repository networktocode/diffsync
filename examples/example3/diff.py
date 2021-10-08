from diffsync.diff import Diff


class AlphabeticalOrderDiff(Diff):
    """Simple diff to return all children country in alphabetical order."""

    @classmethod
    def order_children_default(cls, children):
        """Simple diff to return all children in alphabetical order."""
        for child_name, child in sorted(children.items()):

            # it's possible to access additional information about the object
            #  like  child.action can be "update", "create" or "delete"

            yield children[child_name]
