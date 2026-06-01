import streamlit as st
import numpy as np
import pandas as pd

# App setup - Hide menus for Canva embedding and set title
st.set_page_config(page_title="Energy Audit", layout="wide")
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

st.title("Energy Audit Intuition Calculator")

# --- SIDEBAR SLIDERS ---
st.sidebar.header("Input Parameters")
v_kmh = st.sidebar.slider("Velocity (km/h)", min_value=60, max_value=100, value=60, step=5)
cda = st.sidebar.slider("Aerodynamic Drag (CdA)", min_value=0.08, max_value=0.25, value=0.16, step=0.01)
crr = st.sidebar.slider("Rolling Resistance (Crr)", min_value=0.001, max_value=0.015, value=0.007, step=0.0005, format="%.4f")
mass = st.sidebar.slider("Total Mass including Driver (kg)", min_value=150, max_value=400, value=310, step=10)
p_peak = st.sidebar.slider("Peak Irradiance (W/m²)", min_value=400, max_value=1200, value=750, step=50)

# --- CONSTANTS & CONFIGURATION ---
BATTERY_CAPACITY_WH = 3200  # Fixed 3.2 kWh limit
INITIAL_SOC = 100.0         # Race day start
TOTAL_HOURS = 9
DT_HOURS = 1 / 60           # 1-minute time steps
TOTAL_STEPS = TOTAL_HOURS * 60

# Physics constants
RHO = 1.225   # Air density kg/m3
G = 9.81      # Gravity m/s2
EFF = 0.95    # Hub motor + controller efficiency

# Convert velocity to m/s
v_ms = v_kmh / 3.6

# Calculate constant power output (Watts)
p_aero = 0.5 * RHO * cda * (v_ms ** 3)
p_roll = crr * mass * G * v_ms
p_out = (p_aero + p_roll) / EFF

# --- SIMULATION LOOP ---
soc = INITIAL_SOC
distance = 0.0
soc_history = []
distance_history = []
time_labels = []
error_triggered = False
error_time = 0

for step in range(TOTAL_STEPS):
    # Current hour in the drive day (0.0 at 8 AM to 9.0 at 5 PM)
    t = step * DT_HOURS
    
    # Gaussian distribution peaking at noon (Hour 4.0 of the 9-hour drive)
    sigma = 2.0
    # Math corrected: Irradiance * Gaussian * Efficiency * Area
    p_in = p_peak * np.exp(-((t - 4.0) ** 2) / (2 * (sigma ** 2))) * 0.22 * 6
    
    if not error_triggered:
        # Net energy exchange in this minute (Watt-hours)
        net_power_w = p_in - p_out
        energy_change_wh = net_power_w * DT_HOURS
        
        # Update SOC percentage
        soc += (energy_change_wh / BATTERY_CAPACITY_WH) * 100
        
        # Handle Cap at 100%
        if soc > 100.0:
            soc = 100.0
            
        # Handle Battery Depletion
        if soc <= 0.0:
            soc = 0.0
            error_triggered = True
            error_time = step
            
        # Accumulate distance if there is power
        distance += v_kmh * DT_HOURS
    else:
        # Car is dead; values freeze
        soc = 0.0

    # Log metrics for data visualization
    soc_history.append(soc)
    distance_history.append(distance)
    
    # Format absolute clock time string
    current_hour = 8 + int(t)
    current_min = int((t % 1) * 60)
    time_labels.append(f"{current_hour:02d}:{current_min:02d}")

# --- DISPLAY OUTPUTS ---
col1, col2 = st.columns(2)

with col1:
    if error_triggered:
        st.error(f"⚠️ BATTERY DEPLETED! Vehicle shut down at {time_labels[error_time]}.")
        st.metric(label="Final State of Charge", value="0.0%", delta="-100%")
    else:
        st.success("✅ Race day completed successfully!")
        st.metric(label="Final State of Charge", value=f"{soc:.1f}%")

with col2:
    st.metric(label="Total Distance Covered", value=f"{distance:.1f} km")

# --- VISUAL GRAPH ---
chart_data = pd.DataFrame({
    'Time': time_labels,
    'SOC (%)': soc_history,
    'Distance (km)': distance_history
}).set_index('Time')

st.line_chart(chart_data)
