import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from scipy.optimize import fsolve
import re
import os

# --- 1. DATA LOADING AND PREPARATION ---

def load_data(filename):
    """
    Loads air property data from a text file.
    Assumes standard Sonntag formatting.
    """
    try:
        with open(filename, 'r') as f:
            content = f.read()
        
        # Fix potential formatting issues in source file if any
        # content = content.replace("1182.9", "1182.9") 
        
        # Extract all numbers using regex
        numbers = np.array([float(x) for x in re.findall(r"[-+]?\d*\.\d+|[-+]?\d+", content)])
        
        num_cols = 6
        num_rows = len(numbers) // num_cols
        
        # Reshape to matrix
        data_matrix = numbers[:num_rows*num_cols].reshape((num_rows, num_cols))
        return data_matrix
        
    except FileNotFoundError:
        print(f"Error: {filename} not found. Please ensure it is in the data/ folder.")
        return np.zeros((10, 6))
    except Exception as e:
        print(f"An error occurred loading data: {e}")
        return np.zeros((10, 6))

# Define path to data file (adjust path if running locally vs folder structure)
data_path = "data/AirDataSonntag.txt" 
# Fallback to current directory if file not found in data/
if not os.path.exists(data_path):
    data_path = "AirDataSonntag.txt"

data = load_data(data_path)

if data.sum() == 0:
    print("WARNING: Data loaded is empty. Check AirDataSonntag.txt file.")

# Assign Columns
T_data = data[:, 0]  # Temperature [K]
h_data = data[:, 1]  # Enthalpy [kJ/kg] (Using h column)
s_data = data[:, 5]  # Entropy [kJ/kg-K]

# Interpolation Functions
h = interp1d(T_data, h_data, kind='cubic', fill_value="extrapolate")
s = interp1d(T_data, s_data, kind='cubic', fill_value="extrapolate")

# --- SIMULATION CONSTANTS ---
T1 = 298.15
T3 = 1200.0
R = 0.287

print(">>> SIMULATION RESULTS <<<\n")

# --- PART 1: THERMAL EFFICIENCY (BRAYTON) ---

eta_c = 0.90
eta_t = 0.90

def thermal_efficiency(r):
    # Compressor
    s1 = s(T1)
    # Isentropic T2s: s(T2s) = s1 + R*ln(r)
    def s_diff_comp(T): return s(T) - s1 - R * np.log(r)
    T2s = fsolve(s_diff_comp, T1 * r**0.3)[0]
    
    h1 = h(T1)
    h2s = h(T2s)
    h2 = h1 + (h2s - h1) / eta_c
    
    # Turbine
    s3 = s(T3)
    # Isentropic T4s: s(T4s) = s3 - R*ln(r)
    def s_diff_turb(T): return s(T) - s3 + R * np.log(r)
    T4s = fsolve(s_diff_turb, T3 / r**0.3)[0]
    
    h3 = h(T3)
    h4s = h(T4s)
    h4 = h3 - eta_t * (h3 - h4s)
    
    w_net = (h3 - h4) - (h2 - h1)
    q_in = h3 - h2
    
    return w_net / q_in

r_values = np.linspace(2, 30, 20)
eta_values_percent = [thermal_efficiency(r) * 100 for r in r_values]

df1 = pd.DataFrame({
    "Compression ratio (r)": r_values,
    "Thermal Efficiency (%)": eta_values_percent
}).round(2)

print("--- PART 1 OUTPUT (Efficiency) ---")
print(df1.to_string(index=False))
print("\n" + "="*30 + "\n")


# --- PART 2: NET WORK ANALYSIS ---

def net_work(r):
    # Compressor
    s1 = s(T1)
    T2s = fsolve(lambda T: s(T) - s1 - R * np.log(r), T1 * r**0.3)[0]
    h1 = h(T1)
    h2s = h(T2s)
    h2 = h1 + (h2s - h1) / eta_c
    
    # Turbine
    s3 = s(T3)
    T4s = fsolve(lambda T: s(T) - s3 + R * np.log(r), T3 / r**0.3)[0]
    h3 = h(T3)
    h4s = h(T4s)
    h4 = h3 - eta_t * (h3 - h4s)
    
    return (h3 - h4) - (h2 - h1)

r_values_2 = np.linspace(2, 30, 12)
w_net_values = [net_work(r) for r in r_values_2]

# Find max
w_net_max = max(w_net_values)
r_opt = r_values_2[np.argmax(w_net_values)]

df2 = pd.DataFrame({
    "Compression Ratio (r)": np.round(r_values_2, 2),
    "Net Work (kJ/kg)": np.round(w_net_values, 2)
})

