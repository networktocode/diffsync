from typing import Annotated

from diffsync.nextgen import NGAdapter, NGModel, NGModelFieldKind, NGDiff


class NGTestModel(NGModel):
    metadata = {
        "model_name": "Test"
    }
    identifier: Annotated[int, NGModelFieldKind.IDENTIFIER]
    int_value: Annotated[int, NGModelFieldKind.ATTRIBUTE] = 0
    str_value: Annotated[str, NGModelFieldKind.ATTRIBUTE] = ""


def test_get_identifiers():
    instance = NGTestModel(identifier=1)
    assert instance.get_identifiers() == {"identifier": instance.identifier}


def test_adapter_add_get():
    """Test that the `add` and `get` methods on the adapter work."""
    adapter = NGAdapter()
    instance = NGTestModel(identifier=1)
    adapter.add(instance)
    assert adapter.get(NGTestModel.metadata["model_name"], {"identifier": 1}) == instance


def test_diff_model():
    a = NGTestModel(identifier=5, int_value=10, str_value="a")
    b = NGTestModel(identifier=5, int_value=10, str_value="b")

    assert dict(a.diff_to(b)) == {"str_value": b.str_value}


def test_diff():
    only_in_a = NGTestModel(identifier=1, int_value=10, str_value="Only in A")
    in_both_a = NGTestModel(identifier=2, int_value=10, str_value="In A")
    in_both_b = NGTestModel(identifier=2, int_value=10, str_value="In B")
    only_in_b = NGTestModel(identifier=3, int_value=30, str_value="Only in B")

    adapter_a = NGAdapter()
    adapter_a.add(only_in_a)
    adapter_a.add(in_both_a)
    adapter_b = NGAdapter()
    adapter_b.add(only_in_b)
    adapter_b.add(in_both_b)

    resulting_diff = NGDiff.diff(adapter_a, adapter_b)
    assert resulting_diff.to_create[NGTestModel.metadata["model_name"]] == frozenset(only_in_b)