
from diffsync import DiffSync

import pytest

def test_diffsync_deprecation_warning():
    with pytest.deprecated_call():
        class TestAdapter(DiffSync):
            pass
        TestAdapter()
