# simulation_microgrid_realdata_battery_coupure.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Charger les vraies données
data = pd.read_csv('D:\\malak\\code\\osai\\powerconsumption.csv')
data['Datetime'] = pd.to_datetime(data['Datetime'])
time_steps = data['Datetime']

# Données de charge et de vent
P_loadA_profile = data['PowerConsumption_Zone1'].values
P_loadB_profile = data['PowerConsumption_Zone2'].values
P_loadC_profile = data['PowerConsumption_Zone3'].values
wind_speed_profile = data['WindSpeed'].values

# Paramètres réseau
V = 400  # Tension triphasée
P_gen = 100000  # Générateur principal
battery_capacity = 100000  # Capacité max Wh
battery_charge = 50000  # Niveau initial
batt_power_max = 5000  # Puissance max (W)
dt = 600  # Intervalle en secondes (10 min)

# Historique pour affichage
gen_power_history = []
batt_power_history = []
loadA_history = []
loadB_history = []
loadC_history = []
net_balance_history = []
events_history = []
wind_power_history = []

# Fonctions utilitaires
def calculate_losses(current):
    return (current ** 2) * 0.01

def calculate_current(power):
    return power / V

def wind_power(V):
    rho = 1.225
    R = 38.5
    A = np.pi * R**2
    eta = 0.9
    P_rated = 1_500_000
    v_nominal = 11.8

    def Cp(theta_deg):
        return max(0.0, 0.45 * np.cos(np.radians(theta_deg))**1.5)

    theta = 0 if V <= v_nominal else min(25, 5 + (V - v_nominal) * 2)
    cp = Cp(theta)
    P = 0.5 * rho * A * V**3 * cp * eta
    return min(P, P_rated)

def gestion_batterie(net_balance, battery_charge):
    batt_action = 0
    event = "Aucun événement"
    
    if net_balance < 0:
        besoin = -net_balance
        if battery_charge > 0:
            batt_action = -min(besoin, batt_power_max, battery_charge * 3600 / dt)
            event = "Décharge batterie"
        else:
            event = "⚠️ Batterie vide"
    elif net_balance > 0 and battery_charge < battery_capacity:
        surplus = net_balance
        batt_action = min(surplus, batt_power_max, (battery_capacity - battery_charge) * 3600 / dt)
        event = "🔌 Charge batterie"

    return batt_action, event

def decision_coupures(net_balance, battery_charge, active_loads):
    if net_balance < 0 and battery_charge <= 0:
        if "Zone3" in active_loads:
            active_loads.remove("Zone3")
            return active_loads, "Coupure Zone 3"
        elif "Zone2" in active_loads:
            active_loads.remove("Zone2")
            return active_loads, "Coupure Zone 2"
        elif "Zone1" in active_loads:
            active_loads.remove("Zone1")
            return active_loads, "Coupure Zone 1"
        else:
            return active_loads, "Coupure totale"
    return active_loads, "Aucun événement"

# Simulation
active_loads = ["Zone1", "Zone2", "Zone3"]

for t in range(len(time_steps)):
    P_loadA = P_loadA_profile[t]
    P_loadB = P_loadB_profile[t]
    P_loadC = P_loadC_profile[t]
    V_wind = wind_speed_profile[t]

    P_wind = wind_power(V_wind)
    wind_power_history.append(P_wind)

    P_total_gen = P_gen + P_wind

    # Calcul de la charge active
    P_total_load = 0
    for zone in active_loads:
        if zone == "Zone1":
            P_total_load += P_loadA
        elif zone == "Zone2":
            P_total_load += P_loadB
        elif zone == "Zone3":
            P_total_load += P_loadC

    I_load = calculate_current(P_total_load)
    losses = len(active_loads) * calculate_losses(I_load)

    net_balance = P_total_gen - P_total_load - losses

    # Batterie en premier
    batt_power, event_batt = gestion_batterie(net_balance, battery_charge)
    net_balance += batt_power  # correction du bilan par l'action batterie
    battery_charge += (batt_power * dt) / 3600
    battery_charge = max(0, min(battery_charge, battery_capacity))

    # Coupure si la batterie ne suffit pas
    active_loads, event_cut = decision_coupures(net_balance, battery_charge, active_loads.copy())
    event_final = event_cut if "Coupure" in event_cut else event_batt

    # Historique
    gen_power_history.append(P_total_gen)
    batt_power_history.append(batt_power)
    loadA_history.append(P_loadA if "Zone1" in active_loads else 0)
    loadB_history.append(P_loadB if "Zone2" in active_loads else 0)
    loadC_history.append(P_loadC if "Zone3" in active_loads else 0)
    net_balance_history.append(net_balance)
    events_history.append(event_final)

# Affichage
plt.figure(figsize=(16,12))

plt.subplot(3,1,1)
plt.plot(time_steps, gen_power_history, label="Générateur + Éolien (W)", color='black')
plt.plot(time_steps, loadA_history, label="Zone 1", color='green')
plt.plot(time_steps, loadB_history, label="Zone 2", color='blue')
plt.plot(time_steps, loadC_history, label="Zone 3", color='orange')
plt.plot(time_steps, wind_power_history, label="Éolien seul", color='cyan')
plt.axhline(0, color='gray', linestyle='--')
plt.ylabel("Puissance (W)")
plt.legend()
plt.grid(True)

plt.subplot(3,1,2)
plt.plot(time_steps, batt_power_history, label="Batterie (W)", color='purple')
plt.axhline(0, color='gray', linestyle='--')
plt.ylabel("Action Batterie (W)")
plt.legend()
plt.grid(True)

plt.subplot(3,1,3)
plt.plot(time_steps, net_balance_history, label="Bilan Réseau", color='red')
plt.axhline(0, color='black', linestyle='--')
plt.xlabel("Temps")
plt.ylabel("Bilan (W)")
plt.legend()
plt.grid(True)

plt.suptitle("Simulation Microgrid : Éolien + Batterie avec Coupures Priorisées")
plt.tight_layout()
plt.show()

print("Simulation terminée !")
