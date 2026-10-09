"""Pick real resistors for the Kp window, and size the two dividers.

White Lab stock is 10 percent, so a non-inverting stage built from two of them
has a worst case gain of 1 + 0.9*R1/(1.1*R2) up to 1 + 1.1*R1/(0.9*R2). This
script only keeps pairs whose whole tolerance band lands inside the Kp window
that design.py reported, so the controller meets spec without hand picking.

Usage:
    python bom.py gain --kp-lo 0.76 --kp-hi 1.14
    python bom.py divider --target 2.5 --rail 15 --span 0.5
    python bom.py steptest --v1 2.0 --v2 3.5
"""

import argparse
import itertools

E12 = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]
DECADES = [1e2, 1e3, 1e4, 1e5]
TOL = 0.10


def stock():
    return [v * d for d in DECADES for v in E12]


def fmt_r(r):
    if r >= 1e6:
        return f"{r / 1e6:g}M"
    if r >= 1e3:
        return f"{r / 1e3:g}k"
    return f"{r:g}R"


def gain_pairs(kp_lo, kp_hi, target=None, limit=12, inverting=False):
    """Resistor pairs whose whole tolerance band stays inside the Kp window.

    Non-inverting stage: gain = 1 + R1/R2, so it cannot go below unity.
    Inverting stage: gain = Rf/Rin in magnitude, any gain, but it flips the sign,
    so it needs a second inverting stage of unity gain to put the sign back.
    """
    target = target or (kp_lo * kp_hi) ** 0.5
    if not inverting and kp_lo <= 1.0 <= kp_hi:
        print("The window contains unity, so a plain voltage follower meets the spec with no resistors")
        print("and no tolerance at all. Only reach for a resistor pair if you want gain above 1.")
        print()
    if not inverting and kp_hi <= 1.0:
        print("The whole window is below unity gain, which a non-inverting stage cannot reach.")
        print("Rerun with --inverting and plan on two stages.")
        return []

    rows = []
    for ra, rb in itertools.product(stock(), stock()):
        if not 1e3 <= rb <= 1e6 or not 1e3 <= ra <= 1e6:  # keep both legs out of op-amp loading territory
            continue
        if inverting:
            nominal = ra / rb
            worst_lo = (ra * (1 - TOL)) / (rb * (1 + TOL))
            worst_hi = (ra * (1 + TOL)) / (rb * (1 - TOL))
        else:
            nominal = 1 + ra / rb
            worst_lo = 1 + (ra * (1 - TOL)) / (rb * (1 + TOL))
            worst_hi = 1 + (ra * (1 + TOL)) / (rb * (1 - TOL))
        if worst_lo < kp_lo or worst_hi > kp_hi:
            continue
        margin = min(worst_lo - kp_lo, kp_hi - worst_hi)
        rows.append((abs(nominal - target), -margin, ra, rb, nominal, worst_lo, worst_hi))
    rows.sort()
    if not rows:
        print(f"no E12 pair fits entirely inside {kp_lo:.3f} to {kp_hi:.3f} at {TOL * 100:.0f} percent tolerance.")
        print("Options: measure a tray of resistors on the bench multimeter and pick a matched pair, put a")
        print("trim pot in the feedback leg, or trim the hover bias to widen the window first.")
        return []

    labels = ("Rf", "Rin") if inverting else ("R1", "R2")
    print(f"target gain {target:.3f}, window {kp_lo:.3f} to {kp_hi:.3f}")
    print()
    print(f"| {labels[0]} | {labels[1]} | nominal gain | worst case | margin |")
    print("| --- | --- | --- | --- | --- |")
    for _, negmargin, ra, rb, nominal, lo, hi in rows[:limit]:
        print(f"| {fmt_r(ra)} | {fmt_r(rb)} | {nominal:.3f} | {lo:.3f} to {hi:.3f} | {-negmargin:.3f} |")
    if inverting:
        print()
        print("Inverting stage flips the sign. Follow it with a unity inverting stage, four equal resistors,")
        print("or fold the flip into the differential amplifier by swapping its two inputs.")
    return rows


