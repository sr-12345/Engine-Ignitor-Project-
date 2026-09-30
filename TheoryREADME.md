# Engine & Injector Sizing — Theory Reference

This document explains the physics and equations behind `Engine.py`, `Chamber.py`,
`IPA.py`, and `N2O.py`. It's meant to be read alongside the code: each section below
corresponds to one or more functions in those files.

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

| Symbol | Meaning | Units |
|---|---|---|
| $F$ | Thrust | N |
| $P_c$ | Chamber pressure | Pa |
| $P_e$ | Nozzle exit pressure | Pa |
| $P_a$ | Ambient pressure | Pa |
| $P_0$ | Upstream (feed) stagnation pressure | Pa |
| $T_c$ | Chamber (combustion) temperature | K |
| $\gamma$ | Ratio of specific heats, $c_p/c_v$ | – |
| $R$ | Specific gas constant, $R = \bar{R}/M$ | J/(kg·K) |
| $\bar{R}$ | Universal gas constant (8314.46) | J/(kmol·K) |
| $M$ | Molecular weight | kg/kmol (g/mol) |
| $c^*$ | Characteristic velocity | m/s |
| $C_F$ | Thrust coefficient | – |
| $A_t, A_e$ | Throat / exit area | m² |
| $D_t, D_e$ | Throat / exit diameter | m |
| $\varepsilon$ | Expansion (area) ratio, $A_e/A_t$ | – |
| $\dot m$ | Mass flow rate | kg/s |
| $I_{sp}$ | Specific impulse | s |
| $g_0$ | Standard gravity (9.80665) | m/s² |
| $L^*$ | Characteristic chamber length | m |
| $V_c$ | Chamber volume (injector face to throat) | m³ |
| $C_R$ | Contraction ratio, $A_c/A_t$ | – |
| $C_d$ | Discharge coefficient | – |
| $\rho$ | Density | kg/m³ |
| $A$ | Flow (orifice) area | m² |

---

## 1. Engine sizing (`Engine.py`)

### 1.1 Specific gas constant

The combustion gas's specific gas constant comes from the universal gas constant
and the gas's molecular weight:

$$
R = \frac{\bar{R}}{M}
$$

Implemented in `SpecificGasConstant()`.

### 1.2 The Vandenkerckhove function

Several isentropic relations share a recurring combination of $\gamma$ terms, usually
called the Vandenkerckhove function:

$$
\Gamma(\gamma) = \sqrt{\gamma}\left(\frac{2}{\gamma+1}\right)^{\frac{\gamma+1}{2(\gamma-1)}}
$$

Implemented in `VandenkerckhoveFunction()`.

### 1.3 Characteristic velocity, $c^*$

$c^*$ measures how effectively the combustion chamber converts propellant chemical
energy into hot, high-pressure gas — it depends only on the propellant combination
and chamber conditions, **not** on the nozzle:

$$
c^* = \frac{\sqrt{R T_c}}{\Gamma(\gamma)}
$$

Implemented in `CharacteristicVelocity()`. A real chamber never reaches the ideal
value (incomplete mixing, finite reaction rate, heat loss to the walls), so the
code scales it by an efficiency:

$$
c^*_{\text{real}} = \eta_{c^*} \, c^*_{\text{ideal}}, \qquad \eta_{c^*} \approx 0.90\text{–}0.98
$$

### 1.4 Isentropic exit Mach number

For isentropic flow, the static-to-chamber pressure ratio at any station sets the
local Mach number:

$$
\frac{P}{P_c} = \left(1+\frac{\gamma-1}{2}M^2\right)^{-\frac{\gamma}{\gamma-1}}
$$

Solved for $M$, this gives the exit Mach number from the exit pressure ratio:

$$
M_e = \sqrt{\frac{2}{\gamma-1}\left[\left(\frac{P_e}{P_c}\right)^{-\frac{\gamma-1}{\gamma}}-1\right]}
$$

Implemented in `ExitMachFromPressureRatio()`.

### 1.5 Area ratio from Mach number

The isentropic area–Mach relation gives the nozzle area ratio needed to reach a
given Mach number:

$$
\frac{A}{A^*} = \frac{1}{M}\left[\frac{2}{\gamma+1}\left(1+\frac{\gamma-1}{2}M^2\right)\right]^{\frac{\gamma+1}{2(\gamma-1)}}
$$

