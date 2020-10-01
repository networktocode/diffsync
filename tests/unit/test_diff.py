"""Unit tests for the Diff class."""

from dsync.diff import Diff, DiffElement


def test_diff_empty():
    """Test the basic functionality of the Diff class when initialized and empty."""
    diff = Diff()

    assert diff.children == {}
    assert list(diff.groups()) == []
    assert not diff.has_diffs()
    assert list(diff.get_children()) == []

    # TODO: print_detailed


def test_diff_children():
    """Test the basic functionality of the Diff class when adding child elements."""
    diff = Diff()
    device_element = DiffElement("device", "device1", {"name": "device1"})
    intf_element = DiffElement("interface", "eth0", {"device_name": "device1", "name": "eth0"})

    diff.add("device", device_element)
    assert "device" in diff.children
    assert diff.children["device"] == {"device1": device_element}
    assert list(diff.groups()) == ["device"]
    assert not diff.has_diffs()
    assert list(diff.get_children()) == [device_element]

    diff.add("interface", intf_element)
    assert "interface" in diff.children
    assert diff.children["interface"] == {"eth0": intf_element}
    assert list(diff.groups()) == ["device", "interface"]
    assert not diff.has_diffs()
    assert list(diff.get_children()) == [device_element, intf_element]

    source_attrs = {"interface_type": "ethernet", "description": "my interface"}
    dest_attrs = {"description": "your interface"}
    intf_element.add_attrs(source=source_attrs, dest=dest_attrs)

    assert diff.has_diffs()

    # TODO: print_detailed
