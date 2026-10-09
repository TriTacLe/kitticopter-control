"""Check your own answers to prep tasks (a) to (d) for consistency.

This does not hand you the derivation. You give it the plant constants you
worked from and the answers you got, and it tells you which lines hold up,
recomputing each from the model and confirming against a simulation.

    python checkprep.py --a 0.5 --b 0.625 --k 1.0 --kp 0.93 \
        --claim-A 0.80 --claim-T 1.60 --claim-type 1 \
        --claim-zeta 0.458 --claim-step-error 0 \
        --claim-offset 0.054 --bias 0.05 --setpoint 1.0

    python checkprep.py --selftest

Claims you leave out are simply not checked.
"""

import argparse
import math

import numpy as np

import simloop

TOL = 0.02  # 2 percent, loose enough for a hand calculation, tight enough to catch a real slip


class Check:
    def __init__(self):
        self.rows = []

    def add(self, name, claimed, computed, hint, tol=TOL, absolute=False):
        if claimed is None:
            self.rows.append((name, None, computed, None, ""))
            return
        if absolute:
            ok = abs(claimed - computed) <= tol
        else:
            denom = max(abs(computed), 1e-9)
            ok = abs(claimed - computed) / denom <= tol
        self.rows.append((name, claimed, computed, ok, "" if ok else hint))

    def report(self):
        width = max(len(r[0]) for r in self.rows) + 2
        print(f"{'quantity':<{width}}{'yours':>12}{'model':>12}  verdict")
        print("-" * (width + 34))
        failures = 0
        for name, claimed, computed, ok, hint in self.rows:
            if claimed is None:
                print(f"{name:<{width}}{'-':>12}{computed:>12.4f}  not claimed")
                continue
            mark = "agrees" if ok else "DISAGREES"
            failures += 0 if ok else 1
            print(f"{name:<{width}}{claimed:>12.4f}{computed:>12.4f}  {mark}")
            if hint:
                print(f"{'':<{width}}{'':>24}  {hint}")
        print()
        if failures:
            print(f"{failures} line(s) disagree. Rework those before you present the prep, and before")
            print("you spend one of your three model-check attempts.")
        else:
            print("Every claimed line agrees with the model. That is consistency, not correctness:")
            print("it cannot see a block diagram, so the interface and the disturbance node are")
            print("still on you.")
        return failures


def type_number(poles_at_origin):
    return poles_at_origin


def run(args):
    a, b, k, Kp = args.a, args.b, args.k, args.kp
    A, T = a / b, 1.0 / b
    wn = math.sqrt(Kp * k * A / T)
    zeta = 1.0 / (2.0 * math.sqrt(Kp * k * A * T))

    # loop gain Kp*k*A / (s(Ts+1)) has one pole at the origin
    poles = np.roots([T, 1.0, 0.0])
    at_origin = int(np.sum(np.abs(poles) < 1e-12))

    # two separate questions, so two runs. Setpoint tracking is asked with no disturbance,
    # the offset is asked with the bias error and no other change.
    clean = simloop.simulate(A, T, k, Kp, args.setpoint, v_hover=2.5,
                             bias_error=0.0, saturate=False)
    m_clean = simloop.metrics(clean, args.setpoint)
    sim = simloop.simulate(A, T, k, Kp, args.setpoint, v_hover=2.5,
                           bias_error=args.bias, saturate=False)
    m = simloop.metrics(sim, args.setpoint)
    offset_sim = abs(m["final"] - m_clean["final"])
    offset_formula = args.bias / (Kp * k)

    c = Check()
    c.add("A = a/b", args.claim_A, A,
          "A is the velocity gain, thrust constant over drag constant, not a/(something else)")
    c.add("T = 1/b", args.claim_T, T,
          "T is set by drag alone. If yours carries an a in it, the gain leaked into the time constant")
    c.add("type number", float(args.claim_type) if args.claim_type is not None else None,
          float(type_number(at_origin)),
          "count poles of the LOOP GAIN at the origin, not poles of the closed loop", tol=0.5, absolute=True)
    c.add("omega_n", args.claim_wn, wn,
          "wn^2 is the constant term of the closed-loop denominator after dividing through by T")
    c.add("zeta", args.claim_zeta, zeta,
          "2*zeta*wn is the s coefficient, which is 1/T here, so zeta = 1/(2*sqrt(Kp k A T))")
    c.add("step error (m)", args.claim_step_error, args.setpoint - m_clean["final"],
          "type 1 tracks a step with zero error. A nonzero answer usually means the integrator "
          "was put in the controller or left out of the plant", tol=2e-3, absolute=True)
    c.add("disturbance offset (m)", args.claim_offset, offset_formula,
          "offset is dV/(Kp k). If yours has a T or an A in it, the integrator was not cancelled "
          "in the final value")

    failures = c.report()
    print()
    print(f"simulation cross-check, no disturbance: settled at {m_clean['final']:.5f} m against a "
          f"{args.setpoint:.2f} m setpoint")
    print(f"  with {args.bias:.3f} V of bias error it settles at {m['final']:.5f} m")
    print(f"  simulated offset {offset_sim:.5f} m, formula {offset_formula:.5f} m")
    print(f"  overshoot {m['overshoot'] * 100:.2f} %, zeta {sim['zeta']:.3f}")
    return 1 if failures else 0


def selftest():
    """A consistent set must pass, and a wrong T must fail on the T line and the ones downstream."""
    base = dict(a=0.5, b=0.625, k=1.0, kp=0.93, setpoint=1.0, bias=0.05,
                claim_A=0.80, claim_T=1.60, claim_type=1, claim_wn=0.6822,
                claim_zeta=0.4583, claim_step_error=0.0, claim_offset=0.05376)
    print("== consistent set, expect every line to agree ==")
    good = run(argparse.Namespace(**base))
    print()
    print("== same set with T claimed as 1.0, expect the T line to fail ==")
    bad_args = dict(base)
    bad_args["claim_T"] = 1.0
    bad = run(argparse.Namespace(**bad_args))
    print()
    ok = good == 0 and bad == 1
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--a", type=float, help="thrust constant you are working from, m/(V s^2)")
    p.add_argument("--b", type=float, help="drag constant, 1/s")
    p.add_argument("--k", type=float, help="sensor constant, V/m")
    p.add_argument("--kp", type=float, help="the gain you are checking at")
    p.add_argument("--setpoint", type=float, default=1.0)
    p.add_argument("--bias", type=float, default=0.05, help="bias trim error, V")
    p.add_argument("--claim-A", type=float)
    p.add_argument("--claim-T", type=float)
    p.add_argument("--claim-type", type=int)
    p.add_argument("--claim-wn", type=float)
    p.add_argument("--claim-zeta", type=float)
    p.add_argument("--claim-step-error", type=float, help="steady-state position error to a step, m")
    p.add_argument("--claim-offset", type=float, help="steady-state offset from the bias error, m")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args(argv)

    if args.selftest:
        return selftest()
    if None in (args.a, args.b, args.k, args.kp):
        p.error("--a, --b, --k and --kp are required unless --selftest is given")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
