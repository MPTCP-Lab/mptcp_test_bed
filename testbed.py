#!/usr/bin/env python3

import toml
import sys
import os

from core.api.grpc import client
from core.api.grpc.wrappers import Position, NodeType, LinkOptions
from auxs.auxs import SubNetManager, NodeAux, InterfaceData

if len(sys.argv) < 2:
    print("Not enough arguments")
    exit(1)

# Load YAML file
filename = sys.argv[1]
dir_path = os.path.abspath(os.path.dirname(__file__))
topo_path = os.path.join(dir_path, "topologies", filename + ".toml")

try:
    data = toml.load(topo_path)
except FileNotFoundError:
    print(f"File not found: {topo_path}")
    exit(1)

# create grpc client and connect
core = client.CoreGrpcClient()
core.connect()

# add session
session = core.create_session()

# Reset SubNetManager
SubNetManager.new_topo()

###############
#### NODES ####
###############
node_id = 1
nodes = {}

for node, params in data["nodes"].items():
    posX = params.get("posX", 100)
    posY = params.get("posY", 100)
    position = Position(x=posX, y=posY)
    model = params.get("model", "router")
    services = params.get("services", [])
    files = params.get("files", [])

    if model == "PC":
        obj = session.add_node(
            node_id, name=node, model="PC", position=position
        )
        files.append("configurator.sh")
    elif model == "router":
        obj = session.add_node(
            node_id, name=node, model="router", position=position
        )
    elif model == "switch":
        obj = session.add_node(
            node_id,
            name=node,
            _type=NodeType.SWITCH,
            position=position,
        )
    elif model == "wlan":
        obj = session.add_node(
            node_id,
            name=node,
            _type=NodeType.WIRELESS_LAN,
            position=position,
        )
        obj.set_wlan(
            {
                "range": params.get("range", None),
                "bandwidth": params.get("bandwidth", None),
                "delay": params.get("delay", None),
                "jitter": params.get("jitter", None),
                "error": params.get("error", None),
            }
        )
    else:
        print(f"Unknown model {model}")
        exit(1)

    obj.config_services = services
    nodes[node] = NodeAux(obj, files, params, [])
    node_id += 1

###############
#### LINKS ####
###############
ip_manager_mapper = {}

for link in data["links"].values():
    n1, n2 = link["node1"], link["node2"]

    options = LinkOptions(
        bandwidth=link.get("bandwidth", None),
        delay=link.get("delay", None),
        dup=link.get("dup", None),
        loss=link.get("loss", None),
        jitter=link.get("jitter", None),
    )

    if n1 in ip_manager_mapper:
        ip_manager = ip_manager_mapper[n1]
    elif n2 in ip_manager_mapper:
        ip_manager = ip_manager_mapper[n2]
    else:
        ip_manager = SubNetManager.new_subnet()

    if nodes[n1].obj.model == "switch" or nodes[n1].obj.model == "wlan":
        ip_manager_mapper[n1] = ip_manager
    if nodes[n2].obj.model == "switch" or nodes[n2].obj.model == "wlan":
        ip_manager_mapper[n2] = ip_manager

    iface1 = ip_manager.new_interface(nodes[n1].obj)
    iface2 = ip_manager.new_interface(nodes[n2].obj)

    session.add_link(
        node1=nodes[n1].obj,
        node2=nodes[n2].obj,
        iface1=iface1,
        iface2=iface2,
        options=options,
    )

    use_mptcp = link.get("use_mptcp", True)

    # We do not consider PC-to-PC links
    if (
        (nodes[n1].obj.model == "PC") ^ (nodes[n2].obj.model == "PC")
    ) and use_mptcp:

        if nodes[n2].obj.model == "PC":
            iface1, iface2 = iface2, iface1
            n1, n2 = n2, n1

        gateway_ipv4, _ = ip_manager.gateway()
        nodes[n1].interfaces.append(InterfaceData(iface1.name, gateway_ipv4))

# start session
core.start_session(session)

# Copy files
for node in nodes.values():
    for file in node.files:
        core.node_command(
            session_id=session.id,
            node_id=node.obj.id,
            command=f"cp {dir_path}/files/{file} .",
            shell=True,
        )

# MPTCP configurations
for node in nodes.values():
    if node.obj.model == "PC":
        path_manager = node.params.get("path_manager", "ip_mptcp")
        args = ""
        for interface in node.interfaces:
            args += " " + interface.name + " " + interface.gateway_ipv4
        if path_manager == "ip_mptcp":
            core.node_command(
                session_id=session.id,
                node_id=node.obj.id,
                command=f"./configurator.sh -p ip_mptcp{args}",
                shell=True,
            )
        elif path_manager == "mptcpd":
            core.node_command(
                session_id=session.id,
                node_id=node.obj.id,
                command=f"./configurator.sh{args}",
                shell=True,
            )

            addr_flags = node.params.get("addr_flags", "subflow,signal")
            notify_flags = node.params.get("notify_flags", "existing")
            load_plugins = node.params.get("load_plugins", "")
            plugins_conf_dir = node.params.get("plugins_conf_dir", "")

            if len(load_plugins) > 0:
                load_plugins = f"--load-plugins={load_plugins}"
            if len(plugins_conf_dir) > 0:
                plugins_conf_dir = f"--plugins-conf-dir={plugins_conf_dir}"

            core.node_command(
                session_id=session.id,
                node_id=node.obj.id,
                command=f"mptcpd --addr-flags={addr_flags} --notify-flags={notify_flags} {load_plugins} {plugins_conf_dir}",
                shell=True,
                wait=False,
            )
