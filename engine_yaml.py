#!/usr/bin/env python
# -*- coding: utf-8 -*-

# CoreEmu related imports
import core
from core.emulator.coreemu import CoreEmu
from core.emulator.data import InterfaceData, NodeOptions, LinkOptions
from core.emulator.enumerations import EventTypes
from core.nodes.base import CoreNode
from core.nodes.network import SwitchNode, WlanNode
from core.location.mobility import BasicRangeModel

# Parser related imports
import yaml
import sys
import os
import re
import logging

path = os.path.dirname(sys.argv[0])
logging.basicConfig(filename=os.path.join(path, "engine.log"), filemode="w", force=True)

if len(sys.argv) < 2:
    logging.error("Not enough arguments")
    exit(1)

# Load YAML file
filename = sys.argv[1]
try:
    with open(os.path.join(path, "topologies", filename)) as file_in:
        data = yaml.load(file_in, Loader=yaml.FullLoader)
except FileNotFoundError:
    logging.error("File not found '{}'".format(filename))
    exit(1)

# Create the new core session
coreemu = globals().get("coreemu", CoreEmu())
session = coreemu.create_session()

# Set the topology to configuration mode
session.set_state(EventTypes.CONFIGURATION_STATE)

# Read nodes and add them to the session
t_nodes = dict()
for elem in data["nodes"]:

    name = elem["name"]
    posX = elem.get("posX", 100)
    posY = elem.get("posY", 100)
    model = elem.get("model", "router")

    if model == "router" or model == "PC":
        options = NodeOptions(model=model, x=posX, y=posY, name=name)
        obj = session.add_node(CoreNode, options=options)
    elif model == "switch":
        options = NodeOptions(x=posX, y=posY, name=name)
        obj = session.add_node(SwitchNode, options=options)
    elif model == "wlan":
        options = NodeOptions(x=posX, y=posY, name=name)
        obj = session.add_node(WlanNode, options=options)
        session.mobility.set_model_config(
            obj.id,
            BasicRangeModel.name,
            {
                "range": elem.get("range", None),
                "bandwidth": elem.get("bandwidth", None),
                "delay": elem.get("delay", None),
                "jitter": elem.get("jitter", None),
                "error": elem.get("error", None),
            },
        )
    else:
        logging.error("Unknown '{}' model".format(model))
        exit(1)

    t_nodes[name] = {
        "obj": obj,
        "posX": posX,
        "posY": posY,
        "model": model,
    }

# Read links and add them to the session
SORT_ORDER = {"router": 0, "switch": 1, "wlan": 2, "PC": 3}

subnet_counter = 0
switches_networks = {}
switches_networks_counter = {}

for link in data["links"]:

    [n1, n2] = sorted(
        [link["node1"], link["node2"]],
        key=lambda val: SORT_ORDER[t_nodes[val]["model"]],
    )

    if t_nodes[n1]["model"] == "router":
        iface1 = InterfaceData(
            ip4="10.0.{}.1".format(subnet_counter),
            ip4_mask=24,
        )

        if t_nodes[n2]["model"] == "switch" or t_nodes[n2]["model"] == "wlan":
            switches_networks[n2] = "10.0.{}".format(subnet_counter)
            switches_networks_counter[n2] = 20
            iface2 = InterfaceData(
                ip4_mask=24,
            )
        else:  # Host
            iface2 = InterfaceData(
                ip4="10.0.{}.20".format(subnet_counter),
                ip4_mask=24,
            )
        subnet_counter += 1

    elif t_nodes[n1]["model"] == "switch":
        iface1 = InterfaceData(
            ip4_mask=24,
        )

        if t_nodes[n2]["model"] == "switch" or t_nodes[n2]["model"] == "wlan":
            switches_networks[n2] = switches_networks[n1]
            switches_networks_counter[n2] = switches_networks_counter[n1]
            iface2 = InterfaceData(
                ip4_mask=24,
            )
        else:  # n2 Host
            iface2 = InterfaceData(
                ip4="{}.{}".format(
                    switches_networks[n1], switches_networks_counter[n1]
                ),
                ip4_mask=24,
            )
            switches_networks_counter[n1] += 1
    # Here we'll assume that wlan can only be conected to hosts
    elif t_nodes[n1]["model"] == "wlan":
        iface1 = InterfaceData(
            ip4_mask=24,
        )

        iface2 = InterfaceData(
            ip4="{}.{}".format(switches_networks[n1], switches_networks_counter[n1]),
            ip4_mask=24,
        )
        switches_networks_counter[n1] += 1
    else:  # PC-to-PC ??
        logging.error("PC-to-PC connection")
        exit(1)

    bandwidth = link.get("bandwidth", None)
    delay = link.get("delay", None)
    dup = link.get("dup", None)
    loss = link.get("loss", None)
    jitter = link.get("jitter", None)

    options = LinkOptions(
        bandwidth=bandwidth, delay=delay, dup=dup, loss=loss, jitter=jitter
    )

    session.add_link(
        t_nodes[n1]["obj"].id, t_nodes[n2]["obj"].id, iface1, iface2, options
    )


# Configure routing
link_list = [
    x for x in session.nodes.values() if isinstance(x, core.nodes.network.PtpNet)
]

gws = dict()
for node in t_nodes:
    gws[node] = 1

for link in link_list:
    iface1 = link.get_ifaces()[0]
    iface2 = link.get_ifaces()[1]

    if iface1.node.type == "PC" or iface2.node.type == "PC":

        if iface1.node.type == "router":
            iface1, iface2 = iface2, iface1

        gateway = str(iface2.get_ip4()).split("/")[0]
        pieces = re.split("[./]", str(iface1.get_ip4()))
        ip = "{}.{}.{}.{}".format(pieces[0], pieces[1], pieces[2], pieces[3])
        subnet = "{}.{}.{}.{}/{}".format(pieces[0], pieces[1], pieces[2], 0, pieces[4])
        table_count = gws[iface1.node.name]
        gws[iface1.node.name] += 1

        iface1.node.cmd("ip rule add from {} table {}".format(ip, table_count))
        iface1.node.cmd(
            "ip route add {} dev {} scope link table {}".format(
                subnet, iface1.name, table_count
            )
        )
        iface1.node.cmd(
            "ip route add default via {} dev {} table {}".format(
                gateway, iface1.name, table_count
            )
        )
        iface1.node.cmd(
            "ip mptcp endpoint add {} dev {} subflow signal".format(ip, iface1.name)
        )
        # These limits should be configured in the future
        iface1.node.cmd("ip mptcp limits set subflows 8 add_addr_accepted 8")

for elem in t_nodes:
    node = t_nodes[elem]
    if "script" in node and node["script"]:
        node["obj"].nodefilecopy("script.sh", node["script"])
        node["obj"].cmd("bash script.sh")

session.instantiate()
