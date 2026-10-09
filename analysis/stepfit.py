"""Session 1: turn kitticopter step-test logs into A, T and k.

The velocity loop is first order, v(s)/u(s) = A/(Ts+1), so a step of dV volts
gives v(t) = A*dV*(1 - exp(-t/T)). Position is logged, not velocity, so the
position trace gets differentiated first.

Usage:
    python stepfit.py fit ../data/session-1/*.csv
    python stepfit.py fit ../data/session-1/*.csv --plot ../report/figures/step_response.png
    python stepfit.py sensor --volts 1.02 2.51 3.98 --metres 1.0 2.5 4.0
    python stepfit.py selftest
"""

import argparse
import csv
import glob
import math
import os
import sys
import tempfile

import numpy as np

SAT_VOLTS = 5.0  # the kitticopter ignores anything above this


def read_log(path):
    """Read a bench CSV and return time, input volts, position in metres.

    The lab rig logs four columns, Time(s) Input(v) Output(v) Output(m), so pick
    the metre column by name. Lab 1 style three-column files fall back to order.
    """
    with open(path, newline="") as fh:
        rows = list(csv.reader(fh))
    header = [c.strip() for c in rows[0]]
    if len(header) < 3:
        raise ValueError(f"{path}: expected at least 3 columns, got {header}")

    def find(*names):
        for i, h in enumerate(header):
            if h.lower().replace(" ", "") in names:
                return i
        return None

    i_t = find("time(s)", "time") or 0
    i_u = find("input(v)", "input") or 1
    i_m = find("output(m)", "output_displacement", "output")
    i_v = find("output(v)")
    if i_m is None:
        i_m = 2
    width = max(i for i in (i_t, i_u, i_m, i_v) if i is not None) + 1
    data = np.array([[float(c) for c in r[:width]] for r in rows[1:] if r and r[0].strip()])
    read_log.volts = data[:, i_v] if i_v is not None else None
    return data[:, i_t], data[:, i_u], data[:, i_m]


def savgol(y, window, polyorder, deriv=0, delta=1.0):
    """Savitzky-Golay filter. numpy only, since the venv has no scipy."""
    if window % 2 == 0:
        window += 1
    if window <= polyorder:
        raise ValueError("window must exceed polyorder")
    half = window // 2
    offsets = np.arange(-half, half + 1)
    design = np.vander(offsets, polyorder + 1, increasing=True)
    pinv = np.linalg.pinv(design)
    coeffs = pinv[deriv] * (math.factorial(deriv) / delta**deriv)
    # fit the edges on their own windows instead of padding, which would bend them
    out = np.convolve(y, coeffs[::-1], mode="same")
    for i in list(range(half)) + list(range(len(y) - half, len(y))):
        lo = max(0, i - half)
        hi = min(len(y), i + half + 1)
        local = np.arange(lo, hi) - i
        fit = np.linalg.lstsq(np.vander(local, polyorder + 1, increasing=True), y[lo:hi], rcond=None)[0]
        out[i] = fit[deriv] * math.factorial(deriv) / delta**deriv
    return out


def find_step(t, u):
    """Locate the step in the input trace. Returns (index, V1, V2)."""
    du = np.abs(np.diff(u))
    idx = int(np.argmax(du)) + 1
    if du[idx - 1] < 1e-6:
        raise ValueError("no step found in the input channel")
    v1 = float(np.median(u[max(0, idx - 50):idx - 1])) if idx > 2 else float(u[0])
    v2 = float(np.median(u[idx + 1:idx + 51])) if idx + 2 < len(u) else float(u[-1])
    return idx, v1, v2


def fit_first_order(t, v, idx):
    """Fit v(t) = v_ss*(1 - exp(-t/T)) after the step. Returns v_ss and both T estimates."""
    ts = t[idx:] - t[idx]
    vs = v[idx:] - np.median(v[max(0, idx - 20):idx])
    tail = vs[int(0.8 * len(vs)):]
    v_ss = float(np.mean(tail))
    if abs(v_ss) < 1e-9:
        raise ValueError("velocity settles back to zero, so this trace is not a first-order velocity step")

    # 63.2 percent crossing, linearly interpolated
    target = 0.632 * v_ss
    crossed = np.nonzero(np.sign(vs - target) == np.sign(v_ss))[0]
    t_632 = float("nan")
    if len(crossed):
        j = crossed[0]
        if j > 0:
            frac = (target - vs[j - 1]) / (vs[j] - vs[j - 1])
            t_632 = float(ts[j - 1] + frac * (ts[j] - ts[j - 1]))
        else:
            t_632 = float(ts[j])

    # log-linear fit on the approach to steady state, over the part that is not noise
    resid = v_ss - vs
    keep = np.abs(resid) > 0.05 * abs(v_ss)
    keep[int(0.8 * len(vs)):] = False
    t_fit = float("nan")
    if keep.sum() > 5:
        slope, _ = np.polyfit(ts[keep], np.log(np.abs(resid[keep])), 1)
        t_fit = float(-1.0 / slope)
    return v_ss, t_632, t_fit


