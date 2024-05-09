
import dearpygui.dearpygui as dpg
from typing import List
import os
from network.mesh_communication import MeshCommunicationService
from config import WINDOW_SIZE
import json

class LogInWindowManager:
    def __init__(self):
        self.successful_login_callback = None
    def setup_login_window(self, successful_login_callback: callable) -> None:
        
        self.successful_login_callback = successful_login_callback 
        
        with dpg.window(label="Log-in", tag="log_in_window", width=WINDOW_SIZE[0] - 1200, height=WINDOW_SIZE[1] - 550, show=True):
            dpg.add_text("Please select a mesh site to monitor:")
            
            # Find all available sites and add them to the GUI dropdown
            sites = self.get_sites()
            items = sites if sites else ["No sites found, authenticate!"]
            dpg.add_combo(label ="", items=items, tag="sites")
            
            dpg.add_text("Choose what you want to do:")        
            with dpg.group(horizontal=True, tag="action_group"):
                dpg.add_button(label="Monitoring", tag="monitoring_button", callback=self._on_monitoring_button)
                dpg.add_button(label="Console", tag="console_button", callback=self._on_console_button)
    
    @staticmethod      
    def get_sites() -> List:
        """ Find all available sites, remove .json extension and return the list of sites """
        try:
            return [os.path.splitext(filename)[0] for filename in os.listdir("./.auth")]
        except:
            return []
        
    # Function to get hex keys from the file
    @staticmethod
    def get_hex_keys(selected_site: str) -> List:
        """
        A static method that retrieves the access and crypto keys for a selected site.

        Parameters:
            selected_site (str): The name of the selected site.

        Returns:
            List: A list containing the access address and crypto key.
        """
        hex_keys = []
        # Construct the file path
        file_path = os.path.join("./.auth", f"{selected_site}.json")
        # Open the file and read the first two lines
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        access_addr = data["accessAddr"]
        crypto_key = data["cryptoKey"]
        hex_keys = [access_addr, crypto_key]
        
        return hex_keys

    # Function to handle the monitoring button click
    def _on_monitoring_button(self, sender: str) -> None:
        
        # Get the selected site
        selected_site = dpg.get_value("sites")
        
        # If no site is selected, return
        if selected_site in ["No sites found, authenticate!", ""]:
            dpg.delete_item("login_error_text")
            dpg.add_text("Please select a site to monitor!", parent="log_in_window", color=(255, 0, 0), tag="login_error_text")
            return
        
        # If the site is found, initiate the USB connection
        if MeshCommunicationService().initiate_usb_connection() == False:
            dpg.delete_item("login_error_text")
            dpg.add_text("Monitoring tool was not found!", parent="log_in_window", color=(255, 0, 0), tag="login_error_text")
            return
        
        # Get the hex keys for the selected site
        hex_keys = self.get_hex_keys(selected_site)
        # Set the crypto keys for the mesh
        MeshCommunicationService().send_access_keys(hex_keys)
        
        self.successful_login_callback(sender, site_name=selected_site)
        
        # Hide the login window
        dpg.delete_item("log_in_window")

    # Function to handle the console button click
    def _on_console_button(self, sender, app_data) -> None:
        pass
