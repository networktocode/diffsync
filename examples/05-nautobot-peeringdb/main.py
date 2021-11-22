# Import Adapters
from diffsync.enum import DiffSyncFlags

from adapter_nautobot import NautobotRemote
from adapter_peeringdb import PeeringDB

# Initialize PeeringDB adapter, using CATNIX id for demonstration
peeringdb = PeeringDB(ix_id=62)

# Initialize Nautobot adapter, pointing to the demo instance (it's also the default settings)
nautobot = NautobotRemote(url="https://demo.nautobot.com", token="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")

# Load PeeringDB info into the adapter
peeringdb.load()

# We can check the data that has been imported, some as `site` and some as `region` (with the parent relationships)
peeringdb.dict()

# Load Nautobot info into the adapter
nautobot.load()

# Let's diffsync do it's magic
diff = nautobot.diff_from(peeringdb)

# Quick summary of the expected changes (remember that delete ones are dry-run)
diff.summary()

# Execute the synchronization
nautobot.sync_from(peeringdb, flags=DiffSyncFlags.SKIP_UNMATCHED_DST)
