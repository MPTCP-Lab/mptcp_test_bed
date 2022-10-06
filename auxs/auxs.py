from typing import List
from dataclasses import dataclass
from core.api.grpc.wrappers import Interface, Node, NodeType


# Class to manage ips in a subnet
class IpManager:
    _interfaces = {}

    def __init__(self, subnet_n):
        self._counter = 19
        self._gateway_counter = 0
        self._subnet_ipv4 = f"10.0.{subnet_n}"
        self._subnet_ipv6 = f"2001:{subnet_n}"

    def _new_host_ip(self):
        self._counter += 1
        return (
            f"{self._subnet_ipv4}.{self._counter}",
            f"{self._subnet_ipv6}::{self._counter}",
        )

    def _new_gateway_ip(self):
        self._gateway_counter += 1
        return (
            f"{self._subnet_ipv4}.{self._gateway_counter}",
            f"{self._subnet_ipv6}::{self._gateway_counter}",
        )

    def new_interface(self, node):
        model = node.model

        if node.name not in self._interfaces:
            self._interfaces[node.name] = 0

        self._interfaces[node.name] += 1
        id = self._interfaces[node.name]

        if model == "switch" or model == "wlan":
            return Interface(id=id, name=f"eth{id}", ip4_mask=24, ip6_mask=64)
        elif model == "router":
            ipv4, ipv6 = self._new_gateway_ip()
        else:  # PC
            ipv4, ipv6 = self._new_host_ip()
        return Interface(
            id=id, ip4=ipv4, name=f"eth{id}", ip4_mask=24, ip6=ipv6, ip6_mask=64
        )

    def gateway(self):
        return f"{self._subnet_ipv4}.1", f"{self._subnet_ipv6}::1"


# Class to manage subnets
class SubNetManager:
    _counter = -1

    @staticmethod
    def new_topo():
        SubNetManager._counter = -1

    @staticmethod
    def new_subnet():
        SubNetManager._counter += 1
        return IpManager(SubNetManager._counter)


@dataclass
class InterfaceData:
    name: str
    gateway_ipv4: str


@dataclass
class NodeAux:
    obj: Node
    files: List[str]
    params: dict
    interfaces: List[InterfaceData]


def is_switch(node):
    return node.type == NodeType.SWITCH


def is_pc(node):
    return node.type == NodeType.DEFAULT and node.model == "PC"


def is_router(node):
    return node.type == NodeType.DEFAULT and node.model == "router"


def is_wlan(node):
    return node.type == NodeType.WIRELESS_LAN