def divider(target, rail, span):
    """Pot divider off the rails giving `target` volts with +/- span of trim range."""
    print(f"target {target:.2f} V from a {rail:.0f} V rail, trim range +/-{span:.2f} V")
    print()
    print("| R_top | pot | R_bottom | range (V) |")
    print("| --- | --- | --- | --- |")
    pots = [1e3, 5e3, 1e4, 5e4]
    rows = []
    for pot in pots:
        for rt, rb in itertools.product(stock(), stock()):
            total = rt + pot + rb
            v_lo = rail * rb / total
            v_hi = rail * (rb + pot) / total
            if not (v_lo <= target - span and v_hi >= target + span):
                continue
            width = v_hi - v_lo
            if width > 6 * span:  # a pot that spans far too much is hard to set
                continue
            rows.append((width, rt, pot, rb, v_lo, v_hi))
    rows.sort()
    for width, rt, pot, rb, v_lo, v_hi in rows[:8]:
        print(f"| {fmt_r(rt)} | {fmt_r(pot)} | {fmt_r(rb)} | {v_lo:.2f} to {v_hi:.2f} |")
    if not rows:
        print("| none | | | widen the span or try another pot value |")
    return rows


def steptest(v1, v2, rail=15.0):
    """Divider for the step test, swinging between V1 and V2 inside the 0 to 5 V input limit."""
    if v2 > 5.0:
        print(f"V2 = {v2:.2f} V is above the 5 V input limit, the kitticopter saturates")
    print(f"step from {v1:.2f} V to {v2:.2f} V off a {rail:.0f} V rail")
    print("Appendix A1 circuit 1: R1 top, pot R2, R3 bottom.")
    print("Bottom of the swing is rail*R3/(R1+R2+R3), top is rail*(R2+R3)/(R1+R2+R3).")
    print()
    print("| R1 | pot R2 | R3 | swing (V) |")
    print("| --- | --- | --- | --- |")
    rows = []
    for pot in (1e3, 5e3, 1e4):
        for r1, r3 in itertools.product(stock(), stock()):
            total = r1 + pot + r3
            lo = rail * r3 / total
            hi = rail * (pot + r3) / total
            if abs(lo - v1) > 0.15 or abs(hi - v2) > 0.15:
                continue
            rows.append((abs(lo - v1) + abs(hi - v2), r1, pot, r3, lo, hi))
    rows.sort()
    for _, r1, pot, r3, lo, hi in rows[:8]:
        print(f"| {fmt_r(r1)} | {fmt_r(pot)} | {fmt_r(r3)} | {lo:.2f} to {hi:.2f} |")
    if not rows:
        print("| none | | | try another pot value or loosen the targets |")
    return rows


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gain", help="non-inverting pairs inside the Kp window")
    g.add_argument("--kp-lo", type=float, required=True)
    g.add_argument("--kp-hi", type=float, required=True)
    g.add_argument("--kp-target", type=float, default=None, help="default is the geometric centre of the window")
    g.add_argument("--inverting", action="store_true", help="size an inverting stage instead, gain Rf/Rin")
    g.add_argument("--limit", type=int, default=12)

    d = sub.add_parser("divider", help="pot divider for the level shift")
    d.add_argument("--target", type=float, required=True, help="hover bias voltage")
    d.add_argument("--rail", type=float, default=15.0)
    d.add_argument("--span", type=float, default=0.5, help="trim range needed either side")

    s = sub.add_parser("steptest", help="pot divider for the session 1 step")
    s.add_argument("--v1", type=float, required=True, help="hover baseline")
    s.add_argument("--v2", type=float, required=True, help="top of the step, keep at or below 5 V")
    s.add_argument("--rail", type=float, default=15.0)

    args = p.parse_args(argv)
    if args.cmd == "gain":
        gain_pairs(args.kp_lo, args.kp_hi, args.kp_target, args.limit, args.inverting)
    elif args.cmd == "divider":
        divider(args.target, args.rail, args.span)
    else:
        steptest(args.v1, args.v2, args.rail)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
