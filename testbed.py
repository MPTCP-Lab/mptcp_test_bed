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
    logging.error(f"File not found '{filename}'")
    exit(1)

# Create the new core session
coreemu = globals().get("coreemu", CoreEmu())
session = coreemu.create_session()

# Set the topology to configuration mode
session.set_state(EventTypes.CONFIGURATION_STATE)

# Reset SubNetManager
SubNetManager.new_topo()

# Auxs
t_nodes = {}
path_managers = {}
gws = {}
ip_manager_mapper = {}

# Read nodes and add them to the session
for node in data["nodes"]:
    params = data["nodes"][node]
    name = node
    posX = params.get("posX", 100)
    posY = params.get("posY", 100)
    model = params.get("model", "router")
    services = params.get("services", [])
    files = params.get("files", [])

    if model == "PC":
        options = NodeOptions(
            model=model, x=posX, y=posY, name=name, services=services
        )
        obj = session.add_node(CoreNode, options=options)
        path_manager = params.get("path_manager", "ip_mptcp")
        path_managers[node] = path_manager

        if path_manager == "ip_mptcp":
            subflows = params.get("subflows", 8)
            add_addr_accepted = params.get("add_addr_accepted", 8)
            obj.cmd(
                f"ip mptcp limits set subflows {subflows} add_addr_accepted {add_addr_accepted}"
            )
    elif model == "router":
        options = NodeOptions(
            model=model, x=posX, y=posY, name=name, services=services
        )
        obj = session.add_node(CoreNode, options=options)
    elif model == "switch":
        options = NodeOptions(x=posX, y=posY, name=name, services=services)
        obj = session.add_node(SwitchNode, options=options)
    elif model == "wlan":
        options = NodeOptions(x=posX, y=posY, name=name, services=services)
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
        logging.error(f"Configuration Error: Unknown '{model}' model")
        exit(1)

    for file in files:
        obj.nodefilecopy(file, os.path.join(path, "files", file))

    t_nodes[name] = {"obj": obj, "model": model, "params": params}

# Read links and add them to the session
for link in data["links"]:
    params = data["links"][link]

    # TODO: We should check if these nodes exist
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

    use_mptcp = params.get("use_mptcp", True)

    # We do not consider PC-to-PC links
    if ((n1_model == "PC") ^ (n2_model == "PC")) and use_mptcp:

        if n2_model == "PC":
            iface1, iface2 = iface2, iface1
            n1, n2 = n2, n1

        # Routing configuration as described in:
        # http://multipath-tcp.org/pmwiki.php/Users/ConfigureRouting
        ipv4 = str(iface1.get_ip4()).split("/")[0]
        ipv6 = str(iface1.get_ip6()).split("/")[0]
        gateway_ipv4, gateway_ipv6 = ip_manager.gateway()
        subnet_ipv4, subnet_ipv6 = ip_manager.subnet()

        table_count = gws.get(n1, 1)
        gws[n1] = table_count + 1

        iface1.node.cmd(f"ip rule add from {ipv4} table {table_count}")
        iface1.node.cmd(f"ip -6 rule add from {ipv6} table {table_count}")

        iface1.node.cmd(
            f"ip route add {subnet_ipv4} dev {iface1.name} scope link table {table_count}"
        )
        iface1.node.cmd(
            f"ip -6 route add {subnet_ipv6} dev {iface1.name} scope link table {table_count}"
        )

        iface1.node.cmd(
            f"ip route add default via {gateway_ipv4} dev {iface1.name} table {table_count}"
        )
        iface1.node.cmd(
            f"ip -6 route add default via {gateway_ipv6} dev {iface1.name} table {table_count}"
        )

        # MPTCP ip_mptcp configuration
        if path_managers[n1] == "ip_mptcp":
            flags = params.get("ip_mptcp_flags", "subflow signal")
            iface1.node.cmd(
                f"ip mptcp endpoint add {ipv4} dev {iface1.name} {flags}"
            )
            iface1.node.cmd(
                f"ip mptcp endpoint add {ipv6} dev {iface1.name} {flags}"
            )

# We start mptcpd only after all links are configured
for node in path_managers:
    if path_managers[node] == "mptcpd":
        addr_flags = t_nodes[node]["params"].get("addr_flags", "subflow,signal")
        notify_flags = t_nodes[node]["params"].get("notify_flags", "existing")
        load_plugins = t_nodes[node]["params"].get("load_plugins", "")
        plugins_conf_dir = t_nodes[node]["params"].get("plugins_conf_dir", "")
        if len(load_plugins) > 0:
            load_plugins = f"--load-plugins={load_plugins}"
        if len(plugins_conf_dir) > 0:
            plugins_conf_dir = f"--plugins-conf-dir={plugins_conf_dir}"

        t_nodes[node]["obj"].cmd(
            f"mptcpd --addr-flags={addr_flags} --notify-flags={notify_flags} {load_plugins} {plugins_conf_dir}",
            wait=False,
        )

# Start session
session.instantiate()
