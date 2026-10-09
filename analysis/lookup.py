"""Precompute the Kp window over a grid, so session 2 needs no laptop.

Session 1 gives you A, T and k. Session 2 wants a gain and a resistor pair. If
the two sit close together, or White Lab closes, you do not want to be deriving
anything. Print this before session 1 and read the row off it at the bench.

    python lookup.py --setpoint 1.0 --dist-volts 0.05
    python lookup.py --setpoint 1.0 --k-values 0.8 1.0 1.2 --markdown

Columns are the same numbers design.py reports and the same pairs bom.py picks,
computed here rather than looked up again.
"""

import argparse
import io
import math
from contextlib import redirect_stdout

import bom
import design


def nearest_row(A, T, k, args):
    """Window and recommended gain for one grid cell, from design.window."""
    headroom = design.V_PLANT_HI - args.v_hover
    v_limit = min(args.vmax, headroom)
    lo, hi, binding = design.window(A, T, k, args.dist_volts, args.setpoint,
                                    args.overshoot, args.error, v_limit, args.tol_b)
    if lo > hi:
        return {"A": A, "T": T, "k": k, "lo": lo, "hi": hi, "target": None,
                "pair": None, "note": f"no gain clears every corner ({binding['ceiling'][2]} binds)"}
    target = math.sqrt(lo * hi)

    # a window straddling unity is met by a plain follower, no resistors and no tolerance
    if lo <= 1.0 <= hi:
        return {"A": A, "T": T, "k": k, "lo": lo, "hi": hi, "target": target,
                "pair": None, "note": "voltage follower, no resistors needed"}

    # bom.gain_pairs prints its table, so capture it and keep the best row
    buf = io.StringIO()
    with redirect_stdout(buf):
        rows = bom.gain_pairs(lo, hi, target, limit=1)
    pair = None
    if rows:
        _, _, ra, rb, nominal, wlo, whi = rows[0]
        pair = (ra, rb, nominal, wlo, whi)
    return {"A": A, "T": T, "k": k, "lo": lo, "hi": hi, "target": target,
            "pair": pair, "note": "" if pair else "no E12 pair fits, use a trim pot"}


def grid(args):
    rows = []
    for A in args.a_values:
        for T in args.t_values:
            for k in args.k_values:
                rows.append(nearest_row(A, T, k, args))
    return rows


def print_plain(rows, args):
    print(f"Kp lookup, setpoint {args.setpoint:.2f} m, bias error {args.dist_volts:.3f} V, "
          f"hover {args.v_hover:.2f} V")
    print(f"specs overshoot < {args.overshoot * 100:.0f} %, disturbance < {args.error * 100:.0f} %, "
          f"drag +/-{args.tol_b * 100:.0f} %, resistors {bom.TOL * 100:.0f} %")
    print()
    print(f"{'A':>6}{'T':>6}{'k':>6}{'Kp lo':>8}{'Kp hi':>8}{'aim':>8}  resistor pair")
    print("-" * 64)
    for r in rows:
        if r["target"] is None:
            print(f"{r['A']:>6.2f}{r['T']:>6.2f}{r['k']:>6.2f}{r['lo']:>8.3f}{r['hi']:>8.3f}"
                  f"{'-':>8}  {r['note']}")
            continue
        if r["pair"]:
            ra, rb, nominal, wlo, whi = r["pair"]
            desc = f"{bom.fmt_r(ra)} / {bom.fmt_r(rb)}, gain {nominal:.2f} ({wlo:.2f} to {whi:.2f})"
        else:
            desc = r["note"]
        print(f"{r['A']:>6.2f}{r['T']:>6.2f}{r['k']:>6.2f}{r['lo']:>8.3f}{r['hi']:>8.3f}"
              f"{r['target']:>8.3f}  {desc}")
    print()
    print("Read the row nearest your measured A, T and k, then confirm with design.py when you")
    print("next have a machine. Interpolating between rows is fine, the window moves smoothly.")


def print_markdown(rows, args):
    print(f"| $A$ | $T$ | $k$ | $K_p$ low | $K_p$ high | aim | Resistor pair |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for r in rows:
        if r["target"] is None:
            print(f"| {r['A']:.2f} | {r['T']:.2f} | {r['k']:.2f} | {r['lo']:.3f} | {r['hi']:.3f} | - | {r['note']} |")
            continue
        if r["pair"]:
            ra, rb, nominal, wlo, whi = r["pair"]
            desc = f"{bom.fmt_r(ra)} / {bom.fmt_r(rb)}, gain {nominal:.2f}"
        else:
            desc = r["note"]
        print(f"| {r['A']:.2f} | {r['T']:.2f} | {r['k']:.2f} | {r['lo']:.3f} | {r['hi']:.3f} | "
              f"{r['target']:.3f} | {desc} |")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--a-values", nargs="+", type=float, default=[0.4, 0.6, 0.8, 1.0, 1.4])
    p.add_argument("--t-values", nargs="+", type=float, default=[0.8, 1.2, 1.6, 2.0, 2.5])
    p.add_argument("--k-values", nargs="+", type=float, default=[1.0])
    p.add_argument("--setpoint", type=float, default=1.0)
    p.add_argument("--dist-volts", type=float, default=0.05)
    p.add_argument("--overshoot", type=float, default=0.30)
    p.add_argument("--error", type=float, default=0.08)
    p.add_argument("--vmax", type=float, default=10.0)
    p.add_argument("--v-hover", type=float, default=2.5)
    p.add_argument("--tol-b", type=float, default=0.10)
    p.add_argument("--markdown", action="store_true", help="emit a markdown table to paste into notes")
    args = p.parse_args(argv)

    rows = grid(args)
    if args.markdown:
        print_markdown(rows, args)
    else:
        print_plain(rows, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
