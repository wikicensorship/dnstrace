#!/usr/bin/env python3

import ipaddress
import json
import os
from time import sleep
from turtle import shape

import networkx as nx
from pyvis.network import Network

ROUTER_COLOR = "green"
WINDOWS_COLOR = "blue"
LINUX_COLOR = "purple"
MIDDLEBOX_COLOR = "red"
NO_RESPONSE_COLOR = "gray"
DEVICE_OS_NAME = {
    ROUTER_COLOR: "Router", WINDOWS_COLOR: "Windows", LINUX_COLOR: "Linux",
    MIDDLEBOX_COLOR: "Middlebox", NO_RESPONSE_COLOR: "unknown"
}
REQUEST_COLORS = [
    "DarkTurquoise", "HotPink", "LimeGreen", "Red", "DodgerBlue", "Orange",
    "MediumSlateBlue", "DarkGoldenrod", "Green", "Brown", "YellowGreen", "Magenta"
]


TEMPLATE_PATH = os.path.dirname(
    __file__) + "/templates/template_offline.html.jinja"

multi_directed_graph = nx.MultiDiGraph()


def parse_ttl(response_ttl, current_ttl):
    device_color = ""
    backttl = 0
    if response_ttl <= 20:
        backttl = int((current_ttl - response_ttl) / 2) + 1
        device_color = MIDDLEBOX_COLOR
    elif response_ttl <= 64:
        backttl = 64 - response_ttl + 1
        device_color = LINUX_COLOR
    elif response_ttl <= 128:
        backttl = 128 - response_ttl + 1
        device_color = WINDOWS_COLOR
    else:
        backttl = 255 - response_ttl + 1
        device_color = ROUTER_COLOR
    return backttl, device_color


def visualize(previous_node_id, current_node_id,
              current_node_label, current_node_title, device_color,
              current_edge_title, requset_color, current_edge_label,
              current_node_shape):
    if not multi_directed_graph.has_node(current_node_id):
        multi_directed_graph.add_node(current_node_id,
                                      label=current_node_label, color=device_color,
                                      title=current_node_title,shape=current_node_shape)
    multi_directed_graph.add_edge(previous_node_id, current_node_id, label=current_edge_label,
                                  color=requset_color, title=current_edge_title)


def styled_tooltips(
        current_request_colors, current_ttl_str, backttl, request_ip, elapsed_ms,
        packet_size, repeat_all_steps, device_os_name, annotation):
    time_size = "*"
    elapsed_ms_str = "*"
    packet_size_str = "*"
    if packet_size != "*":
        packet_size_str = str(packet_size) + "B"
    if elapsed_ms != "*":
        elapsed_ms_str = str(format(elapsed_ms, '.3f')) + "ms"
        time_size = str(format(elapsed_ms/packet_size, '.3f')) + "ms/B"
    return ("<pre style=\"color:" + current_request_colors
            + "\">TTL: " + current_ttl_str
            + "<br/>Back-TTL: " + backttl
            + "<br/>Request to: " + request_ip
            + "<br/>annotation: " + annotation
            + "<br/>Time: " + elapsed_ms_str
            + "<br/>Size: " + packet_size_str
            + "<br/>Time/Size: " + time_size
            + "<br/>OS: " + device_os_name
            + "<br/>Repeat step: " + str(repeat_all_steps) + "</pre>")


def already_reached_destination(previous_node_id, current_node_ip):
    if previous_node_id in {
            str(current_node_ip),
            ("middlebox" + str(current_node_ip) + "x")}:
        return True
    else:
        return False


def initialize_first_nodes(src_addr):
    nodes = []
    for _ in range(10):
        nodes.append(str(src_addr))
    return nodes


