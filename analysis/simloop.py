"""Offline rehearsal of the closed loop as it is actually wired.

design.py works on the linear model. The bench adds three things that model does
not have: a level shift that biases the controller output to the hover point, a
plant that only accepts 0 to 5 V, and a supply that caps the op-amp at 10 V.

    u_cmd = V_h + Kp*k*(x - y)          what the op-amp wants to put out
    u_sup = clip(u_cmd, -V_sup, V_sup)  what the supply allows
    u_in  = clip(u_sup, 0, 5)           what the kitticopter actually sees
    v_dot = a*(u_in - V_hover) - b*v    plant, gravity cancelled at V_hover
    y_dot = v

V_h is your trimmed bias and V_hover is the true hover voltage. The difference
between them is the bias trim error, which is the whole of the 8 percent budget.

Usage:
    python simloop.py step --A 0.80 --T 1.60 --k 1.00 --kp 0.93 --setpoint 1.0
    python simloop.py sweep --A 0.80 --T 1.60 --k 1.00 --kp 0.93 --over kp
    python simloop.py sweep --A 0.80 --T 1.60 --k 1.00 --kp 0.93 --over bias
    python simloop.py demo --A 0.80 --T 1.60 --k 1.00 --kp 0.93 --plot ../report/figures/demo.png
    python simloop.py selftest
"""

import argparse
import math

import numpy as np

V_PLANT_LO, V_PLANT_HI = 0.0, 5.0
V_SUPPLY = 10.0


def simulate(A, T, k, Kp, setpoint, v_hover=2.5, bias_error=0.0,
             tmax=None, dt=None, saturate=True, v_supply=V_SUPPLY, y0=0.0):
    """RK4 on the wired loop. Returns time, position, plant input and both clip flags."""
    a, b = A / T, 1.0 / T
    zeta = 1.0 / (2.0 * math.sqrt(max(Kp * k * A * T, 1e-12)))
    wn = math.sqrt(Kp * k * A / T)
    tmax = tmax or max(10.0 / (zeta * wn), 8 * T)
    dt = dt or min(0.002, 0.02 / wn)
    n = int(tmax / dt)
    v_bias = v_hover + bias_error

    t = np.empty(n)
    y = np.empty(n)
    u = np.empty(n)
    clipped_plant = clipped_supply = False
    state = np.array([y0, 0.0])  # position, velocity

    def command(pos):
        nonlocal clipped_plant, clipped_supply
        raw = v_bias + Kp * k * (setpoint - pos)
        if not saturate:
            return raw
        sup = min(max(raw, -v_supply), v_supply)
        if sup != raw:
            clipped_supply = True
        plant = min(max(sup, V_PLANT_LO), V_PLANT_HI)
        if plant != sup:
            clipped_plant = True
        return plant

    def deriv(state, u_in):
        return np.array([state[1], a * (u_in - v_hover) - b * state[1]])

    for i in range(n):
        t[i] = i * dt
        y[i] = state[0]
        u_in = command(state[0])
        u[i] = u_in
        k1 = deriv(state, u_in)
        k2 = deriv(state + 0.5 * dt * k1, u_in)
        k3 = deriv(state + 0.5 * dt * k2, u_in)
        k4 = deriv(state + dt * k3, u_in)
        state = state + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)

    return {"t": t, "y": y, "u": u, "clipped_plant": clipped_plant,
            "clipped_supply": clipped_supply, "zeta": zeta, "wn": wn}


def metrics(res, setpoint):
    y = res["y"]
    tail = y[int(0.9 * len(y)):]
    final = float(np.mean(tail))
    peak = float(np.max(y))
    overshoot = (peak - final) / final if final > 1e-9 else float("nan")
    offset = setpoint - final
    # settling to 2 percent of the final value
    band = 0.02 * abs(final)
    outside = np.nonzero(np.abs(y - final) > band)[0]
    ts = float(res["t"][outside[-1]]) if len(outside) else 0.0
    return {"final": final, "peak": peak, "overshoot": overshoot,
            "offset": offset, "offset_pct": offset / setpoint * 100, "ts": ts}


def linear_overshoot(zeta):
    if zeta >= 1.0:
        return 0.0
    return math.exp(-math.pi * zeta / math.sqrt(1.0 - zeta**2))


