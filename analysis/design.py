"""Session 2 prep: the Kp window that survives the tolerance budget.

Model from session 1, unit mass and gravity taken at the plant input:

    v_dot = a*u - b*v - g,   A = a/b,   T = 1/b

so the position loop is P(s) = A/(s(Ts+1)) in metres per volt, the sensor
turns metres back into volts through k, and a proportional controller gives

    Y/X   = Kp k A / (T s^2 + s + Kp k A)      ... type 1, zero step error
    wn    = sqrt(Kp k A / T),  zeta = 1 / (2 sqrt(Kp k A T))

Three specs bound Kp from different sides:

    overshoot  < 30 %   caps Kp, since more gain means less damping
    disturbance residue < 8 %   floors Kp, the offset is dV / (Kp k)
    controller effort            caps Kp, the kick at a step is Kp k r

The effort ceiling is not the supply. The op-amp can swing to 10 V, but the
kitticopter only accepts 0 to 5 V, so the headroom above the hover bias is
5 - V_h and that is what binds first. Going past it opens the loop for as long
as the input is clipped, and the measured overshoot stops matching any linear
prediction.

A type 1 loop tracks a step setpoint with zero error, so the 8 percent spec is
really about the disturbance. Gravity is cancelled by the level shift, and what
survives is the bias trim error dV in volts at the plant input, which lands as a
steady offset dV/(Kp k) metres. That is why trimming the hover bias buys margin
faster than raising the gain does.

Usage:
    python design.py --A 0.80 --T 1.60 --k 1.00
    python design.py --A 0.80 --T 1.60 --k 1.00 --g-residual 0.5 --setpoint 2.0
    python design.py --A 0.80 --T 1.60 --k 1.00 --plot ../report/figures/design.png
    python design.py --crosscheck
"""

import argparse
import math

import numpy as np

G = 9.81
V_PLANT_HI = 5.0  # the kitticopter ignores anything above this
RESISTOR_LO, RESISTOR_HI = 0.82, 1.22  # realised gain band for a 10 percent non-inverting stage


def damping(Kp, A, T, k):
    return 1.0 / (2.0 * math.sqrt(max(Kp * k * A * T, 1e-12)))


def overshoot(zeta):
    if zeta >= 1.0:
        return 0.0
    return math.exp(-math.pi * zeta / math.sqrt(1.0 - zeta**2))


def disturbance_offset(Kp, k, dist_volts):
    """Steady-state position offset in metres left by a constant input voltage error."""
    return dist_volts / (Kp * k)


def volts_from_accel(g_res, A, T):
    """Convert a residual acceleration in m/s^2 to the equivalent input voltage error."""
    return g_res * T / A


def simulate_step(Kp, A, T, k, r=1.0, tmax=None, dt=None):
    """Numerical step response of the closed loop, used to check the formulas."""
    wn = math.sqrt(Kp * k * A / T)
    zeta = damping(Kp, A, T, k)
    tmax = tmax or 12.0 / (zeta * wn)
    dt = dt or min(0.01, 0.02 / wn)
    n = int(tmax / dt)
    y = v = 0.0
    peak = 0.0
    for _ in range(n):
        # T y'' + y' = Kp k A (r - y)
        acc = (Kp * k * A * (r - y) - v) / T
        v += acc * dt
        y += v * dt
        peak = max(peak, y)
    return peak / r - 1.0, y / r


def corners(A, T, tol_b=0.10):
    """Plant and gain corners: drag 10 percent either way, resistors 0.82 to 1.22.

    A = a/b and T = 1/b both scale with 1/b, so one drag error moves them together
    and the damping goes as 1/scale, not 1/sqrt(scale).
    """
    for tscale in (1 - tol_b, 1.0, 1 + tol_b):
        for gscale in (RESISTOR_LO, 1.0, RESISTOR_HI):
            yield A * tscale, T * tscale, gscale


def window(A, T, k, dist_volts, setpoint, os_limit, err_limit, v_limit, tol_b=0.10):
    """Smallest Kp meeting the disturbance spec and largest meeting overshoot and effort, over all corners."""
    lo, hi = 0.0, math.inf
    binding = {}
    for Ac, Tc, gscale in corners(A, T, tol_b):
        # disturbance floor, independent of T since the offset is dV/(Kp k)
        need = dist_volts / (err_limit * setpoint * k) / gscale
        if need > lo:
            lo, binding["floor"] = need, (Tc, gscale, "disturbance residue")
        # overshoot ceiling, from zeta = 1/(2 sqrt(Kp k A T))
        zeta_min = -math.log(os_limit) / math.sqrt(math.pi**2 + math.log(os_limit) ** 2)
        cap_os = 1.0 / (4.0 * zeta_min**2 * k * Ac * Tc) / gscale
        # effort ceiling, the kick at a step of size setpoint, against the tighter of the two limits
        cap_v = v_limit / (k * setpoint) / gscale
        cap = min(cap_os, cap_v)
        if cap < hi:
            hi = cap
            binding["ceiling"] = (Tc, gscale, "overshoot" if cap_os <= cap_v else "controller effort")
    return lo, hi, binding


