from core.emulator.data import InterfaceData


# Class to manage ips in a subnet
class IpManager:
    def __init__(self, subnetIp):
        self._counter = 19
        self._gateway_counter = 0
        self._subnetIp = subnetIp

    def _new_host_ip(self):
        self._counter += 1
        return "{}.{}".format(self._subnetIp, self._counter)

    def _new_gateway_ip(self):
        self._gateway_counter += 1
        return "{}.{}".format(self._subnetIp, self._gateway_counter)

    def new_interface(self, model="PC"):
        if model == "router":
            return InterfaceData(ip4=self._new_gateway_ip(), ip4_mask=24)
        elif model == "switch" or model == "wlan":
            return InterfaceData(ip4_mask=24)
        else:  # PC
            return InterfaceData(ip4=self._new_host_ip(), ip4_mask=24)

    def gateway(self):
        return "{}.1".format(self._subnetIp)

    def subnet(self):
        return "{}.0/24".format(self._subnetIp)


# Class to manage subnets
class SubNetManager:
    _counter = -1

    @staticmethod
    def new_topo():
        SubNetManager._counter = -1

    @staticmethod
    def new_subnet():
        SubNetManager._counter += 1
        return IpManager("10.0.{}".format(SubNetManager._counter))
