from datetime import datetime, timezone

import pytest

from finnflip.service import ROOT, load_config
from finnflip.sources import DemoAdapter
from finnflip.storage import Store


@pytest.fixture(autouse=True)
def freeze_test_clock(monkeypatch):
    # Static demo observations must remain testable after their real-world freshness window.
    import finnflip.models
    import finnflip.morning
    import finnflip.notifications
    import finnflip.service
    import finnflip.sources
    import finnflip.storage

    fixed = datetime(2026, 10, 19, 14, tzinfo=timezone.utc)
    for module in (
        finnflip.models,
        finnflip.morning,
        finnflip.notifications,
        finnflip.service,
        finnflip.sources,
        finnflip.storage,
    ):
        monkeypatch.setattr(module, "utcnow", lambda: fixed)


@pytest.fixture
def cfg():
    return load_config()


@pytest.fixture
def at():
    return datetime(2026, 10, 19, 14, tzinfo=timezone.utc)


@pytest.fixture
def candidates():
    rows, _ = DemoAdapter(ROOT / "fixtures").load("candidates")
    return {row.id: row for row in rows}


@pytest.fixture
def refs():
    return DemoAdapter(ROOT / "fixtures").load("references")[0]


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "test.sqlite")
