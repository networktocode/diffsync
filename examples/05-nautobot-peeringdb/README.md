# Example 5 - PeeringDB to Nautobot synchronisation

## Context

The goal of this example is to synchronize some data from [PeeringDB](https://www.peeringdb.com/), that as the name suggests is a DB where peering entities define their facilities and presence to facilitate peering, towards [Nautobot Demo](https://demo.nautobot.com/) that is a always on demo service for [Nautobot](https://nautobot.readthedocs.io/), an open source Source of Truth.

In Peering DB there is a model that defines a `Facility` and you can get information about the actual data center and the city where it is placed. In Nautobot, this information could be mapped to the `Region` and `Site` models, where `Region` can depend from other `Region` and also contain `Site` as children. For instance, Barcelona is in Spain and Spain is in Europe, and all of them are `Regions`. And, finally, the actual datacenter will refer to the `Region` where it is placed.

Because of the nature of the demo, we will focus on syncing from PeeringDB to Nautobot (we assume that PeeringDB is the authoritative System of Record) and we will skip the `delete` part of the `diffsync` library, using diffsync flags.

We have 3 files:

- `models.py`: defines the reference models that we will use: `RegionMode` and `SiteModel`
- `adapter_peeringdb.py`: defines the PeeringDB adapter to translate via `load()` the data from PeeringDB into the reference models commented above. Notice that we don't define CRUD methods because we will sync from it (no to it)
- `adapter_nautobot.py`: defines the Nautobot adapter with the `load()` and the CRUD methods

> The source code for this example is in Github in the [examples/05-nautobot-peeringdb/](https://github.com/networktocode/diffsync/tree/main/examples/05-nautobot-peeringdb) directory.

## Get PeeringDB API Key (optional)

To ensure a good performance from PeeringDB API, you should provide an API Key: https://docs.peeringdb.com/howto/api_keys/

Then, copy the example `creds.example.env` into `creds.env`, and place your new API Key.

```bash
$ cp examples/05-nautobot-peeringdb/creds.example.env examples/05-nautobot-peeringdb/creds.env

```

> Without API Key it might also work, but it could fail due to API rate limiting.

## Set up local docker environment

```bash
$ docker-compose -f examples/05-nautobot-peeringdb/docker-compose.yml up -d --build

$ docker exec -it 05-nautobot-peeringdb_example_1 python
```

## Interactive execution

```python
from adapter_nautobot import NautobotRemote
from adapter_peeringdb import PeeringDB
from diffsync.enum import DiffSyncFlags
from diffsync.store.redis import RedisStore

store_one = RedisStore(host="redis")
store_two = RedisStore(host="redis")

# Initialize PeeringDB adapter, using CATNIX id for demonstration
peeringdb = PeeringDB(
    ix_id=62,
    internal_storage_engine=store_one
)

# Initialize Nautobot adapter, pointing to the demo instance (it's also the default settings)
nautobot = NautobotRemote(
    url="https://demo.nautobot.com",
    token="a" * 40,
    internal_storage_engine=store_two
)

# Load PeeringDB info into the adapter
peeringdb.load()

# We can check the data that has been imported, some as `site` and some as `region` (with the parent relationships)
peeringdb.dict()

# Load Nautobot info into the adapter
nautobot.load()

# Let's diffsync do it's magic
diff = nautobot.diff_from(peeringdb, flags=DiffSyncFlags.SKIP_UNMATCHED_DST)

# Quick summary of the expected changes (remember that delete ones are dry-run)
diff.summary()

# Execute the synchronization
nautobot.sync_from(peeringdb, flags=DiffSyncFlags.SKIP_UNMATCHED_DST)
```