def sensor_from_log(metres, volts):
    """Sensor constant from the rig's own two output columns, volts per metre.

    The rig logs Output(v) and Output(m) side by side, so k is a regression
    through the pairs rather than a separate bench measurement. Returns None for
    a three-column Lab 1 file.
    """
    if volts is None:
        return None
    move = np.abs(metres) > 0.05 * np.max(np.abs(metres))
    if move.sum() < 5:
        return None
    return float(np.polyfit(metres[move], volts[move], 1)[0])


def analyse(path, window=21, polyorder=2):
    t, u, y = read_log(path)
    y_volts = read_log.volts
    dt = float(np.median(np.diff(t)))
    v = savgol(y, window, polyorder, deriv=1, delta=dt)
    idx, v1, v2 = find_step(t, u)
    if v2 > SAT_VOLTS:
        raise ValueError(f"step ends at {v2:.2f} V, above the {SAT_VOLTS} V input limit, discard this run")
    dv = v2 - v1
    v_ss, t_632, t_fit = fit_first_order(t, v, idx)
    T = np.nanmean([t_632, t_fit])
    A = v_ss / dv
    return {
        "path": path, "t": t, "u": u, "y": y, "v": v, "idx": idx,
        "V1": v1, "V2": v2, "dV": dv, "v_ss": v_ss,
        "T_632": t_632, "T_fit": t_fit, "T": T, "A": A,
        "k": sensor_from_log(y, y_volts),
    }


def report(results):
    print(f"{'run':<28}{'V1':>7}{'V2':>7}{'dV':>7}{'A':>10}{'T(63%)':>10}{'T(fit)':>10}{'T':>9}")
    for r in results:
        name = r["path"].split("/")[-1]
        print(f"{name:<28}{r['V1']:>7.3f}{r['V2']:>7.3f}{r['dV']:>7.3f}"
              f"{r['A']:>10.4f}{r['T_632']:>10.4f}{r['T_fit']:>10.4f}{r['T']:>9.4f}")

    A = np.array([r["A"] for r in results])
    T = np.array([r["T"] for r in results])
    print()
    print(f"A = {A.mean():.4f} +/- {A.std(ddof=1) if len(A) > 1 else 0:.4f} "
          f"(spread {A.max() - A.min():.4f} over {len(A)} runs)")
    print(f"T = {T.mean():.4f} +/- {T.std(ddof=1) if len(T) > 1 else 0:.4f} "
          f"(spread {T.max() - T.min():.4f} over {len(T)} runs)")

    b = 1.0 / T.mean()
    print()
    print("Sanity, from v_dot = a*u - b*v at unit mass:")
    print(f"  drag constant b = 1/T = {b:.4f} 1/s")
    print(f"  thrust constant a = A/T = {A.mean() / T.mean():.4f} m/(V s^2)")
    if T.mean() <= 0:
        print("  WARNING negative time constant, the fit window is wrong")
    if len(T) > 1 and T.std(ddof=1) > 0.2 * T.mean():
        print("  WARNING spread above 20 percent, repeat the step test")
    print()
    print("Appendix A2 dialog wants, in this order:")
    print(f"  gain A         = {A.mean():.4f}")
    print(f"  time constant T = {T.mean():.4f}")
    ks = [r["k"] for r in results if r.get("k")]
    if ks:
        print(f"  sensor k        = {np.mean(ks):.4f} V/m  (from the log's own "
              f"Output(v) and Output(m) columns, {len(ks)} runs)")
    else:
        print("  sensor k        = run 'stepfit.py sensor' with your paired readings")
    print("You get 3 attempts. Aim above 60 percent on A and T, above 90 percent on k.")


