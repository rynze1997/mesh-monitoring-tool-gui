from drivers.usb import USBManager
from network.crypto import cryptoKeys
from network.version_cache import VersionCache
from network.validation import validate_rbc_header, validate_ble_phy_header
import logging
import struct

class MeshCommunicationService:
    _instance = None  # Class-level attribute to store the singleton instance

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MeshCommunicationService, cls).__new__(cls)
            # Initialize the instance once
            cls._instance.init_once()
        return cls._instance

    def init_once(self):
        self.usb_manager = USBManager()
        self.crypto = cryptoKeys()
        self.version_cache = VersionCache()
        self.packet_counter = 1
    
    def initiate_usb_connection(self):
        return self.usb_manager.initiate_connection()  
    
    def send_access_keys(self, access_keys):
        access_addr = [int(hex_val, 16) for hex_val in access_keys[0].split()]
        crypto_key = [int(hex_val, 16) for hex_val in access_keys[1].split()]

        self.crypto.set_mesh_address(access_addr)
        self.crypto.set_crypto_key(crypto_key)
        
        protocol = [255]
        keys = protocol + access_addr + crypto_key # Add 0xFF (protocol) to the beginning of the list
        self.usb_manager.send_data(keys)
        
    def enable_radio(self):
        self.packet_counter = 1
        self.usb_manager.send_data([0xFD, 1])
        
    def disable_radio(self):
        self.usb_manager.send_data([0xFD, 0])

    def send_data(self, data):
        self.usb_manager.send_data(data)
        
    def clear_buffers(self):
        self.usb_manager.clear_buffer()
        
    def send_mesh_command(self, flags, command, variable_payload, index):
        self.version_cache.version_increment(index)
        latest_version = self.version_cache.version_cache_get_latest_version(index)
        plejd_payload_length, plejd_crypted_payload = self.assemble_mesh_packet(flags, command, variable_payload, index, latest_version)
        usb_data = assemble_usb_packet(0xFE, plejd_crypted_payload, plejd_payload_length, index, latest_version)
        self.usb_manager.send_data(usb_data)
        
    def receive_mesh_packet(self):
        return packet, metadata
        
            
    def assemble_mesh_packet(self, flags, command, variable_payload, index, version):
        
        return payload_length, payload_crypted

def assemble_usb_packet(protocol, payload_crypted, payload_length, index, version):
    
    return usb_data      

def crc16_compute(p_data, size, p_crc=None):

    return crc