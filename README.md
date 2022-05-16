# MPTCP Test Bed

## NOTE: At the moment this project is only compatible with [CORE <7.5.2](https://github.com/coreemu/core). It will not work with newer releases!    

## Contents
1. [Overview](#overview)
2. [How to Use](#how-to-use)
3. [Configuration](#configuration)
   1. [Topology Configuration File](#topology-configuration-file)
   2. [Configuration Options](#configuration-options)
      1. [Node Options](#node-options)
      2. [Link Options](#link-options)

## Overview
This project aims to provide an easy to set up environment to test MPTCP in different network topologies and scenarios. Since MPTCP usually requires some previous configuration related to routing and path managing for each host, recreating the same configurations multiple times in order to conduct tests can become a time consuming task. With this in mind, this project allows to describe a topology using [TOML](https://github.com/toml-lang/toml), and then instantiate a [CORE](https://github.com/coreemu/core) session with routing and endpoints configured in all nodes. 

For path managing configuration it's possible to use `ip mptcp` or Intel's daemon [`mptcpd`](https://github.com/intel/mptcpd). As for routing rules, the configuration is conducted as described in [multipath-tcp.org](http://multipath-tcp.org/pmwiki.php/Users/ConfigureRouting).

---

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

### Configuration Options

#### Node options

| Option   | Description                                                                            | Default Value        |
|----------|----------------------------------------------------------------------------------------|----------------------|
| model    | The node type ("PC", "router", "switch")                                               | "router"             |
| posX     | Node position in the X axis                                                            | 100                  |
| posY     | Node position in the Y axis                                                            | 100                  |
| files    | List of files to be copied to the node (The files must be contained in `files` folder) | [ ]                  |
| services | Services to run on the node                                                            | [ ] (CORE's default) |


<ul>

<details>
  <summary>When <b>model="PC"</b>, the following suboptions are available:</summary>

  | Option        | Description                                                      | Default Value |
  |---------------|------------------------------------------------------------------|---------------|
  | path\_manager | The path manager to be used in this node ("ip\_mptcp", "mptcpd") | "ip\_mptcp"   |

  <ul>

  <details>
  <summary>When <b>path_manager="ip_mptcp"</b>, the following suboptions are available:</summary>

  | Option              | Description                                                                   | Default Value |
  |---------------------|-------------------------------------------------------------------------------|---------------|
  | subflows            | The maximum number of additional subflows allowed for each MPTCP connection   | 8             |
  | add\_addr\_accepted | The maximum number of ADD\_ADDR suboptions accepted for each MPTCP connection | 8             |
  
  For more information about these flags see `man ip-mptcp`
  </details>


  <details>
  <summary>When <b>path_manager="mptcpd"</b>, the following suboptions are available:</summary>

  | Option             | Description                                                                                                                    | Default Value           |
  |--------------------|--------------------------------------------------------------------------------------------------------------------------------|-------------------------|
  | add\_flags         | Flags for announced adresses                                                                                                   | "subflow,signal"        |
  | notify\_flags      | Address notification flags                                                                                                     | "existing"              |
  | load\_plugins      | Plugins to load                                                                                                                | " " (Loads all plugins" |
  | plugins\_conf\_dir | Plugins configuration path (Specific flag for this [`mptcpd version`](https://github.com/dulive/mptcpd/tree/patched_version))  | Default config path     |

  For more information about these flags see [`mptcpd` documentation](https://github.com/intel/mptcpd)
  </details>

  </ul>

</details>

<details>
  <summary>When <b>model="wlan"</b>, the following suboptions are available:</summary>

  | Option    | Description           | Default Value         |
  |-----------|-----------------------|-----------------------|
  | range     | Wlan range            | None (CORE's default) |
  | bandwidth | Wlan bandwidth        | None (CORE's default) |
  | delay     | Wlan delay            | None (CORE's default) |
  | jitter    | Wlan jitter           | None (CORE's default) |
  | error     | Wlan error percentage | None (CORE's default) |
</details>

</ul>

#### Link options

| Option           | Description                                                                                                          | Default Value         |
|------------------|----------------------------------------------------------------------------------------------------------------------|-----------------------|
| node1            | Host name of link endpoint 1                                                                                         | **Required Field**    |    
| node2            | Host name of link endpoint 2                                                                                         | **Required Field**    |
| bandwidth        | Link bandwidth                                                                                                       | None (CORE's default) |
| delay            | Link delay                                                                                                           | None (CORE's default) |
| dup              | Link duplication rate                                                                                                | None (CORE's default) |
| loss             | Link loss percentage                                                                                                 | None (CORE's default) |
| jitter           | Link jitter                                                                                                          | None (CORE's default) |
| use\_mptcp       | If this link should be considered to configure a MPTCP endpoint when connected to a "PC" node                        | true                  |
| ip\_mptcp\_flags | Flags to use when configuring this link as a MPTCP endpoint using `ip_mptcp` (See `man ip-mptcp`)                    | "subflow signal"      |

