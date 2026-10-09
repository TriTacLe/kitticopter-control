# Session 1 runbook, system identification

**Gate:** show a tutor or Mr De Maar your write-up of prep tasks (a) to (d) before you touch
anything. No write-up, no session.

**Bring:** breadboard, jumper wires, small screwdriver and cutters, the resistor values from
`bom.py steptest`, a printed copy of your block diagram, a USB stick or laptop for the CSVs.

**You have an hour.** The order below puts everything that blocks something else first.

## 1. Find the hover voltage, 10 minutes

Everything downstream depends on this number. Bring the input up slowly until the kitticopter
holds height, and write down $V_{\text{hover}}$. This is the zero point of your controller and
the baseline $V_1$ of every step test. If you skip it and step from 0 V, the cat falls and the
trace is useless.

Record it in the log sheet as a number with the date, not in your head.

## 2. Build the step-test divider, 10 minutes

Appendix A1 circuit 1, values already picked by

```
python analysis/bom.py steptest --v1 <V_hover> --v2 <target, at or below 5>
```

Picked ahead of the session for the brief's nominal hover of 2.5 V, stepping to 3.5 V off the
15 V rail. Build from the first row and only re-run the script if the measured hover is more
than about 0.2 V off 2.5 V.

| R1 top | pot R2 | R3 bottom | swing (V) |
| --- | --- | --- | --- |
| 56k | 5k | 12k | 2.47 to 3.49 |
| 12k | 1k | 2.7k | 2.58 to 3.54 |
| 10k | 1k | 2.2k | 2.50 to 3.64 |

Swing the pot from one end to the other and check with a multimeter that the bottom sits at
$V_{\text{hover}}$ and the top stays at or below 5 V. Above 5 V the kitticopter ignores the
extra and your measured step size is a lie.

## 3. Step tests, 25 minutes

At least three runs, and vary the step size across them so you can see whether $A$ is really
constant. Start logging before the step, hold well past settling, and let the trace run long
enough that the velocity plateau is obvious.

Naming matters, because `stepfit.py` globs the folder:

```
data/session-1/step_<amplitude>_<run>.csv       e.g. step_1p0_a.csv
```

After each run, eyeball the trace. A step that saturates, starts from the wrong baseline or is
cut off before the velocity plateaus is a run you should repeat now rather than discover at
home.

## 4. Sensor constant, 5 minutes

Command a known height, read the voltage, repeat at two or three heights. Write down the pairs.

```
python analysis/stepfit.py sensor --volts <v1> <v2> <v3> --metres <m1> <m2> <m3>
```

Appendix A2 calls $k$ trivial to get and expects over 90 percent accuracy on it, so this is the
cheapest of the three numbers and the one most annoying to be missing later.

## 5. Before you leave, 5 minutes

- copy the CSVs off the lab machine
- photograph the bench, the divider and the simulator panel, captioned for the report
- note anything odd: a run you discarded, a wobble in the hover point, a reading that drifted

## Afterwards, same evening

```
python analysis/stepfit.py fit data/session-1/*.csv --plot report/figures/step_response.png
```

Check the two $T$ estimates agree and that the spread across runs is under about 20 percent. If
it is not, you have a bad run in the set, not a bad plant.

**Do not open the Appendix A2 parameter check yet.** Three attempts total. Submit only once the
repeats agree with each other and the model reproduces the measured trace.

## Gain table, print this page

Session 2 has no laptop, so the $K_p$ window is precomputed over the grid you are likely to land
on. Read the row nearest your measured $A$, $T$ and $k$. Generated with

```
python analysis/lookup.py --setpoint 1.0 --dist-volts 0.05 --k-values 0.6 0.8 1.0 1.2 1.4 --markdown
```