Implemented in `AreaRatioFromMach()`; used to convert $M_e$ into the expansion ratio
$\varepsilon = A_e/A_t$.

### 1.6 Thrust coefficient, $C_F$

$C_F$ is the "amplification" the nozzle gives to the basic $P_c A_t$ force. It has
a momentum term (always positive) and a pressure term (zero only when the nozzle
is *ideally expanded*, $P_e = P_a$):

$$
C_F = \underbrace{\sqrt{\frac{2\gamma^2}{\gamma-1}\left(\frac{2}{\gamma+1}\right)^{\frac{\gamma+1}{\gamma-1}}\left[1-\left(\frac{P_e}{P_c}\right)^{\frac{\gamma-1}{\gamma}}\right]}}_{\text{momentum term}} \;+\; \underbrace{\varepsilon\,\frac{P_e-P_a}{P_c}}_{\text{pressure term}}
$$

Implemented in `ThrustCoefficient()`, which returns both $C_F$ and the expansion
ratio $\varepsilon$ used to get there. As with $c^*$, a real nozzle falls short of
the ideal value (boundary-layer friction, nozzle divergence losses), scaled by:

$$
C_{F,\text{real}} = \eta_{C_F} \, C_{F,\text{ideal}}, \qquad \eta_{C_F} \approx 0.90\text{–}0.98
$$

When under- or over-expansion is severe, the flow can separate from the nozzle
wall before reaching the geometric exit — a classic rule of thumb (the **Summerfield
criterion**) is that separation becomes likely once $P_e/P_a \lesssim 0.4$.

### 1.7 Sizing from target thrust

Rearranging the definitions of $C_F$ and $c^*$ gives the throat area and mass flow
directly from a target thrust:

$$
A_t = \frac{F}{C_F P_c}
\qquad\qquad
\dot m = \frac{P_c A_t}{c^*}
\qquad\qquad
D_t = 2\sqrt{\frac{A_t}{\pi}}
$$

$$
A_e = \varepsilon A_t
\qquad\qquad
D_e = 2\sqrt{\frac{A_e}{\pi}}
\qquad\qquad
I_{sp} = \frac{F}{\dot m\, g_0}
$$

All implemented in `SizeEngine()`.

### 1.8 Splitting mass flow by O/F ratio

For a target oxidizer-to-fuel mass ratio $O/F = \dot m_{ox}/\dot m_{fuel}$:

$$
\dot m_{ox} = \dot m\,\frac{O/F}{1+O/F}
\qquad\qquad
\dot m_{fuel} = \frac{\dot m}{1+O/F}
$$

Implemented in `SplitMassFlow()` — this is what connects `Engine.py`'s output to
the `mdot_IPA` / `mdot_N2O` inputs that `IPA.py` and `N2O.py` expect.

### 1.9 Solving for exit pressure at a fixed expansion ratio

If you'd rather fix the expansion ratio $\varepsilon$ than design for ideal expansion
at $P_a$, `EpsilonToPe()` inverts §1.5 numerically (bisection on $P_e/P_c \in (0,1)$)
to find the $P_e$ that produces the requested $\varepsilon$ — there's no closed form
for this inversion, so it's solved iteratively rather than with a single equation.

### 1.10 Stay time

A simple cross-check on $L^*$ (see §2.1): the gas's mean residence time in the
chamber, estimated from the chamber's stagnation density and $c^*$:

$$
\tau = \frac{L^* \, c^*}{R\, T_c}
$$

Implemented in `StayTime()`.

---

## 2. Chamber & nozzle geometry (`Chamber.py`)

### 2.1 Characteristic length, $L^*$, and chamber volume

$L^*$ is an empirical, propellant- and injector-dependent number representing how
much chamber volume the gas needs to finish reacting before reaching the throat.
It defines the chamber volume (injector face to throat) directly:

$$
V_c = L^* A_t
$$

Typical values are roughly 0.5–2 m for small liquid engines — treat your first
choice as a starting point to refine (from literature, similar engines, or your
own hot-fire data), not a known-good number.

### 2.2 Contraction ratio

The contraction ratio $C_R = A_c/A_t$ sets the chamber cross-sectional area:

$$
A_c = C_R\,A_t
\qquad\qquad
R_c = \sqrt{\frac{A_c}{\pi}}
$$

If you don't fix $C_R$ yourself, `ContractionRatioEstimate()` uses a common
empirical curve fit (throat diameter $D_t$ in cm):

