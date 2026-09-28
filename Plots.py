#Importing inputs and libraries

from UserInputs import IPA_mdot, P_c, P_feedsystem, Cd_IPA, Rho_IPA, Gamma_N2O, N2O_mdot, R_N2O, N2O_Temp, Cd_N2O
from IPA import SPI, Coaxial_IPA_Size, IPA_area
from N2O import ChokedFlowCriteria, ChokedNitrousAreaRequired, Coaxial_Nitrous_Size, nitrous_area
import numpy as np
import matplotlib.pyplot as plt

#C_d graphing for IPA

Plotting_C_d_IPA = np.linspace(0.1,1,100) #horizontal axis
Plotting_A_values_IPA = SPI(Plotting_C_d_IPA,IPA_mdot,Rho_IPA,P_c,P_feedsystem) #vertical axis
Plotting_d_values_IPA = Coaxial_IPA_Size(Plotting_A_values_IPA)

plt.figure()
plt.plot(Plotting_C_d_IPA,Plotting_d_values_IPA)
plt.title("IPA Drill Hole Diameter vs Discharge Coefficient")
plt.xlabel("Discharge Coefficient")
plt.ylabel("Drill Hole Diameter (mm)")
plt.show()

Plotting_m_dot_values_IPA = np.linspace(0.1,0.05,100)
Plotting_d_values_mdot_IPA = Coaxial_IPA_Size(SPI(Cd_IPA,Plotting_m_dot_values_IPA,Rho_IPA,P_c,P_feedsystem))

plt.figure()
plt.plot(Plotting_m_dot_values_IPA,Plotting_d_values_mdot_IPA)
plt.title("IPA Drill Hole Diameter vs Mass Flow Rate")
plt.xlabel("Mass Flow Rate (kg/s)")
plt.ylabel("Drill Hole Diameter (mm)")
plt.show()

#3D Plotting of C_d vs m_dot vs IPA Hole Diameter

from mpl_toolkits.mplot3d import Axes3D

# Generate data for the 3D plot
# Create a meshgrid for C_d and m_dot
C_d_mesh_IPA, m_dot_mesh_IPA = np.meshgrid(Plotting_C_d_IPA, Plotting_m_dot_values_IPA)

# Calculate IPA hole diameter for each combination of C_d and m_dot
IPA_diameter_mesh = Coaxial_IPA_Size(SPI(C_d_mesh_IPA, m_dot_mesh_IPA, Rho_IPA, P_c, P_feedsystem))

# Create the 3D plot
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

# Plot the surface
surf = ax.plot_surface(C_d_mesh_IPA, m_dot_mesh_IPA, IPA_diameter_mesh, cmap='viridis')

# Add labels and title
ax.set_title("3D Plot of C_d vs m_dot vs IPA Hole Diameter")
ax.set_xlabel("Discharge Coefficient (C_d)")
ax.set_ylabel("Mass Flow Rate (m_dot) [kg/s]")
ax.set_zlabel("IPA Hole Diameter (mm)")

# Add a color bar for reference
fig.colorbar(surf, ax=ax,orientation='vertical', shrink=0.5, aspect=10, pad=0.15)

plt.show()


#Cd graphing for Nitrous

Plotting_C_d_nitrous = np.linspace(0.1,1,100) #horizontal axis
Plotting_A_values_nitrous = ChokedNitrousAreaRequired(N2O_mdot,Plotting_C_d_nitrous,P_c,Gamma_N2O,R_N2O,N2O_Temp) #vertical axis
Plotting_d_values_nitrous = Coaxial_Nitrous_Size(Plotting_A_values_nitrous)

plt.figure()
plt.plot(Plotting_C_d_nitrous,Plotting_d_values_nitrous)
plt.title("Nitrous Drill Hole Diameter vs Discharge Coefficient")
plt.xlabel("Discharge Coefficient")
plt.ylabel("Drill Hole Diameter (mm)")
plt.show()

Plotting_m_dot_values_N20 = np.linspace(0.01,0.05,100)
Plotting_d_values_mdot_N20 = Coaxial_Nitrous_Size(ChokedNitrousAreaRequired(Plotting_m_dot_values_N20,Cd_N2O,P_c,Gamma_N2O,R_N2O,N2O_Temp))

plt.figure()
plt.plot(Plotting_m_dot_values_N20,Plotting_d_values_mdot_N20)
plt.title("Nitrous Drill Hole Diameter vs Mass Flow Rate")
plt.xlabel("Mass Flow Rate (kg/s)")
plt.ylabel("Drill Hole Diameter (mm)")
plt.show()


# 3D Plotting of C_d vs m_dot vs N2O Hole Diameter

# Create a meshgrid for C_d and m_dot for N2O
C_d_mesh_N20, m_dot_mesh_N20 = np.meshgrid(Plotting_C_d_nitrous, Plotting_m_dot_values_N20)

# Calculate N2O hole diameter for each combination of C_d and m_dot
N20_diameter_mesh = Coaxial_Nitrous_Size(
    ChokedNitrousAreaRequired(m_dot_mesh_N20, C_d_mesh_N20, P_c, Gamma_N2O, R_N2O, N2O_Temp)
)

# Create the 3D plot
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

# Plot the surface
surf = ax.plot_surface(C_d_mesh_N20, m_dot_mesh_N20, N20_diameter_mesh, cmap='plasma')

# Add labels and title
ax.set_title("3D Plot of C_d vs m_dot vs N2O Hole Diameter")
ax.set_xlabel("Discharge Coefficient (C_d)")
ax.set_ylabel("Mass Flow Rate (m_dot) [kg/s]")
ax.set_zlabel("N2O Hole Diameter (mm)")

# Add a color bar for reference
fig.colorbar(surf, ax=ax, orientation='vertical', shrink=0.5, aspect=10, pad=0.15)

# Show the plot
plt.show()