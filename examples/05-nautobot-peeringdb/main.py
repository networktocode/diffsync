"""Main.py."""
from uuid import uuid4

# Import Adapters
from adapter_nautobot import NautobotRemote
from adapter_peeringdb import PeeringDB

from diffsync.enum import DiffSyncFlags
from diffsync.store.redis import RedisStore  # pylint: disable=no-name-in-module,import-error

REDIS_HOST = "redis"
PEERING_DB_IX_ID = 62  # CATNIX ID
NAUTOBOT_URL = "https://demo.nautobot.com"
NAUTOBOT_TOKEN = "a" * 40

store_one = RedisStore(host=REDIS_HOST, id=uuid4())
store_two = RedisStore(host=REDIS_HOST, id=uuid4())

# Initialize PeeringDB adapter
peeringdb = PeeringDB(ix_id=PEERING_DB_IX_ID, internal_storage_engine=store_one)

# Initialize Nautobot adapter, pointing to the demo instance (it's also the default settings)
nautobot = NautobotRemote(url=NAUTOBOT_URL, token=NAUTOBOT_TOKEN, internal_storage_engine=store_two)  # nosec

# Load PeeringDB info into the adapter
peeringdb.load()

# We can check the data that has been imported, some as `site` and some as `region` (with the parent relationships)
peeringdb.dict()

# Load Nautobot info into the Nautobot adapter
nautobot.load()

# Let's diffsync do it's magic
diff = nautobot.diff_from(peeringdb, flags=DiffSyncFlags.SKIP_UNMATCHED_DST)

# Quick summary of the expected changes
diff.summary()

# Execute the synchronization
nautobot.sync_from(peeringdb, flags=DiffSyncFlags.SKIP_UNMATCHED_DST)
