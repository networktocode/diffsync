# Store backends

By default, `Diffsync` supports a local memory storage. All the loaded models from the adapters will be stored in memory, and become available for the diff calculation and sync process. This default behavior works well when executing all the steps in the same process, having access to the same memory space. However, if you want to scale out the execution of the tasks, running it in different processes or in totally different workers, a more distributed memory support is necessary.

The `store` is a class attribute in the `Adapter` class, but all the store operations in that class are abstracted in the following methods: `get_all_model_names`, `get`, `get_by_uids`, `add`, `update`, `remove`, `get_or_instantiate`, `update_or_instantiate` and `count`.

## Use the `LocalStore` Backend

When you initialize the `Diffsync` Adapter class, there is an optional keyed-argument, `internal_storage_engine`, defaulting to the `LocalStore` class.

```python
>> > from diffsync import Adapter
>> > adapter = Adapter()
>> > type(adapter.store)
<

class 'diffsync.store.local.LocalStore'>
```

## Use the `RedisStore` Backend

To get it, you have to install diffsync package with the "redis" extra option: `pip install diffsync[redis]`

The `RedisStore` backend, as the name suggests, connects to an external Redis service, to store data loaded by the `Adapter` tasks. The biggest change is that it requires to initialize the Redis store class, before using it in the `Adapter` adapter class.

```python
>> > from diffsync import Adapter
>> > from diffsync.store.redis import RedisStore
>> > store = RedisStore(host="redis host")
>> > adapter = Adapter(internal_storage_engine=store)
>> > type(adapter.store)
<

class 'diffsync.store.local.RedisStore'>
```

Notice that the `RedisStore` will validate, when initialized, that there is a reachability to the Redis host, and if not, will raise an exception:

```python
>>> from diffsync.store.redis import RedisStore
>>> store = RedisStore(host="redis host")
redis.exceptions.ConnectionError

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/Users/chadell/github.ntc/diffsync/diffsync/store/redis.py", line 34, in __init__
    raise ObjectStoreException("Redis store is unavailable.") from RedisConnectionError
diffsync.exceptions.ObjectStoreException: Redis store is unavailable.
```

Using `RedisStore`, every adapter uses a specific Redis label, generated automatically, if not provided via the `store_id` keyed-argument. This `store_id` can be used to point an adapter to the specific memory state needed for diffsync operations.
