# Example 5 - PeeringDB to Nautobot synchronisation

## Context

The goal of this example is to synchronize some data from [PeeringDB](https://www.peeringdb.com/), that as the name suggests is a DB where peering entities define their facilities and presence to facilitate peering, towards [Nautobot Demo](https://demo.nautobot.com/) that is a always on demo service for [Nautobot](https://nautobot.readthedocs.io/), an open source Source of Truth.

In Peering DB there is a model that defines a `Facility` and you can get information about the actual data center and the city where it is placed. In Nautobot, this information could be mapped to the `Region` and `Site` models, where `Region` can define hierarchy. For instance, Barcelona is in Spain and Spain is in Europe, and all of them are `Regions`. And, finally, the actual datacenter will refer to the `Region` where it is placed.

Because of the nature of the demo, we will focus on syncing from PeeringDB to Nautobot (we can assume that PeeringDB is the authoritative System of Record) and we will skip the `delete` part of the `diffsync` library, using diffsync flags.

We have 3 files:

- `models.py`: defines the reference models that we will use: `RegionMode` and `SiteModel`
- `adapter_peeringdb.py`: defines the PeeringDB adapter to translate via `load()` the data from PeeringDB into the reference models commented above. Notice that we don't define CRUD methods because we will sync from it (no to it)
- `adapter_nautobot.py`: deifnes the Nautobot adapter with the `load()` and the CRUD methods

> The source code for this example is in Github in the [examples/05-nautobot-peeringdb/](https://github.com/networktocode/diffsync/tree/main/examples/05-nautobot-peeringdb) directory.

## Set up local docker environment

```bash
$ git clone https://github.com/networktocode/diffsync.git

$ docker-compose -f examples/05-nautobot-peeringdb/docker-compose.yml up -d

$ docker exec -it 05-nautobot-peeringdb_example_1 bash
```

## Run it interactively

```python
from IPython import embed
embed(colors="neutral")

import uuid

# Import Adapters
from adapter_nautobot import NautobotRemote
from adapter_peeringdb import PeeringDB

from diffsync.enum import DiffSyncFlags
from diffsync.store.redis import RedisStore

REDIS_HOST = "redis"
PEERING_DB_IX_ID = 62
NAUTOBOT_URL = "https://demo.nautobot.com"
NAUTOBOT_TOKEN = "a" * 40

store_one = RedisStore(host=REDIS_HOST, id=uuid.uuid4())
store_two = RedisStore(host=REDIS_HOST, id=uuid.uuid4())

# Initialize PeeringDB adapter, using CATNIX id for demonstration
peeringdb = PeeringDB(ix_id=PEERING_DB_IX_ID, internal_storage_engine=store_one)

# Initialize Nautobot adapter, pointing to the demo instance (it's also the default settings)
nautobot = NautobotRemote(url=NAUTOBOT_URL, token=NAUTOBOT_TOKEN, internal_storage_engine=store_two)  # nosec

# Load PeeringDB info into the adapter
peeringdb.load()

# We can check the data that has been imported, some as `site` and some as `region` (with the parent relationships)
peeringdb.dict()

# Load Nautobot info into the adapter
nautobot.load()

# Let's diffsync do it's magic
diff = nautobot.diff_from(peeringdb, flags=DiffSyncFlags.SKIP_UNMATCHED_DST)

# Quick summary of the expected changes
diff.summary()

# Execute the synchronization
nautobot.sync_from(peeringdb, flags=DiffSyncFlags.SKIP_UNMATCHED_DST)

```
