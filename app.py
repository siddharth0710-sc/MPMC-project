import streamlit as st
from backend import send_bus_stop_request

st.set_page_config(
    page_title="MTC Chennai Smart Bus Stop", 
    page_icon="🚌", 
    layout="wide"
)

# Custom CSS for transit kiosk UI design
st.markdown("""
    <style>
    /* Dark Terminal Theme Adjustments */
    .stApp {
        background-color: #0d1117;
    }
    
    /* Bus Route Card Styling */
    .bus-card {
        background: linear-gradient(145deg, #161b22, #21262d);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    }
    
    /* Highlighted Styling for Main Bus (515A) */
    .main-bus-card {
        background: linear-gradient(145deg, #0d3880, #161b22);
        border: 2px solid #2f81f7;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        margin-bottom: 12px;
        box-shadow: 0 0 18px rgba(47, 129, 247, 0.4);
    }
    
    .bus-badge {
        font-size: 1.6rem;
        font-weight: 800;
        letter-spacing: 1px;
    }
    
    .badge-main { color: #58a6ff; }
    .badge-dummy { color: #8b949e; }
    
    .route-desc {
        font-size: 0.8rem;
        color: #c9d1d9;
        margin-top: 6px;
        font-weight: 500;
    }
    
    .type-tag {
        font-size: 0.7rem;
        color: #8b949e;
        text-transform: uppercase;
        margin-top: 4px;
        letter-spacing: 0.5px;
    }
    </style>
""", unsafe_allow_html=True)

# App Header
st.title("🚏 MTC Chennai Smart Bus Stop")
st.caption("Interactive Passenger Request Kiosk • Terminal Stop: OMR - Kelambakkam")

# Sidebar Hardware Configuration
st.sidebar.header("⚙️ Hardware Settings")
port = st.sidebar.text_input("ESP32 Serial Port", value="COM7")
baud_rate = st.sidebar.selectbox("Baud Rate", [115200, 9600], index=0)

# Session State Initialization
if "status" not in st.session_state:
    st.session_state.status = "IDLE"
if "selected_bus" not in st.session_state:
    st.session_state.selected_bus = None
if "last_log" not in st.session_state:
    st.session_state.last_log = ""

# Chennai MTC Bus Data
buses = [
    {"route": "515A", "destination": "Tambaram ⇄ Kovalam", "type": "⚡ Active Module", "is_main": True},
    {"route": "21G", "destination": "Broadway ⇄ Tambaram", "type": "Express", "is_main": False},
    {"route": "102X", "destination": "Broadway ⇄ Kelambakkam", "type": "Deluxe Express", "is_main": False},
    {"route": "570", "destination": "CMBT ⇄ Kelambakkam", "type": "A/C Volvo", "is_main": False},
    {"route": "19B", "destination": "Saidapet ⇄ Kelambakkam", "type": "Standard", "is_main": False},
]

st.markdown("### 🚌 Select Approaching Bus Route")

cols = st.columns(5)

for i, bus in enumerate(buses):
    with cols[i]:
        card_style = "main-bus-card" if bus["is_main"] else "bus-card"
        badge_style = "badge-main" if bus["is_main"] else "badge-dummy"
        
        # UI Card Render
        st.markdown(f"""
            <div class="{card_style}">
                <div class="bus-badge {badge_style}">{bus['route']}</div>
                <div class="route-desc">{bus['destination']}</div>
                <div class="type-tag">{bus['type']}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Button Logic
        if bus["is_main"]:
            if st.button(f"🔴 REQUEST {bus['route']}", key=f"btn_{bus['route']}", type="primary", use_container_width=True):
                st.session_state.selected_bus = bus['route']
                st.session_state.status = "TRANSMITTING"
                
                # Triggers serial write to ESP32 for 515A
                response = send_bus_stop_request(port, baud_rate)
                st.session_state.last_log = response
                
                if "TX_SUCCESS" in response:
                    st.session_state.status = "SUCCESS"
                else:
                    st.session_state.status = "HARDWARE_ERROR"
        else:
            if st.button(f"Request {bus['route']}", key=f"btn_{bus['route']}", use_container_width=True):
                st.session_state.selected_bus = bus['route']
                st.session_state.status = "DUMMY_CLICKED"
                st.session_state.last_log = f"Local UI Log: Bus {bus['route']} requested. Hardware signal transmission is disabled for dummy routes."

st.divider()

# System Output Section
col_status, col_reset = st.columns([4, 1])

with col_reset:
    if st.button("🔄 Reset Terminal", use_container_width=True):
        st.session_state.status = "IDLE"
        st.session_state.selected_bus = None
        st.session_state.last_log = ""
        st.rerun()

with col_status:
    st.subheader("System Status")
    
    if st.session_state.status == "IDLE":
        st.info(" Standby Mode: Press a bus route button above to dispatch a stop signal.")
    elif st.session_state.status == "DUMMY_CLICKED":
        st.warning(f"ℹ️ **Route {st.session_state.selected_bus} Selected (Dummy)**: Local interaction logged. Serial hardware transmission is active for **515A** only.")
    elif st.session_state.status == "SUCCESS":
        st.success(f"✅ **Signal Broadcasted for Bus {st.session_state.selected_bus}**: Wireless transmission confirmed by ESP32!")
    elif st.session_state.status == "HARDWARE_ERROR":
        st.error(f"⚠️ **Serial Communication Error (Route 515A)**: {st.session_state.last_log}")

if st.session_state.last_log:
    with st.expander("View ESP32 Serial Communication Log"):
        st.code(st.session_state.last_log, language="text")
