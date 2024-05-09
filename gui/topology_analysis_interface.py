import dearpygui.dearpygui as dpg
from network.topology_analysis_service import TopologyAnalysisService
from .canvas_manager import CanvasManager
from config import WINDOW_SIZE, CANVAS_WINDOW_SIZE, DRAWLIST_SIZE
import ast

class topologyAnalysisInterfaceManager:
    def __init__(self):
        self.discover_handler = None
        self.site_name = ""
        self.reset_callback = None
    def create_topology_analysis_button(self, site_name, reset_callback):
        
        self.site_name = site_name
        self.discover_handler = TopologyAnalysisService()
        self.reset_callback = reset_callback
        
        dpg.add_button(label="START Topology Analysis", callback=self._on_start, tag="__start_stop_topology_analysis_button", 
                       parent="__topology_analysis_window", height=30)
        
        
        dpg.add_text("Find shortest paths:", parent="__topology_analysis_window")
        with dpg.child_window(tag="__shortest_path_from_to_child_window", width=DRAWLIST_SIZE[0]/2, height=85, parent="__topology_analysis_window"):
            with dpg.group(horizontal=True, parent="__shortest_path_from_to_child_window", tag = "__shortest_path_from_to_group"):
                dpg.add_text("From:")
                dpg.add_combo(label="", items=[], tag="__shortest_path_combo_from", width=(WINDOW_SIZE[0] - 900)/3)
                dpg.add_text("To:")
                dpg.add_combo(label="", items=[], tag="__shortest_path_combo_to", width=(WINDOW_SIZE[0] - 900)/3)
                dpg.add_button(label="Find", callback=self._on_find_shortest_path_button_callback, tag="__find_shortest_path_button")
                dpg.add_text(default_value="", tag="__shortest_path_error_text")
        
        with dpg.group(horizontal=True, parent="__topology_analysis_window", pos=[5, CANVAS_WINDOW_SIZE[1]-25]):
            dpg.add_button(label="Restart", callback=self._on_reset_button_callback, tag="__reset_topology_analysis_button")
            dpg.add_button(label="Clear edges", callback=self._on_clear_shortest_path_button_callback, tag="__clear_shortest_path_button")
            
    def _on_start(self):
        print("Start Topology Analysis button pressed")
        
        # Start Topology analysis
        self.discover_handler.start_topology_analysis(self.site_name)
        
        dpg.delete_item("__start_topology_analysis_button")
        dpg.configure_item(item ="__start_stop_topology_analysis_button", label="STOP Topology Analysis", callback=self._on_stop, 
                           tag="__stop_topology_analysis_button", parent="__topology_analysis_window")
            
    def _on_stop(self):
        print("Stop Topology Analysis button pressed")
        
        # Stop Discovery Process
        self.discover_handler.stop_topology_analysis()
        
        dpg.delete_item("__stop_topology_analysis_button")
        dpg.configure_item(item ="__start_stop_topology_analysis_button", label="START Topology Analysis", callback=self._on_start, 
                           tag="__start_topology_analysis_button", parent="__topology_analysis_window")        
        # All other analysis only available after topology analysis
        dpg.configure_item(item="__analysis_menu", enabled=True)
        
        # Retrieve MAC to label map from Mesh Topology analysis results
        mac_label_map = self.discover_handler.get_mac_label_map()
        # Create list of MAC labels
        mac_label_list = [f"{info['number']}: {info['title']:<15}: {mac}" for mac, info in mac_label_map.items()]
        dpg.configure_item(item="__shortest_path_combo_from", items=mac_label_list)
        dpg.configure_item(item="__shortest_path_combo_to", items=mac_label_list)
        
        # If MDR or/and Latency window are already open and new topology discovery is made, update
        # the source and destination combo boxes with the new MAC labels
        if dpg.does_item_exist("__latency_source"):
            dpg.configure_item(item="__latency_source", items=mac_label_list)
            dpg.configure_item(item="__latency_destination", items=mac_label_list)
            
        if dpg.does_item_exist("__latency_source"):
            dpg.configure_item(item="__mdr_source", items=mac_label_list)
            dpg.configure_item(item="__mdr_destination", items=mac_label_list)
    
    def _on_find_shortest_path_button_callback(self):
        # Get selected source and destination
        source = dpg.get_value("__shortest_path_combo_from")
        destination = dpg.get_value("__shortest_path_combo_to")
        # Remove labels from source and destination
        source_mac = source.split(": ")[2]
        destination_mac = destination.split(": ")[2]
        
        if not CanvasManager().get_has_path(self.discover_handler.get_mac_label_map(), source_mac, destination_mac):
            dpg.configure_item(item="__shortest_path_error_text", default_value="No path found!", color=(255, 0, 0))
        else:
            dpg.configure_item(item="__shortest_path_error_text", default_value="")
            all_shortest_paths = CanvasManager().get_shortest_paths(self.discover_handler.get_mac_label_map(), source_mac, destination_mac)
            all_shortest_paths_list = list(all_shortest_paths)
            if dpg.does_item_exist("__shortest_paths_group"):
                dpg.delete_item("__shortest_paths_group")
            with dpg.group(horizontal=True, parent="__shortest_path_from_to_child_window", tag="__shortest_paths_group"):
                dpg.add_text("Select shortest path to display:")
                dpg.add_combo(label="", items=all_shortest_paths_list, tag="__shortest_paths_combo", width=(WINDOW_SIZE[0] - 900)/3, 
                              callback=self._on_shortest_path_combo_callback)
                
            
    def _on_shortest_path_combo_callback(self):
        selected_shortest_path = dpg.get_value("__shortest_paths_combo")
        selected_shortest_path_list = ast.literal_eval(selected_shortest_path)
        CanvasManager().highlight_shortest_path(selected_shortest_path_list)
        
    def _on_clear_shortest_path_button_callback(self):
        CanvasManager().redraw_edges()
        
    def _on_reset_button_callback(self):
        print("Reset button pressed")
        dpg.delete_item("__shortest_paths_group") 
        dpg.configure_item(item="__shortest_path_combo_from", items=[], default_value="")
        dpg.configure_item(item="__shortest_path_combo_to", items=[], default_value="")
        
        # Stop Discovery Process
        self.discover_handler.stop_topology_analysis()
        
        dpg.delete_item("__stop_topology_analysis_button")
        dpg.configure_item(item ="__start_stop_topology_analysis_button", label="START Topology Analysis", 
                           callback=self._on_start, tag="__start_topology_analysis_button", parent="__topology_analysis_window")        
        # All other analysis only available after topology analysis
        dpg.configure_item(item="__analysis_menu", enabled=True)
        
        self.reset_callback()