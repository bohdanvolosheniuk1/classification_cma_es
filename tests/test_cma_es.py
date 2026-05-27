import numpy as np

from classifiers.cma_es import minimize_cma


def sphere(x):
    return float(np.sum(x * x))


def rosen(x):
    return float(np.sum(100 * (x[1:] - x[:-1] ** 2) ** 2 + (1 - x[:-1]) ** 2))


def test_sphere_3d():
    res = minimize_cma(sphere, x0=np.array([1.0, 2.0, 3.0]),
                       sigma0=0.5, max_iter=50, random_state=1)
    assert res.best_f < 1e-3
    assert res.n_evaluations > 0


def test_rosenbrock_2d():
    res = minimize_cma(rosen, x0=np.array([-1.0, 1.0]),
                       sigma0=0.5, max_iter=200, random_state=1)
    assert res.best_f < 1e-2


def test_bounds_respected():
    res = minimize_cma(sphere, x0=np.array([0.5, 0.5]),
                       sigma0=0.3, max_iter=30,
                       bounds=(0.1, 0.9), random_state=1)
    assert np.all(res.best_x >= 0.1 - 1e-9)
    assert np.all(res.best_x <= 0.9 + 1e-9)
