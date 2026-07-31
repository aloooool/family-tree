import networkx as nx
import pandas as pd
from pyvis.network import Network

class FamilyTree:
    def __init__(self, root_name: str = "خلاف"):
        self.root_name = root_name.strip()
        self.graph = nx.DiGraph()
        self.graph.add_node(self.root_name)

    def add_person(self, person_name: str, son_of: str = None):
        """
        Adds a person using their full name as the unique node identifier.
        """
        person_name = person_name.strip()
        self.graph.add_node(person_name)

        # 1. Direct father link if father's full name is provided
        if son_of and str(son_of).strip() != "nan":
            father_name = str(son_of).strip()
            self.graph.add_edge(father_name, person_name)
            return

        # 2. Auto-parse father-child relationships directly from full name
        parts = person_name.split()
        if len(parts) < 2:
            return

        current_child = person_name
        while len(parts) > 1:
            father_name = " ".join(parts[1:])
            self.graph.add_edge(father_name, current_child)
            
            # Move up the chain
            current_child = father_name
            parts = parts[1:]

    def load_from_excel(self, file_path: str, name_col: str = "Name", father_col: str = None):
        """Loads members directly from an Excel/CSV file."""
        df = pd.read_excel(file_path) if file_path.endswith('.xlsx') else pd.read_csv(file_path)
        
        for _, row in df.iterrows():
            p_name = str(row[name_col])
            f_name = str(row[father_col]) if father_col and father_col in row else None
            self.add_person(person_name=p_name, son_of=f_name)

    def visualize(self, output_filename="family_tree.html"):
        """Generates visual graph with Yellow Search and Green Lineage Path."""
        net = Network(height="700px", width="100%", directed=True)
        
        # Calculate horizontal generation levels relative to root
        levels = {}
        for node in self.graph.nodes():
            if nx.has_path(self.graph, self.root_name, node):
                levels[node] = nx.shortest_path_length(self.graph, self.root_name, node)
            else:
                levels[node] = 0

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

        for node in self.graph.nodes():
            first_name = node.split()[0]
            node_level = levels[node]
            
            if node == self.root_name:
                net.add_node(node, label=first_name, title=f"ROOT: {node}", shape="dot", size=26, level=node_level, color="#FF4500")
            else:
                net.add_node(node, label=first_name, title=f"Full Name: {node}\nGen: {node_level}", shape="dot", size=16, level=node_level, color="#1E90FF")

        for edge in self.graph.edges():
            net.add_edge(edge[0], edge[1])

        net.write_html(output_filename)

        # Custom JavaScript for Yellow Search & Tap-to-Green Lineage
        custom_html_ui = """
        <div style="position: absolute; top: 15px; left: 15px; z-index: 1000; background: rgba(255,255,255,0.95); padding: 12px; border-radius: 8px; box-shadow: 0px 4px 10px rgba(0,0,0,0.3); font-family: sans-serif;">
            <label for="personSearch" style="font-weight: bold; display: block; margin-bottom: 5px;">Search Name:</label>
            <input type="text" id="personSearch" placeholder="Type first name (e.g. محمد)..." style="padding: 6px; width: 220px; border: 1px solid #ccc; border-radius: 4px;">
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
            // Match search against full name string or first name label
            var matches = allNodes.filter(n => n.id.toLowerCase().includes(inputVal) || n.label.toLowerCase().includes(inputVal));

            if (matches.length === 0) {
                msgBox.style.color = "#d9534f";
                msgBox.innerHTML = "No person found with that name!";
                return;
            }

            var matchIds = new Set(matches.map(m => m.id));

            // Highlight all matching nodes in YELLOW
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

            // Trace path from target node up to root
            var pathNodes = new Set();
            var curr = selectedNodeId;
            pathNodes.add(curr);

            while (true) {
                var parentEdges = edges.get({ filter: e => e.to === curr });
                if (parentEdges.length === 0) break;
                curr = parentEdges[0].from;
                pathNodes.add(curr);
            }

            // Green highlight for lineage nodes
            var nodeUpdates = allNodes.map(n => {
                if (pathNodes.has(n.id)) {
                    return { id: n.id, color: { background: "#00FF00", border: "#008000" }, size: 24 };
                } else {
                    return { id: n.id, color: { background: "#E0E0E0", border: "#CCCCCC" }, size: 14 };
                }
            });
            nodes.update(nodeUpdates);

            // Green highlight for lineage edges
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

        // Tap/Click handler on nodes
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

        updated_html = html_content.replace("</body>", f"{custom_html_ui}\n</body>")

        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(updated_html)

        print(f"Interactive tree saved to '{output_filename}'.")


# ==========================================
# Execution Test
# ==========================================
if __name__ == "__main__":
    tree = FamilyTree(root_name="خلاف")

    # Add members directly without managing IDs
    tree.add_person("محمد عبدالجليل محمود خلاف")
    tree.add_person("الحسن محمد عبدالجليل محمود خلاف")
    tree.add_person("الحسين محمد عبدالجليل محمود خلاف")
    tree.add_person("صلاح محمد عبدالجليل محمود خلاف")
    tree.add_person("حمدى محمد عبدالجليل محمود خلاف")
    tree.add_person("عمر الحسن محمد عبدالجليل محمود خلاف")
    # Explicit son_of connection using full name
    tree.add_person("علي الحسن محمد عبدالجليل محمود خلاف")

    tree.visualize("family_tree.html")