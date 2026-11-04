"""Reproducible local ensemble timings; no performance claims from assertions.

Run from the repository root: python examples/benchmark_markov.py
Writes docs/benchmarks.json. Timing excludes model construction and memory
instrumentation. Peak tracemalloc allocations are measured in a separate run;
they are not whole-process RSS or all native-library memory.
"""
import argparse
from datetime import datetime, timezone
import gc
import json
from pathlib import Path
import platform
from statistics import median
from time import perf_counter
import tracemalloc

import numpy as np
import scipy
from sqw.core import (GraphModel, ScatteringWalk, InducedVertexWalk,
                      EdgeReduction, VertexReduction, run_ensemble, scattering_matrix)


def make_model(kind, size, vertex):
    graph = GraphModel.preset(kind, size)
    rng = np.random.default_rng(714)
    edge = ScatteringWalk(graph, {x: scattering_matrix("random", graph.degree(x), rng)
                                  for x in graph.vertices})
    model = InducedVertexWalk(edge, beta={x: .23 * x for x in graph.vertices}) if vertex else edge
    d = model.dimension if vertex else graph.dimension
    a = rng.normal(size=(d, d)) + 1j * rng.normal(size=(d, d))
    rho = a @ a.conj().T
    return model, rho / np.trace(rho)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("docs/benchmarks.json"))
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("repeats must be positive")
    report = {
        "measured_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(), "python": platform.python_version(),
        "numpy": np.__version__, "scipy": scipy.__version__,
        "runtime_method": "Median perf_counter seconds; model/initial construction and tracemalloc excluded; reduction construction inside run_ensemble included.",
        "memory_method": "Peak bytes tracked by tracemalloc in a separate run, with prebuilt model/initial excluded; not process RSS or total native-library memory.",
        "statistics": ["states", "vertices", "edges", "exact"],
        "selected_histories": 3, "seed": 42, "cases": [],
    }
    for vertex, kind, size, count, steps in [
        (False, "cycle", 8, 300, 20), (False, "star", 10, 300, 20),
        (True, "cycle", 8, 300, 20), (True, "star", 10, 300, 20),
        (False, "cycle", 32, 50000, 40),
    ]:
        walk, initial = make_model(kind, size, vertex)
        reduced = VertexReduction(walk) if vertex else EdgeReduction(walk)
        rho = initial.copy()
        kraus = walk.kraus_operators()
        discrepancy = 0.0
        for state in reduced.iter_mean(initial, 8):
            discrepancy = max(discrepancy, float(np.max(abs(state.density() - rho))))
            rho = sum(k @ rho @ k.conj().T for k in kraus)
        case = {"model": "vertex" if vertex else "edge", "graph": kind,
                "vertices": size, "dimension": len(initial), "trajectories": count,
                "steps": steps, "initial": "complex mixed", "scattering": "random unitary",
                "max_mean_density_error_through_step_8": discrepancy, "strategies": {}}
        strategies = ("reference", "optimized") if count < 50000 else ("optimized",)
        for strategy in strategies:
            def run():
                return run_ensemble(walk, initial, count, steps, seed=42, strategy=strategy,
                                    selected_histories=3)
            elapsed = []
            for _ in range(args.repeats):
                gc.collect()
                start = perf_counter()
                result = run()
                elapsed.append(perf_counter() - start)
                del result
            gc.collect()
            tracemalloc.start()
            result = run()
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            case["strategies"][strategy] = {"seconds": elapsed, "median_seconds": median(elapsed),
                "peak_traced_bytes": peak,
                "final_born_vertex_tv": result.frames[-1].born_vertex_total_variation,
                "final_label_tv": result.frames[-1].state_total_variation}
            del result
            print(f'{case["model"]} {kind}({size}) N={count} T={steps} {strategy}: '
                  f'{median(elapsed):.6f}s, traced peak {peak / 1048576:.3f} MiB', flush=True)
        report["cases"].append(case)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
