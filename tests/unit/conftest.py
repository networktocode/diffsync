"""Used to setup fixtures to be used through tests"""
import pytest


@pytest.fixture()
def give_me_success():
    """
    Provides True to make tests pass

    Returns:
        (bool): Returns True
    """
    return True
