import os
import networkx as nx
import pandas as pd
from pyvis.network import Network


class FamilyTree:

    def __init__(self, root_name: str, root_is_man: bool = True):
        self.root_name = root_name.strip()
        self.graph = nx.DiGraph()
        self.graph.add_node(self.root_name, is_man=root_is_man)

    def add_person(self, person_name: str, is_man: bool = True):
        """Adds a person using their full name as the unique node identifier.

        Sets gender (`is_man=True` by default) and automatically parses father-child relationships.
        """
        person_name = person_name.strip()
        if not person_name:
            return

        # Add or update the target node with gender attribute
        self.graph.add_node(person_name, is_man=is_man)

        parts = person_name.split()
        if len(parts) < 2:
            return

        current_child = person_name
        while len(parts) > 1:
            father_name = " ".join(parts[1:])

            # Add father node if missing (defaults to True for father ancestors)
            if father_name not in self.graph:
                self.graph.add_node(father_name, is_man=True)

            self.graph.add_edge(father_name, current_child)

            # Move up the ancestral chain
            current_child = father_name
            parts = parts[1:]

    def load_from_excel(
        self,
        file_path: str,
        name_col: str = "Name",
        gender_col: str = "IsMan",
    ):
        """Loads members directly from an Excel or CSV file."""
        df = (
            pd.read_excel(file_path)
            if file_path.endswith(".xlsx")
            else pd.read_csv(file_path)
        )

        for _, row in df.iterrows():
            p_name = str(row[name_col]).strip()
            if not p_name or p_name.lower() == "nan":
                continue

            # Parse gender column if it exists
            is_man = True
            if gender_col in df.columns and pd.notna(row[gender_col]):
                val = str(row[gender_col]).strip().lower()
                if val in ["false", "f", "0", "female", "woman", "no"]:
                    is_man = False

            self.add_person(person_name=p_name, is_man=is_man)

    def visualize(self, output_filename="family_tree.html"):
        """Generates an interactive pyvis network graph with custom search and lineage tracing."""
        _generate_pyvis_html(
            graph=self.graph,
            root_nodes=[self.root_name],
            output_filename=output_filename,
        )


class Village:

    def __init__(self, village_name: str):
        self.village_name = village_name.strip()
        self.families = {}  # Maps root_name -> FamilyTree object

    def add_family(
        self, root_name: str, root_is_man: bool = True
    ) -> FamilyTree:
        """Explicitly creates and registers a new family within the village."""
        root_name = root_name.strip()
        if root_name not in self.families:
            self.families[root_name] = FamilyTree(
                root_name=root_name, root_is_man=root_is_man
            )
        return self.families[root_name]

    def load_from_excel(
        self,
        file_path: str,
        name_col: str = "Name",
        family_col: str = "FamilyRoot",
        gender_col: str = "IsMan",
    ):
        """Loads data from a file containing members across multiple families."""
        df = (
            pd.read_excel(file_path)
            if file_path.endswith(".xlsx")
            else pd.read_csv(file_path)
        )

        for _, row in df.iterrows():
            person_name = str(row[name_col]).strip()
            if not person_name or person_name.lower() == "nan":
                continue

            # Determine family root
            if family_col in df.columns and pd.notna(row[family_col]):
                root_name = str(row[family_col]).strip()
            else:
                root_name = person_name.split()[-1]

            # Determine gender (default True unless explicitly false)
            is_man = True
            if gender_col in df.columns and pd.notna(row[gender_col]):
                val = str(row[gender_col]).strip().lower()
                if val in ["false", "f", "0", "female", "woman", "no"]:
                    is_man = False

            if root_name not in self.families:
                self.add_family(root_name, root_is_man=True)

            self.families[root_name].add_person(
                person_name=person_name, is_man=is_man
            )

    def visualize_family(self, root_name: str, output_filename: str = None):
        """Visualizes a single specific family tree inside the village."""
        root_name = root_name.strip()
        if root_name not in self.families:
            print(
                f"Warning: Family '{root_name}' does not exist in {self.village_name}."
            )
            return

        if output_filename is None:
            output_filename = f"{self.village_name}_{root_name}_tree.html"

        self.families[root_name].visualize(output_filename)

    def visualize_all(self, output_filename: str = "village_network.html"):
        """Combines all families into a single unified village network graph."""
        combined_graph = nx.DiGraph()
        all_roots = list(self.families.keys())

        for family in self.families.values():
            combined_graph = nx.compose(combined_graph, family.graph)

        _generate_pyvis_html(
            graph=combined_graph,
            root_nodes=all_roots,
            output_filename=output_filename,
        )

