#Sizes the throat and exit of a converging-diverging nozzle from a target thrust,
#using standard 1-D isentropic (ideal) rocket relations, then scales by efficiencies
#to get "real" performance. Also splits the resulting mass flow into oxidizer/fuel
#mass flows using your target O/F ratio, so those numbers can feed straight into IPA.py / N2O.py.



from UserInputs import F_target, P_c, P_a, OF_ratio, Tc, Gamma_gas, MW_gas, eta_cstar, eta_cf
import numpy as np

R_universal = 8314.46   #universal gas constant, J/(kmol K)
g0 = 9.80665             #standard gravity, m/s^2


#Specific gas constant for the combustion gas

def SpecificGasConstant(MW_gas):

    #R = R_universal / MW    (MW in g/mol == kg/kmol)

    return R_universal / MW_gas


#Vandenkerckhove function, Gamma(gamma) - shows up in c* and area-ratio relations

def VandenkerckhoveFunction(Gamma_gas):

    return np.sqrt(Gamma_gas) * (2 / (Gamma_gas + 1))**((Gamma_gas + 1) / (2 * (Gamma_gas - 1)))


#Ideal characteristic velocity, c* = sqrt(R*Tc) / Gamma(gamma)

def CharacteristicVelocity(Gamma_gas, R_gas, Tc):

    return np.sqrt(R_gas * Tc) / VandenkerckhoveFunction(Gamma_gas)


#Exit Mach number from the static-to-chamber pressure ratio Pe/Pc
#(isentropic relation, rearranged for M)

def ExitMachFromPressureRatio(Pe_over_Pc, Gamma_gas):

    return np.sqrt(2 / (Gamma_gas - 1) * (Pe_over_Pc**(-(Gamma_gas - 1) / Gamma_gas) - 1))


#Area ratio Ae/At for a given exit Mach number (isentropic area-Mach relation)

def AreaRatioFromMach(Me, Gamma_gas):

    return (1 / Me) * ((2 / (Gamma_gas + 1)) * (1 + (Gamma_gas - 1) / 2 * Me**2))**(
        (Gamma_gas + 1) / (2 * (Gamma_gas - 1)))


#Ideal thrust coefficient CF and the resulting expansion ratio, for chamber
#pressure P_c, exit pressure P_e and ambient pressure P_a.
#
#CF = sqrt( 2*gamma^2/(gamma-1) * (2/(gamma+1))^((gamma+1)/(gamma-1)) * [1-(Pe/Pc)^((gamma-1)/gamma)] )
#     + epsilon*(Pe - Pa)/Pc
#
#The first term is the momentum thrust, the second is the pressure thrust (zero
#when the nozzle is ideally expanded, i.e. Pe = Pa).

def ThrustCoefficient(Gamma_gas, P_c, P_e, P_a):

    pressure_ratio = P_e / P_c
    Me = ExitMachFromPressureRatio(pressure_ratio, Gamma_gas)
    epsilon = AreaRatioFromMach(Me, Gamma_gas)

    momentum_term = np.sqrt(
        2 * Gamma_gas**2 / (Gamma_gas - 1)
        * (2 / (Gamma_gas + 1))**((Gamma_gas + 1) / (Gamma_gas - 1))
        * (1 - pressure_ratio**((Gamma_gas - 1) / Gamma_gas))
    )
    pressure_term = epsilon * (P_e - P_a) / P_c

    CF = momentum_term + pressure_term

    return CF, epsilon


#Size the engine (throat, exit, mass flow, Isp) for a target thrust F.
#
#At   = F / (CF * Pc)          <- definition of thrust coefficient, rearranged
#mdot = Pc * At / c*           <- definition of c*, rearranged
#Isp  = F / (mdot * g0)
#
#P_e defaults to P_a (ideal/on-design expansion). Pass a different P_e, or use
#EpsilonToPe() below, to design for a fixed expansion ratio instead.

