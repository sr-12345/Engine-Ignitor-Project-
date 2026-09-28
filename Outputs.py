#Importing inputs and libraries

from UserInputs import IPA_mdot, P_c, P_feedsystem, Cd_IPA, Rho_IPA, Gamma_N2O, N2O_mdot, R_N2O, N2O_Temp, Cd_N2O
from IPA import SPI, Coaxial_IPA_Size, IPA_area
from N2O import ChokedFlowCriteria, ChokedNitrousAreaRequired, Coaxial_Nitrous_Size, nitrous_area
import numpy as np
import matplotlib.pyplot as plt

#Input validation function

def validate_inputs(Cd, m_dot, Rho, P_c, P_feedsystem):

    if not (0 < Cd <= 1):
        raise ValueError(f"Discharge Coefficient (Cd) must be between 0 and 1. Received: {Cd}")
    if m_dot <= 0:
        raise ValueError(f"Mass Flow Rate (m_dot) must be greater than 0. Received: {m_dot}")
    if Rho <= 0:
        raise ValueError(f"Density (Rho) must be greater than 0. Received: {Rho}")
    if P_c <= 0 or P_feedsystem <= 0:
        raise ValueError(f"Pressures (P_c and P_feedsystem) must be greater than 0. Received: P_c={P_c}, P_feedsystem={P_feedsystem}")
    if P_feedsystem <= P_c:
        raise ValueError(f"Feed system pressure (P_feedsystem) must be greater than chamber pressure (P_c). Received: P_feedsystem={P_feedsystem}, P_c={P_c}")

try:
    # Call the validate_inputs function with the parameters you want to validate
    validate_inputs(Cd_IPA, IPA_mdot, Rho_IPA, P_c, P_feedsystem)
    print("All inputs are valid!")
except ValueError as e:
    # Catch and print any validation errors
    print(f"Validation Error: {e}")


print("IPA Area Required is " + str(SPI(Cd_IPA,IPA_mdot,Rho_IPA,P_c,P_feedsystem)) + " m^2")

print("IPA Coaxial Hole Diameter " + str(Coaxial_IPA_Size(IPA_area)) + " mm")

print("Test for Nitrous choked flow: " + str(ChokedFlowCriteria(Gamma_N2O,P_feedsystem,P_c)))

