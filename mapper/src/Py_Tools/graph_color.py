import sys

def _parse_graph_args(argv):
    nodes_size = int(argv[0])
    access_node_list = [str(i) for i in range(0, nodes_size)]
    argv_conflict = [str(int(arg)) for arg in argv[1:]]
    conflict_pairs = [
        (argv_conflict[i], argv_conflict[i + 1])
        for i in range(0, len(argv_conflict), 2)
    ]
    return access_node_list, conflict_pairs

def _greedy_color(access_node_list, conflict_pairs):
    graph = {node: set() for node in access_node_list}
    for src, dst in conflict_pairs:
        graph.setdefault(src, set()).add(dst)
        graph.setdefault(dst, set()).add(src)

    coloring = {}
    node_order = sorted(graph, key=lambda node: (-len(graph[node]), int(node)))
    for node in node_order:
        used_colors = {coloring[other] for other in graph[node] if other in coloring}
        color = 0
        while color in used_colors:
            color += 1
        coloring[node] = color
    return coloring

def runII(*argv):
    access_node_list, conflict_pairs = _parse_graph_args(argv)
    coloring = _greedy_color(access_node_list, conflict_pairs)
    return max(coloring.values()) + 1 if coloring else 0

def runCtrlStep(*argv):
    access_node_list, conflict_pairs = _parse_graph_args(argv)
    return _greedy_color(access_node_list, conflict_pairs)

if __name__ == "__main__":
    access_node_list, conflict_pairs = _parse_graph_args(sys.argv[1:])
    coloring = _greedy_color(access_node_list, conflict_pairs)
    num_steps = max(coloring.values()) + 1 if coloring else 0
