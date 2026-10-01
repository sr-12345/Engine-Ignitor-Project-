
#Sizes the combustion chamber and conical nozzle from the throat area (from
#Engine.py), a characteristic length L*, and a contraction ratio.

#The chamber volume up to the throat is defined by L*:
#   Vc = L* * At
#L* is a propellant-dependent empirical number representing how much volume
#the gas needs to finish burning before it reaches the throat (0.5-2 m is a
#common range for small liquid engines).
#
#That volume is split between a cylindrical section and the convergent cone
#leading to the throat; the geometry below solves for the cylindrical length
#once the cone's volume is subtracted off.

from UserInputs import L_star, contraction_ratio, conv_half_angle_deg, nozzle_half_angle_deg
import numpy as np


#Empirical contraction ratio estimate, Ac/At = 8*Dt^-0.6 + 1.25 (Dt in cm).
#A common first-pass curve fit for small liquid engines - only use this if you
#haven't chosen your own contraction ratio; prefer a value you can justify
#(3-6 is a common design range) over relying on this alone.

def ContractionRatioEstimate(Dt_m):

    Dt_cm = Dt_m * 100

    return 8 * Dt_cm**(-0.6) + 1.25


#Size the chamber: contraction ratio, chamber diameter, and the cylindrical
#length needed once the convergent cone's volume is subtracted from L**At.
#
#Vc = L* * At                                   <- definition of L*
#V_cone = (pi/3) * L_conv * (Rc^2 + Rc*Rt + Rt^2)   <- frustum (truncated cone) volume
#V_cyl = Vc - V_cone
#L_cyl = V_cyl / Ac
#
#contraction_ratio: pass a number to fix Ac/At, or None to use the empirical
#estimate above.

def SizeChamber(At, L_star, contraction_ratio=None, conv_half_angle_deg=45.0):

    Rt = np.sqrt(At / np.pi)

    if contraction_ratio is None:
        CR = ContractionRatioEstimate(2 * Rt)
        CR_source = "empirical"
    else:
        CR = contraction_ratio
        CR_source = "user"

    Ac = CR * At
    Rc = np.sqrt(Ac / np.pi)

    Vc = L_star * At

    theta = np.radians(conv_half_angle_deg)
    L_conv = (Rc - Rt) / np.tan(theta)
    V_conv = np.pi / 3 * L_conv * (Rc**2 + Rc * Rt + Rt**2)

    V_cyl = Vc - V_conv
    if V_cyl <= 0:
        raise ValueError(
            "L* is too small: the convergent cone alone exceeds the target chamber "
            "volume. Increase L*, lower the contraction ratio, or steepen the "
            "convergent half-angle."
        )
    L_cyl = V_cyl / Ac

    return {
        "contraction_ratio": CR,
        "contraction_ratio_source": CR_source,
        "Rt_m": Rt,
        "Rc_m": Rc,
        "Dc_mm": 2 * Rc * 1000,
        "Ac": Ac,
        "Vc_m3": Vc,
        "Vc_cm3": Vc * 1e6,
        "L_conv_mm": L_conv * 1000,
        "V_conv_m3": V_conv,
        "L_cyl_mm": L_cyl * 1000,
        "L_total_mm": (L_cyl + L_conv) * 1000,
        "L_over_D": L_cyl / (2 * Rc),
    }


#Size the conical divergent (nozzle) section: exit radius from the expansion
#ratio, cone length from the half-angle, plus the 80%-bell-equivalent length
#and divergence loss factor for reference (a real bell nozzle is shorter than
#a 15-degree cone for the same area ratio; lambda below corrects CF for the
#extra radial component of exit velocity a cone has that a bell does not).
#
#L_cone = (Re - Rt) / tan(half_angle)
#lambda = (1 + cos(half_angle)) / 2

def SizeNozzle(At, epsilon, half_angle_deg=15.0):

    Rt = np.sqrt(At / np.pi)
    Re = Rt * np.sqrt(epsilon)

    alpha = np.radians(half_angle_deg)
    L_cone = (Re - Rt) / np.tan(alpha)

    #80% bell length is commonly approximated as 80% of an equivalent 15-degree cone
    L_bell_80 = 0.8 * (Re - Rt) / np.tan(np.radians(15.0))

    divergence_factor = (1 + np.cos(alpha)) / 2

    return {
        "Re_m": Re,
        "De_mm": 2 * Re * 1000,
        "L_cone_mm": L_cone * 1000,
        "L_bell_80_mm": L_bell_80 * 1000,
        "divergence_factor": divergence_factor,
    }



# Example using the values in UserInputs.py, chained after Engine.py

if __name__ == "__main__":

    from Engine import SizeEngine, StayTime
    from UserInputs import F_target, P_c, P_a, Tc, Gamma_gas, MW_gas, eta_cstar, eta_cf

    engine = SizeEngine(F_target, P_c, P_a, Tc, Gamma_gas, MW_gas, eta_cstar, eta_cf)
    chamber = SizeChamber(engine["At"], L_star, contraction_ratio, conv_half_angle_deg)
    nozzle = SizeNozzle(engine["At"], engine["epsilon"], nozzle_half_angle_deg)
    tau = StayTime(L_star, engine["cstar"], engine["R_gas"], Tc)

    print("CHAMBER / NOZZLE SIZING")
    print(f"  L*                   {L_star*1000:.0f} mm    stay time {tau*1000:.2f} ms")
    print(f"  Contraction ratio    {chamber['contraction_ratio']:.2f} ({chamber['contraction_ratio_source']})")
    print(f"  Chamber diameter     {chamber['Dc_mm']:.2f} mm")
    print(f"  Cylinder length      {chamber['L_cyl_mm']:.1f} mm   (L/D {chamber['L_over_D']:.2f})")
    print(f"  Convergent length    {chamber['L_conv_mm']:.1f} mm")
    print(f"  Chamber volume       {chamber['Vc_cm3']:.1f} cm^3")
    print(f"  Injector-to-throat   {chamber['L_total_mm']:.1f} mm")
    print(f"  Divergent length     {nozzle['L_cone_mm']:.1f} mm (cone, {nozzle_half_angle_deg:.0f} deg half-angle)")
    print(f"  80% bell (approx)    {nozzle['L_bell_80_mm']:.1f} mm")