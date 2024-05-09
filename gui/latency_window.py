import dearpygui.dearpygui as dpg
from config import CANVAS_WINDOW_SIZE, WINDOW_SIZE, LATENCY_WINDOW_SIZE, LATENCY_HISTOGRAM_TIMESLOT_SIZE_SEC
from network.latency_service import LatencyService
from gui.canvas_manager import CanvasManager

class LatencyTab:
    def __init__(self):
        self.site = ""                            # site for which the analysis is being performed
    def create_latency_tab(self, site:str) -> None:
        """
        Create a latency tab and set site.

        Parameters:
            site (str): The site for which the analysis is being performed.
        Returns:
            None
        """
        dpg.add_menu_item(label="Latency Analysis", callback=self._on_latency_tab, parent="__analysis_menu")
        self.site = site

        
    def _on_latency_tab(self):
        """ Create Latency Analysis Window."""
        LatencyWindow().create_latency_window(site = self.site)
        
    def close_latency_window(self):
        """ Close Latency Analysis Window."""
        dpg.delete_item("__latency_window")
        
    def delete_tab(self):
        """ Delete Latency tab. """
        dpg.delete_item("__latency_menu_item")

class LatencyWindow:
    
    def __init__(self):
        self.latency_action_handler = LatencyService(self._analysis_complete_callback)
        self.theoretical_latency = 0
        self.site = ""                                                                    # site for which the analysis is being performed
        self.avg_latency_list = [0] * 50
        self.max_latency_list = [0]* 50
        self.theoretical_latency_list = [0]* 50
    
    def create_latency_window(self, site: str) -> None:
        
        self.site = site
        self.avg_latency_list = [0]* 50
        self.max_latency_list = [0]* 50
        self.theoretical_latency_list = [0]* 50
        
        # Get Mac to letter map for dropdown menu
        mac_label_map = self.latency_action_handler.latency_service_get_mac_label_map()
        mac_label_list = [f"{info['number']}: {info['title']:<15}: {mac}" for mac, info in mac_label_map.items()]
        
        # Create Latency Analysis Window
        with dpg.window(label="Latency Analysis Window", tag="__latency_window", width=LATENCY_WINDOW_SIZE[0], height=LATENCY_WINDOW_SIZE[1], show=True, on_close=self._delete_window):
            # Add option to choose source and destination
            with dpg.group(horizontal=True):
                with dpg.group(horizontal=False):
                    dpg.add_text("Choose Source:")
                    dpg.add_combo(label="Source", items=mac_label_list, tag="__latency_source", width=(WINDOW_SIZE[0] - 900)/3)
                    # Add checkbox for manual mode
                    dpg.add_checkbox(label="Manual Stimulation Mode", tag="__latency_manual_mode_checkbox")
                with dpg.group(horizontal=False):    
                    dpg.add_text("Choose Destination:")
                    dpg.add_combo(label="Destination", items=mac_label_list, tag="__latency_destination", width=(WINDOW_SIZE[0] - 900)/3)
            # Add error text to fill in if there is an error
            with dpg.group(horizontal=True):
                dpg.add_text("", tag="__latency_error_text", color=(255, 0, 0))
                dpg.add_loading_indicator(tag="__latency_loading_indicator", show=False)
            dpg.add_text("", tag="__latency_error_text2", color=(255, 0, 0))
            
            # Prepare plots
            self._prepare_plot()
            
            # Add button to start latency test            
            dpg.add_button(label="Start Latency Test", callback=self.start_latency_button_cb, tag="__start_stop_latency_button", parent="__latency_window")
        
    def _prepare_plot(self):
            with dpg.subplots(2, 1, height=LATENCY_WINDOW_SIZE[1]-200, width=-1, parent="__latency_window"):
                
                with dpg.plot(label="Latency Histogram Plot", height=(LATENCY_WINDOW_SIZE[1]/2)-300, 
                              width=LATENCY_WINDOW_SIZE[0]-100, tag="__latency_histogram"):
                    dpg.add_plot_legend(outside=True)
                    dpg.add_plot_axis(dpg.mvXAxis, label="Time-slots (5 ms/slot)", no_gridlines=True, tag="__latency_histogram_x_axis",
                                      parent="__latency_histogram")
                    dpg.add_plot_axis(dpg.mvYAxis, label="Distribution", tag="__latency_histogram_y_axis",
                                      parent="__latency_histogram")
                
                with dpg.plot(label="Average Latency", height=(LATENCY_WINDOW_SIZE[1]/2)-300, 
                            width=LATENCY_WINDOW_SIZE[0]-100, tag="__avg_latency_plot"):
                    dpg.add_plot_legend(outside=True)
                    dpg.add_plot_axis(dpg.mvXAxis, label="", no_gridlines=True, tag="__avg_latency_x_axis")
                    dpg.add_plot_axis(dpg.mvYAxis, label="Latency (ms)", tag="__avg_latency_y_axis")
    
    def start_latency_button_cb(self):
        
        # Get selected source and destination
        source = dpg.get_value("__latency_source")
        destination = dpg.get_value("__latency_destination")
        # Remove labels from source and destination
        try:
            source_mac = source.split(": ")[2]
            destination_mac = destination.split(": ")[2]
        except:
            source_mac = ""
            destination_mac = ""
                
        # Print an error if both combos are the same
        if source == "" or destination == "":
            dpg.configure_item("__latency_error_text", default_value="Please choose source and destination")
        elif source == destination:
            dpg.configure_item("__latency_error_text", default_value="Source and destination cannot be the same!")
        # Check if path exists between source and destination
        elif not CanvasManager().get_has_path(self.latency_action_handler.latency_service_get_mac_label_map(), source_mac, destination_mac):
            dpg.configure_item("__latency_error_text", default_value="No path between source and destination")
        # Everything is OK, start latency analysis
        else:
            dpg.configure_item("__latency_error_text", default_value="")
            
            mac_to_label = self.latency_action_handler.latency_service_get_mac_label_map()
            # Get shortest path between source and destination    
            shortest_path = CanvasManager().get_shortest_path(mac_to_label, source_mac, destination_mac)

            num_of_neighbors_per_hop = CanvasManager().get_number_of_neighbors_for_each_hop(mac_to_label, source_mac, destination_mac)
            theoretical_latency = self.latency_action_handler.calculate_theoretical_latency(num_of_neighbors_per_hop, shortest_path)
            if len(shortest_path) < 3:
                self.theoretical_latency = 0
            else:
                self.theoretical_latency = theoretical_latency
            
            manual_mode = dpg.get_value("__latency_manual_mode_checkbox")
            
            # Start analysis
            self.latency_action_handler.start_latency_analysis(source_mac, destination_mac, self._update_latency_histogram_callback, 
                                                               self.site, manual_mode, CanvasManager().get_node_neighbor_map())
            
            dpg.configure_item("__start_stop_latency_button", label="Stop Latency Analysis", callback=self._stop_latency_button_cb)
            if not manual_mode:
                dpg.configure_item("__latency_error_text", default_value="Analyzing... Please wait!", color=(255, 0, 0))
                dpg.configure_item("__latency_loading_indicator", show=True)
    
    def _analysis_complete_callback(self):
        """ A callback function for when the analysis is complete using automatic mode. Configures UI elements accordingly."""
        dpg.configure_item("__start_stop_latency_button", label="Start Latency Analysis", callback=self.start_latency_button_cb, enabled=True)
        dpg.configure_item("__latency_error_text", default_value="Analysis Complete!", color=(0, 255, 0))
        
    def _stop_latency_button_cb(self):
        """ This function is the callback for stopping latency analysis with button. Configures UI elements accordingly. """
        manual_mode_checkbox_value = dpg.get_value("__latency_manual_mode_checkbox")
        if manual_mode_checkbox_value == False:
            dpg.configure_item("__latency_error_text", default_value="Last analysis did not complete a full cycle!", color=(255, 0, 0))
        
        self.latency_action_handler.stop_latency_analysis()
        dpg.configure_item("__start_stop_latency_button", label="Start Latency Analysis", callback=self.start_latency_button_cb)
        dpg.configure_item("__latency_loading_indicator", show=False)

    def _map_latency_to_custom_bins(self, latency_list, bin_size=5):
        """
        Map the given latency values to custom bins of a specified size and normalize the histogram
        to reflect probabilities of each bin.

        Args:
            latency_list (list): A list of latency values.
            bin_size (int, optional): The size of each bin. Defaults to 5.

        Returns:
            list: A list of normalized counts for each bin which reflect the probability distribution
            of the observed latency values.
        """
        # Determine the maximum latency to understand the range of data.
        max_latency = max(latency_list)
        # Calculate the number of bins needed by dividing the maximum latency by the bin size.
        # The ceil operation (achieved through integer division plus 1) ensures that any remaining
        # latency value that does not perfectly divide by the bin size is accounted for in a final bin.
        num_bins = int(max_latency // bin_size) + 1
        
        # Initialize a list with zero counts for each bin.
        # This array will hold the raw count of latency events that fall into each bin.
        bin_counts = [0] * num_bins
        
        # Iterate over each latency value in the provided list.
        for latency in latency_list:
            # Determine the bin index for each latency value using floor division.
            # This groups each latency value into the correct bin by its size.
            bin_index = int(latency // bin_size)
            # Increment the count of the corresponding bin to count how many latencies fall into this range.
            bin_counts[bin_index] += 1

        # Normalize the histogram to create a probability distribution.
        # First, calculate the total number of events observed.
        total_events = sum(bin_counts)
        # Create a new list of normalized counts, where each count is divided by the total number of events.
        # This transformation converts raw counts into a probability that a randomly selected latency value
        # from the list falls into a given bin.
        normalized_bin_counts = [count / total_events for count in bin_counts]

        return normalized_bin_counts

    
    def _update_latency_histogram_callback(self, latency_list, avg_latency, max_latency, consecutive_runs):
        
        ################## HISTOGRAM PLOT ##################
        bin_size = LATENCY_HISTOGRAM_TIMESLOT_SIZE_SEC
        # Map result from latency analysis to custom, normalized bins
        normalized_bins = self._map_latency_to_custom_bins(latency_list, bin_size=bin_size)
       
        x_axis = [i*bin_size + bin_size/2 for i in range(len(normalized_bins))] # Middle point of each bin
        if dpg.does_item_exist("__histogram_bars"):
            dpg.configure_item("__histogram_bars", x=x_axis, y=normalized_bins, weight=bin_size-0.2)
        else:
            dpg.add_bar_series(x_axis, normalized_bins, weight=bin_size-0.1, tag="__histogram_bars",parent="__latency_histogram_y_axis")
        
        ################## AVG LATENCY PLOT ##################
        # Get selected source and destination
        source = dpg.get_value("__latency_source")
        destination = dpg.get_value("__latency_destination")

        # Split the source and destination strings
        source_parts = source.split(':')
        destination_parts = destination.split(':')

        ticks = [1 + (i * 5) for i in range(consecutive_runs)]
        labels = []
        for i in range(consecutive_runs):
            # Create the label for this run
            source_label = f"{source_parts[0].strip()}: {source_parts[1].strip()}"
            destination_label = f"{destination_parts[0].strip()}: {destination_parts[1].strip()}"
            run_label = f"Run {i+1}"
            label = f"{source_label} <-> {destination_label}\n{run_label}"
            labels.append(label)
        
        # Combine the ticks and labels into a list of tuples
        ticks_and_labels = list(zip(labels, ticks))
        dpg.set_axis_ticks("__avg_latency_x_axis", tuple(ticks_and_labels))
        
        
        self.avg_latency_list[consecutive_runs - 1] = round(avg_latency, 2)
        self.max_latency_list[consecutive_runs - 1] = max_latency
        self.theoretical_latency_list[consecutive_runs - 1] = self.theoretical_latency
        bar_x = [1 + (i * 5) for i in range(consecutive_runs)]
        bar_width = 1
        if dpg.does_item_exist("__avg_latency"):
            dpg.configure_item("__avg_latency", x=bar_x, y=self.avg_latency_list, weight=bar_width)
            dpg.configure_item("__max_latency", x=[x + 1 for x in bar_x], y=self.max_latency_list, weight=bar_width)
            dpg.configure_item("__theoretical_latency", x=[x - 1 for x in bar_x], y=self.theoretical_latency_list, weight=bar_width)
        else:
            dpg.add_bar_series(bar_x, self.avg_latency_list, label="Average Latency", weight=bar_width, 
                               parent="__avg_latency_y_axis", tag = "__avg_latency")
            dpg.add_bar_series([x + 1 for x in bar_x], self.max_latency_list, label="Max Latency", 
                               weight=bar_width, parent="__avg_latency_y_axis", tag="__max_latency")
            dpg.add_bar_series([x - 1 for x in bar_x], self.theoretical_latency_list, label=f"Theoretical Latency", 
                               weight=bar_width, parent="__avg_latency_y_axis", tag="__theoretical_latency")
            
        dpg.set_axis_limits_auto("__latency_histogram_y_axis")
        dpg.set_axis_limits_auto("__latency_histogram_x_axis")
        dpg.fit_axis_data("__latency_histogram_y_axis")
        dpg.fit_axis_data("__latency_histogram_x_axis")
        dpg.set_axis_limits_auto("__avg_latency_y_axis")
        dpg.set_axis_limits_auto("__avg_latency_x_axis")
        dpg.fit_axis_data("__avg_latency_y_axis")
        dpg.fit_axis_data("__avg_latency_x_axis")

    def _delete_window(self,sender):
        """When the window is closed, delete the window and its associated items."""
        dpg.delete_item(sender)
                    
