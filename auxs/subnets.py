from core.emulator.data import InterfaceData


# Class to manage ips in a subnet
class IpManager:
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

    def new_interface(self, model="PC"):
        if model == "switch" or model == "wlan":
            return InterfaceData(ip4_mask=24, ip6_mask=64)
        elif model == "router":
            ipv4, ipv6 = self._new_gateway_ip()
        else:  # PC
            ipv4, ipv6 = self._new_host_ip()
        return InterfaceData(ip4=ipv4, ip4_mask=24, ip6=ipv6, ip6_mask=64)

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
