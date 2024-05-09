from network.mesh_communication import MeshCommunicationService
from threading import Thread
from data.data_service import DataService
from gui.canvas_manager import CanvasManager
from config import MDR_FILE_PATH, MDR_DEBUG_FILE_PATH
from typing import List, Dict, Tuple
import csv
import os
import time

class MDRService:
    def __init__(self, mdr_callback) -> None:
        
        self.mdr_stop = False               # Stop the MDR thread
        self.mdr_callback = mdr_callback    # MDR callback to update MDR Bar Plot
        self.time_before = 0
        self.mdr_results = []               # MDR results
        self.rx_thread = None
        self.site = ""
        self.node_neighbor_map = None
        self.source_mac = ""
        self.destination_mac = ""
        self.consecutive_runs = 0
        
    def start_analysis(self, source_mac: str, destination_mac: str, site_name: str, node_neighbor_map: Dict) -> None:
        """
        Starts the analysis process.

        This function enables the radio communication service and initializes the necessary variables for the analysis. 
        It then creates a new thread to handle the receiving of packets in the background.
        """
        MeshCommunicationService().enable_radio()
        
        self.node_neighbor_map = node_neighbor_map
        print(f"Node neighbor map: {self.node_neighbor_map}")
        self.mdr_stop = False
        self.source_mac = source_mac
        self.destination_mac = destination_mac
        self.site = site_name
        self.consecutive_runs += 1
        
        DataService().clean_mdr_data()
        # Thread for receiving 
        self.rx_thread = Thread(target=self._rx_packet_thread, daemon=True)
        self.rx_thread.start()

    def stop_analysis(self) -> None:
        """ Stops the analysis by setting the `mdr_stop` flag to True. """
        self.mdr_stop = True
        self.rx_thread.join()
        
    def get_mac_label_map(self) -> dict:
        """
        Retrieves the MAC label map from the DataService.

        :return: A dictionary containing the MAC labels as keys and their corresponding values.
        :rtype: dict
        """
        return DataService().get_mac_label_map()
        
    def _rx_packet_thread(self):
        """Receives packets and logs them for MDR analysis, performing periodic data processing."""
        MeshCommunicationService().clear_buffers()
        
        self._prepare_logging_environment()
        
        self.time_before = time.time()
        
        while not self.mdr_stop:
            
            self._perform_periodic_processing(self.time_before)
            
            received_packet, metadata = MeshCommunicationService().receive_mesh_packet()
            
            if not received_packet or not metadata:
                continue
            
            log_data = self._parse_packet_data(metadata, received_packet)
            self._log_packet_data(MDR_FILE_PATH, log_data)
            self._log_packet_data(MDR_DEBUG_FILE_PATH, log_data)
            
        # Perform last processing after the loop ends
        Thread(target=self._data_processing_thread, daemon=True).start()
            
        MeshCommunicationService().disable_radio()
        
    def _data_processing_thread(self) -> None:
        """ Executes the data processing thread for the MDR (Packet Delivery Ratio)."""
        print("Data processing MDR started")
        
        time_before = time.time()
        
        # Get the directory of the current script
        current_script_dir = os.path.dirname(__file__)
        csv_file_path = os.path.join(current_script_dir, '..', MDR_FILE_PATH)
        
        new_results = DataService().data_processing_mdr(self.source_mac, self.destination_mac,
                                                        csv_file_path, self.site, self.node_neighbor_map)
        print(new_results)
                
        self.mdr_callback(new_results, DataService().get_mac_label_map(), self.consecutive_runs)
        
        print(f"MDR processing took {time.time() - time_before} seconds")
    
        
    def _prepare_logging_environment(self):
        """Prepares logging files and directories."""
        os.makedirs('.results', exist_ok=True)
        header = ['Timestamp', 'MAC', 'Command', 'Flags', 'Index', 'Payload', 'Version', 'Channel']
        self._initialize_log_file(MDR_FILE_PATH, header)
        self._initialize_log_file(MDR_DEBUG_FILE_PATH, header)
            
    def _perform_periodic_processing(self, time_before):
        """Performs data processing periodically."""
        if time.time() - time_before > 2:
            Thread(target=self._data_processing_thread, daemon=True).start()
            self.time_before = time.time()
    
    @staticmethod
    def _initialize_log_file(file_path, header):
        """Initializes a log file with a given header."""
        with open(file_path, 'w', newline='') as file:
            csv.writer(file).writerow(header)
    
    @staticmethod
    def _log_packet_data(file_path, data):
        """Logs packet data to the specified file."""
        with open(file_path, 'a', newline='') as file:
            csv.writer(file).writerow(data)
    
    @staticmethod
    def delete_lines_preserving_header(file_path: str, lines_to_preserve=5000, threshold=10000) -> None:
        # Check if the file meets the condition for line deletion
        with open(file_path, 'r') as file:
            for i, _ in enumerate(file):
                if i >= threshold - 1:  # Zero-based index, threshold is the total count including the header
                    break
            else:
                # File has fewer than threshold lines, no action needed
                return
        
        # File meets the condition, proceed with deleting lines while preserving the header
        temp_file_path = file_path + '.tmp'
        with open(file_path, 'r') as file, open(temp_file_path, 'w', newline='') as temp_file:
            for i, line in enumerate(file):
                # Always write the header row; then skip lines until the preserve threshold is reached
                if i == 0 or i >= lines_to_preserve:
                    temp_file.write(line)
        
        # Replace the original file with the modified temporary file
        os.replace(temp_file_path, file_path)
        
