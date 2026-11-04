"""Reproducible E-09 benchmark; Monte Carlo evidence is not a proof/test oracle.

Run from the repository root: python examples/trajectory_statistics.py
The default run uses 256 independent stationary-start paths of length 8192
for each SQW model. Only two chart points and one empirical law are retained.
"""
import argparse
import json
import platform
from time import perf_counter

import numpy as np
import scipy
from sqw.core import (GraphModel, ScatteringWalk, InducedVertexWalk,
    scattering_matrix, PoissonSolver, TrajectoryStatistics)


def benchmark(engine, paths, samples, seed):
    f = engine.observable(index=0)
    initial = np.eye(engine.model.dimension)/engine.model.dimension
    theory = engine.analyze(initial,f).classes[0].poisson
    seeds = np.random.SeedSequence(seed).spawn(paths)
    means = np.empty(paths)
    started = perf_counter()
    for i,child in enumerate(seeds):
        path = engine.sample(initial,f,samples,seed=int(child.generate_state(1)[0]),
            start='stationary_class',class_index=0,max_points=2)
        means[i] = path.empirical_mean
    elapsed = perf_counter()-started
    # A finite stationary-start identity, not an infinite covariance series.
    # Valid for this benchmark's irreducible block (periodicity is allowed).
    t = engine.stationary.chain.transition
    pi = np.asarray(theory.stationary)
    g = f-theory.mean
    v = g.copy()
    finite_scaled_variance = float(pi@(g*g))
    for k in range(1,samples):
        v = t@v
        finite_scaled_variance += 2*(1-k/samples)*float(pi@(g*v))
    half = theory.uncertainty(samples).half_width
    return {'paths':paths,'samples_per_path':samples,'master_seed':seed,
        'initialization':'stationary_class','period':theory.period,'mu':theory.mean,
        'sigma_squared':theory.asymptotic_variance,'instantaneous_variance':theory.instantaneous_variance,
        'N_times_exact_finite_variance':finite_scaled_variance,
        'N_times_empirical_variance':float(samples*means.var(ddof=1)),
        'empirical_grand_mean':float(means.mean()),
        'observed_pointwise_95_percent_coverage':float(np.mean(abs(means-theory.mean)<=half)),
        'seconds':elapsed,'observations_per_second':paths*samples/elapsed,
        'retained_points_per_path':2,'density_history_entries':0,
        'relative_poisson_residual':theory.relative_residual}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paths',type=int,default=256)
    parser.add_argument('--samples',type=int,default=8192)
    args = parser.parse_args()
    if args.paths<2 or args.samples<2: parser.error('paths and samples must be at least 2')
    graph = GraphModel.preset('path',3)
    edge = ScatteringWalk(graph,{x:scattering_matrix('dft',graph.degree(x)) for x in graph.vertices})
    triangle = GraphModel.preset('cycle',3)
    vertex = InducedVertexWalk(ScatteringWalk(triangle,
        {x:scattering_matrix('grover',triangle.degree(x)) for x in triangle.vertices}))
    two = PoissonSolver([[2/3,1/3],[1/3,2/3]]).solve([1,0])
    print(json.dumps({'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,
        'two_state':{'mu':two.mean,'h':two.solution,'sigma_squared':two.asymptotic_variance}}),flush=True)
    for name,engine,seed in [('edge_path3_DFT',TrajectoryStatistics(edge),20261104),
                             ('vertex_triangle_Grover',TrajectoryStatistics(vertex),20261105)]:
        print(json.dumps({name:benchmark(engine,args.paths,args.samples,seed)}),flush=True)


if __name__=='__main__': main()
