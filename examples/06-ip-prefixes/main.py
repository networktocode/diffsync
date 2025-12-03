#!/usr/bin/env python
"""Main example."""

from adapter_ipam_a import IpamA
from adapter_ipam_b import IpamB


if __name__ == "__main__":
    ipam_a = IpamA()
    ipam_b = IpamB()
    ipam_a.load()
    ipam_b.load()
    diff = ipam_a.diff_to(ipam_b)
    # ipam_a.sync_to(ipam_b)
