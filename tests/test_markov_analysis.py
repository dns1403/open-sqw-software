"""Independent finite-chain fixtures, including support/conditioning hazards."""
import numpy as np
import pytest
from numpy.testing import assert_allclose
from scipy.sparse import csr_matrix, eye
from sqw.core.markov_analysis import MarkovAnalysis


def test_nonuniform_stationary_and_raw_evolution():
    p = np.array([[.8, .2], [.4, .6]])
    a = MarkovAnalysis(p)
    assert a.irreducible and a.unique_stationary and a.ordinary_for_all_initials
    assert a.closed_classes[0].period == 1
    assert_allclose(a.stationary_basis.toarray(), [[2/3, 1/3]], atol=1e-14)
    frames = list(a.evolve([1, 0], 12, start_step=1))
    expected = np.array([[1, 0] @ np.linalg.matrix_power(p, n) for n in range(13)])
    for n, f in enumerate(frames):
        assert f.step == n + 1
        assert_allclose(f.probabilities, expected[n], atol=2e-14)
        assert_allclose(f.cesaro, expected[:n+1].mean(axis=0), atol=2e-14)
    assert frames[-1].total_variation < frames[0].total_variation


def test_multiple_classes_periods_and_fractional_absorption():
    # 0 transient with geometric waiting; 1,2 cycle; 3,4,5 cycle; 6 absorbing.
    p = np.zeros((7, 7)); p[0, [0, 1, 3, 6]] = [.5, .1, .15, .25]
    p[1, 2] = p[2, 1] = p[3, 4] = p[4, 5] = p[5, 3] = p[6, 6] = 1
    a = MarkovAnalysis(csr_matrix(p))
    assert a.transient_states == (0,)
    assert [c.period for c in a.closed_classes] == [2, 3, 1]
    assert [c.states for c in a.closed_classes] == [(1, 2), (3, 4, 5), (6,)]
    assert a.classes[0].period == 1  # transient self-loop, not a recurrent class
    h = a.absorption.toarray()
    assert_allclose(h[0], [.2, .3, .5], atol=1e-14)
    assert_allclose(p @ h, h, atol=1e-14)
    assert_allclose(h.sum(axis=1), 1, atol=1e-14)
    q = np.eye(7)[0]
    mixture = a.mixture(q)
    assert not mixture.ordinary_guaranteed and not a.unique_stationary
    assert_allclose(mixture.stationary, [0, .1, .1, .1, .1, .1, .5], atol=1e-14)
    assert a.mixture(np.eye(7)[6]).ordinary_guaranteed
    assert not a.mixture(mixture.stationary).ordinary_guaranteed  # sufficient guarantee, not an iff
    frames = list(a.evolve(q, 1200))
    assert frames[-1].total_variation > .05
    assert frames[-1].cesaro_total_variation < .002
    for c in a.closed_classes:
        for i, subclass in enumerate(c.cyclic_subclasses):
            for x in subclass:
                assert set(np.flatnonzero(p[x])) <= set(c.cyclic_subclasses[(i+1) % c.period])


@pytest.mark.parametrize('length', [1, 2, 3, 4, 7])
def test_deterministic_cycle_gcd_period(length):
    p = np.roll(np.eye(length), 1, axis=1)
    a = MarkovAnalysis(p)
    assert a.closed_classes[0].period == length
    assert_allclose(a.stationary_basis.toarray(), [np.ones(length) / length])
    assert a.unique_stationary
    assert a.ordinary_for_all_initials == (length == 1)


def test_transient_singleton_without_return_has_no_period_and_unique_stationary():
    a = MarkovAnalysis([[0, 1, 0], [0, .5, .5], [0, 0, 1]])
    assert a.classes[0].period is None
    assert a.classes[1].period == 1
    assert a.transient_states == (0, 1)
    assert not a.irreducible and a.unique_stationary and a.ordinary_for_all_initials
    assert_allclose(a.mixture([1, 0, 0]).stationary, [0, 0, 1])


