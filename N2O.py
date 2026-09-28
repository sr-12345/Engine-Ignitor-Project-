#Importing inputs and libraries

from UserInputs import N2O_mdot, P_c, P_feedsystem, Cd_N2O, R_N2O, N2O_Temp, Gamma_N2O, pintle_elements_N2O
import numpy as np


#Nitrous Area Required - Choked Flow

#Condition for choked flow - critical pressure ratio for isentropic compressible flow

def ChokedFlowCriteria(Gamma_N2O, P_feedsystem, P_c):

    LHS = P_c / P_feedsystem

    RHS = (2 / (Gamma_N2O + 1))**(Gamma_N2O / (Gamma_N2O - 1))

    if LHS <= RHS:
        return 'Choked Flow Applies'
    else:
        return 'Choked Flow Not Applicable'



#Choked Flow Model for Nitrous (gaseous)

def ChokedNitrousAreaRequired(mdot, Cd, P_feed, Gamma, R, T_feed):

    root_term = Gamma / ( R * T_feed ) * ( 2 / (Gamma + 1) )**( (Gamma + 1) / (Gamma - 1) )

    A = mdot / (Cd * P_feed * ( root_term )**0.5)

    return A


nitrous_area = ChokedNitrousAreaRequired(N2O_mdot,Cd_N2O,P_c,Gamma_N2O,R_N2O,N2O_Temp)

#Unprocessed Hole size for Nitrous Coaxial Injector

def Coaxial_Nitrous_Size(nitrous_area):
    
    drill_d = 2*(nitrous_area/np.pi)**0.5
    
    in_mm = drill_d*1000
    
    return in_mm


def Coaxial_Drill_Diameter_Nitrous(nitrous_area, IPA_needle_outer_diameter):
    
    IPA_needle_displacement_area = np.pi * (IPA_needle_outer_diameter / 2)**2

    Total_drill_area = nitrous_area + IPA_needle_displacement_area

    drill_diameter = 2 * (Total_drill_area / np.pi)**0.5

    in_mm = drill_diameter * 1000

    return in_mm



#Impinging Model for Nitrous

def Impinging_Nitrous_Size(nitrous_area,pintle_elements_N2O):

    Area_per_element = nitrous_area/pintle_elements_N2O

    Diameter_per_element = 2*(Area_per_element/np.pi)**0.5

    in_mm = Diameter_per_element*1000

    return in_mm