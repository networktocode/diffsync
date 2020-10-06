"""Unit tests for the DiffElement class."""

from dsync.diff import DiffElement


def test_diff_element_empty():
    """Test the basic functionality of the DiffElement class when initialized and empty."""
    # TODO: as currently used, the second parameter is a shortname, not a unique_id...
    element = DiffElement("interface", "eth0", {"device_name": "device1", "name": "eth0"})

    assert element.type == "interface"
    assert element.name == "eth0"
    assert element.keys == {"device_name": "device1", "name": "eth0"}
    assert element.source_attrs is None
    assert element.dest_attrs is None
    assert list(element.get_children()) == []
    assert not element.has_diffs()
    assert not element.has_diffs(include_children=True)
    assert not element.has_diffs(include_children=False)
    assert element.get_attrs_keys() == []

    # TODO print_detailed


def test_diff_element_attrs():
    """Test the basic functionality of the DiffElement class when setting and retrieving attrs."""
    # TODO: as currently used, the second parameter is a shortname, not a unique_id...
    element = DiffElement("interface", "eth0", {"device_name": "device1", "name": "eth0"})

    source_attrs = {"interface_type": "ethernet", "description": "my interface"}
    element.add_attrs(source=source_attrs)
    assert element.source_attrs == source_attrs

    assert element.has_diffs()
    assert element.has_diffs(include_children=True)
    assert element.has_diffs(include_children=False)
    assert element.get_attrs_keys() == source_attrs.keys()

    dest_attrs = {"description": "your interface"}
    element.add_attrs(dest=dest_attrs)
    assert element.source_attrs == source_attrs
    assert element.dest_attrs == dest_attrs

    assert element.has_diffs()
    assert element.has_diffs(include_children=True)
    assert element.has_diffs(include_children=False)
    assert element.get_attrs_keys() == ["description"]  # intersection of source_attrs.keys() and dest_attrs.keys()

    # TODO: print_detailed


def test_diff_element_children():
    """Test the basic functionality of the DiffElement class when storing and retrieving child elements."""
    # TODO: as currently used, the second parameter is a shortname, not a unique_id...
    child_element = DiffElement("interface", "eth0", {"device_name": "device1", "name": "eth0"})
    parent_element = DiffElement("device", "device1", {"name": "device1"})

    parent_element.add_child(child_element)
    assert list(parent_element.get_children()) == [child_element]
    assert not parent_element.has_diffs()
    assert not parent_element.has_diffs(include_children=True)
    assert not parent_element.has_diffs(include_children=False)

    source_attrs = {"interface_type": "ethernet", "description": "my interface"}
    dest_attrs = {"description": "your interface"}
    child_element.add_attrs(source=source_attrs, dest=dest_attrs)

    assert parent_element.has_diffs()
    assert parent_element.has_diffs(include_children=True)
    assert not parent_element.has_diffs(include_children=False)

    # TODO: print_detailed
