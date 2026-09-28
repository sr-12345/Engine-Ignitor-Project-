import numpy as np
import matplotlib.pyplot as plt

#USER INPUTS

#Fuel Properties

N2O_mdot =      0.0197545
IPA_mdot =      0.0079018
Cd_IPA =        0.82
Cd_N2O =        0.9
N2O_Temp =      290 #ROOM TEMP APPROX. - Location dependent
Gamma_N2O =     1.29
R_N2O =         188.9
Rho_IPA =       786

#Feedsystem/Engine Properties

P_c =           8e5 #CHAMBER PRESSURE
P_feedsystem =  4.7e6

#Injector Properties

IPA_needle_outer_diameter = 0.003 #for coaxial injector, this is the outer diameter of the IPA needle

pintle_elements_IPA = 4
pintle_elements_N2O = 4

