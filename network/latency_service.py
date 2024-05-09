from network.mesh_communication import MeshCommunicationService
from threading import Thread
from data.data_service import DataService
from config import LATENCY_DATA_POINT_AMOUNT, LATENCY_DEBUG_FILE_PATH, LATENCY_FILE_PATH, LATENCY_ANALYSIS_UPDATE_INTERVAL_SECONDS
from typing import List, Dict, Tuple
from math import prod, exp
import csv
import os
import time
import json

# Plibble
from plibble.mesh import SetupMesh

MESH_COMMAND_RBC_CHANNEL_CONFIG = 0x0056
RTR_FLAG = (0x02)

class LatencyService:
    def __init__(self, analysis_complete_callback: callable) -> None:
        self.latency_analysis_stop = False
        self.source_mac = ""
        self.destination_mac = ""
        self.latency_list = []
        self.analysis_complete_callback = analysis_complete_callback
        self.latency_callback = None
        self.rx_thread = None
        self.gatt_thread = None
        self.site = ""
        self.node_neighbor_map = None
        self.time_before = 0
        self.consecutive_runs = 0
        
    def start_latency_analysis(self, source_mac, destination_mac, latency_callback, site, manual_mode, node_neighbor_map: Dict):
        
        self.source_mac = source_mac
        self.destination_mac = destination_mac
        self.latency_analysis_stop = False
        self.latency_list = []
        self.latency_callback = latency_callback
        self.site = site
        self.node_neighbor_map = node_neighbor_map
        self.consecutive_runs += 1
        
        MeshCommunicationService().enable_radio()    
        
        # Thread for receiving 
        self.rx_thread = Thread(target=self.rx_packet_thread, daemon=True)
        self.rx_thread.start()
        
        if not manual_mode:
            self.gatt_thread = Thread(target=self._gatt_thread, daemon=True, args=(source_mac, destination_mac))
            self.gatt_thread.start()
        
    def stop_latency_analysis(self):
        """ Stop the latency analysis process by setting a flag to True and joining threads. """
        self.latency_analysis_stop = True
        if self.gatt_thread:
            self.gatt_thread.join()
        self.rx_thread.join()
        
    def latency_service_get_mac_label_map(self) -> dict:
        """ Returns a dictionary containing the mapping of MAC addresses to labels. """
        return DataService().get_mac_label_map()
            
    def rx_packet_thread(self):
        
        self._prepare_logging_environment()
            
        self.time_before = time.time()
        
        
        while not self.latency_analysis_stop:
            
            self._perform_periodic_processing(self.time_before)
            
            received_packet, metadata = MeshCommunicationService().receive_mesh_packet()
            
            if not received_packet or not metadata:
                continue
            
            log_data = self._parse_packet_data(metadata, received_packet)
            self._log_packet_data(LATENCY_FILE_PATH, log_data)
            self._log_packet_data(LATENCY_DEBUG_FILE_PATH, log_data)
            
        MeshCommunicationService().disable_radio()
    
    def _gatt_thread(self, source_mac, destination_mac):
        
        site_data = self._load_site_data(self.site)
        if not site_data:
            # TODO: Add error text in Window
            return
        
        crypto_key, destination_index = self._parse_site_data(site_data, destination_mac)
        
        mesh, ble = SetupMesh(source_mac, crypto_key)

        if mesh is None:
            return
        
        try:
            while not self.latency_analysis_stop:
                mesh.Get(index = destination_index, command=MESH_COMMAND_RBC_CHANNEL_CONFIG, payload=[])

            ble.Disconnect()
            ble.Stop()
        except KeyboardInterrupt:
            self.latency_analysis_stop = True
            ble.Disconnect()
            ble.Stop()
            
    def _data_processing_thread(self):
        print("Data processing started")
        time_before = time.time()
        
        # Construct path to the file for writing the results to
        csv_file_path = os.path.join(os.path.dirname(__file__), '..', '', LATENCY_FILE_PATH)
        
        # Perform latency analysis
        self.latency_list, avg_latency, max_latency = DataService().calculate_latency(self.source_mac, self.destination_mac,
                                                                                    csv_file_path, self.site, self.node_neighbor_map)
        # Update Latency Plot only when enough data points are available
        if len(self.latency_list) > 0:
            self.latency_callback(self.latency_list, avg_latency, max_latency, self.consecutive_runs)
        
        # Stop the analysis when enough data points are available
        if len(self.latency_list) > LATENCY_DATA_POINT_AMOUNT:
            self.latency_analysis_stop = True
            self.analysis_complete_callback()
            if self.gatt_thread:
                self.gatt_thread.join()
            self.rx_thread.join()
            
        print(f"Data processing finished in {time.time() - time_before} seconds")
        print(f"Data points: {len(self.latency_list)}")
        
    def _prepare_logging_environment(self):
        """Prepares logging files and directories."""
        os.makedirs('.results', exist_ok=True)
        header = ['Timestamp', 'MAC', 'Command', 'Flags', 'Index', 'Payload', 'Version']
        self._initialize_log_file(LATENCY_FILE_PATH, header)
        self._initialize_log_file(LATENCY_DEBUG_FILE_PATH, header)
        
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
    def _parse_packet_data(metadata, received_packet):
        """Parses packet data for logging."""
        packet_time = f"[{metadata['MIN']}.{metadata['SEC']}.{metadata['MS']}.{metadata['US']}]"
        incoming_mac = ":".join(f"{b:02X}" for b in metadata['MAC'][0:7][::-1])
        incoming_command = f"[{metadata['CMD'][0]:02X}{metadata['CMD'][1]:02X}]"
        incoming_handle = f"{metadata['HDL']}"
        incoming_version = f"{metadata['VER']}"
        incoming_payload = "".join(f"[{b:02X}]" for b in received_packet[21:21+metadata['LEN']-6])
        flags = received_packet[18]
        flag_dict = {0x01: "[ACK]", 0x10: "[DR]", 0x02: "[GET]", 0x04: "[NA]", 0x00: "[SET]", 0x03: "[RESP]"}
        incoming_flags = flag_dict.get(flags, "[Unknown]")
        return [packet_time, incoming_mac, incoming_command, incoming_flags, incoming_handle, incoming_payload, incoming_version]
        
    def _perform_periodic_processing(self, time_before):
        """Performs data processing periodically."""
        if time.time() - time_before > LATENCY_ANALYSIS_UPDATE_INTERVAL_SECONDS:
            Thread(target=self._data_processing_thread, daemon=True).start()
            self.time_before = time.time()
            
    def _parse_site_data(self, site_data, destination_mac):
        """ Parse site data and return crypto key and destination index. """
        
        # Read cryptoKey from the json file and convert each hex value to a list of integers
        crypto_key = [int(hex_val, 16) for hex_val in site_data['cryptoKey'].split()]
        # MAC here is of form xx:xx:xx
        destination_mac_cleaned = destination_mac.replace(":", "")
        destination_index = site_data['devices'][destination_mac_cleaned]['deviceAddress']
        return crypto_key, destination_index
            
    def _load_site_data(self, site: str):
        """ Load site data from a JSON file for a given site name. """
        try:
            with open(f'.auth/{site}.json') as file:
                return json.load(file)
        except IOError:
            return None


    def calculate_theoretical_latency(self, num_of_neighbors_per_hop, shortest_path):
        I_min = 32
        # Maximum number of rebroadcasts
        num_rebroadcasts = 7
        
        success_probabilities = [1 - 10/152, 1 - 10/152, 1 - 10/152, 1 - 10/152, 1 - 10/152, 1 - 10/152, 1 - 10/152]
        fail_probabilities = list(map(lambda x: 1-x, success_probabilities))
    
        avg_latency = 0
        num_hops = len(shortest_path) - 2

        for hop in range(num_hops):
            # Number of neighbors for current hop
            max_periods = []
            n = num_of_neighbors_per_hop[shortest_path[hop]]
            for rebroadcast in range(num_rebroadcasts):
                if rebroadcast == 0:
                    avg_latency += success_probabilities[rebroadcast] * (2**rebroadcast*I_min*((1/2)+(1/(2*(n+1)))))
                    max_periods.append(2**rebroadcast*I_min)

                else:
                    avg_latency += success_probabilities[rebroadcast] * (2**rebroadcast*I_min*((1/2)+(1/(2*(n+1)))) + sum(max_periods))*prod(fail_probabilities[:rebroadcast])
                    max_periods.append(2**rebroadcast*I_min)
    

        return avg_latency