def write_latex(results, out):
    """Emit a booktabs fragment for the report, so numbers are not retyped."""
    A = np.array([r["A"] for r in results])
    T = np.array([r["T"] for r in results])
    lines = [
        "% generated by analysis/stepfit.py, do not edit by hand",
        "\\begin{table}[ht]",
        "  \\centering",
        "  \\caption{Step test results. $A$ and $T$ from each run, with the aggregate used for the model.}",
        "  \\label{tab:stepfit}",
        "  \\begin{tabular}{lrrrrr}",
        "    \\toprule",
        "    Run & $V_1$ (V) & $V_2$ (V) & $A$ (m/(V s)) & $T$ (s) & $T$ spread (s) \\\\",
        "    \\midrule",
    ]
    for r in results:
        name = r["path"].split("/")[-1].replace("_", "\\_")
        spread = abs(r["T_632"] - r["T_fit"])
        lines.append(f"    {name} & {r['V1']:.3f} & {r['V2']:.3f} & {r['A']:.4f} & {r['T']:.4f} & {spread:.4f} \\\\")
    sd_a = A.std(ddof=1) if len(A) > 1 else 0.0
    sd_t = T.std(ddof=1) if len(T) > 1 else 0.0
    lines += [
        "    \\midrule",
        f"    Mean & & & {A.mean():.4f} & {T.mean():.4f} & \\\\",
        f"    Standard deviation & & & {sd_a:.4f} & {sd_t:.4f} & \\\\",
        "    \\bottomrule",
        "  \\end{tabular}",
        "\\end{table}",
    ]
    with open(out, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {out}")


def plot(results, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7, 6), sharex=True)
    for r in results:
        name = r["path"].split("/")[-1]
        ax1.plot(r["t"], r["y"], lw=1, label=name)
        ax2.plot(r["t"], r["v"], lw=1)
        t0 = r["t"][r["idx"]]
        ax2.axhline(r["v_ss"], color="grey", ls=":", lw=0.8)
        ax2.axvline(t0 + r["T"], color="grey", ls="--", lw=0.8)
    ax1.set_ylabel("position (m)")
    ax2.set_ylabel("velocity (m/s)")
    ax2.set_xlabel("time (s)")
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3)
    ax2.grid(alpha=0.3)
    fig.suptitle("Kitticopter step test, position and derived velocity")
    fig.tight_layout()
    fig.savefig(out, dpi=200)
    print(f"wrote {out}")


def sensor(volts, metres):
    volts = np.asarray(volts, float)
    metres = np.asarray(metres, float)
    if volts.shape != metres.shape or volts.size < 2:
        raise ValueError("need at least two paired readings")
    k, offset = np.polyfit(metres, volts, 1)
    pred = k * metres + offset
    resid = volts - pred
    print(f"k      = {k:.4f} V/m")
    print(f"offset = {offset:.4f} V (should be near zero, a large value means a bias in the reading)")
    print(f"max residual = {np.abs(resid).max():.4f} V")
    return float(k)


def selftest():
    """Recover known A and T from a synthetic trace. Synthetic data, never a lab result."""
    rng = np.random.default_rng(0)
    A_true, T_true, dV = 0.8, 1.6, 1.2
    dt = 0.01
    t = np.arange(0, 20, dt)
    idx = len(t) // 4
    u = np.where(t < t[idx], 2.0, 2.0 + dV)
    v = np.where(t < t[idx], 0.0, A_true * dV * (1 - np.exp(-(t - t[idx]) / T_true)))
    y = np.cumsum(v) * dt
    y = np.round(y + rng.normal(0, 2e-4, y.size), 3)  # 1 mm logger quantisation

    path = os.path.join(tempfile.gettempdir(), "_stepfit_selftest.csv")
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Time(s)", "Input", "Output_Displacement"])
        w.writerows(zip(t, u, y))

    r = analyse(path)
    errA = abs(r["A"] - A_true) / A_true
    errT = abs(r["T"] - T_true) / T_true
    print(f"true  A={A_true:.4f} T={T_true:.4f}")
    print(f"fit   A={r['A']:.4f} T={r['T']:.4f}   error {errA * 100:.2f}% and {errT * 100:.2f}%")
    ok = errA < 0.05 and errT < 0.05
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fit", help="fit A and T from one or more step logs")
    f.add_argument("paths", nargs="+")
    f.add_argument("--plot", metavar="PNG")
    f.add_argument("--latex", metavar="TEX", help="write a booktabs table fragment for the report")
    f.add_argument("--window", type=int, default=21, help="Savitzky-Golay window in samples")
    f.add_argument("--polyorder", type=int, default=2)

    s = sub.add_parser("sensor", help="fit the sensor constant k from paired readings")
    s.add_argument("--volts", nargs="+", type=float, required=True)
    s.add_argument("--metres", nargs="+", type=float, required=True)

    sub.add_parser("selftest", help="check the fitter against a synthetic first-order trace")

    args = p.parse_args(argv)
    if args.cmd == "selftest":
        return selftest()
    if args.cmd == "sensor":
        sensor(args.volts, args.metres)
        return 0

    paths = [q for pat in args.paths for q in sorted(glob.glob(pat))] or args.paths
    results = []
    for path in paths:
        try:
            results.append(analyse(path, args.window, args.polyorder))
        except (ValueError, OSError) as exc:
            print(f"skipped {path}: {exc}", file=sys.stderr)
    if not results:
        print("nothing to fit", file=sys.stderr)
        return 1
    report(results)
    if args.latex:
        write_latex(results, args.latex)
    if args.plot:
        plot(results, args.plot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
