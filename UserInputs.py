import numpy as np
import matplotlib.pyplot as plt

#USER INPUTS in SI UNITS (m, kg, s, K, Pa, etc.)

#Fuel Properties

N2O_mdot =      0.0197545 
IPA_mdot =      0.0079018
Cd_IPA =        0.82
Cd_N2O =        0.9
N2O_Temp =      290 #Room temperature - location dependent
Gamma_N2O =     1.29
R_N2O =         188.9
Rho_IPA =       786

#Feedsystem Properties

P_c =           8e5 #Chamber Pressure
P_feedsystem =  4.7e6

#Injector Properties

IPA_needle_outer_diameter = 0.003 #for the coaxial injector, this is the outer diameter of the IPA needle
pintle_elements_IPA = 4
pintle_elements_N2O = 4




#Engine Properties (used by Engine.py and Chamber.py)

#Design target
F_target =      50.0    #Target thrust
P_a =           101325  #Ambient Pressure at which the nozzle is designed to be ideally expanded, Pa
OF_ratio =      2.5     #Target Oxidiser-to-fuel mass ratio (N2O_mdot / IPA_mdot)


#Combustion gas properties at the chamber, for your chosen P_c and OF_ratio.
#Get these from RPA / NASA CEA (or rocketcea) for your propellant combination
#they are NOT the same as the N2O properties above, which describe the N2O feed BEFORE combustion.

Tc =            2500.0  #Chamber (combustion) temperature
Gamma_gas =     1.20    #Combustion gas specific heat ratio
MW_gas =        22.0    #Combustion gas molecular weight

#Efficiencies (real engines fall short of the ideal 1-D isentropic numbers;
#0.90-0.98 is a typical range, small engines sit toward the low end)
eta_cstar =     0.95    #c* efficiency
eta_cf =        0.95    #Thrust coefficient efficiency

#Chamber / nozzle geometry
L_star =                1.0   #Characteristic chamber length (0.5-2 m is typical for small engines)
contraction_ratio =     None  #Ac/At; set a number to fix it, or leave as None to use the empirical estimate in Chamber.py
conv_half_angle_deg =   45.0  #Convergent section half-angle, degrees
nozzle_half_angle_deg = 15.0  #Divergent (conical) nozzle half-angle, degrees