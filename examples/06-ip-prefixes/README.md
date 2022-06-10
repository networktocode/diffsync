# Example 06 - IP Prefixes

This example shows how to play around to IPAM systems which have a different implementation of an IP Prefix.

These IPAM systems, IPAM A and IPAM B, are simulated using two YAML files within the `data` folder. These files are dynamic, and they will be loaded and updated from diffsync.

## Test the example

You could simply run the `main.py` file, but to run step by step.

### Set up the environment

Install the dependencies (recommended into a virtual environment)

```
pip3 install -r requirements.txt
```

and go into a `python` interactive session:

```
python3
>>>
```

### Import the DiffSync adapters

```py
>>> from adapter_ipam_a import IpamA
>>> from adapter_ipam_b import IpamB
```

### Initialize and load adapter for IPAM A

```py
>>> ipam_a = IpamA()
>>> ipam_a.load()
```

You can check the content loaded from IPAM A. Notice that the data has been transformed into the DiffSync model, which is different from the original YAML data.

```py
>>> import pprint
>>> pprint.pprint(ipam_a.dict())
{'prefix': {'10.10.10.10/24': {'prefix': '10.10.10.10/24',
                               'vlan_id': 10,
                               'vrf': 'data'},
            '10.20.20.20/24': {'prefix': '10.20.20.20/24',
                               'tenant': 'ABC corp',
                               'vlan_id': 20,
                               'vrf': 'voice'},
            '172.18.0.0/16': {'prefix': '172.18.0.0/16', 'vlan_id': 18}}}
```

### Initialize and load adapter for IPAM B

```py
>>> ipam_b = IpamB()
>>> ipam_b.load()
```

You can check the content loaded from IPAM B. Notice that the data has been transformed into the DiffSync model, which again is different from the original YAML format.

```py
>>> pprint.pprint(ipam_b.dict())
{'prefix': {'10.10.10.10/24': {'prefix': '10.10.10.10/24', 'vlan_id': 123},
            '2001:DB8::/32': {'prefix': '2001:DB8::/32',
                              'tenant': 'XYZ Corporation',
                              'vlan_id': 10,
                              'vrf': 'data'}}}
```

### Check the difference

We can use `diff_to` or `diff_from` to select, from the perspective of the calling adapter, who is the authoritative in each case.

```py
>>> diff = ipam_a.diff_to(ipam_b)
```

From this `diff`, we can check the summary of what would happen.

```py
>>> diff.summary()
{'create': 2, 'update': 1, 'delete': 1, 'no-change': 0}
```

And, also go into the details. We can see how the `'+'` and + `'-'` represent the actual changes in the target adapter: create, delete or update (when both symbols appear).

```py
>>> pprint.pprint(diff.dict())
{'prefix': {'10.10.10.10/24': {'+': {'vlan_id': 10, 'vrf': 'data'},
                               '-': {'vlan_id': 123, 'vrf': None}},
            '10.20.20.20/24': {'+': {'tenant': 'ABC corp',
                                     'vlan_id': 20,
                                     'vrf': 'voice'}},
            '172.18.0.0/16': {'+': {'tenant': None,
                                    'vlan_id': 18,
                                    'vrf': None}},
            '2001:DB8::/32': {'-': {'tenant': 'XYZ Corporation',
                                    'vlan_id': 10,
                                    'vrf': 'data'}}}}
```

### Enforce synchronization

Simply transforming the `diff_to` to `sync_to`, we are going to change the state of the destination target.

```py
>>> ipam_a.sync_to(ipam_b)
```

### Validate synchronization

Now, if we reload the IPAM B, and try to check the difference, we should see no differences.

```py
>>> new_ipam_b = IpamB().load()
>>> diff = ipam_a.diff_to(ipam_b)
>>> diff.summary()
{'create': 0, 'update': 0, 'delete': 0, 'no-change': 3}
```
