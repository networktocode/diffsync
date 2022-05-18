"""Testing of RedisStore."""
import pytest
from diffsync.store.redis import RedisStore
from diffsync.exceptions import ObjectStoreException


def test_redisstore_init(redis_url):
    store = RedisStore(name="mystore", store_id="123", url=redis_url)
    assert str(store) == "mystore (123)"


def test_redisstore_init_wrong():
    with pytest.raises(ObjectStoreException):
        RedisStore(name="mystore", store_id="123", url="redis://wrong")


def test_redisstore_add_obj(redis_url, make_site):
    store = RedisStore(name="mystore", store_id="123", url=redis_url)
    site = make_site()
    store.add(obj=site)
    assert store.count() == 1


def test_redisstore_add_obj_twice(redis_url, make_site):
    store = RedisStore(name="mystore", store_id="123", url=redis_url)
    site = make_site()
    store.add(obj=site)
    store.add(obj=site)
    assert store.count() == 1


def test_redisstore_get_all_obj(redis_url, make_site):
    store = RedisStore(name="mystore", store_id="123", url=redis_url)
    site = make_site()
    store.add(obj=site)
    assert store.get_all(model=site.__class__)[0] == site


def test_redisstore_get_obj(redis_url, make_site):
    store = RedisStore(name="mystore", store_id="123", url=redis_url)
    site = make_site()
    store.add(obj=site)
    assert store.get(model=site.__class__, identifier=site.name) == site


def test_redisstore_remove_obj(redis_url, make_site):
    store = RedisStore(name="mystore", store_id="123", url=redis_url)
    site = make_site()
    store.add(obj=site)
    assert store.count(modelname=site.__class__.__name__) == store.count() == 1
    store.remove(obj=site)
    assert store.count(modelname=site.__class__.__name__) == store.count() == 0


def test_redisstore_get_all_model_names(redis_url, make_site, make_device):
    store = RedisStore(name="mystore", store_id="123", url=redis_url)
    site = make_site()
    store.add(obj=site)
    device = make_device()
    store.add(obj=device)
    assert site.get_type() in store.get_all_model_names()
    assert device.get_type() in store.get_all_model_names()
