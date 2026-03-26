import random
import networkx as nx


# ─────────────────────────────────────────────
#  Build Confusion Graph
# ─────────────────────────────────────────────
def build_confusion_graph(real_ids: list) -> nx.DiGraph:
    """
    Build a directed confusion graph.

    Type-1 confusion nodes  → added to nodes with few outgoing edges
                               (breaks predictable ordering patterns).
    Type-2 confusion nodes  → replace real edges with fake routing hops
                               (distorts graph structure, may create cycles).

    Real slice ratio : confusion nodes ≈ 4:1  (paper recommendation)
    """
    G = nx.DiGraph()

    # Add real nodes
    for r in real_ids:
        G.add_node(r, real=True, node_type="real")

    # ── Type-1 confusion nodes ──────────────────
    fake_count = max(1, len(real_ids) // 4)
    fake_ids = []
    base = max(real_ids) + 1

    for i in range(fake_count):
        fid = base + i
        G.add_node(fid, real=False, node_type="confusion_type1")
        fake_ids.append(fid)

    # ── Build random ordering of all nodes ──────
    all_nodes = real_ids + fake_ids
    random.shuffle(all_nodes)

    for i in range(len(all_nodes) - 1):
        G.add_edge(all_nodes[i], all_nodes[i + 1])

    # ── Type-2 confusion nodes ───────────────────
    # Insert extra fake nodes in the middle of some real→real edges
    type2_base = base + fake_count
    type2_count = max(1, len(real_ids) // 4)

    real_edges = [(u, v) for u, v in list(G.edges())
                  if G.nodes[u]["real"] and G.nodes[v]["real"]]

    for j in range(min(type2_count, len(real_edges))):
        u, v = real_edges[j]
        fid2 = type2_base + j
        G.add_node(fid2, real=False, node_type="confusion_type2")
        G.remove_edge(u, v)
        G.add_edge(u, fid2)
        G.add_edge(fid2, v)

    return G


# ─────────────────────────────────────────────
#  Recover Real Order via Topological Sort
# ─────────────────────────────────────────────
def real_topological_order(G: nx.DiGraph) -> list:
    """
    Strip confusion nodes and return topological order of real slices.
    Handles cycles introduced by Type-2 nodes by working on subgraph only.
    """
    real_nodes = [n for n, d in G.nodes(data=True) if d.get("real")]
    sub = G.subgraph(real_nodes).copy()

    # Make it a DAG if cycles exist (shouldn't in real-only subgraph, but safe)
    if not nx.is_directed_acyclic_graph(sub):
        # Fall back to original sorted order
        return sorted(real_nodes)

    return list(nx.topological_sort(sub))


# ─────────────────────────────────────────────
#  Graph Export (serialisable for metadata)
# ─────────────────────────────────────────────
def graph_to_meta(G: nx.DiGraph) -> dict:
    return {
        "edges": list(G.edges()),
        "nodes": [
            {"id": n, "real": d.get("real"), "type": d.get("node_type")}
            for n, d in G.nodes(data=True)
        ]
    }


def graph_from_meta(meta: dict) -> nx.DiGraph:
    G = nx.DiGraph()
    for node in meta["nodes"]:
        G.add_node(node["id"], real=node["real"], node_type=node["type"])
    for u, v in meta["edges"]:
        G.add_edge(u, v)
    return G
