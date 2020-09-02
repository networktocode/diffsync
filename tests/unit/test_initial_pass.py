"""Example Test using Fixtures."""


def test_initial_success(give_me_success):
    "Assert give_me_success is true"
    assert give_me_success
