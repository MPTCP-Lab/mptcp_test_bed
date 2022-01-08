# MPTCP Test Bed

## Contents
1. [Overview](#overview)
2. [How to Use](#how-to-use)
3. [Configuration](#configuration)
   1. [Topology Configuration File](#topology-configuration-file)
   2. [Configuration Options](#configuration-options)
      1. [Node Options](#node-options)
      2. [Link Options](#link-options)

## Overview
This project aims to provide an environment to easily test MPTCP in different network topologies and scenarios. Since MPTCP usually requires some previous configuration related to routing and path managing for each host, recreating the same configurations multiple times in order to conduct tests can become a time consuming task. With this in mind, this project allows to describe a topology using [TOML](https://github.com/toml-lang/toml), and then instantiate a [CORE](https://github.com/coreemu/core) session with routing and endpoints configured in all nodes. 

For path managing configuration it's possible to use `ip mptcp` or Intel's daemon [`mptcpd`](https://github.com/intel/mptcpd). As for routing rules, the configuration is conducted as described in [multipath-tcp.org](http://multipath-tcp.org/pmwiki.php/Users/ConfigureRouting).



## How to Use

**Note:** These steps have only been validated in the Classic CORE GUI

1. Create your topology and add it to the `topologies` folder
2. Open the CORE GUI
3. File > Execute Python script with options
4. Select `testbed.py`
5. Click `Open`
6. Append the name of your topology **(without file extension)** 
7. Click `OK` 

If the session does not start after a few seconds, check the `testbed.log` for errors

---

## Configuration

### Topology Configuration File
The topology configuration file uses TOML to describe the details of each node and link. The file should be organized in sections, as the following example:

```TOML
[nodes]

  [nodes.<node_name1>]
  posX = 500 
  posY = 200
  model = "PC"

  [nodes.<node_name2>]
  model = "router"

  [nodes.<node_name3>]

  # ...
  # ...

[links]

  [links.1]
  node1 = "<node_name1>"
  node2 = "<node_name2>"
  
  [links.2]
  node1 = "<node_name2>"
  node2 = "<node_name3>"

  # ...
  # ...  

```

---

### Configuration Options
For both nodes and links it's possible to specify different options in order to override default values.

#### Node options
For nodes the following options are available:

- `model`
  - Node type ("PC", "router", "switch", "wlan")
  - Default="router"

- `posX`
  - X position 
  - Default=100 

- `posY` 
  - Y position
  - Default=100

- `path_manager`
  - The path manager to be used in this node ("ip\_mptcp", "mptcpd") 
  - Used when `model`=="PC"
  - Default="ip\_mptcp"
  - **Note:** When using `mptcpd`, make sure it's installed in your system

- `files`
  - List of files to be uploaded
  - Default=[]
  - **Note:** The target files must be in the `files` folder

- `subflows`
  - Maximum number of additional subflows allowed for each MPTCP connection
  - Used when `path_manager`="ip\_mptcp"
  - Default=8 

- `add_addr_accepted`
  - Specifies the maximum number of ADD\_ADDR suboptions accepted for each MPTCP connection.
  - Used when `path_manager`="ip\_mptcp"
  - Default=8 

- `addr_flags`
  - Flags for announced address
  - Used when `path_manager`=="mptcpd"
  - Default="subflow,signal" 

- `notify_flags`
  - Address notification flags
  - Used when `path_manager`=="mptcpd"
  - Default="existing"

- `load_plugins`
  - Plugins to load on startup
  - Used when `path_manager`=="mptcpd"
  - Default="" (Loads all plugins) 

- `plugins_conf_dir`
  - Plugins configuration path
  - Used when `path_manager`=="mptcpd"
  - **This option only works with this particular [version](https://github.com/dulive/mptcpd/tree/patched_version) of mptcpd**
  
- `range`
  - Wlan range 
  - Used when `model`="wlan"
  - Default=None (Uses CORE default)

- `bandwidth`
  - Wlan bandwidth
  - Used when `model`="wlan"
  - Default=None (Uses CORE default)

- `delay`
  - Wlan delay
  - Used when `model`="wlan"
  - Default=None (Uses CORE default)

- `jitter`
  - Wlan jitter
  - Used when `model`="wlan"
  - Default=None (Uses CORE default)

- `error`
  - Wlan error percentage
  - Used when `model`="wlan"
  - Default=None (Uses CORE default)

- `services`
  - Services to run in this host
  - Default=[] (Runs the default CORE services associated with the Node Model)
  - **Note:** This option will **override all** the default services that CORE uses associated with a Node Model

---

#### Link options
For links the following options are available:

- `node1` **Required** 
  - Host name of link endpoint 1

- `node2` **Required**
  - Host name of link endpoint 2

- `bandwidth`
  - Link bandwidth
  - Default=None (Uses CORE default)

- `delay`
  - Link delay 
  - Default=None (Uses CORE default)

- `dup` 
  - Link duplication rate 
  - Default=None (Uses CORE default)

- `loss`
  - Link loss percentage 
  - Default=None (Uses CORE default)

- `jitter`
  - Link jitter
  - Default=None (Uses CORE default)

- `use_mptcp`
  - Specifies if this link should be use for MPTCP connections when connected to a PC
  - When this value is set to **false**, MPTCP related routing will not be configured for this link, and the same applies to `ip_mptcp` path managing configuration
  - Default=true

- `ip_mptcp_flags`
  - Flags to use when configuring this link as a MPTCP endpoint with `ip mptcp` (similarly to `addr_flags` from `mptcpd`)
  - Used if `path_manager`=="ip\_mptcp" in one of the hosts connected by this link
  - Default="subflow signal"



