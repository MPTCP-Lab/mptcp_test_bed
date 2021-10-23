#!/usr/bin/env python
# -*- coding: utf-8 -*-

# CoreEmu related imports
from core.emulator.coreemu import CoreEmu
from core.emulator.data import NodeOptions, LinkOptions
from core.emulator.enumerations import EventTypes
from core.nodes.base import CoreNode
from core.nodes.network import SwitchNode, WlanNode
from core.location.mobility import BasicRangeModel

# Parser related imports
import toml
import os
import logging
import sys

# When runing a script from the GUI, we need to append the
# path so we can find our custom modules
path = os.path.dirname(sys.argv[0])
sys.path.append(path)
from auxs.subnets import SubNetManager  # noqa: E402

# Init logging
logging.basicConfig(
    filename=os.path.join(path, "testbed.log"), filemode="w", force=True
)

if len(sys.argv) < 2:
    logging.error("Not enough arguments")
    exit(1)

# Load YAML file
filename = sys.argv[1]
try:
    data = toml.load(os.path.join(path, "topologies", filename + ".toml"))
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
for node in data["nodes"]:
    params = data["nodes"][node]
    name = node
    posX = params.get("posX", 100)
    posY = params.get("posY", 100)
    model = params.get("model", "router")

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
                "range": params.get("range", None),
                "bandwidth": params.get("bandwidth", None),
                "delay": params.get("delay", None),
                "jitter": params.get("jitter", None),
                "error": params.get("error", None),
            },
        )
    else:
        logging.error("Configuration Error: Unknown '{}' model".format(model))
        exit(1)

    t_nodes[name] = {
        "obj": obj,
        "posX": posX,
        "posY": posY,
        "model": model,
    }

ip_manager_mapper = {}
gws = dict()

# Read links and add them to the session
for link in data["links"]:
    params = data["links"][link]

    n1, n2 = params["node1"], params["node2"]
    n1_model, n2_model = t_nodes[n1]["model"], t_nodes[n2]["model"]

    if n1 in ip_manager_mapper:
        ip_manager = ip_manager_mapper[n1]
    elif n2 in ip_manager_mapper:
        ip_manager = ip_manager_mapper[n2]
    else:
        ip_manager = SubNetManager.new_subnet()

    if n1_model == "switch" or n1_model == "wlan":
        ip_manager_mapper[n1] = ip_manager
    if n2_model == "switch" or n2_model == "wlan":
        ip_manager_mapper[n2] = ip_manager

    iface1 = ip_manager.new_interface(n1_model)
    iface2 = ip_manager.new_interface(n2_model)

    bandwidth = params.get("bandwidth", None)
    delay = params.get("delay", None)
    dup = params.get("dup", None)
    loss = params.get("loss", None)
    jitter = params.get("jitter", None)

    options = LinkOptions(
        bandwidth=bandwidth, delay=delay, dup=dup, loss=loss, jitter=jitter
    )

    iface1, iface2 = session.add_link(
        t_nodes[n1]["obj"].id, t_nodes[n2]["obj"].id, iface1, iface2, options
    )

    # We do not consider PC-to-PC links
    if (n1_model == "PC") ^ (n2_model == "PC"):

        if n2_model == "PC":
            iface1, iface2 = iface2, iface1
            n1, n2 = n2, n1

        # Routing configuration
        ip = str(iface1.get_ip4()).split("/")[0]
        gateway = ip_manager.gateway()
        subnet = ip_manager.subnet()

        table_count = gws.get(n1, 1)
        gws[n1] = table_count + 1

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
        # MPTCP kernel configuration
        iface1.node.cmd(
            "ip mptcp endpoint add {} dev {} subflow signal".format(
                ip, iface1.name
            )
        )
        # These limits should be configured in the future
        iface1.node.cmd("ip mptcp limits set subflows 8 add_addr_accepted 8")

# Start session
session.instantiate()