| $A$ | $T$ | $k$ | $K_p$ low | $K_p$ high | aim | Resistor pair |
| --- | --- | --- | --- | --- | --- | --- |
| 0.40 | 0.80 | 0.60 | 1.270 | 3.415 | 2.083 | 1k / 1k, gain 2.00 |
| 0.40 | 0.80 | 0.80 | 0.953 | 2.561 | 1.562 | voltage follower, no resistors needed |
| 0.40 | 0.80 | 1.00 | 0.762 | 2.049 | 1.250 | voltage follower, no resistors needed |
| 0.40 | 0.80 | 1.20 | 0.635 | 1.708 | 1.041 | voltage follower, no resistors needed |
| 0.40 | 0.80 | 1.40 | 0.544 | 1.464 | 0.893 | voltage follower, no resistors needed |
| 0.40 | 1.20 | 0.60 | 1.270 | 3.415 | 2.083 | 1k / 1k, gain 2.00 |
| 0.40 | 1.20 | 0.80 | 0.953 | 2.561 | 1.562 | voltage follower, no resistors needed |
| 0.40 | 1.20 | 1.00 | 0.762 | 2.049 | 1.250 | voltage follower, no resistors needed |
| 0.40 | 1.20 | 1.20 | 0.635 | 1.708 | 1.041 | voltage follower, no resistors needed |
| 0.40 | 1.20 | 1.40 | 0.544 | 1.464 | 0.893 | voltage follower, no resistors needed |
| 0.40 | 1.60 | 0.60 | 1.270 | 3.415 | 2.083 | 1k / 1k, gain 2.00 |
| 0.40 | 1.60 | 0.80 | 0.953 | 2.561 | 1.562 | voltage follower, no resistors needed |
| 0.40 | 1.60 | 1.00 | 0.762 | 2.049 | 1.250 | voltage follower, no resistors needed |
| 0.40 | 1.60 | 1.20 | 0.635 | 1.708 | 1.041 | voltage follower, no resistors needed |
| 0.40 | 1.60 | 1.40 | 0.544 | 1.464 | 0.893 | voltage follower, no resistors needed |
| 0.40 | 2.00 | 0.60 | 1.270 | 3.031 | 1.962 | 1k / 1k, gain 2.00 |
| 0.40 | 2.00 | 0.80 | 0.953 | 2.273 | 1.472 | voltage follower, no resistors needed |
| 0.40 | 2.00 | 1.00 | 0.762 | 1.818 | 1.177 | voltage follower, no resistors needed |
| 0.40 | 2.00 | 1.20 | 0.635 | 1.515 | 0.981 | voltage follower, no resistors needed |
| 0.40 | 2.00 | 1.40 | 0.544 | 1.299 | 0.841 | voltage follower, no resistors needed |
| 0.40 | 2.50 | 0.60 | 1.270 | 2.424 | 1.755 | 12k / 15k, gain 1.80 |
| 0.40 | 2.50 | 0.80 | 0.953 | 1.818 | 1.316 | voltage follower, no resistors needed |
| 0.40 | 2.50 | 1.00 | 0.762 | 1.455 | 1.053 | voltage follower, no resistors needed |
| 0.40 | 2.50 | 1.20 | 0.635 | 1.212 | 0.877 | voltage follower, no resistors needed |
| 0.40 | 2.50 | 1.40 | 0.544 | 1.039 | 0.752 | voltage follower, no resistors needed |
| 0.60 | 0.80 | 0.60 | 1.270 | 3.415 | 2.083 | 1k / 1k, gain 2.00 |
| 0.60 | 0.80 | 0.80 | 0.953 | 2.561 | 1.562 | voltage follower, no resistors needed |
| 0.60 | 0.80 | 1.00 | 0.762 | 2.049 | 1.250 | voltage follower, no resistors needed |
| 0.60 | 0.80 | 1.20 | 0.635 | 1.708 | 1.041 | voltage follower, no resistors needed |
| 0.60 | 0.80 | 1.40 | 0.544 | 1.464 | 0.893 | voltage follower, no resistors needed |
| 0.60 | 1.20 | 0.60 | 1.270 | 3.367 | 2.068 | 1k / 1k, gain 2.00 |
| 0.60 | 1.20 | 0.80 | 0.953 | 2.525 | 1.551 | voltage follower, no resistors needed |
| 0.60 | 1.20 | 1.00 | 0.762 | 2.020 | 1.241 | voltage follower, no resistors needed |
| 0.60 | 1.20 | 1.20 | 0.635 | 1.684 | 1.034 | voltage follower, no resistors needed |
| 0.60 | 1.20 | 1.40 | 0.544 | 1.443 | 0.886 | voltage follower, no resistors needed |
| 0.60 | 1.60 | 0.60 | 1.270 | 2.525 | 1.791 | 12k / 15k, gain 1.80 |
| 0.60 | 1.60 | 0.80 | 0.953 | 1.894 | 1.343 | voltage follower, no resistors needed |
| 0.60 | 1.60 | 1.00 | 0.762 | 1.515 | 1.075 | voltage follower, no resistors needed |
| 0.60 | 1.60 | 1.20 | 0.635 | 1.263 | 0.896 | voltage follower, no resistors needed |
| 0.60 | 1.60 | 1.40 | 0.544 | 1.082 | 0.768 | voltage follower, no resistors needed |
| 0.60 | 2.00 | 0.60 | 1.270 | 2.020 | 1.602 | 3.3k / 5.6k, gain 1.59 |
| 0.60 | 2.00 | 0.80 | 0.953 | 1.515 | 1.202 | voltage follower, no resistors needed |
| 0.60 | 2.00 | 1.00 | 0.762 | 1.212 | 0.961 | voltage follower, no resistors needed |
| 0.60 | 2.00 | 1.20 | 0.635 | 1.010 | 0.801 | voltage follower, no resistors needed |
| 0.60 | 2.00 | 1.40 | 0.544 | 0.866 | 0.687 | no E12 pair fits, use a trim pot |
| 0.60 | 2.50 | 0.60 | 1.270 | 1.616 | 1.433 | 1.2k / 2.7k, gain 1.44 |
| 0.60 | 2.50 | 0.80 | 0.953 | 1.212 | 1.075 | voltage follower, no resistors needed |
| 0.60 | 2.50 | 1.00 | 0.762 | 0.970 | 0.860 | no E12 pair fits, use a trim pot |
| 0.60 | 2.50 | 1.20 | 0.635 | 0.808 | 0.716 | no E12 pair fits, use a trim pot |
| 0.60 | 2.50 | 1.40 | 0.544 | 0.693 | 0.614 | no E12 pair fits, use a trim pot |
| 0.80 | 0.80 | 0.60 | 1.270 | 3.415 | 2.083 | 1k / 1k, gain 2.00 |
| 0.80 | 0.80 | 0.80 | 0.953 | 2.561 | 1.562 | voltage follower, no resistors needed |
| 0.80 | 0.80 | 1.00 | 0.762 | 2.049 | 1.250 | voltage follower, no resistors needed |
| 0.80 | 0.80 | 1.20 | 0.635 | 1.708 | 1.041 | voltage follower, no resistors needed |
| 0.80 | 0.80 | 1.40 | 0.544 | 1.464 | 0.893 | voltage follower, no resistors needed |
| 0.80 | 1.20 | 0.60 | 1.270 | 2.525 | 1.791 | 12k / 15k, gain 1.80 |
| 0.80 | 1.20 | 0.80 | 0.953 | 1.894 | 1.343 | voltage follower, no resistors needed |
| 0.80 | 1.20 | 1.00 | 0.762 | 1.515 | 1.075 | voltage follower, no resistors needed |
| 0.80 | 1.20 | 1.20 | 0.635 | 1.263 | 0.896 | voltage follower, no resistors needed |
| 0.80 | 1.20 | 1.40 | 0.544 | 1.082 | 0.768 | voltage follower, no resistors needed |
| 0.80 | 1.60 | 0.60 | 1.270 | 1.894 | 1.551 | 1k / 1.8k, gain 1.56 |
| 0.80 | 1.60 | 0.80 | 0.953 | 1.421 | 1.163 | voltage follower, no resistors needed |
| 0.80 | 1.60 | 1.00 | 0.762 | 1.136 | 0.931 | voltage follower, no resistors needed |
| 0.80 | 1.60 | 1.20 | 0.635 | 0.947 | 0.776 | no E12 pair fits, use a trim pot |
| 0.80 | 1.60 | 1.40 | 0.544 | 0.812 | 0.665 | no E12 pair fits, use a trim pot |
| 0.80 | 2.00 | 0.60 | 1.270 | 1.515 | 1.387 | 3.9k / 10k, gain 1.39 |
| 0.80 | 2.00 | 0.80 | 0.953 | 1.136 | 1.041 | voltage follower, no resistors needed |
| 0.80 | 2.00 | 1.00 | 0.762 | 0.909 | 0.832 | no E12 pair fits, use a trim pot |
| 0.80 | 2.00 | 1.20 | 0.635 | 0.758 | 0.694 | no E12 pair fits, use a trim pot |
| 0.80 | 2.00 | 1.40 | 0.544 | 0.649 | 0.595 | no E12 pair fits, use a trim pot |
| 0.80 | 2.50 | 0.60 | 1.270 | 1.212 | - | no gain clears every corner (overshoot binds) |
| 0.80 | 2.50 | 0.80 | 0.953 | 0.909 | - | no gain clears every corner (overshoot binds) |
| 0.80 | 2.50 | 1.00 | 0.762 | 0.727 | - | no gain clears every corner (overshoot binds) |
| 0.80 | 2.50 | 1.20 | 0.635 | 0.606 | - | no gain clears every corner (overshoot binds) |
| 0.80 | 2.50 | 1.40 | 0.544 | 0.520 | - | no gain clears every corner (overshoot binds) |
| 1.00 | 0.80 | 0.60 | 1.270 | 3.031 | 1.962 | 1k / 1k, gain 2.00 |
| 1.00 | 0.80 | 0.80 | 0.953 | 2.273 | 1.472 | voltage follower, no resistors needed |
| 1.00 | 0.80 | 1.00 | 0.762 | 1.818 | 1.177 | voltage follower, no resistors needed |
| 1.00 | 0.80 | 1.20 | 0.635 | 1.515 | 0.981 | voltage follower, no resistors needed |
| 1.00 | 0.80 | 1.40 | 0.544 | 1.299 | 0.841 | voltage follower, no resistors needed |
| 1.00 | 1.20 | 0.60 | 1.270 | 2.020 | 1.602 | 3.3k / 5.6k, gain 1.59 |
| 1.00 | 1.20 | 0.80 | 0.953 | 1.515 | 1.202 | voltage follower, no resistors needed |
| 1.00 | 1.20 | 1.00 | 0.762 | 1.212 | 0.961 | voltage follower, no resistors needed |
| 1.00 | 1.20 | 1.20 | 0.635 | 1.010 | 0.801 | voltage follower, no resistors needed |
| 1.00 | 1.20 | 1.40 | 0.544 | 0.866 | 0.687 | no E12 pair fits, use a trim pot |
| 1.00 | 1.60 | 0.60 | 1.270 | 1.515 | 1.387 | 3.9k / 10k, gain 1.39 |
| 1.00 | 1.60 | 0.80 | 0.953 | 1.136 | 1.041 | voltage follower, no resistors needed |
| 1.00 | 1.60 | 1.00 | 0.762 | 0.909 | 0.832 | no E12 pair fits, use a trim pot |
| 1.00 | 1.60 | 1.20 | 0.635 | 0.758 | 0.694 | no E12 pair fits, use a trim pot |
| 1.00 | 1.60 | 1.40 | 0.544 | 0.649 | 0.595 | no E12 pair fits, use a trim pot |
| 1.00 | 2.00 | 0.60 | 1.270 | 1.212 | - | no gain clears every corner (overshoot binds) |
| 1.00 | 2.00 | 0.80 | 0.953 | 0.909 | - | no gain clears every corner (overshoot binds) |
| 1.00 | 2.00 | 1.00 | 0.762 | 0.727 | - | no gain clears every corner (overshoot binds) |
| 1.00 | 2.00 | 1.20 | 0.635 | 0.606 | - | no gain clears every corner (overshoot binds) |
| 1.00 | 2.00 | 1.40 | 0.544 | 0.520 | - | no gain clears every corner (overshoot binds) |
| 1.00 | 2.50 | 0.60 | 1.270 | 0.970 | - | no gain clears every corner (overshoot binds) |
| 1.00 | 2.50 | 0.80 | 0.953 | 0.727 | - | no gain clears every corner (overshoot binds) |
| 1.00 | 2.50 | 1.00 | 0.762 | 0.582 | - | no gain clears every corner (overshoot binds) |
| 1.00 | 2.50 | 1.20 | 0.635 | 0.485 | - | no gain clears every corner (overshoot binds) |
| 1.00 | 2.50 | 1.40 | 0.544 | 0.416 | - | no gain clears every corner (overshoot binds) |
| 1.40 | 0.80 | 0.60 | 1.270 | 2.165 | 1.658 | 1k / 1.5k, gain 1.67 |
| 1.40 | 0.80 | 0.80 | 0.953 | 1.624 | 1.244 | voltage follower, no resistors needed |
| 1.40 | 0.80 | 1.00 | 0.762 | 1.299 | 0.995 | voltage follower, no resistors needed |
| 1.40 | 0.80 | 1.20 | 0.635 | 1.082 | 0.829 | voltage follower, no resistors needed |
| 1.40 | 0.80 | 1.40 | 0.544 | 0.928 | 0.711 | no E12 pair fits, use a trim pot |
| 1.40 | 1.20 | 0.60 | 1.270 | 1.443 | 1.354 | no E12 pair fits, use a trim pot |
| 1.40 | 1.20 | 0.80 | 0.953 | 1.082 | 1.015 | voltage follower, no resistors needed |
| 1.40 | 1.20 | 1.00 | 0.762 | 0.866 | 0.812 | no E12 pair fits, use a trim pot |
| 1.40 | 1.20 | 1.20 | 0.635 | 0.722 | 0.677 | no E12 pair fits, use a trim pot |
| 1.40 | 1.20 | 1.40 | 0.544 | 0.618 | 0.580 | no E12 pair fits, use a trim pot |
| 1.40 | 1.60 | 0.60 | 1.270 | 1.082 | - | no gain clears every corner (overshoot binds) |
| 1.40 | 1.60 | 0.80 | 0.953 | 0.812 | - | no gain clears every corner (overshoot binds) |
| 1.40 | 1.60 | 1.00 | 0.762 | 0.649 | - | no gain clears every corner (overshoot binds) |
| 1.40 | 1.60 | 1.20 | 0.635 | 0.541 | - | no gain clears every corner (overshoot binds) |
| 1.40 | 1.60 | 1.40 | 0.544 | 0.464 | - | no gain clears every corner (overshoot binds) |
| 1.40 | 2.00 | 0.60 | 1.270 | 0.866 | - | no gain clears every corner (overshoot binds) |
| 1.40 | 2.00 | 0.80 | 0.953 | 0.649 | - | no gain clears every corner (overshoot binds) |
| 1.40 | 2.00 | 1.00 | 0.762 | 0.520 | - | no gain clears every corner (overshoot binds) |
| 1.40 | 2.00 | 1.20 | 0.635 | 0.433 | - | no gain clears every corner (overshoot binds) |
| 1.40 | 2.00 | 1.40 | 0.544 | 0.371 | - | no gain clears every corner (overshoot binds) |
| 1.40 | 2.50 | 0.60 | 1.270 | 0.693 | - | no gain clears every corner (overshoot binds) |
| 1.40 | 2.50 | 0.80 | 0.953 | 0.520 | - | no gain clears every corner (overshoot binds) |
| 1.40 | 2.50 | 1.00 | 0.762 | 0.416 | - | no gain clears every corner (overshoot binds) |
| 1.40 | 2.50 | 1.20 | 0.635 | 0.346 | - | no gain clears every corner (overshoot binds) |
| 1.40 | 2.50 | 1.40 | 0.544 | 0.297 | - | no gain clears every corner (overshoot binds) |

