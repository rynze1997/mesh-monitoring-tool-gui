import os
import csv
import time
from threading import Thread

def prepare_logging_environment(file_path: str) -> None:
        """Prepares logging files and directories."""
        os.makedirs('.results', exist_ok=True)
        header = ['Timestamp', 'MAC', 'Command', 'Flags', 'Index', 'Payload', 'Version', 'Channel']
        _initialize_log_file(file_path, header)
        
def _initialize_log_file(file_path: str, header: list) -> None:
        """Initializes a log file with a given header."""
        with open(file_path, 'w', newline='') as file:
            csv.writer(file).writerow(header)
            
def log_packet_data(file_path, data):
        """Logs packet data to the specified file."""
        with open(file_path, 'a', newline='') as file:
            csv.writer(file).writerow(data)

def delete_lines_preserving_header(file_path: str, lines_to_preserve=7500, threshold=15000) -> None:
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
    
# def perform_periodic_processing(time_before: float, processing_interval : int = 2, processing_function: callable = None) -> None:
#         """Performs data processing periodically."""
#         if time.time() - time_before > processing_interval:
#             Thread(target=processing_function, daemon=True).start()
#             time_before = time.time()
#         return time_before

def parse_packet_data(metadata, received_packet):
    """Parses packet data for logging."""
    pass