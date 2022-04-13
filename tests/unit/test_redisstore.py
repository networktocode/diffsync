"""Testing of RedisStore."""
import pytest
from diffsync.store.redis import RedisStore
from diffsync.exceptions import ObjectStoreException


def test_redisstore_init(redis_url):
    store = RedisStore(name="mystore", store_id="123", url=redis_url)
    assert str(store) == "mystore(123)"


def test_redisstore_init_wrong():
    with pytest.raises(ObjectStoreException):
        RedisStore(name="mystore", store_id="123", url="redis://wrong")


def test_redisstore_add_obj(redis_url, make_site):
    store = RedisStore(name="mystore", store_id="123", url=redis_url)
    site = make_site()
    store.add(site)
    assert store.count() == 1


def test_redisstore_get_all_obj(redis_url, make_site):
    store = RedisStore(name="mystore", store_id="123", url=redis_url)
    site = make_site()
    store.add(site)
    assert store.get_all(site.__class__)[0] == site


def test_redisstore_get_obj(redis_url, make_site):
    store = RedisStore(name="mystore", store_id="123", url=redis_url)
    site = make_site()
    store.add(site)
    assert store.get(site.__class__, site.name) == site


def test_redisstore_remove_obj(redis_url, make_site):
    store = RedisStore(name="mystore", store_id="123", url=redis_url)
    site = make_site()
    store.add(site)
    assert store.count(site.__class__.__name__) == store.count() == 1
    store.remove(site)
    assert store.count(site.__class__.__name__) == store.count() == 0
