import dearpygui.dearpygui as dpg
from network.mdr_service import MDRService
from config import WINDOW_SIZE, MDR_WINDOW_SIZE
from .canvas_manager import CanvasManager

class MDRTab:
    def __init__(self) -> None:
        self.site = ""
        self.mdr_window = None
        
    def mdr_tab_create(self, site) -> None:
        """ Creates a MDR tab and initializes the MDR service. """
        
        self.site = site
        dpg.add_menu_item(label="MDR Analysis", callback=self._on_mdr_tab, tag="__mdr_menu_item", parent="__analysis_menu")
   
    def _on_mdr_tab(self):
        """ Create MDR Analysis Window."""
        self.mdr_window = MDRWindow()
        self.mdr_window.mdr_window_create(site = self.site)
        
    def close_mdr_window(self):
        """ Close MDR Analysis Window."""
        dpg.delete_item("__mdr_window")
        
    def delete_tab(self):
        """ Delete MDR tab. """
        dpg.delete_item("__mdr_menu_item")

class MDRWindow:
    
    def __init__(self) -> None:
        self.mdr_service = MDRService(self._plot_mdr_callback)
        self.conn_mdr_map = {}
        self.site = ""
    
    def mdr_window_create(self, site: str) -> None:
        """
        Perform various operations related to MDR callback, including retrieving MAC to label map, creating mdr window, setting the position of the mdr window, 
        adding options for source and destination, preparing place for error text, adding bar plot for mdr values, and adding a button to start mdr analysis.
        """
        
        self.site = site
        
        # Retrieve MAC to label map from Mesh Topology analysis results
        mac_label_map = self.mdr_service.get_mac_label_map()
        # Create list of MAC labels
        mac_label_list = [f"{info['number']}: {info['title']:<15}: {mac}" for mac, info in mac_label_map.items()]
        
        # Disable mdr tab, two mdr windows can not be opened at the same time
        dpg.configure_item("__mdr_menu_item", enabled=False)
        
        # Create mdr window
        with dpg.window(label="Message-Delivery-Rate (MDR) Window", tag="__mdr_window", width=MDR_WINDOW_SIZE[0], height=MDR_WINDOW_SIZE[1], show=True, on_close=self._delete_window):
            
            # Add option to choose source and destination
            with dpg.group(horizontal=True):
                with dpg.group(horizontal=False):
                    dpg.add_text("Choose Source:")
                    dpg.add_combo(label="Source", items=mac_label_list, tag="__mdr_source", width=(WINDOW_SIZE[0] - 900)/3)
                with dpg.group(horizontal=False):    
                    dpg.add_text("Choose Destination:")
                    dpg.add_combo(label="Destination", items=mac_label_list, tag="__mdr_destination", width=(WINDOW_SIZE[0] - 900)/3)
                    
            # Prepare place for error text
            dpg.add_text("", tag="__mdr_error_text", color=(255, 0, 0))
            # Add bar plot for mdr values
            self._prepare_plot()
            
        # Add button to start mdr analysis
        dpg.add_button(label="START MDR", callback=self._on_start_mdr_button_callback, tag="__start_mdr_button", parent="__mdr_window")
    def _on_start_mdr_button_callback(self):
        """
        Callback function for the start MDR button.

        This function is triggered when the start MDR button is clicked. It performs the following steps:
        1. Retrieves the selected source and destination from the corresponding input fields.
        2. Removes the labels from the source and destination.
        3. Checks if both the source and destination are selected. If not, it displays an error message.
        4. Checks if the source and destination are the same. If so, it displays an error message.
        5. Checks if there is a path between the source and destination. If not, it displays an error message.
        6. If all the above conditions are met, it starts the MDR analysis by calling the `start` method of the `mdr_service` object.
        7. Removes the error message if it exists.
        8. Deletes the start MDR button and adds a stop MDR button.

        Parameters:
        - self: The instance of the class.

        Returns:
        - None
        """
        
        # Get selected source and destination
        source = dpg.get_value("__mdr_source")
        destination = dpg.get_value("__mdr_destination")
        # Remove labels from source and destination
        source_mac = source.split(": ")[2]
        destination_mac = destination.split(": ")[2]
        
        if source == "" or destination == "":
            dpg.configure_item("__mdr_error_text", default_value="Please choose source and destination")
        # Print an error if source and destination nodes are same
        elif source == destination:
            dpg.configure_item("__mdr_error_text", default_value="Source and Destination cannot be the same")
        # Check if path exists between source and destination
        elif not CanvasManager().get_has_path(self.mdr_service.get_mac_label_map(), source_mac, destination_mac):
            dpg.configure_item("__mdr_error_text", default_value="No path between source and destination")
        else:
            # Start mdr analysis by starting mdr service
            self.mdr_service.start_analysis(source_mac, destination_mac, self.site,
                                            CanvasManager().get_node_neighbor_map())
            # Remove error text if it exists
            dpg.configure_item("__mdr_error_text", default_value="")
            
            
            dpg.delete_item("__start_mdr_button")
            dpg.add_button(label="STOP MDR", callback=self._on_stop_mdr_button_callback, tag="__stop_mdr", parent="__mdr_window")
            
    def _delete_window(sender):
        """A function to delete a window and its associated items."""
        
        dpg.configure_item("__mdr_menu_item", enabled=True)
        if dpg.does_item_exist("__mdr_plot"):
            dpg.delete_item("__mdr_plot")
            
        dpg.delete_item("__mdr_window")
        dpg.delete_item(sender)
        
    def _on_stop_mdr_button_callback(self):
        """
        Executes when the stop button for the mdr service is clicked. Prints a message indicating that the stop button was pressed, 
        stops the mdr service, deletes the stop button, and adds a start button to the mdr window.
        """
        
        print("Stop button pressed")
        self.mdr_service.stop_analysis()
        dpg.delete_item("__stop_mdr")
        dpg.add_button(label="START MDR", callback=self._on_start_mdr_button_callback, tag="__start_mdr_button", parent="__mdr_window")
        
    def _plot_mdr_callback(self, result, mac_label_map, consecutive_runs):
        """
        Plot mdr values with Dear PyGui, including connection labels and mdr percentages.
        """
        for i, conn in enumerate(result):
            # Use the labels for connections 
            throughput = result[i]['throughput']
            conn['source_label'] = mac_label_map[conn['source']]
            conn['destination_label'] = mac_label_map[conn['destination']]
            label = f"{conn['source_label']['number']}: {conn['source_label']['title']} <-> {conn['destination_label']['number']}: {conn['destination_label']['title']}: Run {consecutive_runs}"
            mdr_value = conn['mdr'] if conn['mdr'] is not None else 0  # mdr Percentage
            self.conn_mdr_map[label] = {'mdr': mdr_value, 'throughput': throughput}

        for i, (label, values) in enumerate(self.conn_mdr_map.items()):
            mdr_value = values['mdr']
            throughput = values['throughput']
            print(f"Plotting {label} with mdr {mdr_value} and throughput {throughput}")
            bar_x = i * 5 + 10  # Middle point of a bar
            bar_width_mdr = 2   # Width of a bar
            # Add the bar series as before
            if dpg.does_item_exist(label):
                dpg.configure_item(item = label, x=[bar_x], y=[mdr_value])
                dpg.configure_item(item = f'{label}_tooltip', default_value=f"{label}: {mdr_value}")
                dpg.configure_item(item = f'{label}_throughput', x=[bar_x+1.5], y=[throughput])
                dpg.configure_item(item = f'{label}_tooltip_throughput', default_value=f"{label}: {throughput}")

            else:
                dpg.add_bar_series([bar_x], [mdr_value], label=label, weight=bar_width_mdr, parent="__mdr_plot_y_axis", tag = label)
                dpg.add_bar_series([bar_x+1.5], [throughput], label=label, weight=bar_width_mdr-1, parent="__throughput_plot_y_axis", tag = f'{label}_throughput')
                with dpg.tooltip(label):
                    dpg.add_text(f"{label}: {mdr_value}", tag=f'{label}_tooltip')
                with dpg.tooltip(f'{label}_throughput'):
                    dpg.add_text(f"{label}: {throughput}", tag=f'{label}_tooltip_throughput')

        dpg.set_axis_limits("__mdr_plot_y_axis", 0, 110)
        dpg.set_axis_limits("__throughput_plot_y_axis", 0, 45)
        dpg.set_axis_limits_auto("__mdr_plot_x_axis")
        dpg.set_axis_limits_auto("__throughput_plot_x_axis")
        dpg.fit_axis_data("__mdr_plot_x_axis")
        dpg.fit_axis_data("__throughput_plot_x_axis")
        
        
    def _prepare_plot(self):
        with dpg.subplots(2, 1, height=MDR_WINDOW_SIZE[1]-200, width=-1):
            
            with dpg.plot(label="Message-Delivery-Rate (MDR) Plot", height=(MDR_WINDOW_SIZE[1]/2)-300, width=MDR_WINDOW_SIZE[0] - 100, tag="__mdr_plot"):
                dpg.add_plot_legend(outside=True)
                dpg.add_plot_axis(dpg.mvXAxis, label="", no_gridlines=True, 
                                        no_tick_labels=True, tag="__mdr_plot_x_axis", parent="__mdr_plot")
                dpg.add_plot_axis(dpg.mvYAxis, label="Message-Delivery Rate (MDR) (%)", parent="__mdr_plot", tag="__mdr_plot_y_axis")
                
            with dpg.plot(label="Throughput Plot", height=(MDR_WINDOW_SIZE[1]/2)-300, width=MDR_WINDOW_SIZE[0] - 100, tag="__throughput_plot"):
                dpg.add_plot_legend(outside=True)
                dpg.add_plot_axis(dpg.mvXAxis, label="Connection", no_gridlines=True, 
                                        no_tick_labels=True, tag="__throughput_plot_x_axis")
                dpg.add_plot_axis(dpg.mvYAxis, label="Throughput (Msg/s)", tag="__throughput_plot_y_axis")