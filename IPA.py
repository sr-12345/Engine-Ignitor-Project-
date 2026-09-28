#Importing inputs and libraries

from UserInputs import IPA_mdot, P_c, P_feedsystem, Cd_IPA, Rho_IPA, pintle_elements_IPA
import numpy as np



#Single Phase Incompressible Model for IPA

def SPI(Cd_IPA,IPA_mdot,Rho_IPA,P_c,P_feedsystem):

    square_root = (2*Rho_IPA*(P_feedsystem-P_c))**0.5
    
    A = IPA_mdot/(Cd_IPA*square_root)

    return A


IPA_area = SPI(Cd_IPA,IPA_mdot,Rho_IPA,P_c,P_feedsystem)

#Coaxial Area for IPA

def Coaxial_IPA_Size(IPA_area):
    
    drill_d = 2*(IPA_area/np.pi)**0.5
    
    in_mm = drill_d*1000
    
    return in_mm


#Impinging Model

def Impinging_IPA_Size(IPA_area,pintle_elements_IPA):

    Area_per_element = IPA_area/pintle_elements_IPA

    Diameter_per_element = 2*(Area_per_element/np.pi)**0.5

    in_mm = Diameter_per_element*1000

    return in_mm

