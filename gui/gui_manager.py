# gui/gui_manager.py
import dearpygui.dearpygui as dpg
from config import WINDOW_TITLE, WINDOW_SIZE
from gui.auth_tab import create_authentication_tab
from gui.topology_analysis_interface import topologyAnalysisInterfaceManager
from gui.mdr_tab import MDRTab
from gui.login_window import LogInWindowManager
from gui.canvas_manager import CanvasManager
from data.data_service import DataService
from .latency_window import LatencyTab
import dearpygui.demo as demo

class GuiManager:
    def __init__(self):
        self.setup_gui()
        self.selected_site = ""

    def setup_gui(self):
        dpg.create_context()
        LogInWindowManager().setup_login_window(self._on_successful_login_callback)
        
        dpg.create_viewport(title=WINDOW_TITLE, width=WINDOW_SIZE[0], height=WINDOW_SIZE[1])
        with dpg.viewport_menu_bar(tag="__menu_bar"):
                # Authentication
                create_authentication_tab()
        demo.show_demo()
        dpg.setup_dearpygui()

    def run(self):
        dpg.show_viewport()
        dpg.start_dearpygui()
        dpg.destroy_context()
    
    def _on_successful_login_callback(self, sender: str, site_name: str):
        # Setup the canvas window if login was successful
        # It is possible to use the tool as console too, therefore two options are available
        if sender == "monitoring_button":
            DataService().data_service_register_site_information(site_name)
            CanvasManager().create_canvas_window()
            topologyAnalysisInterfaceManager().create_topology_analysis_button(site_name, self._reset_callback)
            self.selected_site = site_name
            with dpg.menu(label="Analysis", tag="__analysis_menu", parent="__menu_bar", enabled=False):
                # Message-Delivery Rate (MDR)
                mdr_tab = MDRTab()
                mdr_tab.mdr_tab_create(self.selected_site)
                # Latency
                LatencyTab().create_latency_tab(site = self.selected_site)
        elif sender == "console_button":
            pass
        dpg.add_menu_item(label="Log-out", callback=self._logout, tag="__log_out_menu_button", parent="__menu_bar", indent=WINDOW_SIZE[0])
        
    def _reset_callback(self):
        CanvasManager().reset_graph()
        DataService().reset()
        MDRTab().close_mdr_window()
        LatencyTab().close_latency_window()
        dpg.configure_item(item="__analysis_menu", enabled=False)
        
    def _logout(self):
        self._reset_callback()
        MDRTab().delete_tab()
        LatencyTab().delete_tab()
        CanvasManager().close_canvas_window()
        dpg.delete_item("__log_out_menu_button")
        dpg.delete_item("__analysis_menu")
        LogInWindowManager().setup_login_window(self._on_successful_login_callback)
        
        
    