$$
C_R \approx 8\,D_t^{-0.6} + 1.25
$$

This is a first-pass estimate only — verify it against your own reference before
relying on it for a real design.

### 2.3 Convergent section volume

The convergent section is modeled as a cone frustum (flat cone from the chamber
radius $R_c$ down to the throat radius $R_t$, at half-angle $\theta$):

$$
L_{conv} = \frac{R_c - R_t}{\tan\theta}
\qquad\qquad
V_{conv} = \frac{\pi}{3}\,L_{conv}\left(R_c^2 + R_c R_t + R_t^2\right)
$$

(the standard formula for the volume of a truncated cone).

### 2.4 Cylindrical section length

Whatever volume $L^*$ calls for that *isn't* used by the convergent cone becomes
the straight cylindrical section:

$$
V_{cyl} = V_c - V_{conv}
\qquad\qquad
L_{cyl} = \frac{V_{cyl}}{A_c}
$$

If $L^*$ is too small — i.e. the convergent cone alone would exceed $V_c$ — this
has no physical solution (`SizeChamber()` raises an error rather than returning a
negative length). A useful sanity check is the cylinder's length-to-diameter
ratio, $L_{cyl}/D_c$; most designs land somewhere around 1–3.

### 2.5 Divergent nozzle geometry

For a simple conical nozzle at half-angle $\alpha$, the exit radius comes straight
from the expansion ratio, and the cone length follows the same geometry as the
convergent side:

$$
R_e = R_t\sqrt{\varepsilon}
\qquad\qquad
L_{cone} = \frac{R_e - R_t}{\tan\alpha}
$$

A common design choice is a 15° half-angle cone, or a shorter contoured ("bell")
nozzle approximated as 80% of the equivalent 15° cone's length:

$$
L_{bell,80\%} \approx 0.8\,L_{cone,15^\circ}
$$

A conical nozzle also loses some thrust to the radial component of the exit
velocity (a bell nozzle, which straightens the flow, does not). This is
captured by the divergence loss factor:

$$
\lambda = \frac{1+\cos\alpha}{2}
$$

All implemented in `SizeNozzle()`.

---

## 3. IPA injector — incompressible liquid flow (`IPA.py`)

IPA is injected as a liquid, so its flow is modeled with the standard
**single-phase incompressible (SPI)** orifice equation — the same relation used
for any liquid flowing through a sharp-edged orifice under a pressure drop:

$$
\dot m = C_d\, A\, \sqrt{2\rho\,\Delta P}, \qquad \Delta P = P_{feed} - P_c
$$

Rearranged for the required flow area, given a target mass flow:

$$
A = \frac{\dot m}{C_d \sqrt{2\rho\,\Delta P}}
$$

Implemented in `SPI()`. The resulting area is converted to a drill diameter for
a single round orifice (coaxial injector):

$$
D = 2\sqrt{\frac{A}{\pi}}
$$

or split evenly across $n$ identical holes (impinging injector), each with area
$A/n$:

$$
D_{hole} = 2\sqrt{\frac{A}{n\pi}}
$$

Implemented in `Coaxial_IPA_Size()` and `Impinging_IPA_Size()`.

---

## 4. N2O injector — choked compressible flow (`N2O.py`)

N2O is injected as a gas (assumed vapor — see §5), so its flow uses the
**choked (sonic) compressible flow** relation instead of the incompressible one.

### 4.1 Choking criterion

Gas flow through an orifice accelerates as the downstream pressure drops, but
velocity can't exceed the local speed of sound at the orifice — once the
downstream-to-upstream pressure ratio falls below a critical value, the flow is
**choked**, and mass flow becomes independent of everything downstream:

$$
\frac{P_c}{P_0} \le \left(\frac{2}{\gamma+1}\right)^{\frac{\gamma}{\gamma-1}}
$$

Implemented in `ChokedFlowCriteria()`. This is why the model needs the **N2O feed
pressure** $P_0$, not the chamber pressure, as its driving pressure — chamber
pressure only matters for checking whether this condition holds.

### 4.2 Choked mass flow

For choked, calorically-perfect-gas flow:

$$
\dot m = C_d\, A\, P_0 \sqrt{\frac{\gamma}{R\,T_0}\left(\frac{2}{\gamma+1}\right)^{\frac{\gamma+1}{\gamma-1}}}
$$

