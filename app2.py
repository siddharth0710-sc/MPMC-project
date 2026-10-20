import streamlit as st
import time
from backend_stm32 import (
    stm32_controller, 
    send_payment_confirmation, 
    send_system_reset
)

# Page Setup
st.set_page_config(
    page_title="MTC Smart Bus - Onboard Dashboard",
    page_icon="🚌",
    layout="wide"
)

# CSS Styling matching Dark Kiosk / Transit Console
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    
    /* Status Banner Styling */
    .banner-stop {
        background: linear-gradient(135deg, #8b0000, #dc3545);
        color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        font-size: 2rem;
        font-weight: 900;
        letter-spacing: 2px;
        box-shadow: 0 0 20px rgba(220, 53, 69, 0.6);
        margin-bottom: 15px;
    }
    .banner-continue {
        background: linear-gradient(135deg, #0d5c2e, #198754);
        color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        font-size: 2rem;
        font-weight: 900;
        letter-spacing: 2px;
        box-shadow: 0 0 15px rgba(25, 135, 84, 0.4);
        margin-bottom: 15px;
    }
    .banner-warning {
        background: linear-gradient(135deg, #8a6d0b, #ffc107);
        color: #000000;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        font-size: 1.8rem;
        font-weight: 800;
        box-shadow: 0 0 18px rgba(255, 193, 7, 0.5);
        margin-bottom: 15px;
    }
    
    /* Telemetry & Card Boxes */
    .telemetry-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 14px;
        text-align: center;
    }
    .telemetry-val {
        font-size: 1.4rem;
        font-weight: bold;
        color: #58a6ff;
    }
    
    /* Payment Ticket Card */
    .ticket-card {
        background: linear-gradient(145deg, #1c2128, #2d333b);
        border: 2px solid #388bfd;
        border-radius: 15px;
        padding: 24px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
    }
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# Session State Initialization
# ----------------------------------------------------
if "seat_occupied" not in st.session_state:
    st.session_state.seat_occupied = False
if "platform_occupied" not in st.session_state:
    st.session_state.platform_occupied = False
if "payment_status" not in st.session_state:
    st.session_state.payment_status = "IDLE"  # IDLE, PENDING, COMPLETED, TIMEOUT
if "selected_dest" not in st.session_state:
    st.session_state.selected_dest = None
if "driver_alert" not in st.session_state:
    st.session_state.driver_alert = "STANDBY"  # STANDBY, STOP, SKIP, PREPARING_TO_ALIGHT, WARNING
if "bus_stop_request" not in st.session_state:
    st.session_state.bus_stop_request = False
if "log_history" not in st.session_state:
    st.session_state.log_history = []
if "payment_start_time" not in st.session_state:
    st.session_state.payment_start_time = 0

def add_log(msg: str):
    timestamp = time.strftime("%H:%M:%S")
    st.session_state.log_history.insert(0, f"[{timestamp}] {msg}")

# ----------------------------------------------------
# Hardware Settings & Sidebar
# ----------------------------------------------------
st.sidebar.title("⚙️ Hardware Settings")
port_input = st.sidebar.text_input("STM32 Serial Port", value="COM8")
baud_input = st.sidebar.selectbox("Baud Rate", [115200, 9600], index=0)

col_conn1, col_conn2 = st.sidebar.columns(2)
with col_conn1:
    if st.button("🔌 Connect", use_container_width=True):
        res = stm32_controller.connect(port_input, baud_input)
        add_log(f"Connection attempt: {res}")
        st.success("Connected!") if "SUCCESS" in res or "SIMULATION" in res else st.error(res)

with col_conn2:
    if st.button("❌ Disconnect", use_container_width=True):
        stm32_controller.disconnect()
        add_log("Serial disconnected.")
        st.warning("Disconnected")

st.sidebar.divider()
st.sidebar.subheader("🧪 Manual Simulation Controls")
st.sidebar.caption("Use to test interface logic offline without physical hardware")

if st.sidebar.button("💺 Simulate Seat Occupied", use_container_width=True):
    st.session_state.seat_occupied = True
    st.session_state.payment_status = "PENDING"
    st.session_state.payment_start_time = time.time()
    add_log("EVENT: Seat FSR Occupied -> Payment Pending")

if st.sidebar.button("🚶 Simulate Platform Occupied", use_container_width=True):
    st.session_state.platform_occupied = True
    if st.session_state.payment_status == "COMPLETED":
        st.session_state.driver_alert = "PREPARING_TO_ALIGHT"
        add_log("EVENT: Paid passenger moved to platform -> Preparing to alight")
    else:
        add_log("EVENT: Platform FSR Occupied")

if st.sidebar.button("🧲 Simulate Hall Sensor (Demo Stop)", use_container_width=True):
    add_log("EVENT: Hall Effect Sensor Triggered (Demo Stop)")
    # Evaluate Stop Logic
    if st.session_state.bus_stop_request:
        st.session_state.driver_alert = "STOP"
        add_log("DECISION: STOP (Bus Stop Request Active)")
    elif st.session_state.payment_status == "COMPLETED" and st.session_state.selected_dest == "Demo Stop":
        st.session_state.driver_alert = "STOP"
        add_log("DECISION: STOP (Passenger Destination Match)")
    else:
        st.session_state.driver_alert = "SKIP"
        add_log("DECISION: SKIP (No request, destination mismatch)")

if st.sidebar.button("📡 Simulate Bus Stop Wireless Request", use_container_width=True):
    st.session_state.bus_stop_request = True
    add_log("EVENT: Wireless Bus Stop Request Received via nRF24")

st.sidebar.divider()
if st.sidebar.button("🔄 System Reset", type="primary", use_container_width=True):
    send_system_reset()
    st.session_state.seat_occupied = False
    st.session_state.platform_occupied = False
    st.session_state.payment_status = "IDLE"
    st.session_state.selected_dest = None
    st.session_state.driver_alert = "STANDBY"
    st.session_state.bus_stop_request = False
    st.session_state.payment_start_time = 0
    add_log("SYSTEM RESET executed.")
    st.rerun()

# ----------------------------------------------------
# Real-Time Serial Telemetry Polling
# ----------------------------------------------------
incoming = stm32_controller.read_incoming_telemetry()
if incoming["has_data"]:
    evt = incoming["event_type"]
    payload = incoming["payload"]
    add_log(f"STM32 TX: {incoming['raw']}")
    
    if evt == "SEAT_OCCUPIED":
        st.session_state.seat_occupied = True
        st.session_state.payment_status = "PENDING"
        st.session_state.payment_start_time = time.time()
    elif evt == "SEAT_VACATED":
        st.session_state.seat_occupied = False
    elif evt == "PLATFORM_OCCUPIED":
        st.session_state.platform_occupied = True
        if st.session_state.payment_status == "COMPLETED":
            st.session_state.driver_alert = "PREPARING_TO_ALIGHT"
    elif evt == "PLATFORM_VACATED":
        st.session_state.platform_occupied = False
    elif evt == "PAYMENT_TIMEOUT":
        st.session_state.payment_status = "TIMEOUT"
        st.session_state.driver_alert = "WARNING"
    elif evt == "STANDING_TIMEOUT":
        st.session_state.driver_alert = "WARNING"
    elif evt == "RF_REQUEST_RECEIVED":
        st.session_state.bus_stop_request = True
    elif evt == "STOP_ALERT":
        st.session_state.driver_alert = "STOP"
    elif evt == "SKIP_ALERT":
        st.session_state.driver_alert = "SKIP"

# ----------------------------------------------------
# Header & Interface View Mode Selector
# ----------------------------------------------------
st.title("🚌 MTC Smart Bus Onboard System")
st.caption("Central Control Unit • STM32 Hardware Interfacing • Route 515A")

# Primary Option Selector to switch views on a single screen
interface_mode = st.radio(
    "Select Operating View:",
    ["👨‍✈️ Driver Interface", "🎟️ Passenger Interface"],
    horizontal=True
)

st.divider()

# ====================================================
# VIEW 1: DRIVER INTERFACE
# ====================================================
if interface_mode == "👨‍✈️ Driver Interface":
    st.subheader("👨‍✈️ Driver Navigation & Safety Console")
    
    # Major Driver Alert Banner
    if st.session_state.driver_alert == "STOP":
        st.markdown('<div class="banner-stop">🛑 STOP AT NEXT BUS STOP</div>', unsafe_allow_html=True)
    elif st.session_state.driver_alert == "SKIP":
        st.markdown('<div class="banner-continue">🟢 CONTINUE (NO STOP REQUIRED)</div>', unsafe_allow_html=True)
    elif st.session_state.driver_alert == "PREPARING_TO_ALIGHT":
        st.markdown('<div class="banner-warning">⚠️ PASSENGER PREPARING TO ALIGHT</div>', unsafe_allow_html=True)
    elif st.session_state.driver_alert == "WARNING":
        st.markdown('<div class="banner-warning">🚨 TIMEOUT WARNING: CHECK PASSENGER / SEAT</div>', unsafe_allow_html=True)
    else:
        st.info("ℹ️ System Standby • Monitoring route and sensor telematics...")

    # Hardware Telemetry Row
    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
    with col_t1:
        seat_str = "🔴 OCCUPIED" if st.session_state.seat_occupied else "🟢 VACANT"
        st.markdown(f"""
            <div class="telemetry-card">
                <div>Functional Seat Status</div>
                <div class="telemetry-val">{seat_str}</div>
            </div>
        """, unsafe_allow_html=True)
    with col_t2:
        plat_str = "🔴 OCCUPIED" if st.session_state.platform_occupied else "🟢 CLEAR"
        st.markdown(f"""
            <div class="telemetry-card">
                <div>Platform Area</div>
                <div class="telemetry-val">{plat_str}</div>
            </div>
        """, unsafe_allow_html=True)
    with col_t3:
        req_str = "YES (PENDING)" if st.session_state.bus_stop_request else "NONE"
        st.markdown(f"""
            <div class="telemetry-card">
                <div>Bus Stop Request</div>
                <div class="telemetry-val">{req_str}</div>
            </div>
        """, unsafe_allow_html=True)
    with col_t4:
        dest_str = st.session_state.selected_dest if st.session_state.selected_dest else "N/A"
        st.markdown(f"""
            <div class="telemetry-card">
                <div>Passenger Destination</div>
                <div class="telemetry-val">{dest_str}</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📋 System Event Telemetry Log")
    if st.session_state.log_history:
        st.code("\n".join(st.session_state.log_history[:8]), language="text")
    else:
        st.caption("No events logged yet.")

# ====================================================
# VIEW 2: PASSENGER INTERFACE
# ====================================================
elif interface_mode == "🎟️ Passenger Interface":
    st.subheader("🎟️ Onboard Interactive Ticketing Kiosk")
    
    if st.session_state.payment_status == "IDLE":
        st.info("💺 **Welcome Boarding Passenger!** Please take a seat on the functional seat to initiate destination ticketing.")
        
    elif st.session_state.payment_status == "PENDING":
        st.markdown('<div class="ticket-card">', unsafe_allow_html=True)
        st.warning("⏱️ **Seat Occupancy Detected! Please Select Destination and Complete Payment.**")
        
        # Countdown Timer Simulation (15-second window)
        elapsed = int(time.time() - st.session_state.payment_start_time)
        remaining = max(0, 15 - elapsed)
        
        st.metric(label="⏳ Payment Time Remaining", value=f"{remaining} Seconds")
        
        if remaining == 0:
            st.session_state.payment_status = "TIMEOUT"
            st.session_state.driver_alert = "WARNING"
            add_log("TIMING: Payment window expired on Passenger GUI")
            st.rerun()

        col_p1, col_p2 = st.columns([1, 1])
        
        with col_p1:
            dest_option = st.radio(
                "Select Destination Stop:",
                ["Demo Stop", "Future Stop A", "Future Stop B"],
                key="dest_radio"
            )
            
            fares = {"Demo Stop": "₹ 15.00", "Future Stop A": "₹ 25.00", "Future Stop B": "₹ 35.00"}
            calculated_fare = fares[dest_option]
            
            st.markdown(f"### Payable Fare: **{calculated_fare}**")
            
        with col_p2:
            st.markdown("**Scan UPI QR to Pay:**")
            # Dummy QR Code Rendering using SVG/HTML
            st.markdown(f"""
                <div style="background:white; padding:12px; display:inline-block; border-radius:8px;">
                    <img src="https://api.qrserver.com/v1/create-qr-code/?size=140x140&data=upi://pay?pa=mtcchennai@upi&pn=MTCBus&am={calculated_fare[2:]}" width="140">
                </div>
            """, unsafe_allow_html=True)
            
        st.divider()
        if st.button("✅ CONFIRM PAYMENT", type="primary", use_container_width=True):
            st.session_state.payment_status = "COMPLETED"
            st.session_state.selected_dest = dest_option
            
            # Transmit confirmation to STM32 over serial
            resp = send_payment_confirmation(dest_option)
            add_log(f"Payment Confirmed ({dest_option}): {resp}")
            st.rerun()
            
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state.payment_status == "COMPLETED":
        st.success(f"🎉 **Payment Successful!** Destination stored: **{st.session_state.selected_dest}**. Red seat LED deactivated.")
        st.caption("Thank you for traveling with MTC Chennai. Enjoy your ride!")

    elif st.session_state.payment_status == "TIMEOUT":
        st.error("🚨 **Payment Window Expired!** The onboard warning buzzer and Red LED have been activated. Please complete payment or inform the conductor.")