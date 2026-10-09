# Lab 2 prep tasks, your working

The write-up now lives in the report itself: `report/tex/system_modelling.tex`, compiled to
`report/main.pdf` pages 4 to 9. Print those pages and present them at the gate. A tutor will ask
you to explain a line, so read it through before you go rather than at the bench.

Under each task is what a marker looks for, in the brief's own terms. Your working goes in the
blank space.

---

## (a) Block diagram of the kitticopter system

> Draw a block diagram of the kitticopter system, representing all of the given information.

What earns marks:
- gravity summed at the plant input, not at the output
- sensor gain $k$ on both the feedback path and the reference conversion, so the summer compares
  volts with volts
- level shift as its own summing junction, not folded into $K_p$
- ADC on the forward path (your circuit into the simulation), DAC on the feedback path
- the 0 to 5 V limit marked on the plant input

Your diagram: report Figure 1 (free-body) and Figure 2 (block diagram), `system_modelling.tex:14-72`.




---

## (b) Differential equation for the acceleration

> Derive a differential equation describing the acceleration of the kitticopter.

What earns marks:
- all three forces present, with the right sign on drag
- an explicit statement that everything is normalised to unit mass, and what that does to the
  units of your coefficients
- gravity as a constant term, with a sentence on why it is not a state

Your working: Equation (1) in the report, `system_modelling.tex` subsection 2.2, with the unit-mass and constant-disturbance arguments in the numbered list above it.




---

## (c) Open-loop and closed-loop transfer functions

> Derive the open-loop transfer function $G(s)$ relating the velocity and rotor thrust, and the
> closed-loop transfer function $G_{cl}(s)$ relating position to the setpoint $x(t)$.

What earns marks:
- velocity level first, giving a first-order form, with a line on why that is the tractable one
  to identify
- the integrator to position shown explicitly
- closed loop in standard second-order form, with $\omega_n$ and $\zeta$ read off it

Your working: Equations (2) to (6), report subsection 2.4. Velocity level first, then the integrator to position, then standard second-order form.




---

## (d) Error, disturbance, type number and expected tracking

> Derive closed-loop transfer functions describing (i) the position error in relation to the
> setpoint, and (ii) the effect of gravity on the position output. Determine the type number and
> describe the tracking performance you expect under proportional control.

What earns marks:
- both transfer functions, derived not quoted
- type number from the poles of the **loop gain** at the origin
- final value theorem applied to each, with the verdict in the brief's words: infinite, finite
  or zero
- the reason the two answers differ, in terms of where the integrator sits relative to where the
  disturbance enters

Your working: Equations (7) to (10), report subsection 2.5. Type 1, zero step error, disturbance offset d/(Kp k), and the paragraph on why they differ.




---

## (e) Optional: simulation model

> Create a Simulink model of the kitticopter system and bring it with you to the lab.

Optional in the brief. `analysis/simloop.py` already does this in Python, including the
saturation Simulink would not give you for free, so build the Simulink version only if you want
it running on the lab PC.

---

## Before you present

Check your own answers for consistency:

```
python analysis/checkprep.py --a <a> --b <b> --k <k> --kp <Kp> \
    --claim-A <your A> --claim-T <your T> --claim-type <your type> \
    --claim-zeta <your zeta> --claim-step-error <your answer> \
    --claim-offset <your answer> --bias 0.05
```

It checks consistency, not correctness. It cannot see your block diagram, so the interface and
the disturbance node are still yours to get right.