def test_numerical_support_is_explicit_and_does_not_change_raw_curve():
    epsilon = 1e-16
    p = np.array([[1 - epsilon, epsilon], [0, 1.]])
    a = MarkovAnalysis(p)
    assert len(a.closed_classes) == 2
    assert a.support_policy == 'numerical_threshold' and a.discarded_entries == 1
    assert a.discarded_max_row_mass == epsilon
    assert a.matrix_change_max_row_l1 > epsilon
    assert a.raw_transition[0, 1] == epsilon
    assert a.transition[0, 1] == 0
    assert list(a.evolve([1, 0], 1))[-1].probabilities[1] == epsilon
    # A certified tiny transition changes the infinite-time answer completely.
    exact = MarkovAnalysis(p, support_mask=p != 0)
    assert exact.unique_stationary and exact.transient_states == (0,)
    assert exact.discarded_entries == 0
    assert_allclose(exact.mixture([1, 0]).stationary, [0, 1])
    assert_allclose(p, [[1-epsilon, epsilon], [0, 1.]])


def test_tiny_rates_do_not_cancel_in_balance_or_absorption_solves():
    p = np.array([[1., 1e-24], [2e-24, 1.]])
    a = MarkovAnalysis(p, support_mask=np.ones((2, 2), bool))
    assert_allclose(a.stationary_basis.toarray(), [[2/3, 1/3]], atol=1e-14)
    transient = MarkovAnalysis([[1, 1e-24, 2e-24], [0, 1, 0], [0, 0, 1]], support_atol=0)
    assert_allclose(transient.absorption.toarray()[0], [1/3, 2/3], atol=1e-14)


def test_coupled_transient_block_with_nontrivial_basin_probabilities():
    # Independent balance: .8 h0 - .3 h1 = .5, -.4 h0 + .9 h1 = 0.
    p = np.array([[.2,.3,.5,0], [.4,.1,0,.5], [0,0,1,0], [0,0,0,1]])
    analysis = MarkovAnalysis(p)
    assert analysis.transient_states == (0, 1)
    assert_allclose(analysis.absorption.toarray(), [[.75,.25],[1/3,2/3],[1,0],[0,1]], atol=2e-14)
    initial = np.array([.2,.8,0,0])
    mixture = analysis.mixture(initial)
    assert_allclose(mixture.class_weights, [5/12,7/12], atol=2e-14)
    assert_allclose(initial @ np.linalg.matrix_power(p,500), mixture.stationary, atol=3e-14)


def test_declared_support_removes_only_justified_roundoff():
    p = np.array([[1, 1e-32], [0, 1.]])
    a = MarkovAnalysis(p, support_mask=np.eye(2, dtype=bool))
    assert a.support_policy == 'declared_mask' and a.discarded_entries == 1
    with pytest.raises(ValueError, match='Declared zeros'):
        MarkovAnalysis([[.9, .1], [0, 1]], support_mask=np.eye(2, dtype=bool))
    with pytest.raises(ValueError, match='zero transition'):
        MarkovAnalysis(np.eye(2), support_mask=np.ones((2, 2), bool))


@pytest.mark.parametrize('p', [[], [[.5, .2]], [[1, 0], [.1, .8]],
    [[1.1, -.1], [0, 1]], [[np.nan]], [[np.inf]], [[1 + 1j]]])
def test_invalid_transition_rejected(p):
    with pytest.raises((ValueError, TypeError)): MarkovAnalysis(p)


def test_options_and_initial_law_validation_and_detached_outputs():
    for options in ({'support_atol': -1}, {'support_atol': np.nan},
                    {'support_atol': .9}, {'validation_atol': 0},
                    {'support_mask': [[2, 0], [0, 1]]}):
        with pytest.raises(ValueError): MarkovAnalysis([[.5, .5], [.5, .5]], **options)
    a = MarkovAnalysis([[.5, .5], [.5, .5]])
    for q in ([1], [1, 1], [-1, 2]):
        with pytest.raises(ValueError): a.mixture(q)
    p = a.transition; p.data[:] = 0
    assert_allclose(a.transition.toarray(), .5)


def test_many_absorbing_classes_keep_sparse_stationary_and_absorption_outputs():
    a = MarkovAnalysis(eye(500, format='csr'))
    assert len(a.closed_classes) == 500
    assert a.stationary_basis.nnz == a.absorption.nnz == 500
    assert a.transient_states == ()
