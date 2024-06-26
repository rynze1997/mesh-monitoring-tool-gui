WINDOW_TITLE = "Mesh Network Monitoring Tool"
WINDOW_SIZE = (1800, 1100) # Height, Width
CANVAS_WINDOW_SIZE = (WINDOW_SIZE[0]+50, WINDOW_SIZE[1])
MDR_WINDOW_SIZE = (WINDOW_SIZE[0] - 100, WINDOW_SIZE[1] - 50)
LATENCY_WINDOW_SIZE = (WINDOW_SIZE[0] - 100, WINDOW_SIZE[1] - 50)
DRAWLIST_SIZE = (CANVAS_WINDOW_SIZE[0] - 320, CANVAS_WINDOW_SIZE[1] - 210)

## COMMANDS 
MESH_COMMAND_RBC_CHANNEL_CONFIG = 0x0056

## Flags
GET_FLAG = 0x02

# Network Topology Analysis Configuration
NETWORK_TOPOLOGY_INDEX_STIMULATION_THRESHOLD_S = 0.1
NETWORK_TOPOLOGY_THRESHOLD = 2
TOPOLOGY_ANALYSIS_FILE_PATH = '.results/discovery.csv'
TOPOLOGY_ANALYSIS_UPDATE_INTERVAL_SECONDS = 1
TOPOLOGY_ANALYSIS_TX_PERIOD_MS = 50
TOPOLOGY_ANALYSIS_STIMULATION_COMMAND = MESH_COMMAND_RBC_CHANNEL_CONFIG


# MDR Analysis Configuration
MDR_DEBUG_FILE_PATH = '.results/mdr_debug.csv'
MDR_FILE_PATH = '.results/mdr.csv'
TRICKLE_I_MIN_MS = 32
TRICKLE_REDUNDANCY_CONSTANT = 4

# Latency Analysis Configuration
LATENCY_DEBUG_FILE_PATH = '.results/latency_debug.csv'
LATENCY_FILE_PATH = '.results/latency.csv'
LATENCY_DATA_POINT_AMOUNT = 1000
LATENCY_ANALYSIS_UPDATE_INTERVAL_SECONDS = 2
LATENCY_HISTOGRAM_TIMESLOT_SIZE_SEC = 5