print("--- PART 2 OUTPUT (Net Work) ---")
print(df2.to_string(index=False))
print(f"\n Maximum Net Work: {w_net_max:.2f} kJ/kg")
print(f" Optimal Compression Ratio: r = {r_opt:.2f}")
print("\n" + "="*30 + "\n")


# --- PART 3: SENSITIVITY ANALYSIS (r=10) ---

def thermal_efficiency_sens(r, eta_c_val, eta_t_val):
    # Re-implementing logic for variable efficiencies
    s1 = s(T1)
    T2s = fsolve(lambda T: s(T) - s1 - R * np.log(r), T1 * r**0.3)[0]
    h1 = h(T1)
    h2s = h(T2s)
    h2 = h1 + (h2s - h1) / eta_c_val
    
    s3 = s(T3)
    T4s = fsolve(lambda T: s(T) - s3 + R * np.log(r), T3 / r**0.3)[0]
    h3 = h(T3)
    h4s = h(T4s)
    h4 = h3 - eta_t_val * (h3 - h4s)
    
    w_net = (h3 - h4) - (h2 - h1)
    q_in = h3 - h2
    return (w_net / q_in) * 100

r_fixed = 10
isentropic_efficiencies = [0.86, 0.88, 0.90, 0.92, 0.94]
eta_th_list = []

for eta in isentropic_efficiencies:
    eta_th = thermal_efficiency_sens(r_fixed, eta_c_val=eta, eta_t_val=eta)
    eta_th_list.append(eta_th)

df3 = pd.DataFrame({
    "n_c = n_t": isentropic_efficiencies,
    "Thermal Efficiency (%)": np.round(eta_th_list, 2)
})

print("--- PART 3 OUTPUT (Sensitivity r=10) ---")
print(df3.to_string(index=False))
print("\n" + "="*30 + "\n")


# --- PART 4: COMBINED CYCLE ---

T_stack = 460.0
T4_limit = 673.15 # 400C (Rankine Limit)
eta_rankine_1kg = 36.53
q_in_rankine = 2917.0 # Corrected Rankine Heat Input

def calculate_efficiencies_comb(r):
    # Brayton Cycle
    s1 = s(T1)
    T2s = fsolve(lambda T: s(T) - s1 - R * np.log(r), 350)[0]
    h1 = h(T1)
    h2s = h(T2s)
    h2 = h1 + (h2s - h1) / eta_c
    
    s3 = s(T3)
    T4s = fsolve(lambda T: s(T) - s3 + R * np.log(r), 1000)[0]
    h3 = h(T3)
    h4s = h(T4s)
    h4 = h3 - eta_t * (h3 - h4s)
    
    w_net_brayton = (h3 - h4) - (h2 - h1)
    q_in_brayton = h3 - h2
    eta_brayton = (w_net_brayton / q_in_brayton) * 100
    
    # Calculate real T4 from h4
    T4_real = fsolve(lambda T: h(T) - h4, 800)[0]
    
    # Combined Cycle Logic
    if T4_real >= T4_limit:
        h_stack = h(T_stack)
        q_to_rankine = max(0, h4 - h_stack)
        
        m_steam = q_to_rankine / q_in_rankine
        w_rankine = m_steam * (q_in_rankine * eta_rankine_1kg / 100)
        
        eta_combined = ((w_net_brayton + w_rankine) / q_in_brayton) * 100
    else:
        # Rankine cannot operate
        eta_combined = eta_brayton
        
    return eta_brayton, eta_combined, T4_real

r_values_comb = np.linspace(2, 30, 20)
results_comb = []

for r in r_values_comb:
    eta_b, eta_cmb, T4_real = calculate_efficiencies_comb(r)
    results_comb.append([r, eta_b, eta_cmb, T4_real])

df4 = pd.DataFrame(results_comb, columns=[
    "Compression Ratio (r)",
    "Brayton Efficiency (%)",
    "Combined Efficiency (%)",
    "T4 Exit Temp (K)"
]).round(2)

print("--- PART 4 OUTPUT (Combined Cycle) ---")
print(df4.to_string(index=False))

# Specific Point r = 13.59
r_max = 13.59
eta_b_max, eta_combined_max, T4_max = calculate_efficiencies_comb(r_max)

print(f"\nMax Combined Efficiency at r={r_max}")
print(f"Brayton Efficiency: {eta_b_max:.2f}%")
print(f"Combined Efficiency: {eta_combined_max:.2f}%")
print(f"T4 Exit Temperature: {T4_max:.2f} K")