def print_run(res, m, setpoint, label=""):
    if label:
        print(label)
    print(f"  zeta {res['zeta']:.3f}, wn {res['wn']:.3f} rad/s")
    print(f"  final {m['final']:.4f} m against a {setpoint:.2f} m setpoint, "
          f"offset {m['offset']:.4f} m ({m['offset_pct']:.2f} %)")
    print(f"  overshoot {m['overshoot'] * 100:.2f} % (linear model predicts "
          f"{linear_overshoot(res['zeta']) * 100:.2f} %)")
    print(f"  settles inside 2 % after {m['ts']:.2f} s")
    print(f"  plant input {res['u'].min():.2f} to {res['u'].max():.2f} V")
    if res["clipped_plant"]:
        print("  CLIPPED at the 0 to 5 V plant input, the loop was briefly open")
    if res["clipped_supply"]:
        print("  CLIPPED at the supply rail, the op-amp ran out of headroom")
    if not (res["clipped_plant"] or res["clipped_supply"]):
        print("  no saturation, the linear design holds")


def cmd_step(args):
    res = simulate(args.A, args.T, args.k, args.kp, args.setpoint,
                   args.v_hover, args.bias_error, saturate=not args.no_saturate)
    m = metrics(res, args.setpoint)
    print_run(res, m, args.setpoint)
    if args.plot:
        plot_runs([(f"Kp = {args.kp:.3f}", res)], args, args.plot)
    return 0


def cmd_sweep(args):
    runs = []
    if args.over == "kp":
        values = [args.kp * s for s in (0.8, 0.9, 1.0, 1.1, 1.2)]
        for kp in values:
            res = simulate(args.A, args.T, args.k, kp, args.setpoint,
                           args.v_hover, args.bias_error, saturate=not args.no_saturate)
            runs.append((f"Kp {kp:.3f}", res))
    else:
        values = [-0.2, -0.1, 0.0, 0.1, 0.2]
        for be in values:
            res = simulate(args.A, args.T, args.k, args.kp, args.setpoint,
                           args.v_hover, be, saturate=not args.no_saturate)
            runs.append((f"bias error {be:+.2f} V", res))

    print(f"{'case':<20}{'final m':>10}{'offset %':>11}{'OS %':>9}{'ts s':>8}{'clip':>8}")
    for label, res in runs:
        m = metrics(res, args.setpoint)
        clip = "plant" if res["clipped_plant"] else ("supply" if res["clipped_supply"] else "-")
        print(f"{label:<20}{m['final']:>10.4f}{m['offset_pct']:>11.2f}"
              f"{m['overshoot'] * 100:>9.2f}{m['ts']:>8.2f}{clip:>8}")
    if args.over == "bias":
        print()
        print("offset tracks the bias error and nothing else, which is why trimming the hover")
        print("point buys more margin than raising the gain does")
    if args.plot:
        plot_runs(runs, args, args.plot)
    return 0


def cmd_demo(args):
    """De Maar's standard sequence: settle, step up, settle, step back down."""
    levels = [args.setpoint, args.setpoint * 1.5, args.setpoint]
    dt = 0.002
    t_all, y_all, u_all, marks = [], [], [], []
    t0 = 0.0
    state_y = 0.0
    clipped_plant = clipped_supply = False
    for sp in levels:
        res = simulate(args.A, args.T, args.k, args.kp, sp, args.v_hover,
                       args.bias_error, tmax=args.hold, dt=dt,
                       saturate=not args.no_saturate, y0=state_y)
        t_all.append(res["t"] + t0)
        y_all.append(res["y"])
        u_all.append(res["u"])
        marks.append((t0, sp))
        state_y = float(res["y"][-1])
        clipped_plant |= res["clipped_plant"]
        clipped_supply |= res["clipped_supply"]
        t0 += args.hold

    t = np.concatenate(t_all)
    y = np.concatenate(y_all)
    u = np.concatenate(u_all)
    print(f"demo sequence {' -> '.join(f'{s:.2f}' for s in levels)} m, {args.hold:.0f} s per level")
    for (start, sp), seg in zip(marks, y_all):
        tail = seg[int(0.9 * len(seg)):]
        print(f"  at t={start:>5.1f}s setpoint {sp:.2f} m, settled to {np.mean(tail):.4f} m, "
              f"error {(sp - np.mean(tail)) / sp * 100:+.2f} %")
    if clipped_plant:
        print("  CLIPPED at the plant input during the sequence")
    if clipped_supply:
        print("  CLIPPED at the supply during the sequence")
    if args.plot:
        plot_demo(t, y, u, marks, args, args.plot)
    return 0


