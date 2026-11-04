import numpy as np
from numpy.testing import assert_allclose
from sqw.core import MarkovAnalysis, StationaryAnalysis, ClasswiseStatistics
from test_edge_markov import make_walk
from test_stationary import x04_walk


def test_reducible_identity_edge_has_random_class_limit_not_one_gaussian():
    stationary=StationaryAnalysis(make_walk('path',3,'identity'))
    q=stationary.initial_law(np.eye(4)/4)
    result=ClasswiseStatistics(stationary.chain).analyze([1,0,0,0],q)
    assert not result.global_clt_available and result.global_mean is None
    assert result.global_asymptotic_variance is None
    assert_allclose([c.absorption_probability for c in result.classes],[.5,.5])
    assert_allclose([c.poisson.mean for c in result.classes],[.5,0])
    assert [c.poisson.period for c in result.classes]==[2,2]
    assert all(c.poisson.degenerate for c in result.classes)
    assert_allclose(result.ensemble_limit_mean,.25)
    assert_allclose(result.between_class_variance,1/16)


def test_X04_transient_mass_enters_classwise_mean_and_variance():
    stationary=StationaryAnalysis(x04_walk())
    engine=ClasswiseStatistics(stationary.chain)
    result=engine.analyze([1,0,0,0,0],np.eye(5)[2])
    assert result.initial_transient_mass==1
    assert result.reachable_class_indices==(0,)
    assert_allclose([c.absorption_probability for c in result.classes],[1,0])
    assert_allclose(result.global_mean,2/3)
    # Left class [[1/2,1/2],[1,0]], eigenvalue -1/2:
    # instantaneous variance 2/9, asymptotic = (2/9)*(1-1/2)/(1+1/2).
    assert_allclose(result.global_asymptotic_variance,2/27)
    assert result.classes[0].poisson.period==1
    assert result.classes[1].poisson.degenerate
    other=engine.analyze([1,0,0,0,0],np.eye(5)[4])
    assert other.classes[0].poisson is result.classes[0].poisson
    assert other.global_mean==0


def test_fractional_transient_absorption_and_same_mean_variance_mixture():
    p=np.array([[0,.25,0,.75,0],[0,2/3,1/3,0,0],[0,1/3,2/3,0,0],
                [0,0,0,0,1],[0,0,0,1,0]])
    engine=ClasswiseStatistics(p)
    result=engine.analyze([9,1,0,1,0],[1,0,0,0,0])
    assert_allclose([c.absorption_probability for c in result.classes],[.25,.75])
    assert_allclose([c.poisson.mean for c in result.classes],[.5,.5])
    assert_allclose([c.poisson.asymptotic_variance for c in result.classes],[.5,0])
    assert result.between_class_variance==0
    assert not result.global_clt_available  # same mean does not merge variances


def test_reachability_does_not_discard_a_tiny_class_probability():
    chain=MarkovAnalysis(np.eye(2))
    assert len(chain.reachable_closed_classes([1.,1e-250]))==2
    result=ClasswiseStatistics(chain).analyze([0,1],[1.,1e-250])
    assert result.reachable_class_indices==(0,1)
    assert not result.global_clt_available
    assert result.classes[1].absorption_probability>0
