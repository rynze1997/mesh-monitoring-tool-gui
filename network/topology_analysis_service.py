from threading import Thread
from network.mesh_communication import MeshCommunicationService
from data.data_service import DataService
from gui.canvas_manager import CanvasManager
from common import prepare_logging_environment, delete_lines_preserving_header, parse_packet_data
from common import log_packet_data
from config import TOPOLOGY_ANALYSIS_FILE_PATH, TOPOLOGY_ANALYSIS_UPDATE_INTERVAL_SECONDS
from config import TOPOLOGY_ANALYSIS_TX_PERIOD_MS, TOPOLOGY_ANALYSIS_STIMULATION_COMMAND, GET_FLAG
from typing import List
import time
import os
import json

class TopologyAnalysisService:
    def __init__(self):
        self.stop = False
        self.site_name = ""
        self.rx_thread = None
        self.tx_thread = None
        
    def start_topology_analysis(self, selected_site: str) -> None:
        MeshCommunicationService().enable_radio()

        self.site_name = selected_site
        self.stop = False
        
        # Find all indices for the selected network site to stimulate each individual node
        indices = self.find_indices(selected_site)
        print(indices)
        
        # Thread for receiving 
        self.rx_thread = Thread(target=self._rx_packet_thread, daemon=True)
        self.rx_thread.start()
        
        # Thread for transmitting
        self.tx_thread = Thread(target=self._tx_packet_thread, args=(indices,), daemon=True)
        self.tx_thread.start()

    def stop_topology_analysis(self) -> None:
        self.stop = True
        self.rx_thread.join()
        self.tx_thread.join()
        
    def get_mac_label_map(self):
        return DataService().get_mac_label_map()
         
    def _tx_packet_thread(self, indices: List) -> None:
        ''' Send GET commands to each node index in the network and listen for responses. '''
        while not self.stop:
            for index in indices:
                MeshCommunicationService().send_mesh_command(GET_FLAG, TOPOLOGY_ANALYSIS_STIMULATION_COMMAND, b"", index)
                time.sleep(TOPOLOGY_ANALYSIS_TX_PERIOD_MS / 1000)
                    
    def _rx_packet_thread(self) -> None:
        """ This function is the thread responsible for receiving packets and logging them for topology analysis."""

        # Empty Serial Buffers before starting
        MeshCommunicationService().clear_buffers()
        prepare_logging_environment(TOPOLOGY_ANALYSIS_FILE_PATH)
        time_before = time.time()
        
        while not self.stop:
            # Do topology analysis once a second
            if time.time() - time_before > TOPOLOGY_ANALYSIS_UPDATE_INTERVAL_SECONDS:
                delete_lines_preserving_header(TOPOLOGY_ANALYSIS_FILE_PATH, 
                                               lines_to_preserve=50000, threshold=100000)
                    
                processing_thread = Thread(target=self._data_processing_thread, daemon=True)
                processing_thread.start()
                time_before = time.time()  
                
            received_packet, metadata = MeshCommunicationService().receive_mesh_packet()
            
            if not received_packet or not metadata:
                continue
            
            log_data = parse_packet_data(metadata, received_packet)
            log_packet_data(TOPOLOGY_ANALYSIS_FILE_PATH, log_data)
            
        MeshCommunicationService().disable_radio()
    
    def _data_processing_thread(self) -> None:
        print("Data processing RTT started")
        time_before = time.time()
        
        unique_connections = DataService().data_processing_find_connections(TOPOLOGY_ANALYSIS_FILE_PATH, self.site_name)
        mac_label_map = DataService().get_mac_label_map()
        print(unique_connections)
        print(mac_label_map)
        
        if len(unique_connections) > 0:
            CanvasManager().plot_data(unique_connections, mac_label_map)
            
        print(f"Data processing Topology finished in {time.time() - time_before} seconds")
            
    @staticmethod
    def find_indices(site: str) -> List:
        # Construct the file path
        file_path = os.path.join("./.auth", f"{site}.json")

        # Open the file and read the last two lines
        with open(file_path, 'r') as file:
            data = json.load(file)
            
        # Extracting deviceAddress and rx_index for each device, if available
        device_addresses_and_rx_indices = [(device["deviceAddress"], device.get("rx_index", None)) for device in data["devices"].values()]

        # Putting all deviceAddress and rx_index values, including None for missing rx_index, into a list
        all_values_list = [value for pair in device_addresses_and_rx_indices for value in pair]
        
        # Removing all occurrences of None from the list
        cleaned_values_list = [value for value in all_values_list if value is not None]

        return cleaned_values_list
        
    
