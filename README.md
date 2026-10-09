# Kitticopter proportional control

EEE3094S Control Systems, UCT, Lab 2. Identify a simulated first-order plant from bench data, then
design and build an analogue proportional controller for it on Veroboard.

The kitticopter is a simulated vehicle that moves vertically under rotor thrust, drag and gravity.
Its parameters are unique per student, so the model has to be measured rather than taken from the
brief. A uDAQ box bridges the simulation and the physical circuit: the controller's command goes in
through an ADC, and the measured height comes back out through a DAC.

## The identified plant

Regressing settled velocity against raw input voltage across eight runs fits the gain and the hover
voltage together, so neither is assumed:

    v_inf = A (V_in - V_h)

    A   = 23.196 m/s/V      rms residual 0.022 m/s over eight runs
    T   =  9.537 s          least-squares fit to 1800 raw position samples
    k   =  0.9500 V/m       ratio of the two logged output columns
    V_h =  2.5016 V         fitted, and it lands on the design midpoint of 2.50 V

In terms of the aerodynamic constant `b`, with `A = a/b` and `T = 1/b`:

    G(s) = a / (s(s + b)) = 2.4322 / (s(s + 0.10485))

## The controller

Overshoot caps the gain through `zeta = 1/(2 sqrt(Kp k A T))`, and this plant has `kAT = 210`, so
nothing above `Kp = 0.0093` meets the 30 percent overshoot spec. The steady-state offset is
`dV/(Kp k)`, which that same small gain makes large. At a 1 m setpoint with a hand-trimmed bias the
floor sits two orders of magnitude above the ceiling and no proportional controller exists.

Two things open a window, both from reading the specification as written. The 8 percent is a
fraction of the setpoint and the brief fixes no setpoint, so a larger demonstration setpoint
relaxes the floor. And the offset is proportional to the bias trim error, so trimming against a
meter lowers it directly. The setpoint is then capped from above by the sensor, which saturates at
10 V or 10.5 m.

    Kp = 0.005 at a 7 m setpoint, bias trimmed to 2 mV
    worst corner: 26.7 percent overshoot, 4.6 percent offset
    Monte Carlo over 20000 builds: all three specs met, 100 percent

Three op-amp stages: a difference amplifier for the error, an inverting attenuator for `Kp`, then a
second difference amplifier that restores the sign while adding the hover bias.

## Layout

    analysis/           parameter extraction, gain window, resistor choice, closed-loop sim
    analysis/spice/     ngspice and LTspice netlists for the controller
    data/session-1/     raw CSV logs from the rig
    kicad/              schematic, ERC clean
    report/             LaTeX source and figures
    build_kitticopter.m Simulink model builder, parameterised on b
    sweep_corners.m     damping and overshoot at every tolerance corner
    session-1.md        bench log and the measurements
    session-2.md        design reasoning and the bench card

## Reproducing the analysis

    python analysis/stepfit.py                       # A, T and k from the logs
    python analysis/design.py --A 23.196 --T 9.537 --k 0.95 \
           --setpoint 7 --dist-volts 0.002 --mc 20000
    python analysis/simloop.py step --A 23.196 --T 9.537 --k 0.95 \
           --kp 0.005 --setpoint 7 --bias-error 0.002
    ngspice -b analysis/spice/controller.cir         # circuit check
    kicad-cli sch erc --output erc.rpt kicad/controller.kicad_sch

In MATLAB, `build_kitticopter` creates the Simulink model and `sweep_corners` prints the corner
table.

## A note on the drag corner

`A = a/b` and `T = 1/b` are both inversely proportional to the drag constant, so one error in `b`
moves them together and the product `AT` varies as its square. Treating `T` as the only affected
parameter understates the worst overshoot corner. `analysis/design.py` originally had that bug.
