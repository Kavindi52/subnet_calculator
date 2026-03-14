from ipaddress import IPv4Network, IPv6Network, ip_network
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional, List, Dict


class SubnetRequest(BaseModel):
    address: str = Field(..., description="IP address (IPv4 or IPv6)")
    prefix_or_mask: str = Field(..., description="Prefix length (e.g. 24, 64) or subnet mask (IPv4 only)")

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        try:
            ip_network(v, strict=False)  # quick check
        except ValueError:
            raise ValueError("Invalid IP address format (IPv4 or IPv6)")
        return v


class SubnetResponse(BaseModel):
    version: Literal[4, 6]
    cidr_notation: str
    network_address: str
    prefix_length: int
    total_ips: str
    usable_hosts: str
    first_usable: Optional[str] = None
    last_usable: Optional[str] = None
    # IPv4 specific
    subnet_mask: Optional[str] = None
    wildcard_mask: Optional[str] = None
    broadcast_address: Optional[str] = None
    # IPv6 specific
    is_lan_recommended: bool = False
    lan_recommendation_note: str = ""


# ── VLSM models ──────────────────────────────────────────────────────────────

class VLSMRequirementItem(BaseModel):
    name: str = Field(default="", description="Optional name/description of the subnet")
    hosts: int = Field(..., gt=0, description="Number of required usable hosts")


class VLSMRequest(BaseModel):
    base_network: str = Field(..., description="Base IPv4 network in CIDR notation (e.g. 192.168.10.0/24)")
    requirements: List[VLSMRequirementItem] = Field(..., min_length=1)


class VLSMSubnetAssignment(BaseModel):
    name: str
    required_hosts: int
    assigned_cidr: str
    subnet_mask: str
    network_address: str
    broadcast_address: str
    first_usable: str
    last_usable: str
    usable_hosts: int
    total_addresses: int


class VLSMResponse(BaseModel):
    base_network: str
    assignments: List[VLSMSubnetAssignment]
    remaining_networks: List[str]
    warning: Optional[str] = None