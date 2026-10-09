# Session 2 runbook, proportional control

**Gate:** session 1 write-up showing a complete model, your controller design with its reasoning,
and the controller already built on Veroboard. A breadboard build caps the demo mark at 50 percent.

**Bring:** the Veroboard controller, spare resistors around your chosen pair, a trimpot, multimeter
leads, the corner table from `design.py`, printed plots from `simloop.py`, camera.

## Before the session

1. Run the parameter check, Appendix A2, once you trust your numbers. Three attempts total, aim
   above 60 percent on $A$ and $T$ and above 90 percent on $k$.
2. Get the window, not a number:
   ```
   python analysis/design.py --A <A> --T <T> --k <k> --setpoint <r> --dist-volts <trim error> \
       --mc 20000 --latex report/tables/design.tex
   ```
3. Pick components against it:
   ```
   python analysis/bom.py gain --kp-lo <lo> --kp-hi <hi>
   ```
   Put a trimpot in the feedback leg. It turns the 10 percent tolerance from a design constraint
   into something you dial out on the bench, and you still report the tolerance analysis.
4. Rehearse offline so nothing in the lab is a surprise:
   ```
   python analysis/simloop.py step --A <A> --T <T> --k <k> --kp <Kp> --setpoint <r> --bias-error 0.05
   python analysis/simloop.py sweep --over bias --A <A> --T <T> --k <k> --kp <Kp>
   python analysis/simloop.py demo --A <A> --T <T> --k <k> --kp <Kp> --plot report/figures/demo.png
   ```
   Know in advance what overshoot and what offset you expect, and whether your design ever hits
   the 0 to 5 V plant limit. If the bench disagrees with these numbers, the model is wrong and
   you say so in the report rather than quietly retuning until it looks nice.

## In the session

1. **Present** the design. Expect to be asked why that $K_p$ and not a larger one.
2. **Power the board alone first.** Check the rails before anything is connected to the
   kitticopter. A wiring fault found with a multimeter costs a minute; found through the ADC it
   costs the slot.
3. **Check the stages one at a time**: differential amplifier subtracts, gain stage multiplies by
   what you think it does, level shift outputs the hover bias. Measure, do not assume. The four
   resistors of the differential amplifier will not match, which is expected, and Appendix A1's
   advice is to trim the level rather than hunt for matched parts.
4. **Close the loop** and take one step. Compare against the rehearsal before touching anything.
5. **Trim the bias** if there is a steady offset. The offset is $\Delta V/(K_p k)$, so a small
   trim error is the whole of your 8 percent budget.
6. **Run the tests you need for the report**, not just the demo: a setpoint step for tracking and
   overshoot, and $K_p$ at plus and minus 10 percent on the trimpot to stand in for the component
   and drag tolerance.
7. **Photograph the board** before the demo. He keeps it afterwards.
8. **Demo** with De Maar's standard step sequence. Screenshot of the controller tracking the
   setpoint goes in the appendix, that is an explicit requirement.

## Afterwards

Write up against the rubric: a verdict per specification with the number that decides it, and a
diagnosis if one fails. A well-diagnosed failure marks better than an unexplained pass.

## Hand-in

Gradescope, assignment 8642539 in course EEE3094S_2026 (1347639), reached through the LTI link
in the Amathuba Lab 2 folder. Due Fri 9 Oct 23:59, with a late window to 11 Oct 23:59 that the
Amathuba calendar does not show. Penalty is 20 percent per day, and Lab 2 is a DP requirement.

The assignment takes a single PDF and then asks you to map pages to rubric questions, the same
as Lab 1. The filename does not matter. What matters is that each section starts on a page you
can point at, so check the page breaks before uploading rather than during.
