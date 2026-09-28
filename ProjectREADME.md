# Engine Ignitor Project

The tool is designed for sizing the fuel injector for the ignitor of an IPA fuelled, N2O oxidised bipropellant rocket engine. Enter your target propellant mass-flow rates, feed-system and chamber conditions and the tool outputs orifice diameters for both a coaxial and an impinging (multi-orifice) injector for both propellants. Matplotlib is also used to generate sensitivity plots for the chosen discharge coefficients of the feed system.


# Features

Coaxial and impinging orifice sizing results for both IPA and N2O, shown side by side.

N2O coaxial orifice size accounts for the thickness of the IPA pipe/needle* as the N2O annulus has to fit around the IPA needle, so the drilled hole diameter is sized from the required N2O flow area plus the needle's cross-sectional area, not just the flow area alone. It should be noted that the IPA orifice size should be determined first and then the needle OD can be decided (from manufacturer specifications) and then fed back into the sizing tool to obtain the N2O orifice size.

*in practice for the fuel injector of an ignitor, hypodermic needles are needed for the mass-flow rates considered.

Chamber and feed pressures shown in Pa and Bar simultaneously, updating live as you type in the GUI.

Choked-flow check: N2O sizing assumes choked (compressible) flow through the orifice. The app checks this explicitly (ChokedFlowCriteria) and warns if your chamber/feed pressure combination would not actually choke.

Sensitivity plots (drill diameter vs. discharge coefficient Cd) for both propellants, docked permanently on the right side of the window and refreshed in place every time you click Calculate.

Export results (inputs + outputs, as JSON) via File > Export Results or Ctrl+E, for record-keeping or feeding into other tools.

Input validation with clear error messages (e.g. feed pressure must exceed chamber pressure, Cd must be between 0 and 1, orifice counts must be positive integers).

# Further Work and Improvements

Sizing the IPA orifice and then determining the needle OD and then updating the tool to find the N2O orifice is inefficient, so having a set of known needle OD's for a variety of gauges would allow automatic calculation of the N2O orifice. The challenge is that for a given gauge of needle, different manufacturers achieve different OD's, so allowing the user to manually input their needle OD is safest albeit slow.

Adding an "oficice type" dropdown menu to set the Cd to more realistic values would be useful. For example, sharp-edged orifice ≈ 0.6–0.65, drilled hole with L/D of 2–4 ≈ 0.7–0.8, chamfered or rounded entry ≈ 0.85–0.95.