Rearranged for the required flow area:

$$
A = \frac{\dot m}{C_d\, P_0 \sqrt{\dfrac{\gamma}{R\,T_0}\left(\dfrac{2}{\gamma+1}\right)^{\frac{\gamma+1}{\gamma-1}}}}
$$

Implemented in `ChokedNitrousAreaRequired()`. Notice $P_c$ does not appear in this
equation at all: once choked, mass flow depends only on the upstream state
$(P_0, T_0)$ — a useful thing to keep in mind when tuning your feed pressure to
hit a target mass flow.

### 4.3 Coaxial drill diameter — accounting for the IPA needle

In a coaxial pintle injector, N2O flows through the annular gap around the IPA
needle, not through an open circular hole. Sizing the drill from the N2O flow
area alone would leave too little room once the needle occupies part of the
bore, so the needle's cross-sectional footprint is added to the required flow
area *before* solving for the drill diameter:

$$
A_{needle} = \pi\left(\frac{D_{needle}}{2}\right)^2
\qquad\qquad
A_{drill} = A_{N_2O} + A_{needle}
\qquad\qquad
D_{drill} = 2\sqrt{\frac{A_{drill}}{\pi}}
$$

Implemented in `Coaxial_Drill_Diameter_Nitrous()`. The resulting annular flow
area is exactly $A_{N_2O}$, i.e. the drilled hole minus the needle's cross-section:

$$
A_{annulus} = \frac{\pi}{4}\left(D_{drill}^2 - D_{needle}^2\right) = A_{N_2O}
$$

### 4.4 Impinging model

Same idea as the IPA impinging case — split the required flow area evenly across
$n$ identical holes:

$$
D_{hole} = 2\sqrt{\frac{A_{N_2O}}{n\pi}}
$$

Implemented in `Impinging_Nitrous_Size()`.

---

## 5. Assumptions & limitations

Worth keeping in mind before trusting these numbers for hardware:

- **1-D, isentropic, calorically perfect gas.** All of `Engine.py`'s relations
  assume frictionless, adiabatic, reversible flow with constant $\gamma$. Real
  chambers and nozzles fall short — that's what $\eta_{c^*}$ and $\eta_{C_F}$ are
  for, but they're still estimates until validated against test data.
- **Combustion gas properties ($T_c$, $\gamma$, $M$) must come from a
  thermochemistry source** (NASA CEA, RPA, or similar) for your actual
  propellant combination, chamber pressure, and O/F ratio. They are *not* the
  same as the N2O feed properties used in `N2O.py`, which describe the
  oxidizer *before* combustion.
- **N2O must actually be gaseous at the injector** for the choked-flow model in
  §4 to apply. N2O's vapor pressure is roughly 50–60 bar in the 20–25 °C range;
  if your feed pressure exceeds the saturation pressure at your feed
  temperature, the N2O is liquid or two-phase, and this model does not apply —
  a different model (e.g. Homogeneous Equilibrium Model or the Dyer model) is
  needed instead.
- **Discharge coefficients ($C_d$) are inputs, not outputs**, in these scripts.
  Sharp-edged short orifices are typically $C_d \approx 0.6$–$0.65$; drilled
  holes with some length-to-diameter ratio are higher; a chamfered or rounded
  entry is higher still. Treat any value you haven't measured (e.g. via a cold
  flow test) as a placeholder.
- **$L^*$ and contraction ratio are design choices**, not physical constants —
  the empirical estimate in `ContractionRatioEstimate()` is a rough starting
  point, and $L^*$ should come from data on similar engines/propellants where
  possible.
- **The nozzle contour is a simple cone**, not a bell. The 80%-bell-length
  approximation and divergence factor $\lambda$ in §2.5 are commonly used
  stand-ins, not a substitute for a proper method-of-characteristics contour if
  you need one.

---

## 6. References

- Sutton, G. P., and Biblarz, O., *Rocket Propulsion Elements*, Wiley.
- Huzel, D. K., and Huang, D. H., *Modern Engineering for Design of Liquid-Propellant
  Rocket Engines*, NASA SP-125.
- Humble, R. W., Henry, G. N., and Larson, W. J., *Space Propulsion Analysis and
  Design*, McGraw-Hill.
- NASA CEA (Chemical Equilibrium with Applications) — for combustion gas
  properties ($T_c$, $\gamma$, $M$) at your chamber pressure and O/F ratio.
