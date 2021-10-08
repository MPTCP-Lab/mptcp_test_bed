#!/usr/bin/env python
# -*- coding: utf-8 -*-

# CoreEmu related imports
import core
from core.emulator.coreemu import CoreEmu
from core.emulator.data import *
from core.emulator.enumerations import EventTypes
from core.nodes.base import CoreNode
from core.nodes.base import *

# Parser related imports
import yaml 
import sys
import os

# Load Topology from JSON file
path = os.path.dirname(sys.argv[0])
filename =  sys.argv[1]

with open(os.path.join(path, "topologies", filename)) as f_in:
    data = yaml.load(f_in, Loader=yaml.FullLoader)

print(data)

# Set IP's tha will be used

# Create the new core session
coreemu = globals().get("coreemu", CoreEmu())
session = coreemu.create_session()

#coreemu = CoreEmu()
#ip route add 10.0.0.0/24 dev eth0 scope link table 2session = coreemu.create_session()


# show table 2") Set the topology to configuration mode
session.set_state(EventTypes.CONFIGURATION_STATE)

t_nodes = dict()
for elem in data['nodes']:
    name = elem['name']
    posX = elem['posX']
    posY = elem['posY']
    model = elem.get('model', 'router')
    script = elem.get('script', None)
    
    options = NodeOptions(model=model, x=posX, y=posY, name=name)
    obj = session.add_node(CoreNode, options=options)

    t_nodes[name] = {
        "obj": obj, 
        "posX": posX,
        "posY": posY,
        "model": model,
        "script": script
    }


counter = 0
for link in data['links']:

    iface1 = InterfaceData(
        ip4="10.0.{}.1".format(counter),
        ip4_mask=24,
    )

    iface2 = InterfaceData(
        ip4="10.0.{}.2".format(counter),
        ip4_mask=24,
    )

    counter += 1

    bandwidth = link.get('bandwidth', None)
    delay = link.get('delay', None)
    dup = link.get('dup', None)
    loss = link.get('loss', None)
    jitter = link.get('jitter', None)

    options = LinkOptions(
        bandwidth=bandwidth,
        delay=delay,
        dup=dup,
        loss=loss,
        jitter=jitter
    )

    n1 = link['node1']
    n2 = link['node2']

    # Maybe we should support swtiches in the future
    if t_nodes[n2]['model'] == 'router':
        n1, n2 = n2, n1

    session.add_link(t_nodes[n1]['obj'].id, t_nodes[n2]['obj'].id, iface1, iface2, options)


# Configure routing

link_list = [x for x in session.nodes.values() if isinstance(x, core.nodes.network.PtpNet)]
import re

l = 1
this_is_dumb = 1
gws = dict()
for node in t_nodes:
    gws[node] = 1

print(gws)

for link in link_list:
    iface1 = link.get_ifaces()[0]
    iface2 = link.get_ifaces()[1]

    if iface1.node.type == "PC" or iface2.node.type == "PC": 

        if iface1.node.type == 'router':
            iface1, iface2 = iface2, iface1

        gateway = str(iface2.get_ip4()).split("/")[0]
        pieces = re.split("[./]", str(iface1.get_ip4()))
        ip = "{}.{}.{}.{}".format(pieces[0], pieces[1], pieces[2], pieces[3])
        subnet = "{}.{}.{}.{}/{}".format(pieces[0], pieces[1], pieces[2], 0, pieces[4]) 
        table_count = gws[iface1.node.name]
        iface1.node.cmd('ip rule add from {} table {}'.format(ip, table_count))
        iface1.node.cmd('ip route add {} dev {} scope link table {}'.format(subnet, iface1.name, table_count))
        iface1.node.cmd('ip route add default via {} dev {} table {}'.format(gateway, iface1.name, table_count))
        # iface1.node.cmd('ip route add default scope global nexthop via {} dev {}'.format(gateway, iface1.name))
        iface1.node.cmd('ip mptcp endpoint add {} dev {} subflow signal'.format(ip, iface1.name))
        iface1.node.cmd('ip mptcp limits set subflows 8 add_addr_accepted 8')
        gws[iface1.node.name] += 1

    print(iface1.node.name)
    print(iface2.node.name)
    print(gws)

for elem in t_nodes:
    node = t_nodes[elem]
    if 'script' in node and node['script']:
        node['obj'].nodefilecopy("script.sh", node['script'])
        node['obj'].cmd("bash script.sh")



#scripts = dict()
#for item in data['scripts']:
#    node = item['node']
#    script_path = item['script']
#    scripts[node] = script_path
#    t_nodes[node]['obj'].nodefilecopy("mptcp.sh", script_path)

def run_script(node, script):
    # node.cmd("bash {}".format(script))
    node.cmd("bash mptcp.sh")

from threading import Thread
#threads = []
#for key in scripts:
#    node = t_nodes[key]['obj']
#    t = Thread(target=run_script, args=(node,scripts[key],))
#    t.start()
#    threads.append(t)
#
#for x in threads:
#    x.join()


session.instantiate()

#  print("Session_id: {}".format(session.id))
#
#  input("press enter to shutdown!")
#  session.shutdown()