def report(args):
    A, T, k = args.A, args.T, args.k
    dist_volts = args.dist_volts
    if args.g_residual is not None:
        dist_volts = volts_from_accel(args.g_residual, A, T)
    headroom = V_PLANT_HI - args.v_hover
    v_limit = min(args.vmax, headroom)
    which = "plant input headroom" if headroom <= args.vmax else "supply"
    lo, hi, binding = window(A, T, k, dist_volts, args.setpoint,
                             args.overshoot, args.error, v_limit, args.tol_b)
    print(f"plant   A = {A:.4f} m/(V s), T = {T:.4f} s, k = {k:.4f} V/m")
    print(f"        b = {1 / T:.4f} 1/s, a = {A / T:.4f} m/(V s^2)")
    print(f"specs   overshoot < {args.overshoot * 100:.0f} %, error and disturbance < {args.error * 100:.0f} %, "
          f"effort < {v_limit:.1f} V at a {args.setpoint:.2f} m step ({which})")
    print(f"        supply {args.vmax:.1f} V, plant input 0 to {V_PLANT_HI:.1f} V with the bias at "
          f"{args.v_hover:.2f} V, so {headroom:.2f} V of headroom")
    print(f"bias    {dist_volts:.3f} V of uncancelled input, {dist_volts * A / T:.3f} m/s^2 equivalent")
    print(f"corners drag +/-{args.tol_b * 100:.0f} %, realised gain {RESISTOR_LO:.2f} to {RESISTOR_HI:.2f}")
    print()
    if lo > hi:
        print(f"NO Kp MEETS EVERY SPEC AT EVERY CORNER: floor {lo:.3f} is above ceiling {hi:.3f}")
        print(f"  floor set by {binding['floor'][2]} at T={binding['floor'][0]:.3f}, gain scale {binding['floor'][1]:.2f}")
        print(f"  ceiling set by {binding['ceiling'][2]} at T={binding['ceiling'][0]:.3f}, gain scale {binding['ceiling'][1]:.2f}")
        print("  relax by trimming the level shift so the residual disturbance drops, or accept a tighter margin")
        if args.mc:
            kp_best, frac = best_kp(A, T, k, dist_volts, args.setpoint, args.overshoot,
                                    args.error, v_limit, args.mc, args.tol_b)
            mc = monte_carlo(A, T, k, dist_volts, args.setpoint, args.overshoot,
                             args.error, v_limit, kp_best, args.mc, args.tol_b)
            print()
            print(f"Monte Carlo, {args.mc} builds sampled inside the tolerance boxes")
            print(f"  best Kp is {kp_best:.3f}, met by {frac * 100:.1f} % of builds")
            print(f"  overshoot spec met by {mc['os'] * 100:.1f} %, disturbance by {mc['err'] * 100:.1f} %, "
                  f"effort by {mc['volts'] * 100:.1f} %")
            print("  a corner check says no, a distribution says how often. Report both and pick knowingly")
        return
    print(f"Kp window {lo:.3f} to {hi:.3f}")
    print(f"  floor   {lo:.3f} from {binding['floor'][2]} at T={binding['floor'][0]:.3f}, gain scale {binding['floor'][1]:.2f}")
    print(f"  ceiling {hi:.3f} from {binding['ceiling'][2]} at T={binding['ceiling'][0]:.3f}, gain scale {binding['ceiling'][1]:.2f}")
    target = math.sqrt(lo * hi) if lo > 0 else hi / 2
    print(f"  pick    {target:.3f} (geometric centre, equal margin either way in log gain)")
    print()
    print(f"{'T':>7}{'gain':>7}{'Kp_eff':>9}{'zeta':>8}{'OS %':>8}{'offset m':>11}{'kick V':>9}")
    for Ac, Tc, gscale in corners(A, T, args.tol_b):
        keff = target * gscale
        z = damping(keff, Ac, Tc, k)
        print(f"{Tc:>7.3f}{gscale:>7.2f}{keff:>9.3f}{z:>8.3f}{overshoot(z) * 100:>8.2f}"
              f"{disturbance_offset(keff, k, dist_volts):>11.4f}{keff * k * args.setpoint:>9.2f}")
    print()
    print("offset is what the level shift does not cancel, so trimming the hover bias buys margin directly")

    if args.mc:
        mc = monte_carlo(A, T, k, dist_volts, args.setpoint, args.overshoot,
                         args.error, v_limit, target, args.mc, args.tol_b)
        print()
        print(f"Monte Carlo, {args.mc} builds sampled inside the tolerance boxes at Kp = {target:.3f}")
        print(f"  overshoot spec met by {mc['os'] * 100:.1f} %, disturbance by {mc['err'] * 100:.1f} %, "
              f"effort by {mc['volts'] * 100:.1f} %")
        print(f"  all three met by {mc['all'] * 100:.1f} %")
        if mc["all"] < 1.0:
            kp_best, frac = best_kp(A, T, k, dist_volts, args.setpoint, args.overshoot,
                                    args.error, v_limit, max(args.mc // 10, 500), args.tol_b)
            print(f"  best achievable is {frac * 100:.1f} % at Kp = {kp_best:.3f}")

    if args.latex:
        write_latex(args, dist_volts, lo, hi, target, args.latex)


def crosscheck():
    """Formulas against a numerical step response. Verification item 3."""
    A, T, k = 0.8, 1.6, 1.0
    print(f"{'Kp':>6}{'zeta':>8}{'OS formula':>12}{'OS sim':>9}{'y_ss sim':>10}")
    worst = 0.0
    for Kp in (0.5, 1.0, 2.0, 4.0, 8.0):
        z = damping(Kp, A, T, k)
        os_formula = overshoot(z) * 100
        os_sim, y_ss = simulate_step(Kp, A, T, k)
        os_sim *= 100
        worst = max(worst, abs(os_formula - os_sim))
        print(f"{Kp:>6.2f}{z:>8.3f}{os_formula:>12.2f}{os_sim:>9.2f}{y_ss:>10.4f}")
    print(f"\nlargest overshoot mismatch {worst:.2f} percentage points")
    ok = worst < 1.0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


def monte_carlo(A, T, k, dist_volts, setpoint, os_limit, err_limit, v_limit, Kp, n, tol_b=0.10, seed=0):
    """Sample inside the tolerance boxes instead of only visiting the corners."""
    rng = np.random.default_rng(seed)
    scale = rng.uniform(1 - tol_b, 1 + tol_b, n)
    Tc = T * scale
    Ac = A * scale
    gain = Kp * rng.uniform(RESISTOR_LO, RESISTOR_HI, n)
    zeta = 1.0 / (2.0 * np.sqrt(np.maximum(gain * k * Ac * Tc, 1e-12)))
    os = np.where(zeta >= 1.0, 0.0,
                  np.exp(-np.pi * zeta / np.sqrt(np.maximum(1.0 - zeta**2, 1e-12))))
    offset = dist_volts / (gain * k)
    kick = gain * k * setpoint
    pass_os = os <= os_limit
    pass_err = offset <= err_limit * setpoint
    pass_v = kick <= v_limit
    return {
        "os": float(pass_os.mean()), "err": float(pass_err.mean()), "volts": float(pass_v.mean()),
        "all": float((pass_os & pass_err & pass_v).mean()),
        "os_median": float(np.median(os)), "offset_median": float(np.median(offset)),
    }


def best_kp(A, T, k, dist_volts, setpoint, os_limit, err_limit, v_limit, n, tol_b=0.10):
    """Kp with the highest pass fraction, for when no gain clears every corner."""
    grid = np.logspace(-2, 2, 200)
    best = (0.0, None)
    for Kp in grid:
        frac = monte_carlo(A, T, k, dist_volts, setpoint, os_limit, err_limit,
                           v_limit, Kp, n, tol_b)["all"]
        if frac > best[0]:
            best = (frac, Kp)
    return best[1], best[0]


def write_latex(args, dist_volts, lo, hi, target, out):
    """Corner table as a booktabs fragment for the report."""
    A, T, k = args.A, args.T, args.k
    lines = [
        "% generated by analysis/design.py, do not edit by hand",
        "\\begin{table}[ht]",
        "  \\centering",
        f"  \\caption{{Controller performance at every corner of the tolerance budget, "
        f"$K_p = {target:.3f}$ nominal. Window {lo:.3f} to {hi:.3f}.}}",
        "  \\label{tab:corners}",
        "  \\begin{tabular}{rrrrrrr}",
        "    \\toprule",
        "    $T$ (s) & gain factor & $K_{p,\\text{eff}}$ & $\\zeta$ & Overshoot (\\%) "
        "& Offset (m) & Kick (V) \\\\",
        "    \\midrule",
    ]
    for Ac, Tc, gscale in corners(A, T, args.tol_b):
        keff = target * gscale
        z = damping(keff, Ac, Tc, k)
        lines.append(f"    {Tc:.3f} & {gscale:.2f} & {keff:.3f} & {z:.3f} & "
                     f"{overshoot(z) * 100:.2f} & {disturbance_offset(keff, k, dist_volts):.4f} & "
                     f"{keff * k * args.setpoint:.2f} \\\\")
    lines += [
        "    \\bottomrule",
        "  \\end{tabular}",
        "\\end{table}",
    ]
    with open(out, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {out}")


def plot(args, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    A, T, k = args.A, args.T, args.k
    dist_volts = args.dist_volts
    if args.g_residual is not None:
        dist_volts = volts_from_accel(args.g_residual, A, T)
    lo, hi, _ = window(A, T, k, dist_volts, args.setpoint, args.overshoot, args.error,
                       min(args.vmax, V_PLANT_HI - args.v_hover), args.tol_b)
    target = math.sqrt(lo * hi) if lo > 0 and hi < math.inf else 1.0

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    # closed-loop poles as Kp sweeps, the root locus of A/(s(Ts+1))
    gains = np.logspace(-2, 2, 400)
    roots = np.array([np.roots([T, 1.0, g * k * A]) for g in gains])
    ax1.plot(roots.real, roots.imag, ".", ms=1.5, color="#3b6ea5")
    for gain, colour in ((lo, "#c1502e"), (target, "#2e7d32"), (hi, "#c1502e")):
        r = np.roots([Tc, 1.0, gain * k * Ac])
        ax1.plot(r.real, r.imag, "x", ms=9, color=colour)
    ax1.axhline(0, color="grey", lw=0.6)
    ax1.axvline(0, color="grey", lw=0.6)
    ax1.set_xlabel("real")
    ax1.set_ylabel("imaginary")
    ax1.set_title("closed-loop poles, Kp sweep")
    ax1.grid(alpha=0.3)

    for Ac, Tc, gscale in corners(A, T, args.tol_b):
        keff = target * gscale
        wn = math.sqrt(keff * k * A / Tc)
        z = damping(keff, Ac, Tc, k)
        t = np.linspace(0, 10 / (z * wn), 800)
        wd = wn * math.sqrt(max(1 - z**2, 1e-9))
        y = 1 - np.exp(-z * wn * t) * (np.cos(wd * t) + z / math.sqrt(max(1 - z**2, 1e-9)) * np.sin(wd * t))
        ax2.plot(t, y, lw=0.9, alpha=0.7)
    ax2.axhline(1 + args.overshoot, color="#c1502e", ls="--", lw=0.8, label=f"{args.overshoot * 100:.0f} % overshoot")
    ax2.axhline(1.0, color="grey", lw=0.6)
    ax2.set_xlabel("time (s)")
    ax2.set_ylabel("normalised position")
    ax2.set_title(f"step response at every corner, Kp = {target:.3f}")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(out, dpi=200)
    print(f"wrote {out}")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--A", type=float, help="velocity gain from stepfit, m/(V s)")
    p.add_argument("--T", type=float, help="time constant from stepfit, s")
    p.add_argument("--k", type=float, help="sensor constant, V/m")
    p.add_argument("--setpoint", type=float, default=1.0, help="step size the specs are judged at, m")
    p.add_argument("--dist-volts", type=float, default=0.10,
                   help="bias trim error at the plant input, V. This is what the level shift fails to cancel")
    p.add_argument("--g-residual", type=float, default=None,
                   help="same disturbance given as an acceleration, m/s^2. Overrides --dist-volts")
    p.add_argument("--overshoot", type=float, default=0.30)
    p.add_argument("--error", type=float, default=0.08)
    p.add_argument("--vmax", type=float, default=10.0, help="supply limit on the op-amp output, V")
    p.add_argument("--v-hover", type=float, default=2.5,
                   help="hover bias, V. Headroom to the 5 V plant limit is what really caps Kp")
    p.add_argument("--tol-b", type=float, default=0.10)
    p.add_argument("--plot", metavar="PNG")
    p.add_argument("--latex", metavar="TEX", help="write the corner table as a booktabs fragment")
    p.add_argument("--mc", type=int, default=0, metavar="N",
                   help="sample N builds inside the tolerance boxes instead of only the corners")
    p.add_argument("--crosscheck", action="store_true", help="check the formulas against a simulation")
    args = p.parse_args(argv)

    if args.crosscheck:
        return crosscheck()
    if None in (args.A, args.T, args.k):
        p.error("--A, --T and --k are required unless --crosscheck is given")
    report(args)
    if args.plot:
        plot(args, args.plot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