## Bench log, 2 October 2026

Walk-in attempt, no data collected. The lab closed before the rig produced anything.

**Built and verified.** Divider on breadboard off the 15 V rail: 56k from the red rail into row
10, trimpot pins in rows 10, 11 and 12 (two pins in column E, the offset wiper in column D),
12k from row 12 to the blue rail. Wiper on row 11 goes to ADC INPUT 1, blue rail to a DAQ
GROUND socket. Confirmed live: `Input(v)` read a steady 3.4 V and dropped when the bench supply
was switched off, so the DAQ is reading this circuit rather than a floating input.

**Two blockers.** No flat screwdriver, so the trimpot could not be swept to find the hover
voltage. And the control app showed "No Connection!" and then closed, on the bench with DAQ
serial 1000025012. A second DAQ box sits on the same bench, so check the white cable traces
from the PC to the box the leads are actually in.

**Learned about the rig.** Both on-screen sliders are indicators, not controls; the only way in
is a physical voltage on ADC INPUT 1. The log writes four columns, `Time(s) Input(v) Output(v)
Output(m)`, at 100 ms, into a folder called `HelicopterData` with the same filename every time,
so rename after each run. Sensor constant `k` comes free from the ratio of the two output
columns, so no separate height-versus-voltage experiment is needed.

**Parts in hand:** stripboard, three UA741CP in sockets, one trimpot, resistors (56k, 12k, 10k
and a spread), 100nF caps. Still missing: track cutter, soldering access, spare 741s.

**Next session:** screwdriver first, then hover voltage, then three or more step tests at
different amplitudes, then `stepfit.py fit` on the laptop before spending an A2 attempt.