def SizeEngine(F_target, P_c, P_a, Tc, Gamma_gas, MW_gas, eta_cstar, eta_cf, P_e=None):

    if P_e is None:
        P_e = P_a   #ideally expanded at the design altitude

    R_gas = SpecificGasConstant(MW_gas)

    cstar_ideal = CharacteristicVelocity(Gamma_gas, R_gas, Tc)
    cstar = eta_cstar * cstar_ideal

    CF_ideal, epsilon = ThrustCoefficient(Gamma_gas, P_c, P_e, P_a)
    CF = eta_cf * CF_ideal

    At = F_target / (CF * P_c)
    Dt = 2 * np.sqrt(At / np.pi)

    Ae = epsilon * At
    De = 2 * np.sqrt(Ae / np.pi)

    mdot = P_c * At / cstar
    Isp = F_target / (mdot * g0)

    return {
        "R_gas": R_gas,
        "cstar_ideal": cstar_ideal,
        "cstar": cstar,
        "CF_ideal": CF_ideal,
        "CF": CF,
        "epsilon": epsilon,
        "P_e": P_e,
        "At": At,
        "Dt_m": Dt,
        "Dt_mm": Dt * 1000,
        "Ae": Ae,
        "De_m": De,
        "De_mm": De * 1000,
        "mdot": mdot,
        "Isp": Isp,
    }


#Split total mass flow into oxidizer (N2O) and fuel (IPA) mass flows for a
#target O/F ratio (OF = mdot_ox / mdot_fuel):
#
#mdot_ox   = mdot * OF / (1 + OF)
#mdot_fuel = mdot / (1 + OF)

def SplitMassFlow(mdot, OF_ratio):

    mdot_ox = mdot * OF_ratio / (1 + OF_ratio)
    mdot_fuel = mdot / (1 + OF_ratio)

    return mdot_ox, mdot_fuel


#Find the exit pressure Pe that gives a target expansion ratio epsilon.
#Useful if you want to design for a fixed nozzle area ratio instead of ideal
#expansion at P_a. Solved by bisection on the supersonic branch (Pe/Pc < 1).

def EpsilonToPe(epsilon, Gamma_gas, P_c):

    if epsilon < 1:
        raise ValueError("Expansion ratio must be >= 1.")

    lo, hi = 1e-6, 1.0   #Pe/Pc between ~0 and 1 (supersonic branch)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        Me = ExitMachFromPressureRatio(mid, Gamma_gas)
        eps_mid = AreaRatioFromMach(Me, Gamma_gas)
        if eps_mid > epsilon:
            lo = mid       #need a higher Pe/Pc (less expansion) to shrink epsilon
        else:
            hi = mid
    pressure_ratio = 0.5 * (lo + hi)

    return pressure_ratio * P_c


#Characteristic (stay) time of the combustion gas in the chamber:
#tau = L* * c* / (R * Tc)     - a useful cross-check alongside L* itself.

def StayTime(L_star, cstar, R_gas, Tc):

    return L_star * cstar / (R_gas * Tc)



# Example run using the values in UserInputs.py

if __name__ == "__main__":

    results = SizeEngine(F_target, P_c, P_a, Tc, Gamma_gas, MW_gas, eta_cstar, eta_cf)
    mdot_ox, mdot_fuel = SplitMassFlow(results["mdot"], OF_ratio)

    print("ENGINE SIZING")
    print(f"  Target thrust        {F_target:.1f} N")
    print(f"  Chamber pressure     {P_c/1e5:.2f} bar")
    print(f"  c* (real)            {results['cstar']:.1f} m/s   (ideal {results['cstar_ideal']:.1f} m/s)")
    print(f"  CF (real)            {results['CF']:.3f}          (ideal {results['CF_ideal']:.3f})")
    print(f"  Expansion ratio      {results['epsilon']:.2f}")
    print(f"  Exit pressure        {results['P_e']/1e5:.3f} bar")
    print(f"  Throat diameter      {results['Dt_mm']:.2f} mm")
    print(f"  Exit diameter        {results['De_mm']:.2f} mm")
    print(f"  Total mass flow      {results['mdot']*1000:.2f} g/s")
    print(f"    N2O (ox)           {mdot_ox*1000:.2f} g/s")
    print(f"    IPA (fuel)         {mdot_fuel*1000:.2f} g/s")
    print(f"  Isp                  {results['Isp']:.1f} s")