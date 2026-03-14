from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ipaddress import IPv4Network, IPv6Network, ip_network
from subnet import SubnetRequest, SubnetResponse, VLSMRequest, VLSMResponse, VLSMSubnetAssignment
import math

app = FastAPI(
    title="IPv4 / IPv6 & VLSM Subnet Calculator API",
    description="Single subnet calculation + Variable Length Subnet Masking (VLSM) for IPv4",
    version="1.2"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/calculate", response_model=SubnetResponse)
def calculate_subnet(req: SubnetRequest):
    try:
        net = ip_network(f"{req.address}/{req.prefix_or_mask}", strict=False)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid network: {str(e)}")

    version = 4 if isinstance(net, IPv4Network) else 6

    total = net.num_addresses
    total_str = str(total) if version == 4 else f"{total:,}" if total < 10**18 else f"≈2^{net.max_prefixlen - net.prefixlen}"

    if version == 4:
        usable = max(0, total - 2)
        first = str(net.network_address + 1) if usable > 0 else "N/A"
        last = str(net.broadcast_address - 1) if usable > 0 else "N/A"
        usable_str = str(usable)
    else:
        usable_str = total_str
        first = str(net.network_address + 1)
        last = "Very large (end of prefix)"
        if net.prefixlen == 64:
            usable_str = "18,446,744,073,709,551,616 (2⁶⁴)"
        elif net.prefixlen > 64:
            usable_str = str(total - 1) if total > 1 else "1"

    response = SubnetResponse(
        version=version,
        cidr_notation=str(net),
        network_address=str(net.network_address),
        prefix_length=net.prefixlen,
        total_ips=total_str,
        usable_hosts=usable_str,
        first_usable=first,
        last_usable=last,
    )

    if version == 4:
        response.subnet_mask = str(net.netmask)
        response.wildcard_mask = str(net.hostmask)
        response.broadcast_address = str(net.broadcast_address)
    else:
        response.is_lan_recommended = (net.prefixlen == 64)
        if net.prefixlen < 64:
            response.lan_recommendation_note = "Prefix shorter than /64 – not recommended for most LANs (breaks SLAAC)"
        elif net.prefixlen > 64:
            response.lan_recommendation_note = "Prefix longer than /64 – valid for point-to-point (/127) or loopback (/128)"

    return response


# ── VLSM Endpoint ─────────────────────────────────────────────────────────────

def smallest_power_of_two_size(needed_hosts: int) -> int:
    """Smallest 2^n >= needed_hosts + 2 (network + broadcast)"""
    if needed_hosts <= 0:
        return 2
    total_needed = needed_hosts + 2
    return 2 ** math.ceil(math.log2(total_needed))


@app.post("/vlsm", response_model=VLSMResponse)
def calculate_vlsm(req: VLSMRequest):
    try:
        base = IPv4Network(req.base_network, strict=False)
    except ValueError as e:
        raise HTTPException(422, detail=f"Invalid base network: {str(e)}")

    if base.version != 4:
        raise HTTPException(422, detail="VLSM currently supported only for IPv4")

    # Sort descending by number of hosts
    sorted_requirements = sorted(req.requirements, key=lambda x: x.hosts, reverse=True)

    assignments = []
    current = base.network_address
    base_end = base.broadcast_address + 1

    for req_item in sorted_requirements:
        block_size = smallest_power_of_two_size(req_item.hosts)
        prefix = 32 - int(math.log2(block_size))

        try:
            subnet = IPv4Network(f"{current}/{prefix}", strict=False)
        except ValueError:
            raise HTTPException(422, detail=f"Cannot create subnet for '{req_item.name}' – out of space")

        if subnet.network_address < current or subnet.broadcast_address + 1 > base_end:
            raise HTTPException(422, detail=f"Overflow: cannot fit '{req_item.name}' ({req_item.hosts} hosts)")

        usable = max(0, subnet.num_addresses - 2)

        assignments.append(VLSMSubnetAssignment(
            name=req_item.name or f"Requirement {len(assignments)+1}",
            required_hosts=req_item.hosts,
            assigned_cidr=str(subnet),
            subnet_mask=str(subnet.netmask),
            network_address=str(subnet.network_address),
            broadcast_address=str(subnet.broadcast_address),
            first_usable=str(subnet.network_address + 1) if usable > 0 else "N/A",
            last_usable=str(subnet.broadcast_address - 1) if usable > 0 else "N/A",
            usable_hosts=usable,
            total_addresses=subnet.num_addresses
        ))

        current = subnet.broadcast_address + 1

    remaining = []
    if current < base_end:
        try:
            rem_net = IPv4Network(f"{current}/{base.prefixlen}", strict=False)
            remaining.append(str(rem_net))
        except:
            pass

    warning = None
    if current > base_end:
        warning = "Assignments exceeded base network size (truncated)"

    return VLSMResponse(
        base_network=str(base),
        assignments=assignments,
        remaining_networks=remaining,
        warning=warning
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)