def _generate_pyvis_html(
    graph: nx.DiGraph, root_nodes: list, output_filename: str
):
    """Internal helper function to construct and inject visual JavaScript UI into Pyvis outputs."""
    net = Network(height="750px", width="100%", directed=True)

    # Compute generation hierarchy relative to known root nodes
    levels = {}
    for node in graph.nodes():
        shortest_dist = float("inf")
        for root in root_nodes:
            if nx.has_path(graph, root, node):
                dist = nx.shortest_path_length(graph, root, node)
                if dist < shortest_dist:
                    shortest_dist = dist

        levels[node] = 0 if shortest_dist == float("inf") else shortest_dist

    net.set_options("""
    var options = {
      "nodes": { "borderWidth": 2, "shadow": true },
      "layout": {
        "hierarchical": {
          "enabled": true,
          "direction": "UD",
          "sortMethod": "directed",
          "levelSeparation": 120,
          "nodeSpacing": 180
        }
      },
      "physics": {
        "hierarchicalRepulsion": { "centralGravity": 0.0, "springLength": 90, "nodeDistance": 150 }
      }
    }
    """)

    # Populate nodes with color logic based on gender and root status
    for node in graph.nodes():
        first_name = node.split()[0] if node else node
        node_level = levels.get(node, 0)

        # Retrieve gender flag (defaults to True if missing)
        is_man = graph.nodes[node].get("is_man", True)

        if node in root_nodes:
            node_color = "#FF4500"  # Family Root (Orange/Red)
            node_size = 28
        elif not is_man:
            node_color = "#FF69B4"  # Pink for False (Female)
            node_size = 16
        else:
            node_color = "#1E90FF"  # Blue for True (Male)
            node_size = 16

        gender_str = "Male" if is_man else "Female"

        net.add_node(
            node,
            label=first_name,
            title=(
                f"ROOT: {node}"
                if node in root_nodes
                else f"Full Name: {node}\nGender: {gender_str}\nGen Level:"
                f" {node_level}"
            ),
            shape="dot",
            size=node_size,
            level=node_level,
            color=node_color,
        )

    # Populate edges
    for edge in graph.edges():
        net.add_edge(edge[0], edge[1])

    net.write_html(output_filename)

    # Injected Search & Interactive Lineage Tracing UI
    custom_html_ui = """
    <div style="position: absolute; top: 15px; left: 15px; z-index: 1000; background: rgba(255,255,255,0.95); padding: 12px; border-radius: 8px; box-shadow: 0px 4px 10px rgba(0,0,0,0.3); font-family: sans-serif;">
        <label for="personSearch" style="font-weight: bold; display: block; margin-bottom: 5px;">Search Village Name:</label>
        <input type="text" id="personSearch" placeholder="Type name (e.g. فاطمة)..." style="padding: 6px; width: 220px; border: 1px solid #ccc; border-radius: 4px;">
        <button onclick="searchPerson()" style="padding: 6px 12px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">Search</button>
        <button onclick="resetHighlight()" style="padding: 6px 10px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">Reset</button>
        <div id="searchMessage" style="margin-top: 6px; font-size: 12px; font-weight: bold;"></div>
    </div>

    <script>
    function searchPerson() {
        var inputVal = document.getElementById("personSearch").value.trim().toLowerCase();
        var msgBox = document.getElementById("searchMessage");
        msgBox.innerHTML = "";

        if (!inputVal) return;

        var allNodes = nodes.get();
        var matches = allNodes.filter(n => n.id.toLowerCase().includes(inputVal) || n.label.toLowerCase().includes(inputVal));

        if (matches.length === 0) {
            msgBox.style.color = "#d9534f";
            msgBox.innerHTML = "No member found with that name!";
            return;
        }

        var matchIds = new Set(matches.map(m => m.id));

        var nodeUpdates = allNodes.map(n => {
            if (matchIds.has(n.id)) {
                return { id: n.id, color: { background: "#FFD700", border: "#B8860B" }, size: 24 };
            } else {
                return { id: n.id, color: { background: "#E0E0E0", border: "#CCCCCC" }, size: 14 };
            }
        });
        nodes.update(nodeUpdates);

        if (matches.length === 1) {
            highlightLineagePath(matches[0].id);
        } else {
            msgBox.style.color = "#856404";
            msgBox.innerHTML = "Found " + matches.length + " matches (Yellow). Tap/Click one to trace lineage!";
        }
    }

    function highlightLineagePath(selectedNodeId) {
        var allNodes = nodes.get();

        var pathNodes = new Set();
        var curr = selectedNodeId;
        pathNodes.add(curr);

        while (true) {
            var parentEdges = edges.get({ filter: e => e.to === curr });
            if (parentEdges.length === 0) break;
            curr = parentEdges[0].from;
            pathNodes.add(curr);
        }

        var nodeUpdates = allNodes.map(n => {
            if (pathNodes.has(n.id)) {
                return { id: n.id, color: { background: "#00FF00", border: "#008000" }, size: 24 };
            } else {
                return { id: n.id, color: { background: "#E0E0E0", border: "#CCCCCC" }, size: 14 };
            }
        });
        nodes.update(nodeUpdates);

        var edgeUpdates = edges.get().map(e => {
            if (pathNodes.has(e.from) && pathNodes.has(e.to)) {
                return { id: e.id, color: { color: "#00FF00", highlight: "#00FF00" }, width: 3 };
            } else {
                return { id: e.id, color: { color: "#E0E0E0" }, width: 1 };
            }
        });
        edges.update(edgeUpdates);

        network.focus(selectedNodeId, { scale: 1.2, animation: true });

        var msgBox = document.getElementById("searchMessage");
        msgBox.style.color = "#28a745";
        msgBox.innerHTML = "Lineage traced to root!";
    }

    network.on("click", function (params) {
        if (params.nodes.length > 0) {
            highlightLineagePath(params.nodes[0]);
        }
    });

    function resetHighlight() {
        location.reload();
    }
    </script>
    """

    with open(output_filename, "r", encoding="utf-8") as f:
        html_content = f.read()

    updated_html = html_content.replace(
        "</body>", f"{custom_html_ui}\n</body>"
    )

    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(updated_html)

    print(f"Rendered interactive view to '{output_filename}'.")

# ==========================================
# Test Usage
# ==========================================
if __name__ == "__main__":
    my_village = Village(village_name="kfr-el-snabsa")
    # Batch loading from CSV (with optional IsMan column)
    my_village.load_from_excel(
            file_path="Nmaes.csv",
            name_col="Name",
            family_col="FamilyRoot",
            gender_col="IsMan",
        )
    my_village.visualize_all("index.html")