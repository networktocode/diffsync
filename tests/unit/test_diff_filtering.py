"""Unit tests for the Diff filter and exclude methods.

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

import pytest

from diffsync.diff import Diff, DiffElement


def test_diff_filter_by_action_create(diff_with_children):
    """Filtering a Diff by action='create' should only retain elements with create diffs."""
    filtered = diff_with_children.filter(actions={"create"})
    actions = []
    for child in filtered.get_children():
        if child.action:
            actions.append(child.action)
    assert "create" in actions
    assert "delete" not in actions


def test_diff_filter_by_action_delete(diff_with_children):
    """Filtering a Diff by action='delete' should only retain elements with delete diffs."""
    filtered = diff_with_children.filter(actions={"delete"})
    actions = []
    for child in filtered.get_children():
        if child.action:
            actions.append(child.action)
    assert "delete" in actions
    assert "create" not in actions


def test_diff_filter_by_model_types(diff_with_children):
    """Filtering a Diff by model_types should only retain elements of those types."""
    filtered = diff_with_children.filter(model_types={"person"})
    types = [child.type for child in filtered.get_children()]
    assert "person" in types
    assert "device" not in types
    assert "address" not in types


def test_diff_filter_by_action_and_model_type(diff_with_children):
    """Filtering by both action and model type should apply both criteria."""
    filtered = diff_with_children.filter(actions={"create"}, model_types={"person"})
    elements = list(filtered.get_children())
    assert len(elements) == 1
    assert elements[0].type == "person"
    assert elements[0].action == "create"


def test_diff_filter_does_not_mutate_original(diff_with_children):
    """Calling filter() should return a new Diff without modifying the original."""
    original_len = len(diff_with_children)
    _ = diff_with_children.filter(actions={"create"})
    assert len(diff_with_children) == original_len


def test_diff_exclude_by_action(diff_with_children):
    """Excluding by action should remove elements with that action."""
    excluded = diff_with_children.exclude(actions={"delete"})
    for child in excluded.get_children():
        assert child.action != "delete"


def test_diff_exclude_by_model_types(diff_with_children):
    """Excluding by model_types should remove elements of those types."""
    excluded = diff_with_children.exclude(model_types={"person"})
    types = [child.type for child in excluded.get_children()]
    assert "person" not in types


def test_diff_filter_no_criteria_returns_full_copy(diff_with_children):
    """Filtering with no criteria should return a copy of the entire Diff."""
    filtered = diff_with_children.filter()
    assert len(filtered) == len(diff_with_children)


def test_diff_exclude_no_criteria_returns_full_copy(diff_with_children):
    """Excluding with no criteria should return a copy of the entire Diff."""
    excluded = diff_with_children.exclude()
    assert len(excluded) == len(diff_with_children)


def test_diff_filter_preserves_models_processed(diff_with_children):
    """The models_processed count should be preserved on the filtered Diff."""
    filtered = diff_with_children.filter(actions={"create"})
    assert filtered.models_processed == diff_with_children.models_processed
