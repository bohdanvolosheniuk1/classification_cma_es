import numpy as np

from classifiers.mixture_cma_es import MixtureCMAES, _em_step, _log_mvn_pdf


def sphere(x):
    return float(np.sum(x * x))


def bimodal(x):
    d1 = np.sum((x - 3.0) ** 2)
    d2 = np.sum((x + 3.0) ** 2)
    return -float(np.exp(-d1) + np.exp(-d2))


def test_log_mvn_pdf_against_scipy_like():
    """Перевіряємо обчислення log-щільності проти аналітичної формули."""
    X = np.array([[0.0, 0.0], [1.0, 0.0]])
    mean = np.zeros(2)
    cov = np.eye(2)
    log_p = _log_mvn_pdf(X, mean, cov)
    # для стандартного N(0,I) у 2D: log p = -d/2 * log(2π) - ||x||²/2
    expected = -np.log(2 * np.pi) - 0.5 * np.sum(X ** 2, axis=1)
    assert np.allclose(log_p, expected, atol=1e-6)


def test_em_step_single_component():
    """З одним компонентом EM зводиться до sample mean / sample cov."""
    rng = np.random.default_rng(0)
    X = rng.normal(loc=[1.0, -2.0], scale=0.5, size=(200, 2))
    new_w, new_m, new_c = _em_step(X, np.array([1.0]),
                                   [np.zeros(2)],
                                   [np.eye(2)],
                                   reg=0.0)
    assert abs(new_w[0] - 1.0) < 1e-9
    assert np.allclose(new_m[0], X.mean(axis=0), atol=1e-6)


def test_sphere_3d_converges():
    opt = MixtureCMAES(n_components=3, pop_size=30, sigma0=0.5,
                       max_iter=80, cov_lr=0.2, adaptive=False,
                       random_state=1, tol=1e-12)
    res = opt.minimize(sphere, np.array([1.0, 2.0, 3.0]))
    assert res.best_f < 0.1


def test_bimodal_finds_optimum():
    opt = MixtureCMAES(n_components=2, pop_size=40, sigma0=1.5,
                       max_iter=80, cov_lr=0.3, adaptive=True,
                       bounds=(-6.0, 6.0), random_state=2)
    res = opt.minimize(bimodal, np.array([0.0, 0.0]))
    # глобальний мінімум близько -1.0
    assert res.best_f < -0.9
    # розв'язок або поблизу (3,3), або (-3,-3)
    assert min(np.linalg.norm(res.best_x - 3), np.linalg.norm(res.best_x + 3)) < 0.5


def test_adaptive_can_shrink_k():
    """При надлишкових k самоадаптація має зменшити кількість піків."""
    opt = MixtureCMAES(n_components=8, pop_size=30, sigma0=0.3,
                       max_iter=20, adaptive=True, random_state=1)
    res = opt.minimize(sphere, np.array([0.5, 0.5]))
    assert res.final_k <= 8
