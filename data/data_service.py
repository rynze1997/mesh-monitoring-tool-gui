import pandas as pd
import string
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from config import NETWORK_TOPOLOGY_THRESHOLD, TRICKLE_I_MIN_MS, TRICKLE_REDUNDANCY_CONSTANT
import json

class DataService:
    _instance = None  # Class-level attribute to store the singleton instance
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DataService, cls).__new__(cls)
            # Initialize the instance once
            cls._instance.init_once()
        return cls._instance

    def init_once(self):
        self.connections = []
        self.mac_label_map = {}
        self.all_unique_macs = set()
        self.mdr_results = {}
        self.site_info = None
        
    def reset(self) -> None:
        self.connections = []
        self.mac_label_map = {}
        self.all_unique_macs = set()
        self.mdr_results = {}
        
    def get_connections(self) -> List[Tuple[str, str]]:
        return self.connections
    
    def get_mac_label_map(self) -> Dict:
        return self.mac_label_map
    
    def data_service_register_site_information(self, site_name: str) -> None:
        """ Load site data from a JSON file for a given site name. """
        with open(f'.auth/{site_name}.json') as file:
            self.site_info = json.load(file)

    def data_processing_find_connections(self, file_path: str, site_name: str) -> List[Tuple[str, str]]:
        
        """
        Processes discovery data to find connections between nodes and map the network topology.

        1. Load the mesh packet data from the specified CSV file into a structured format (DataFrame).
        2. Parse the timestamps in the data to a datetime format.
        3. Find all unique MAC addresses in the data and add them to the set of all unique MAC addresses if they are not already present.
        4. Load the site data from the JSON file for the specified site name. This data holds information about the devices in the network,
            their MAC addresses and indices, and other relevant information.
        5. From the loaded data, filter only the RESPONSE messages. Response messages are ones that we want to analyze.
            The tool sends GET messages to each index and the nodes generate RESPONSE messages to those GET messages.
            Other nodes that hear the RESPONSE message will start to rebroadcast it. If the rebroadcast occurs within 32ms (Trickle configuration), 
            then there is a direct connection between the two nodes.
        6. For each unique MAC address in the loaded dataset, find all new version packets that originate from the source MAC address.
        7. To avoid false positives when it comes to finding packets that originate from the source MAC, find the index of the source MAC address
            in the site data and filter the packets to include only those that have the same index as the source MAC address, because a node
            sends response messages on its own index.
                * It can happen that the tool miss the original message from some other node, and if the current MAC address is the one that rebroadcasts
                that message first, the algorithm will indentify that MAC address as the source.
        8. Find potential connection by merging the source messages with all other messages in the data that have the same index, payload, and version to
            identify which other nodes has sent the same message as the source node.
        9. Calculate the time difference between the source message and its message pair from step before.
        10. Filter out all pairs whose time diffrenece is larger than 32ms. This means that the message was not rebroadcasted within the first trickle period.
        11. Filter out all pairs whose time difference is less than 16ms. This means that the tool has not heard the original message but has heard a rebroadcast of it.
            First trickle period is 16 to 32ms, which means that no node should rebroadcast the message before 16ms.
        12. Count how many times a message is rebroadcasted by other nodes. If a message is rebroadcasted at least NETWORK_TOPOLOGY_THRESHOLD times, then there is a connection.
            A threshold is set to avoid false positives.
        """
    
        # Load the discovery data from the specified CSV file into a structured format (DataFrame).
        data = self.load_data(file_path)
        
        # Parse Timestamps
        data['Timestamp'] = data['Timestamp'].apply(self.get_packet_timestamp)

        # Find all unique MACs and add them to all_unique_macs
        self.all_unique_macs.update(set(data['MAC'].unique()))
        
        # Open the text file and read lines
        with open(f'.auth/{site_name}.json', 'r') as file:
            site_data = json.load(file)

        site_devices = site_data['devices']
        
        # Filter only RESPONSE messages
        data_resp = data[data['Flags'] == '[RESP]']
       
        for mac_address in self.all_unique_macs:
            # Convert the MAC address from the user-friendly format to the format used in the data
            user_mac = mac_address.replace(":", "")
            
            # Find all new version packets that originates from the source MAC
            source_packets = self.get_first_occurrences(data_resp, mac_address)
            
            # Can happen that a node is detected and is not in data
            try:
                # Get the index for the specified MAC address
                mac_index = site_devices[user_mac]['deviceAddress']
            except:
                mac_index = None
                
            if mac_index is not None:
                source_packets = source_packets[source_packets['Index'] == mac_index]
            
            
            if source_packets.empty:
                continue

            # Filter for potential connections. There is a potential connection with another node if the Index, Payload, and Version 
            # are the same as the source. We do this by merging the source_packets DataFrame with the data DataFrame.
            potential_connections = data.merge(source_packets, on=['Index', 'Payload', 'Version'], suffixes=('', '_source'))
            # Filter out potential connections that originate from the same MAC address
            potential_connections = potential_connections[potential_connections['MAC'] != mac_address]

            # Calculate time difference between the source and potential connection
            potential_connections['time_diff'] = (potential_connections['Timestamp'] - potential_connections['Timestamp_source']).dt.total_seconds().abs()
            # MAC address is directly connected to another node if the time difference is less than 32 milliseconds
            directly_connected = potential_connections[potential_connections['time_diff'] < 0.032] # 32 milliseconds
            
            # Find versions where there is at least one packet with a time_diff less than 16. This means that the tool has not received original packet. Received packet
            # in this case is trickle.
            versions_to_remove = directly_connected[directly_connected['time_diff'] < 0.016]['Version'].unique()

            # Remove all rows with those versions
            directly_connected = directly_connected[~directly_connected['Version'].isin(versions_to_remove)]
            

            # Count occurrences of each MAC address in directly_connected and filter out those with less than 5 occurrences.
            # It can happen that the tool does not hear original source MAC message and will translate what it hears to a connection that
            # does not exist. This is why we filter out MACs with less than 5 occurrences.
            mac_occurrences = directly_connected['MAC'].value_counts()
            mac_occurrences = mac_occurrences[mac_occurrences >= NETWORK_TOPOLOGY_THRESHOLD]

            # Use the filtered mac_occurrences index for further processing to ensure only MACs with 5 or more occurrences are considered
            filtered_macs = mac_occurrences.index.tolist()

            # Now, only consider MAC addresses that are in filtered_macs for connection analysis
            directly_connected_filtered = directly_connected[directly_connected['MAC'].isin(filtered_macs)]

            # Proceed with connection analysis using directly_connected_filtered
            # For each MAC in filtered_macs, process their connections
            new_connections = set(directly_connected_filtered['MAC'].unique())
            for conn_mac in new_connections:
                self._add_connection(mac_address, conn_mac)

            # After processing all direct connections, add connections to '0' if no other connections are found for a MAC
            for mac_address in self.all_unique_macs:
                if not any(mac_address in connection for connection in self.connections):
                    self.connections.append((mac_address, '0'))
            
        # Assign letters to each unique MAC address
        self._assign_letter_to_each_unique_mac(self.connections)
            
            
        return self.connections
    
    @staticmethod
    def load_data(filepath: str) -> pd.DataFrame:
        """Load the CSV data into a pandas DataFrame."""
        data = pd.read_csv(filepath)
        return data
    
    def _assign_letter_to_each_unique_mac(self, connections: List[Tuple[str, str]]) -> None:
        """
            Find all unique MAC addresses and assign a unique letter to each one.
            
            Parameters:
            connections (List[Tuple[str, str]]): A list of tuples representing connections.
            
            Returns:
            None
        """
        unique_macs = set()
        for connection in connections:
            unique_macs.update(connection)
        
        # Create iterator over 1 to 500
        numbers = iter(range(1, 501))  # Creates an iterator over 1 to 500
        for mac in unique_macs:
            if mac == "0":
                continue
            # Find MAC in site data
            try:
                node_name = self.site_info['devices'][mac.replace(":", "")]['title']
            except: 
                node_name = "UNIDENTIFIED" # Not in site data
            self.mac_label_map[mac] = {'number': next(numbers), 'title': node_name}
            
    def _remove_zero_connections(self, mac_address: str) -> None:
        """
        Removes the connections with '0' from the list of connections for the given MAC address.
        Args:
            mac_address (str): The MAC address for which connections need to be removed.
        Returns:
            None
        """
        self.connections = [conn for conn in self.connections if not (mac_address == conn[0] and '0' == conn[1]) and not (mac_address == conn[1] and '0' == conn[0])]
        
    
    def _add_connection(self, mac1: str, mac2: str) -> None:
        """
        Adds a connection between two MAC addresses to the connections list.

        Remove any existing connections to '0' for both MAC addresses, and then add the new connection to the connections list
        if it does not already exist.

        Args:
            mac1 (str): The first MAC address.
            mac2 (str): The second MAC address.

        Returns:
            None
        """
        if mac1 != '0' and mac2 != '0':
            ordered_connection = tuple(sorted([mac1, mac2]))
            # Remove existing connections to '0' for both MAC addresses
            self._remove_zero_connections(ordered_connection[0])
            self._remove_zero_connections(ordered_connection[1])
            # Add the new connection if it does not already exist
            if ordered_connection not in self.connections:
                self.connections.append(ordered_connection)
                
    @staticmethod
    def get_packet_timestamp(packet_timestamp: str):
        # Remove brackets and split by the dot
        parts = packet_timestamp.strip('[]').split('.')
        if len(parts) != 4:
            print(f"Invalid timestamp format: {packet_timestamp}")
            return None
        
        try:
            # Extract each part of the timestamp
            minutes, seconds, milliseconds, microseconds = [int(part) for part in parts]
            
            # Construct a timedelta since the minimum component we have is minutes
            # This timedelta represents the duration since the start of the hour
            delta = timedelta(minutes=minutes, seconds=seconds, milliseconds=milliseconds, microseconds=microseconds)
            
            # Construct a base datetime object (you might adjust this according to your needs)
            # Here we use a base date of 1st January 1970 with the hour set to 0
            base_datetime = datetime(1970, 1, 1, hour=0)
            
            # Add the timedelta to the base datetime
            final_datetime = base_datetime + delta
            return final_datetime
        except ValueError as e:
            print(f"Error parsing timestamp: {e}")
            return None
        
    @staticmethod
    def get_first_occurrences(df, mac_address):
        """
        Find which packets are generated by the given MAC address.
        """

        # Group the DataFrame by 'Version', 'Index', and 'Payload' and get the first occurrence in each group
        copy_df = df.copy()
        copy_df['Payload'] = copy_df['Payload'].fillna('NoPayload')
        copy_df = copy_df.groupby(['Version', 'Index']).first().reset_index()
        
        # Filter the DataFrame to include only rows with the given MAC address
        copy_df = copy_df[copy_df['MAC'] == mac_address]

        # Convert the DataFrame to a list of Series and return it
        return copy_df
    
    def _load_site_data(self, site: str):
        """ Load site data from a JSON file for a given site name. """
        try:
            with open(f'.auth/{site}.json') as file:
                return json.load(file)
        except IOError:
            return None
        
    def clean_mdr_data(self):
        self.mdr_results = {}
        
    def data_processing_mdr(self, source_mac: str, destination_mac: str, file_path: str, site_name: str, node_neighbor_map: Dict) -> List[Dict]:

        # Load your dataset
        df = pd.read_csv(file_path)
        df['Timestamp'] = df['Timestamp'].apply(self.get_packet_timestamp)
        
        site_data = self._load_site_data(site_name)
        site_devices = site_data['devices']
        
        source_index = site_devices[source_mac.replace(":", "")]['deviceAddress']
        destination_index = site_devices[destination_mac.replace(":", "")]['deviceAddress']
        
        return [self.calculate_mdr(df, source_mac, destination_mac, source_index, destination_index, node_neighbor_map)]
    
    def calculate_mdr(self, df, source_mac, destination_mac, source_index, destination_index, node_neighbor_map):
        
        '''
        Done in two steps:
        # STEP 1 # 
            1. Find all messages that originates from the source
            2. Separate all SET, GET messages on destination Index
            3. Destination node will answer to SET and GET messages with incremented version. Pair all SET and GET packets with all observed acknowledgements.
            The acknowledgement does not have to come from the destination node itself. The tool can miss it. But if the destination node has received 
            the SET or GET message and acknowledged it (and the tool missed it), the acknowledgement message will be rebroadcasted by all other nodes.
            4. If a pair is found to the source message, then there is an acknowledgement. Otherwise not.
            
        # STEP 2 #
            1. Separate all messages that the source sent on its own index and that are not SET or GET.
            2. Find all messages sent by the destination node.
            3. Pair all source node messages with destination node messages. If a pair is found, then there is a direct acknowledgement.
               If not, then the destination node has not rebroadcasted the message or the tool has not heard it.
               A node does not rebroadcast a message if it does not receive it or if the same message is rebroadcasted by other neighbors at least 4 times 
               before the destination node itself should rebroadcast. This is due to Trickle algorithm redundancy constant.
               If the destination node has not rebroadcasted the source message and neighbors have rebroadcasted it at least 4 times, then it can be said
               with high probability that the destination node has received it but dropped it due to trickle redundancy.
            4. Isolate all unacknowledged messages
            5. Find all neighbors of the destination node
            6. Find all packets that the neighbors has sent
            7. From all neighbor packets, get only those that are the same as the unacknowledged messages
            8. Apply a 32ms (First trickle period) window to all neighbors packets from previous step and count how many times each packet is rebroadcasted
            9. If any of those packets are rebroadcasted at least 4 times in any of the 32ms window, it can be considered that the destination node has received that 
               message and dropped its rebroadcast.
        '''
        try:
            # Find all new version messages that originates from the source
            source_messages = self.get_first_occurrences(df, source_mac)
            
            # THROUGPUT Calculation
            throughput_df = source_messages['Timestamp']
            througput_df = throughput_df.sort_values()
            # Find newest and oldes value
            newest_packet = througput_df.iloc[0]
            oldest_packet = througput_df.iloc[-1]
            time_diff = (oldest_packet - newest_packet).total_seconds()
            throughput = len(source_messages) / time_diff
            
            ## STEP 1 ##
            # Isolate all SET and GET messages that originates from the source node
            source_set_and_get_messages = source_messages[((source_messages['Flags'] == '[SET]') | (source_messages['Flags'] == '[GET]')) & (source_messages['Index'] == destination_index)]
            
            # The destination must answer with new version messages if it receives a SET or a GET message from the source
            # To each SET and GET message that originates from the source, add a new column with the next version that corresponds to the version 
            # that the destination node must answer with
            source_set_and_get_messages = source_set_and_get_messages.copy()
            source_set_and_get_messages.loc[:, 'Next_Version'] = source_set_and_get_messages['Version'] + 1
            
            # Isolate all RESP and ACK from the dataframe before merging
            all_ack_and_resp_packets = df[((df['Flags'] == '[ACK]') | (df['Flags'] == '[RESP]'))]
            
            # If the destination node has received the SET or GET message by the source node, we can either catch the answer from the destination node itself
            # or from other nodes that has received the answer of the destination node and started re-broadcasting.
            # For this reason, we need to pair all SET and GET messages with all observed acknowledgements.
            merged_set_and_get_packets = pd.merge(source_set_and_get_messages, all_ack_and_resp_packets, 
                                        left_on=['Index', 'Next_Version'], 
                                        right_on=['Index', 'Version'], how='left', indicator=True)  # indicator adds _merge column
            # If a source message is rebroadcasted many times by many nodes it will be merged with all of them. We need only one of them to
            # understand if the destination node has received the message or not. So, we need to drop duplicates based on 'Index' and 'Version'
            merged_set_and_get_messages = merged_set_and_get_packets.drop_duplicates(subset=['Index', 'Version_x'])
            
            # From the merge, find all acknowledged packets and unacknowledged packets
            acknowledged_merge_set_and_get_messages = merged_set_and_get_messages[merged_set_and_get_messages['_merge'] == 'both']
            
            unacknowledged_merge_set_and_get_messages = merged_set_and_get_messages[merged_set_and_get_messages['_merge'] == 'left_only']
            # Rename columns for easier manipulation
            unacknowledged_merge_set_and_get_messages = unacknowledged_merge_set_and_get_messages.copy()
            unacknowledged_merge_set_and_get_messages.rename(columns={'Payload_x': 'Payload', 'Version_x': 'Version'}, inplace=True)
            
            ## STEP 2 ## Other messages
            
            # Isolate all other messages that originates from the source and on its own index. All other messages are not relevant because they would be meant for other nodes
            # and not the destination node.
            other_messages = source_messages[(source_messages['Flags'] != '[SET]') & (source_messages['Flags'] != '[GET]') & (source_messages['Index'] == source_index)]
            
            # Find all messages that are sent from destination
            destination_messages = self.filter_packets_by_mac(df, destination_mac)
            
            # Pair all other messages with all observed acknowledgements from the destination node
            merged_other_messages = pd.merge(other_messages, destination_messages, 
                                        left_on=['Index', 'Version', 'Payload'], 
                                        right_on=['Index', 'Version', 'Payload'], how='left', indicator=True)
            # Find all acknowledged packets and unacknowledged packets
            acknowledged_other_messages = merged_other_messages[merged_other_messages['_merge'] == 'both']
            unacknowledged_other_messages = merged_other_messages[merged_other_messages['_merge'] == 'left_only']
            
            acks =  (len(acknowledged_merge_set_and_get_messages) + len(acknowledged_other_messages))
            total_messages = len(source_messages)
            
            # Find all destination node neighbors
            neighbors = node_neighbor_map[self.mac_label_map[destination_mac]['number']]
            
            # If there is no neighbors then there is nothing else to do. Return the mdr
            if not neighbors:
                return self.add_or_update_mdr_pair(source_mac, destination_mac, total_messages, acks, throughput)
            # Get MAC addresses of all neighbors
            neighbor_macs = [mac for mac, info in self.mac_label_map.items() if info['number'] in neighbors]
            
            # Get packets that belong to destination node neighbors
            neighbor_packets = df[df['MAC'].isin(neighbor_macs)]
            neighbor_packets = neighbor_packets.copy()
            neighbor_packets['Payload'] = neighbor_packets['Payload'].fillna('NoPayload')
            
            # From all neighbor packets, get only those that are the same as the unacknowledged messages
            criteria = unacknowledged_other_messages[['Version', 'Index', 'Payload']]
            neighbor_packets = neighbor_packets.merge(criteria, on=['Version', 'Index', 'Payload'], how='inner')
            
            # Apply rolling window of 32ms to all neighbor packets with unique version and index, and count how many times each packet is rebroadcasted
            neighbor_packets.reset_index(inplace=True)
            grouped_packets = neighbor_packets.groupby(['Index', 'Version'])
            rolling_window_result = grouped_packets.apply(lambda group: group.rolling(window=pd.Timedelta(TRICKLE_I_MIN_MS, 'ms'), on='Timestamp').count(), include_groups=False)
            
            # Get the maximum number of times each packet is rebroadcasted. Isolate those packets that are rebroadcasted more than 4 times. These are indirectly acknowledged.
            grouped_packets = rolling_window_result.groupby(['Index', 'Version'])
            max_rebroadcasts_per_group = pd.DataFrame(grouped_packets.apply(lambda group: group['index'].max()), columns=['Max'])
            indirect_acks = max_rebroadcasts_per_group[max_rebroadcasts_per_group['Max'] > TRICKLE_REDUNDANCY_CONSTANT]
            
            acks += len(indirect_acks)
            
            return self.add_or_update_mdr_pair(source_mac, destination_mac, total_messages, acks, throughput)
        except: 
            return self.add_or_update_mdr_pair(source_mac, destination_mac, 0, 0, 0)
    
    def add_or_update_mdr_pair(self, source, destination, source_messages, acks, throughput):
        key = f"{source}->{destination}"
        
        # If the pair is new, initialize its data
        if key not in self.mdr_results:
            self.mdr_results[key] = {
                "source": source,
                "destination": destination,
                "source_messages": source_messages,
                "acks": acks,
                "throughput": throughput if ((source_messages) > 10) else 0,
                "mdr": (acks / (source_messages) * 100) if ((source_messages) > 10) else None
            }
        elif (source_messages) > 10:
            # Update existing data
            entry = self.mdr_results[key]
            entry["source_messages"] = source_messages
            entry["acks"] = acks
            entry["throughput"] = throughput
            entry["mdr"] = (entry["acks"] / entry["source_messages"] * 100) if (entry["source_messages"] > 10) else None
            
        return self.mdr_results[key]
            
    @staticmethod
    def filter_packets_by_mac(df, mac_address):
        """
        Filter packets in the dataframe by MAC address, ensuring unique versions and payloads
        """
        return df[df['MAC'] == mac_address].drop_duplicates(subset=['Version', 'Payload', 'Index'])
    
    def calculate_latency(self, source_mac, destination_mac, file_path: str, site_name: str, node_neighbor_map: Dict):
        '''
        This function calculates Latency between two nodes. 
        Latency for a message is calculated from the time the message is transmitted on the air by the source node
        to the time any of the neighbors of the destination node rebroadcasts it.
        
            1. Find all messages that originates from the source
            2. Separate all SET, GET messages on destination Index
            3. Separate all messages that the source sent on its own index and that are not SET or GET.
            ** Messages from steps 2 and 3 are all messages that destination node should acknowledge or rebroadcast.
            ** Since we are calculating the latency up to the destination node, we are not looking for its own acknowledgements or rebroadcasts.
            ** We are looking for re-rebroadcasts of the source messages by the destination node neighbors.
            4. Find all neighbors of the destination node
            5. Find all packets that the neighbors has sent
            6. From all neighbor packets, get only those that are the same as source messages
            7. Pair all neighbor packets with their corresponding source message
            8. Drop duplicates with same MAC address. We are only interested in the first occurrence, which would be the
            soonest one.
            9. Calculate time difference between source messages and neighbor packets
            10. For each message, find the minimum and maximum time difference
            11. Calculate average latency and maximum latency
        '''
        print(f"Calculating RRT from {source_mac} to {destination_mac}")
        try:
            df = self.load_data(file_path)
            # Convert timestamps to a Pandas compatible format for easy time calculations
            df['Timestamp'] = df['Timestamp'].apply(self.get_packet_timestamp)
            
            site_data = self._load_site_data(site_name)
            site_devices = site_data['devices']
            
            source_index = site_devices[source_mac.replace(":", "")]['deviceAddress']
            destination_index = site_devices[destination_mac.replace(":", "")]['deviceAddress']
            
            
            # Find all new version packets that originates from the source MAC
            source_node_messages = self.get_first_occurrences(df, source_mac)
            
            # Find only SET, GET messages and all other messages that are sent on the source index. 
            # These are all messages that destination node should acknowledge or rebroadcast.
            source_node_set_get_messages = source_node_messages[((source_node_messages['Flags'] == '[SET]') | (source_node_messages['Flags'] == '[GET]')) & (source_node_messages['Index'] == destination_index)]
            source_node_other_messages = source_node_messages[(source_node_messages['Flags'] != '[SET]') & (source_node_messages['Flags'] != '[GET]') & (source_node_messages['Index'] == source_index)]
            # Join all source node messages together
            all_source_node_messages = pd.concat([source_node_set_get_messages, source_node_other_messages])
            
            # Find all destination node neighbors
            destination_node_neighbors = node_neighbor_map[self.mac_label_map[destination_mac]['number']]
            # Get MAC addresses of all neighbors
            destination_neighbor_macs = [mac for mac, info in self.mac_label_map.items() if info['number'] in destination_node_neighbors]
            
            # Get packets that belong to destination node neighbors
            neighbor_packets = df[df['MAC'].isin(destination_neighbor_macs)]
            neighbor_packets = neighbor_packets.copy()
            neighbor_packets['Payload'] = neighbor_packets['Payload'].fillna('NoPayload')
            
            # From all neighbor packets, get only those that are the same as source messages
            criteria = all_source_node_messages[['Version', 'Index', 'Payload']]
            neighbor_packets = neighbor_packets.merge(criteria, on=['Version', 'Index', 'Payload'], how='inner')
            
            # Pair all neighbor packets with their corresponding source message
            merged_df = pd.merge(all_source_node_messages, neighbor_packets, on=['Version', 'Index', 'Payload'], how='inner')
            # Drop duplicates with same MAC address. We are only interested in the first occurrence, which would be the
            # soonest one.
            merged_df_mac_filtered = merged_df.drop_duplicates(subset=['Version', 'Index', 'Payload', 'MAC_y'])
            # Calculate time difference between source messages and neighbor packets
            merged_df_mac_filtered = merged_df_mac_filtered.copy()
            merged_df_mac_filtered['TimeDiff'] = (merged_df_mac_filtered['Timestamp_y'] - merged_df_mac_filtered['Timestamp_x']).dt.total_seconds() * 1000
            
            # Group paired DataFrame by 'Version', 'Index', and 'Payload' and get the minimum and maximum time difference
            merged_df_grouped = merged_df_mac_filtered.groupby(['Version', 'Index', 'Payload'])
            merged_df_min_max = merged_df_grouped['TimeDiff'].agg(['min', 'max']).reset_index()
            
            # Calculate average latency and maximum latency
            avg_mdr = merged_df_min_max['min'].mean()
            max_mdr = merged_df_min_max['max'].max()
            
            return list(merged_df_min_max['min']), avg_mdr, max_mdr
        except:
            return [], 0, 0