def save_measurement_graph(graph_name, attach_jscss):
    net_vis = Network("1500px", "1500px",
                      directed=True, bgcolor="#eeeeee")
    net_vis.from_nx(multi_directed_graph)
    net_vis.set_edge_smooth('dynamic')
    if attach_jscss:
        net_vis.set_template(TEMPLATE_PATH)
    if graph_name.endswith(".json"):
        graph_name = graph_name[:-5]
    graph_path = graph_name + ".html"
    net_vis.save_graph(graph_path)
    print("saved: " + graph_path)


def vis(measurement_path, attach_jscss, edge_lable: str = "none"):
    all_measurements = []
    was_successful = False
    with open(measurement_path) as json_file:
        all_measurements = json.load(json_file)
    measurement_steps = 0
    src_addr = all_measurements[0]["src_addr"]
    src_addr_id = str(int(ipaddress.IPv4Address(src_addr)))
    multi_directed_graph.add_node(
        src_addr_id, label=src_addr, color="Chocolate", title="source address",
        shape="diamond")
    for measurement in all_measurements:
        previous_node_ids = initialize_first_nodes(src_addr_id)
        dst_addr = measurement["dst_addr"]
        dst_addr_id = str(int(ipaddress.IPv4Address(dst_addr)))
        annotation = "-"
        if "annotation" in measurement.keys():
            annotation = measurement["annotation"]
        all_results = measurement["result"]
        for try_step in all_results:  # will be up to 255
            current_ttl = try_step["hop"]
            current_ttl_str = str(current_ttl)
            results = try_step["result"]
            repeat_steps = 0
            skip_next = False
            for result in results:  # will be up to 3
                if skip_next:
                    skip_next = False
                    continue
                not_yet_destination = not (already_reached_destination(
                    previous_node_ids[repeat_steps], dst_addr_id))
                if not_yet_destination:
                    if "late" in result.keys():
                        skip_next = True
                    current_node_label = "***"
                    current_edge_title = "***"
                    current_edge_label = ""
                    current_node_id = "0"
                    current_node_shape= "dot"
                    elapsed_ms = "*"
                    packet_size = "*"
                    backttl = "*"
                    device_color = NO_RESPONSE_COLOR
                    if 'x' in result.keys():
                        current_node_id = (
                            "unknown" + previous_node_ids[repeat_steps] + "x")
                        if edge_lable != "none":
                            current_edge_label = "*"
                    else:
                        answer_ip = result["from"]
                        backttl, device_color = parse_ttl(
                            result["ttl"], current_ttl)
                        if "rtt" in result.keys():
                            elapsed_ms = result["rtt"]
                        if edge_lable == "rtt":
                            if elapsed_ms != "*":
                                current_edge_label = format(elapsed_ms, '.3f')
                        elif edge_lable == "backttl":
                            current_edge_label = str(backttl)
                        current_node_id = str(
                            int(ipaddress.IPv4Address(answer_ip)))
                        if device_color == MIDDLEBOX_COLOR:
                            current_node_id = (
                                "middlebox" + str(current_node_id) + "x")
                            current_node_shape = "star"
                        elif current_node_id == dst_addr_id:
                            current_node_shape = "square"
                        current_node_label = answer_ip
                        current_edge_title = str(backttl)
                        packet_size = result["size"]
                    current_edge_title = styled_tooltips(
                        REQUEST_COLORS[measurement_steps], current_ttl_str,
                        str(backttl), dst_addr, elapsed_ms, packet_size,
                        (repeat_steps + 1), DEVICE_OS_NAME[device_color],
                        annotation
                    )
                    visualize(
                        previous_node_ids[repeat_steps], current_node_id,
                        current_node_label, DEVICE_OS_NAME[device_color], device_color,
                        current_edge_title, REQUEST_COLORS[measurement_steps],
                        current_edge_label, current_node_shape
                    )
                    previous_node_ids[repeat_steps] = current_node_id
                repeat_steps += 1
        measurement_steps += 1
    print("saving measurement graph...")
    save_measurement_graph(measurement_path, attach_jscss)
    print("· · · - · -     · · · - · -     · · · - · -     · · · - · -")