def plot_runs(runs, args, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7, 6), sharex=True)
    for label, res in runs:
        ax1.plot(res["t"], res["y"], lw=1.1, label=label)
        ax2.plot(res["t"], res["u"], lw=1.1)
    ax1.axhline(args.setpoint, color="grey", ls="--", lw=0.8)
    ax2.axhline(V_PLANT_HI, color="#c1502e", ls="--", lw=0.8, label="plant input limit")
    ax2.axhline(V_PLANT_LO, color="#c1502e", ls="--", lw=0.8)
    ax1.set_ylabel("position (m)")
    ax2.set_ylabel("plant input (V)")
    ax2.set_xlabel("time (s)")
    ax1.legend(fontsize=8)
    ax2.legend(fontsize=8)
    ax1.grid(alpha=0.3)
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    print(f"wrote {out}")


def plot_demo(t, y, u, marks, args, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7, 6), sharex=True)
    ax1.plot(t, y, lw=1.2, color="#3b6ea5")
    for start, sp in marks:
        ax1.hlines(sp, start, start + args.hold, color="grey", ls="--", lw=0.8)
    ax2.plot(t, u, lw=1.0, color="#2e7d32")
    ax2.axhline(V_PLANT_HI, color="#c1502e", ls="--", lw=0.8)
    ax2.axhline(V_PLANT_LO, color="#c1502e", ls="--", lw=0.8)
    ax1.set_ylabel("position (m)")
    ax2.set_ylabel("plant input (V)")
    ax2.set_xlabel("time (s)")
    ax1.grid(alpha=0.3)
    ax2.grid(alpha=0.3)
    fig.suptitle("Demo sequence, setpoint steps with the plant input beside it")
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    print(f"wrote {out}")


def selftest():
    """Unsaturated and perfectly trimmed, the simulator must match the linear model."""
    A, T, k, Kp, sp = 0.8, 1.6, 1.0, 0.93, 1.0
    res = simulate(A, T, k, Kp, sp, v_hover=2.5, bias_error=0.0, saturate=False)
    m = metrics(res, sp)
    os_lin = linear_overshoot(res["zeta"])
    err_os = abs(m["overshoot"] - os_lin) / os_lin
    err_final = abs(m["final"] - sp)
    print(f"overshoot  simulated {m['overshoot'] * 100:.3f} %, linear {os_lin * 100:.3f} %, "
          f"error {err_os * 100:.2f} %")
    print(f"final value simulated {m['final']:.5f} m against setpoint {sp:.2f} m")

    # saturation must actually bite at high gain and show up in the flags
    hot = simulate(A, T, k, Kp * 40, sp, v_hover=2.5, bias_error=0.0, saturate=True)
    m_hot = metrics(hot, sp)
    bit = hot["clipped_plant"] or hot["clipped_supply"]
    print(f"high gain run clipped: {bit}, overshoot {m_hot['overshoot'] * 100:.1f} % against "
          f"linear {linear_overshoot(hot['zeta']) * 100:.1f} %")

    ok = err_os < 0.01 and err_final < 1e-3 and bit
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--A", type=float, required=True)
        sp.add_argument("--T", type=float, required=True)
        sp.add_argument("--k", type=float, required=True)
        sp.add_argument("--kp", type=float, required=True)
        sp.add_argument("--setpoint", type=float, default=1.0)
        sp.add_argument("--v-hover", type=float, default=2.5, help="true hover voltage, mid range by design")
        sp.add_argument("--bias-error", type=float, default=0.0, help="how far your trim sits from it, V")
        sp.add_argument("--no-saturate", action="store_true", help="turn the limits off to see the linear response")
        sp.add_argument("--plot", metavar="PNG")

    common(sub.add_parser("step", help="one closed-loop step"))
    sw = sub.add_parser("sweep", help="families of curves for the robustness section")
    common(sw)
    sw.add_argument("--over", choices=["kp", "bias"], default="kp")
    dm = sub.add_parser("demo", help="the standard demo sequence")
    common(dm)
    dm.add_argument("--hold", type=float, default=30.0, help="seconds per setpoint")
    sub.add_parser("selftest", help="check the simulator against the linear model")

    args = p.parse_args(argv)
    if args.cmd == "selftest":
        return selftest()
    if args.cmd == "step":
        return cmd_step(args)
    if args.cmd == "sweep":
        return cmd_sweep(args)
    return cmd_demo(args)


if __name__ == "__main__":
    raise SystemExit(main())
