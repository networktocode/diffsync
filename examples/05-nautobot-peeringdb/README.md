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

## Set up local docker environment

```bash
$ git clone https://github.com/networktocode/diffsync.git

$ docker-compose -f examples/05-nautobot-peeringdb/docker-compose.yml up -d

$ docker exec -it 05-nautobot-peeringdb_example_1 bash
```
