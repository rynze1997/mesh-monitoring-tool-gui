import dearpygui.dearpygui as dpg
from config import CANVAS_WINDOW_SIZE, DRAWLIST_SIZE
import networkx as nx
import numpy as np
from typing import List, Dict

class CanvasManager:
    
    _instance = None  # Class-level attribute to store the singleton instance
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(CanvasManager, cls).__new__(cls)
            # Initialize the instance once
            cls._instance.init_once()
        return cls._instance

    def init_once(self):
        self.node_radius = 10
        self.margin = 100
        self.site = None
        self.pos = None
        self.G = nx.Graph()
        
    def create_canvas_window(self, title="Topology Analysis Window", width=CANVAS_WINDOW_SIZE[0], height=CANVAS_WINDOW_SIZE[1]):
        
        with dpg.window(label=title, tag="__topology_analysis_window", width=width, height=height):
            # Mesh topology drawing canvas and corresponding information texts are grouped together
            with dpg.group(horizontal=True, tag="__topology_analysis_drawing_canvas_group"):
                # Window where mesh topology graph will be drawed
                with dpg.drawlist(width=DRAWLIST_SIZE[0], height=DRAWLIST_SIZE[1], tag="__topology_analysis_drawing_canvas"):
                    dpg.draw_rectangle((0, 0), (DRAWLIST_SIZE[0], DRAWLIST_SIZE[1]), color=(255, 255, 255), thickness=1)
                # Information texts
                with dpg.child_window(tag="__node_info_child_window", width=280, height=DRAWLIST_SIZE[1], parent="__discovered_node_text_group"):
                    with dpg.group(horizontal=False):
                        with dpg.group(tag="__amount_of_nodes_and_edges_text_group"):
                            dpg.add_text("Nodes: 0")
                            dpg.add_text("Edges: 0")
                    # Discovered nodes are drawn here  
                        with dpg.group(tag="__discovered_node_text_group"):
                            pass
                    
    def redraw_edge_colors(self, mdr_result):
        for edge in self.G.edges:
            start_pos = np.array(self.pos[edge[0]])
            end_pos = np.array(self.pos[edge[1]])
            direction = end_pos - start_pos
            length = np.linalg.norm(direction)
            direction = direction / length

            # Shorten the line start and end by the node radius
            start_pos += direction * self.node_radius
            end_pos -= direction * self.node_radius
            
            node1 = self.G.edges[edge]['node1']
            node2 = self.G.edges[edge]['node2']
            
            # Find node1 and node2 in mdr_result dictionary
            for mdr_result_node in mdr_result:
                if mdr_result_node['source_label']['number'] == node1 and mdr_result_node['destination_label']['number'] == node2:
                    mdr = mdr_result_node['mdr']
                    break
                elif mdr_result_node['source_label']['number'] == node2 and mdr_result_node['destination_label']['number']== node1:
                    mdr = mdr_result_node['mdr']
                    break
            else:
                continue
                
            if mdr is None:
                color = (255, 255, 255)
            elif mdr > 80:
                color = (0, 255, 0)
            elif mdr > 50:
                color = (255, 255, 0)
            else:
                color = (255, 0, 0)
            
            dpg.draw_line(start_pos, end_pos, thickness=1, color=color, parent="__topology_analysis_drawing_canvas")

    def plot_data(self, connections, mac_to_letter):
        canvas_width = DRAWLIST_SIZE[0]
        canvas_height = DRAWLIST_SIZE[1]
        
        dpg.delete_item(item="__topology_analysis_drawing_canvas", children_only=True)
        self.G.clear()
        dpg.draw_rectangle((0, 0), (DRAWLIST_SIZE[0], DRAWLIST_SIZE[1]), color=(255, 255, 255), thickness=1, parent="__topology_analysis_drawing_canvas")
        
        for connection in connections:
            start, end = connection
            if (connection[1] == "0"):
                self.G.add_node(mac_to_letter[start]['number'])
            else:
                self.G.add_edge(mac_to_letter[start]['number'], mac_to_letter[end]['number'], weight=1, node1 = mac_to_letter[start]['number'], node2 = mac_to_letter[end]['number'])
            
        # Adjust the spring layout's distance parameter dynamically based on the number of nodes
        node_count = len(self.G.nodes)
        distance = max(min(1.0, 10.0 / max(node_count, 1)), 0.1)  
        
        self.pos = nx.spring_layout(self.G, seed=7, k=distance)  # Adjust k based on needs

        # Find bounds of graph layout
        pos_array = np.array(list(self.pos.values()))
        min_pos = np.min(pos_array, axis=0)
        max_pos = np.max(pos_array, axis=0)

        # Check if there is only one node
        if np.array_equal(min_pos, max_pos):
            # If there is only one node, place it in the center of the canvas
            scaled_pos = np.array([[canvas_width / 2, canvas_height / 2]])
        else:
            # Normalize positions
            scaled_pos = (pos_array - min_pos) / (max_pos - min_pos)

            # Scale positions to fit the drawing area with margin
            scaled_pos *= (canvas_width - 2*self.margin, canvas_height - 2*self.margin)
            scaled_pos += self.margin  # Add margin to each position

        self.pos = dict(zip(self.pos.keys(), scaled_pos))  # update positions with scaled values

        
        for edge in self.G.edges:
            start_pos = np.array(self.pos[edge[0]])
            end_pos = np.array(self.pos[edge[1]])
            direction = end_pos - start_pos
            length = np.linalg.norm(direction)
            direction = direction / length

            # Shorten the line start and end by the node radius
            start_pos += direction * self.node_radius
            end_pos -= direction * self.node_radius


            dpg.draw_line(start_pos, end_pos, thickness=1, parent="__topology_analysis_drawing_canvas")

            # Draw nodes
        for node in self.G.nodes:
            node_pos = self.pos[node]
            dpg.draw_circle(node_pos, radius=self.node_radius, color=(250, 50, 50, 255), parent="__topology_analysis_drawing_canvas")
            # Node labels are now letters, so no need to change label positioning
            label_pos = (node_pos[0] - self.node_radius/2, node_pos[1] - self.node_radius)
            dpg.draw_text(label_pos, node, color=(250, 250, 250, 255), size=15, parent="__topology_analysis_drawing_canvas")
            
        # Add text to the canvas (Letter: MAC)
        dpg.delete_item(item="__discovered_node_text_group", children_only=True)
        dpg.delete_item(item="__amount_of_nodes_and_edges_text_group", children_only=True)
        
        dpg.add_text(f"Nodes: {len(self.G.nodes)}", parent="__amount_of_nodes_and_edges_text_group")
        dpg.add_text(f"Edges: {len(self.G.edges)} ({round((len(self.G.nodes)*(len(self.G.nodes)-1))/2)})", parent="__amount_of_nodes_and_edges_text_group")
        
        for mac, info in mac_to_letter.items():
            with dpg.group(horizontal=True, parent="__discovered_node_text_group"):
                dpg.add_text(f"{info['number']}:" , color=(255, 0, 0))
                dpg.add_text(f"{info['title']:<15}:" , color=(0, 255, 0))  # Adjust 20 to the desired width
                dpg.add_text(f"{mac}")
                    
            
    def get_shortest_path(self, mac_to_label: Dict, source: str, destination: str) -> List:
        start_node = mac_to_label[source]['number']
        end_node = mac_to_label[destination]['number']
        
        shortest_path = nx.shortest_path(self.G, start_node, end_node)
     
        return shortest_path
    
    def get_shortest_paths(self, mac_label_map: Dict, source: str, destination: str) -> List:
        start_node = mac_label_map[source]['number']
        end_node = mac_label_map[destination]['number']
        return nx.all_shortest_paths(self.G, start_node, end_node)
    
    def get_number_of_neighbors_for_each_hop(self, mac_to_label, source, destination):
        
        start_node = mac_to_label[source]['number']
        end_node = mac_to_label[destination]['number']
        
        shortest_path = nx.shortest_path(self.G, start_node, end_node)
        node_neighbor_dict = {}
        for i in range(len(shortest_path) - 2):
            # Find neighbors for each node
            neighbors_a = set(self.G.neighbors(shortest_path[i]))
            neighbors_b = set(self.G.neighbors(shortest_path[i+2]))
            # Identify common neighbors
            common_neighbors = neighbors_a.intersection(neighbors_b)
            node_neighbor_dict[shortest_path[i]] = len(common_neighbors)
        return node_neighbor_dict
    
    def get_has_path(self, mac_label_map: Dict, source: str, destination: str) -> bool:
        start_node = mac_label_map[source]['number']
        end_node = mac_label_map[destination]['number']
        
        return nx.has_path(self.G, start_node, end_node)
    
    def highlight_shortest_path(self, shortest_path: List):
        for edge in self.G.edges:
            start_pos = np.array(self.pos[edge[0]])
            end_pos = np.array(self.pos[edge[1]])
            direction = end_pos - start_pos
            length = np.linalg.norm(direction)
            direction = direction / length

            # Shorten the line start and end by the node radius
            start_pos += direction * self.node_radius
            end_pos -= direction * self.node_radius
            
            node1 = self.G.edges[edge]['node1']
            node2 = self.G.edges[edge]['node2']
            
            for i in range(len(shortest_path) - 1):
                if node1 == shortest_path[i] and node2 == shortest_path[i+1] or node1 == shortest_path[i+1] and node2 == shortest_path[i]:
                    dpg.draw_line((start_pos[0], start_pos[1]), (end_pos[0], end_pos[1]), thickness=5, color=(0, 0, 255), parent="__topology_analysis_drawing_canvas")
                    
    def redraw_edges(self):
        dpg.delete_item(item="__topology_analysis_drawing_canvas", children_only=True)
        dpg.draw_rectangle((0, 0), (DRAWLIST_SIZE[0], DRAWLIST_SIZE[1]), color=(255, 255, 255), thickness=1, parent="__topology_analysis_drawing_canvas")
        
        for edge in self.G.edges:
            start_pos = np.array(self.pos[edge[0]])
            end_pos = np.array(self.pos[edge[1]])
            direction = end_pos - start_pos
            length = np.linalg.norm(direction)
            direction = direction / length

            # Shorten the line start and end by the node radius
            start_pos += direction * self.node_radius
            end_pos -= direction * self.node_radius


            dpg.draw_line(start_pos, end_pos, thickness=1, parent="__topology_analysis_drawing_canvas")

            # Draw nodes
        for node in self.G.nodes:
            node_pos = self.pos[node]
            dpg.draw_circle(node_pos, radius=self.node_radius, color=(250, 50, 50, 255), parent="__topology_analysis_drawing_canvas")
            # Node labels are now letters, so no need to change label positioning
            label_pos = (node_pos[0] - self.node_radius/2, node_pos[1] - self.node_radius)
            dpg.draw_text(label_pos, node, color=(250, 250, 250, 255), size=15, parent="__topology_analysis_drawing_canvas")

    def reset_graph(self):
        dpg.delete_item(item="__topology_analysis_drawing_canvas", children_only=True)
        self.G.clear()
        dpg.draw_rectangle((0, 0), (DRAWLIST_SIZE[0], DRAWLIST_SIZE[1]), color=(255, 255, 255), thickness=1, parent="__topology_analysis_drawing_canvas")
        dpg.delete_item(item="__discovered_node_text_group", children_only=True)
        dpg.delete_item(item="__amount_of_nodes_and_edges_text_group", children_only=True)
        dpg.add_text(f"Nodes: {0}", parent="__amount_of_nodes_and_edges_text_group")
        dpg.add_text(f"Edges: {0}", parent="__amount_of_nodes_and_edges_text_group")
        
    
    def close_canvas_window(self):
        dpg.delete_item("__topology_analysis_window")
        
    def get_node_neighbor_map(self):
        # For each node, find its neighbors and write to a dictionary
        node_neighbor_map = {}
        for node in self.G.nodes:
            neighbors = list(self.G.neighbors(node))
            node_neighbor_map[node] = neighbors
            
        return node_neighbor_map