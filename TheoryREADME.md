# Engine & Injector Sizing — Theory Reference

This document explains the physics and equations behind `Engine.py`, `Chamber.py`, `IPA.py`, and `N2O.py`. It's meant to be read alongside the code: each section below corresponds to one or more functions in those files.

---

## Contents

- [Nomenclature](#nomenclature)
- [1. Engine sizing (`Engine.py`)](#1-engine-sizing-enginepy)
- [2. Chamber & nozzle geometry (`Chamber.py`)](#2-chamber--nozzle-geometry-chamberpy)
- [3. IPA injector — incompressible liquid flow (`IPA.py`)](#3-ipa-injector--incompressible-liquid-flow-ipapy)
- [4. N2O injector — choked compressible flow (`N2O.py`)](#4-n2o-injector--choked-compressible-flow-n2opy)
- [5. Assumptions & limitations](#5-assumptions--limitations)
- [6. References](#6-references)

---

## Nomenclature

| Symbol       | Meaning                                      | Units          |
|--------------|----------------------------------------------|----------------|
| $F$          | Thrust                                       | N              |
| $P_c$        | Chamber pressure                             | Pa             |
| $P_e$        | Nozzle exit pressure                         | Pa             |
| $P_a$        | Ambient pressure                             | Pa             |
| $P_0$        | Upstream (feed) stagnation pressure          | Pa             |
| $T_c$        | Chamber (combustion) temperature             | K              |
| $\gamma$     | Ratio of specific heats, $c_p/c_v$           | –              |
| $R$          | Specific gas constant, $R = \bar{R}/M$       | J/(kg·K)       |
| $\bar{R}$    | Universal gas constant (8314.46)             | J/(kmol·K)     |
| $M$          | Molecular weight                             | kg/kmol (g/mol)|
| $c^*$        | Characteristic velocity                      | m/s            |
| $C_F$        | Thrust coefficient                           | –              |
| $A_t, A_e$   | Throat / exit area                           | m²             |
| $D_t, D_e$   | Throat / exit diameter                       | m              |
| $\varepsilon$| Expansion (area) ratio, $A_e/A_t$            | –              |
| $\dot{m}$    | Mass flow rate                               | kg/s           |
| $I_{sp}$     | Specific impulse                             | s              |
| $g_0$        | Standard gravity (9.80665)                  | m/s²           |
| $L^*$        | Characteristic chamber length                | m              |
| $V_c$        | Chamber volume (injector face to throat)     | m³             |
| $C_R$        | Contraction ratio, $A_c/A_t$                | –              |
| $C_d$        | Discharge coefficient                        | –              |
| $\rho$       | Density                                      | kg/m³          |
| $A$          | Flow (orifice) area                          | m²             |

---

## 1. Engine sizing (`Engine.py`)

### 1.1 Specific gas constant

The combustion gas's specific gas constant comes from the universal gas constant and the gas's molecular weight:

$$
R = \frac{\bar{R}}{M}
$$

Implemented in `SpecificGasConstant()`.

---

### 1.2 The Vandenkerckhove function

Several isentropic relations share a recurring combination of $\gamma$ terms, usually called the Vandenkerckhove function:

$$
\Gamma(\gamma) = \sqrt{\gamma}\left(\frac{2}{\gamma+1}\right)^{\frac{\gamma+1}{2(\gamma-1)}}
$$

Implemented in `VandenkerckhoveFunction()`.

---

### 1.3 Characteristic velocity, $c^*$

$c^*$ measures how effectively the combustion chamber converts propellant chemical energy into hot, high-pressure gas — it depends only on the propellant combination and chamber conditions, **not** on the nozzle:

$$
c^* = \frac{\sqrt{R T_c}}{\Gamma(\gamma)}
$$

Implemented in `CharacteristicVelocity()`. A real chamber never reaches the ideal value (incomplete mixing, finite reaction rate, heat loss to the walls), so the code scales it by an efficiency:

$$
c^*_{\text{real}} = \eta_{c^*} \, c^*_{\text{ideal}}, \qquad \eta_{c^*} \approx 0.90\text{–}0.98
$$

---

### 1.4 Isentropic exit Mach number

For isentropic flow, the static-to-chamber pressure ratio at any station sets the local Mach number:

$$
\frac{P}{P_c} = \left(1+\frac{\gamma-1}{2}M^2\right)^{-\frac{\gamma}{\gamma-1}}
$$

Solved for $M$, this gives the exit Mach number from the exit pressure ratio:

$$
M_e = \sqrt{\frac{2}{\gamma-1}\left[\left(\frac{P_e}{P_c}\right)^{-\frac{\gamma-1}{\gamma}}-1\right]}
$$

Implemented in `ExitMachFromPressureRatio()`.

---

### 1.5 Area ratio from Mach number

The isentropic area–Mach relation gives the nozzle area ratio needed to reach a given Mach number:

$$
\frac{A}{A^*} = \frac{1}{M}\left[\frac{2}{\gamma+1}\left(1+\frac{\gamma-1}{2}M^2\right)\right]^{\frac{\gamma+1}{2(\gamma-1)}}
$$

Implemented in `AreaRatioFromMach()`; used to convert $M_e$ into the expansion ratio $\varepsilon = A_e/A_t$.

---

### 1.6 Thrust coefficient, $C_F$

$C_F$ is the "amplification" the nozzle gives to the basic $P_c A_t$ force. It has a momentum term (always positive) and a pressure term (zero only when the nozzle is *ideally expanded*, $P_e = P_a$):

$$
C_F = \underbrace{\sqrt{\frac{2\gamma^2}{\gamma-1}\left(\frac{2}{\gamma+1}\right)^{\frac{\gamma+1}{\gamma-1}}\left[1-\left(\frac{P_e}{P_c}\right)^{\frac{\gamma-1}{\gamma}}\right]}}_{\text{momentum term}} \;+\; \underbrace{\varepsilon\,\frac{P_e-P_a}{P_c}}_{\text{pressure term}}
$$

Implemented in `ThrustCoefficient()`.

---

## 2. Chamber & nozzle geometry (`Chamber.py`)

### 2.1 Characteristic length, $L^*$, and chamber volume

$L^*$ is an empirical, propellant- and injector-dependent number representing how much chamber volume the gas needs to finish reacting before reaching the throat. It defines the chamber volume (injector face to throat) directly:

$$
V_c = L^* A_t
$$

---

## 3. IPA injector — incompressible liquid flow (`IPA.py`)

The IPA injector uses the **single-phase incompressible (SPI)** orifice equation:

$$
\dot{m} = C_d\, A\, \sqrt{2\rho\,\Delta P}, \qquad \Delta P = P_{feed} - P_c
$$

Rearranged for the required flow area:

$$
A = \frac{\dot{m}}{C_d \sqrt{2\rho\,\Delta P}}
$$

---

## 4. N2O injector — choked compressible flow (`N2O.py`)

The N2O injector uses the **choked (sonic) compressible flow** relation:

$$
\dot{m} = C_d\, A\, P_0 \sqrt{\frac{\gamma}{R\,T_0}\left(\frac{2}{\gamma+1}\right)^{\frac{\gamma+1}{\gamma-1}}}
$$

---

## 5. Assumptions & limitations

- **1-D, isentropic, calorically perfect gas.**
- **Combustion gas properties ($T_c$, $\gamma$, $M$) must come from a thermochemistry source.**
- **N2O must actually be gaseous at the injector.**
- **Discharge coefficients ($C_d$) are inputs, not outputs.**

---

## 6. References

- Sutton, G. P., and Biblarz, O., *Rocket Propulsion Elements*, Wiley.
- Huzel, D. K., and Huang, D. H., *Modern Engineering for Design of Liquid-Propellant Rocket Engines*, NASA SP-125.
- Humble, R. W., Henry, G. N., and Larson, W. J., *Space Propulsion Analysis and Design*, McGraw-Hill.
- NASA CEA (Chemical Equilibrium with Applications).