import numpy as np
import pytest
from numpy.testing import assert_allclose
from scipy.sparse import csr_matrix
from sqw.core.markov_analysis import MarkovAnalysis
from sqw.core.markov_statistics import PoissonSolver


@pytest.mark.parametrize('r', [0., .01, .2, .5, .8, .99])
def test_X01_indicator_variance_with_explicit_handoff_order(r):
    # Handoff Markov order: (xy),(zy),(yx),(yz); M is COLUMN stochastic.
    m = np.array([[0,0,r,1-r],[0,0,1-r,r],[1,0,0,0],[0,1,0,0]])
    solver = PoissonSolver(m.T)
    result = solver.solve([1,0,0,0])
    assert result.period == (4 if r == 0 else 2)
    assert_allclose(result.asymptotic_variance, r/(8*(1-r)), atol=1e-12)
    assert_allclose((np.eye(4)-m.T) @ result.solution, result.centered, atol=2e-13)
    assert_allclose(np.asarray(result.stationary) @ result.solution, 0, atol=2e-13)
    assert result.relative_residual < 1e-12
    assert result.degenerate == (r == 0)
    assert solver.solve([1,0,0,0]) is result


def test_two_state_correlations_confidence_and_stationarity_checks():
    p = np.array([[2/3,1/3],[1/3,2/3]])
    result = PoissonSolver(csr_matrix(p), stationary=[.5,.5]).solve([1,0])
    assert_allclose(result.mean,.5)
    assert_allclose(result.solution,[.75,-.75])
    assert_allclose(result.asymptotic_variance,.5)
    assert_allclose(result.instantaneous_variance,.25)
    uncertainty = result.uncertainty(100, empirical_mean=.53)
    assert_allclose(uncertainty.standard_error,np.sqrt(.005))
    assert_allclose(uncertainty.iid_comparison_standard_error,.05)
    assert_allclose(uncertainty.interval,[.53-1.95996398454*np.sqrt(.005),.53+1.95996398454*np.sqrt(.005)])
    assert uncertainty.approximate and not uncertainty.simultaneous
    with pytest.raises(ValueError,match='not stationary'): PoissonSolver(p,stationary=[.6,.4])


@pytest.mark.parametrize('length', [1,2,3,4,7])
def test_deterministic_periodic_cycles_have_zero_clt_variance(length):
    p = np.roll(np.eye(length),1,axis=1)
    result = PoissonSolver(p).solve(np.arange(length))
    assert result.period == length and result.degenerate
    assert result.asymptotic_variance == 0
    assert_allclose(result.mean,(length-1)/2)
    assert_allclose((np.eye(length)-p) @ result.solution,result.centered,atol=1e-14)
    assert result.uncertainty(3,empirical_mean=1.).interval is None
    if length == 4:
        assert np.mean(np.arange(length)[:3]) != result.mean  # finite error can persist


def test_nonreversible_nonuniform_chain_and_shift_scale_invariance():
    p = np.array([[.1,.9,0],[0,.2,.8],[.6,.1,.3]])
    solver = PoissonSolver(p)
    result = solver.solve([1,2,-3])
    pi = np.asarray(result.stationary); g=np.asarray(result.centered); h=np.asarray(result.solution)
    independent = np.linalg.solve(np.eye(3)-p+np.outer(np.ones(3),pi),g)
    assert_allclose(h,independent,atol=1e-13)
    assert_allclose(result.asymptotic_variance,pi @ (h*h-(p@h)**2),atol=1e-13)
    scaled = solver.solve(3*np.array([1,2,-3])+1e8)
    assert_allclose(scaled.asymptotic_variance,9*result.asymptotic_variance,atol=1e-12)
    tiny = solver.solve(1e-20*np.array([1,2,-3]))
    assert tiny.asymptotic_variance > 0 and not tiny.degenerate
    assert_allclose(tiny.asymptotic_variance/1e-40,result.asymptotic_variance)


def test_weak_exit_reports_conditioning_without_silently_regularizing():
    p = np.array([[1-1e-14,1e-14],[2e-14,1-2e-14]])
    chain = MarkovAnalysis(p,support_atol=0)
    solver = PoissonSolver(chain)
    result = solver.solve([1,0])
    assert result.stability_warning and result.condition_number > 1e12
    assert result.asymptotic_variance > 1e12 and not result.degenerate
    assert result.uncertainty(1000,empirical_mean=.5).interval is None
    with pytest.raises(ValueError,match='not stationary'): PoissonSolver(chain,stationary=[.5,.5])
    with pytest.raises(ValueError,match='irreducible'): PoissonSolver(p)  # default support removes first exit


def test_sparse_large_cycle_does_not_require_dense_condition_diagnostic(monkeypatch):
    p=csr_matrix((np.ones(200),(np.arange(200),(np.arange(200)+1)%200)),shape=(200,200))
    solver=PoissonSolver(p)
    assert solver._condition is None
    assert solver.solve(np.eye(1,200)[0]).degenerate


@pytest.mark.parametrize('f', [[1], [np.inf,0], [np.nan,0], [1+1j,0]])
def test_invalid_observables_rejected(f):
    with pytest.raises(ValueError): PoissonSolver([[.5,.5],[.5,.5]]).solve(f)


def test_invalid_assumptions_and_interval_arguments():
    for p in (np.eye(2), [[1.1,-.1],[0,1]], [[np.nan]], [[.8]]):
        with pytest.raises(ValueError): PoissonSolver(p)
    solver=PoissonSolver([[.5,.5],[.5,.5]])
    for pi in ([1,0],[1,1],[.5+1j,.5]):
        with pytest.raises(ValueError): PoissonSolver(solver.chain,stationary=pi)
    result=solver.solve([1,0])
    for n in (0,-1,1.5,True):
        with pytest.raises(ValueError): result.uncertainty(n)
    for confidence in (0,1,np.nan):
        with pytest.raises(ValueError): result.uncertainty(10,confidence=confidence)
