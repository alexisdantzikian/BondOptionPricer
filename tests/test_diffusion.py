"""Tests du modele gaussien a deux facteurs (main/two_factor_gaussian.py).

Ces controles sont ceux qui cassent en premier si une formule est touchee :
recalage exact de la courbe, equivalence avec la forme fermee G2++,
coherence alpha_bar / integral_alpha_bar, exactitude du schema de
simulation, proprietes de martingale, et concordance des formules fermees
d'options avec le Monte-Carlo.
"""

import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.integrate import quad

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "main"))

import two_factor_gaussian as tfg  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TENORS = np.array([0.5, 1, 2, 3, 5, 7, 10, 15, 20, 30.0])
ZERO_RATES = np.array([1.30, 1.45, 1.62, 1.78, 2.05, 2.25, 2.45, 2.62, 2.70, 2.72]) / 100


@pytest.fixture(scope="module")
def params():
    """Parametres AAA / secteur financier du papier (Exhibit 3), L = 60%."""
    return tfg.TwoFactorGaussianParams(
        a_x=0.0481, sigma_x=0.0097, a_y=0.2327, sigma_y=0.0968, rho=-0.10, L=0.60
    )


@pytest.fixture(scope="module")
def curve():
    return tfg.Curve(TENORS, ZERO_RATES)


@pytest.fixture(scope="module")
def bond():
    """Obligation 3.54% de maturite 15 ans, coupons annuels."""
    return tfg.coupon_bond_cashflows(0.0354, np.arange(1.0, 16.0))


@pytest.fixture(scope="module")
def sim(curve, params):
    """200k trajectoires antithetiques sur une grille de 30 dates."""
    return tfg.simulate(np.linspace(0.5, 15, 30), 200_000, curve, params,
                        seed=7, antithetic=True)


# ---------------------------------------------------------------------------
# Validation des parametres
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "kwargs",
    [
        dict(a_x=0.0),
        dict(a_y=-0.1),
        dict(sigma_x=-1e-4),
        dict(rho=1.5),
        dict(L=1.2),
    ],
)
def test_params_rejette_valeurs_invalides(kwargs):
    base = dict(a_x=0.05, sigma_x=0.01, a_y=0.2, sigma_y=0.1, rho=0.0, L=0.6)
    with pytest.raises(ValueError):
        tfg.TwoFactorGaussianParams(**{**base, **kwargs})


def test_eta_et_recovery(params):
    assert params.eta == pytest.approx(params.L * params.sigma_y)
    assert params.recovery_rate == pytest.approx(0.40)


# ---------------------------------------------------------------------------
# Courbe
# ---------------------------------------------------------------------------

def test_courbe_reprice_les_piliers(curve):
    assert curve.discount(TENORS) == pytest.approx(np.exp(-ZERO_RATES * TENORS), abs=1e-15)


def test_courbe_from_discount_factors_est_inverse():
    df = np.exp(-ZERO_RATES * TENORS)
    c = tfg.Curve.from_discount_factors(TENORS, df)
    assert c.zero_rate(TENORS) == pytest.approx(ZERO_RATES, abs=1e-14)


@pytest.mark.parametrize("interpolation", ["cubic", "linear"])
def test_forward_continu_aux_deux_bornes(interpolation):
    """Non-regression : l'extrapolation plate sur le taux zero creait un saut
    du forward instantane aux piliers extremes (~13 bp a 30 ans, ~19 bp a
    6 mois). L'extrapolation a forward continu supprime les deux."""
    c = tfg.Curve(TENORS, ZERO_RATES, interpolation)
    eps = 1e-7
    for pillar in (TENORS[0], TENORS[-1]):
        gauche = c.instantaneous_forward(pillar - eps)
        droite = c.instantaneous_forward(pillar + eps)
        assert abs(droite - gauche) < 1e-6, f"saut du forward en t={pillar}"


def test_forward_plat_au_dela_du_dernier_pilier(curve):
    f = curve.instantaneous_forward(np.array([30.0, 35.0, 50.0, 80.0]))
    assert f == pytest.approx(f[0], abs=1e-12)


def test_derivee_du_taux_est_coherente_avec_le_taux(curve):
    """zero_rate_derivative doit etre la vraie derivee de zero_rate, dans
    les trois regimes (court, interpole, long)."""
    h = 1e-6
    for t in (0.2, 0.45, 1.5, 12.0, 29.0, 35.0, 45.0):
        fd = (curve.zero_rate(t + h) - curve.zero_rate(t - h)) / (2 * h)
        assert fd == pytest.approx(curve.zero_rate_derivative(t), abs=1e-6)


def test_courbe_plate():
    c = tfg.Curve.flat(0.02)
    assert c.instantaneous_forward(7.3) == pytest.approx(0.02, abs=1e-12)
    assert c.zero_rate(0.1) == pytest.approx(0.02, abs=1e-12)
    assert c.discount(10.0) == pytest.approx(np.exp(-0.2), abs=1e-14)


@pytest.mark.parametrize(
    "args, kwargs",
    [
        ((np.array([2.0, 1.0]), np.array([0.01, 0.02])), {}),          # non croissant
        ((np.array([0.0, 1.0]), np.array([0.01, 0.02])), {}),          # tenor nul
        ((TENORS, ZERO_RATES[:-1]), {}),                                # tailles
        ((TENORS[:3], ZERO_RATES[:3]), dict(interpolation="cubic")),    # < 4 piliers
        ((TENORS, ZERO_RATES), dict(interpolation="quadratic")),        # inconnue
    ],
)
def test_courbe_rejette_entrees_invalides(args, kwargs):
    with pytest.raises(ValueError):
        tfg.Curve(*args, **kwargs)


# ---------------------------------------------------------------------------
# Recalage et equivalence G2++
# ---------------------------------------------------------------------------

def test_recalage_exact_de_la_courbe_risquee(curve, params):
    """Pbar(0, T) doit reproduire exactement Pbar_M(0, T) (eq. 16)."""
    T = np.array([0.5, 1, 2, 5, 10, 15, 20, 30.0])
    prix = tfg.zero_coupon_price(0.0, T, 0.0, 0.0, curve, params)
    assert prix == pytest.approx(curve.discount(T), abs=1e-14)


@pytest.mark.parametrize("t", [0.25, 1.0, 5.0])
@pytest.mark.parametrize("horizon", [0.5, 3.0, 10.0])
@pytest.mark.parametrize("state", [(0.0, 0.0), (0.01, -0.02), (-0.005, 0.03)])
def test_eq16_equivaut_a_la_forme_fermee_g2pp(curve, params, t, horizon, state):
    """Le modele du papier est un G2++ d'eta = L sigma_y : les eq. 16-24
    doivent coincider avec la formule fermee G2++ standard."""
    T, (x, y) = t + horizon, state
    v = tfg.variance_integrated_rate
    a = 0.5 * (v(t, T, params) - v(0, T, params) + v(0, t, params))
    attendu = (curve.discount(T) / curve.discount(t)) * np.exp(
        a - tfg.h_factor(params.a_x, t, T) * x
        - tfg.h_factor(params.a_y, t, T) * params.L * y
    )
    assert tfg.zero_coupon_price(t, T, x, y, curve, params) == pytest.approx(attendu, abs=1e-14)


@pytest.mark.parametrize("T", [1.0, 5.0, 15.0, 40.0])
def test_integral_alpha_bar_vs_quadrature(curve, params, T):
    """La forme fermee de int_0^T alphabar doit egaler la quadrature de
    l'eq. 15, y compris au-dela du dernier pilier."""
    numerique = quad(lambda u: tfg.alpha_bar(u, curve, params), 0, T, limit=400)[0]
    assert numerique == pytest.approx(tfg.integral_alpha_bar(T, curve, params), abs=1e-8)


@pytest.mark.parametrize("t", [1.0, 10.0, 25.0, 40.0])
def test_alpha_bar_est_la_derivee_de_son_integrale(curve, params, t):
    h = 1e-5
    fd = (tfg.integral_alpha_bar(t + h, curve, params)
          - tfg.integral_alpha_bar(t - h, curve, params)) / (2 * h)
    assert fd == pytest.approx(tfg.alpha_bar(t, curve, params), abs=1e-9)


def test_cas_limite_L_nul(curve):
    """L = 0 doit annuler la composante de credit : C_xy = G_y = 1."""
    p0 = tfg.TwoFactorGaussianParams(0.0481, 0.0097, 0.2327, 0.0968, 0.0, 0.0)
    assert tfg.c_xy(1.0, 5.0, p0) == pytest.approx(1.0, abs=1e-15)
    assert tfg.g_y(1.0, 5.0, p0) == pytest.approx(1.0, abs=1e-15)


# ---------------------------------------------------------------------------
# Obligation a coupons et durations
# ---------------------------------------------------------------------------

def test_echeancier(bond):
    times, amounts = bond
    assert times.size == 15
    assert amounts[0] == pytest.approx(0.0354)
    assert amounts[-1] == pytest.approx(1.0354)


def test_prix_obligation_est_la_somme_des_flux(curve, params, bond):
    times, amounts = bond
    prix = tfg.coupon_bond_price(0.0, times, amounts, 0.0, 0.0, curve, params)
    assert prix == pytest.approx(float(np.sum(amounts * curve.discount(times))), abs=1e-14)


def test_prix_obligation_vectorise(curve, params, bond):
    times, amounts = bond
    x = np.array([0.0, 0.01, -0.01])
    y = np.array([0.0, -0.02, 0.02])
    groupe = tfg.coupon_bond_price(1.0, times, amounts, x, y, curve, params)
    un_a_un = [tfg.coupon_bond_price(1.0, times, amounts, xi, yi, curve, params)
               for xi, yi in zip(x, y)]
    assert groupe == pytest.approx(np.array(un_a_un), abs=1e-15)


def test_durations_zcb_vs_differences_finies(curve, params):
    """DP_x = H_x et DP_y = H_y (eq. 26-27), le facteur L restant explicite
    dans la diffusion de l'eq. 25 : d/dy donne donc L H_y."""
    t, T, h = 2.0, 12.0, 1e-6
    x0, y0 = 0.004, -0.01
    f = lambda xx, yy: tfg.zero_coupon_price(t, T, xx, yy, curve, params)
    d_x, d_y = tfg.duration_zcb(t, T, params)
    assert -(f(x0 + h, y0) - f(x0 - h, y0)) / (2 * h) / f(x0, y0) == pytest.approx(d_x, abs=1e-6)
    assert -(f(x0, y0 + h) - f(x0, y0 - h)) / (2 * h) / f(x0, y0) == pytest.approx(
        params.L * d_y, abs=1e-6)


def test_durations_cbb_vs_differences_finies(curve, params, bond):
    times, amounts = bond
    t, h = 2.0, 1e-6
    x0, y0 = 0.004, -0.01
    g = lambda xx, yy: tfg.coupon_bond_price(t, times, amounts, xx, yy, curve, params)
    d_x, d_y = tfg.duration_cbb(t, times, amounts, x0, y0, curve, params)
    assert -(g(x0 + h, y0) - g(x0 - h, y0)) / (2 * h) / g(x0, y0) == pytest.approx(d_x, abs=1e-6)
    assert -(g(x0, y0 + h) - g(x0, y0 - h)) / (2 * h) / g(x0, y0) == pytest.approx(
        params.L * d_y, abs=1e-6)


def test_duration_cbb_degenere_en_duration_zcb(curve, params):
    """Une obligation reduite a un flux unitaire en Tn est un ZC."""
    d_x, d_y = tfg.duration_cbb(1.0, np.array([12.0]), np.array([1.0]), 0.0, 0.0, curve, params)
    h_x, h_y = tfg.duration_zcb(1.0, 12.0, params)
    assert (d_x, d_y) == pytest.approx((h_x, h_y), abs=1e-14)


# ---------------------------------------------------------------------------
# Schema de simulation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("dt", [0.25, 2.0, 10.0])
def test_covariance_du_schema_vs_variance_integree(params, dt):
    """Var[int (x + L y)] deduite de step_covariance doit egaler V(0, dt)."""
    cov = tfg.step_covariance(dt, params)
    v = cov[2, 2] + params.L**2 * cov[3, 3] + 2 * params.L * cov[2, 3]
    assert v == pytest.approx(tfg.variance_integrated_rate(0.0, dt, params), abs=1e-14)


def test_covariance_empirique_vs_theorique(sim, params):
    i = 10
    emp = np.cov(np.vstack([sim.x[:, i], sim.y[:, i], sim.int_x[:, i], sim.int_y[:, i]]))
    th = tfg.step_covariance(sim.times[i], params)   # x(0) = y(0) = 0
    assert np.max(np.abs(emp - th) / np.abs(th)) < 0.03


def test_simulation_sans_biais_de_discretisation(curve, params):
    """Le schema etant exact, un pas unique et cent pas doivent donner la
    meme loi. On compare les deux a la meme graine sur le deflateur."""
    grossier = tfg.simulate([10.0], 100_000, curve, params, seed=3, antithetic=True)
    fin = tfg.simulate(np.linspace(0.1, 10.0, 100), 100_000, curve, params,
                       seed=3, antithetic=True)
    ref = curve.discount(10.0)
    for s in (grossier, fin):
        d = s.discount_factors()[:, -1]
        se = d.std(ddof=1) / np.sqrt(d.size)
        assert abs(d.mean() - ref) < 4 * se


@pytest.mark.parametrize("i, T", [(9, 12.0), (19, 20.0), (29, 25.0)])
def test_martingale_du_zc_actualise(sim, curve, params, i, T):
    """E[D(0,t) Pbar(t,T)] = Pbar_M(0,T)."""
    t = sim.times[i]
    v = sim.discount_factors()[:, i] * tfg.zero_coupon_price(
        t, T, sim.x[:, i], sim.y[:, i], curve, params)
    se = v.std(ddof=1) / np.sqrt(v.size)
    assert abs(v.mean() - curve.discount(T)) < 4 * se


def test_martingale_de_lobligation_actualisee(sim, curve, params, bond):
    times, amounts = bond
    i = 9
    t = sim.times[i]
    v = sim.discount_factors()[:, i] * tfg.coupon_bond_price(
        t, times, amounts, sim.x[:, i], sim.y[:, i], curve, params)
    verses = float(np.sum(amounts[times <= t] * curve.discount(times[times <= t])))
    attendu = float(np.sum(amounts * curve.discount(times))) - verses
    se = v.std(ddof=1) / np.sqrt(v.size)
    assert abs(v.mean() - attendu) < 4 * se


def test_simulation_supporte_rho_unitaire(curve):
    """Avec |rho| = 1 la covariance est singuliere : le repli spectral doit
    prendre le relais de la factorisation de Cholesky."""
    p = tfg.TwoFactorGaussianParams(0.0481, 0.0097, 0.2327, 0.0968, 1.0, 0.8)
    s = tfg.simulate([1.0, 5.0], 2000, curve, p, seed=1)
    assert np.all(np.isfinite(s.x)) and s.x[:, -1].std() > 0


def test_antithetiques_centrent_les_facteurs(curve, params):
    s = tfg.simulate([5.0], 10_000, curve, params, seed=11, antithetic=True)
    assert s.x[:, -1].mean() == pytest.approx(0.0, abs=1e-15)
    assert s.y[:, -1].mean() == pytest.approx(0.0, abs=1e-15)


def test_grille_uniforme_reutilise_la_factorisation(curve, params, monkeypatch):
    """Non-regression du cache : une grille uniforme de n pas ne doit
    declencher qu'une seule factorisation."""
    appels = []
    vraie = tfg._robust_cholesky
    monkeypatch.setattr(tfg, "_robust_cholesky",
                        lambda cov: (appels.append(1), vraie(cov))[1])
    tfg.simulate(np.linspace(0.5, 10.0, 20), 10, curve, params, seed=1)
    assert len(appels) == 1


@pytest.mark.parametrize(
    "times", [np.array([]), np.array([2.0, 1.0]), np.array([-1.0, 1.0])]
)
def test_simulate_rejette_grilles_invalides(curve, params, times):
    with pytest.raises(ValueError):
        tfg.simulate(times, 10, curve, params)


# ---------------------------------------------------------------------------
# Options : formules fermees
# ---------------------------------------------------------------------------

T0, TN, STRIKE_ZC, STRIKE_CB = 5.0, 15.0, 0.50, 1.0


def test_volatilite_cbb_degenere_en_volatilite_zcb(curve, params):
    """Sur un flux unitaire unique en Tn, la quadrature de l'eq. 47 doit
    retrouver la forme fermee de l'eq. 40."""
    quadrature = tfg.cbb_option_volatility(
        0.0, T0, np.array([TN]), np.array([1.0]), 0.0, 0.0, curve, params)
    ferme = tfg.zcb_option_volatility(0.0, T0, TN, params)
    assert quadrature == pytest.approx(ferme, rel=1e-10)


def test_volatilite_zcb_nulle_a_maturite_nulle(params):
    assert tfg.zcb_option_volatility(5.0, 5.0, 15.0, params) == pytest.approx(0.0, abs=1e-15)


def test_parite_call_put_zcb(curve, params):
    """Eq. 58 : Put - Call = X Pbar(t,T0) - Pbar(t,Tn)."""
    args = (0.0, T0, TN, STRIKE_ZC, 0.0, 0.0, curve, params)
    call = tfg.zcb_option_price(*args, option_type="call")
    put = tfg.zcb_option_price(*args, option_type="put")
    attendu = STRIKE_ZC * curve.discount(T0) - curve.discount(TN)
    assert put - call == pytest.approx(attendu, abs=1e-14)


def test_parite_call_put_cbb(curve, params, bond):
    """Eq. 59 : Put - Call = X Pbar(t,T0) - somme_{T_i > T0} K_i Pbar(t,T_i)."""
    times, amounts = bond
    args = (0.0, T0, times, amounts, STRIKE_CB, 0.0, 0.0, curve, params)
    call = tfg.cbb_option_price(*args, option_type="call")
    put = tfg.cbb_option_price(*args, option_type="put")
    fut = times > T0
    attendu = STRIKE_CB * curve.discount(T0) - float(
        np.sum(amounts[fut] * curve.discount(times[fut])))
    assert put - call == pytest.approx(attendu, abs=1e-14)


def test_option_zcb_tres_dans_la_monnaie_vaut_le_forward(curve, params):
    """Strike quasi nul : le call vaut la valeur actuelle du sous-jacent."""
    call = tfg.zcb_option_price(0.0, T0, TN, 1e-12, 0.0, 0.0, curve, params)
    assert call == pytest.approx(curve.discount(TN), rel=1e-10)


def test_prix_croissant_avec_la_perte_en_cas_de_defaut(curve, bond):
    """Resultat du papier : L croissant fait monter calls ET puts, la
    volatilite du sous-jacent augmentant a numeraire inchange."""
    times, amounts = bond
    calls, puts = [], []
    for L in (0.2, 0.4, 0.6, 0.8):
        p = tfg.TwoFactorGaussianParams(0.0481, 0.0097, 0.2327, 0.0968, -0.10, L)
        args = (0.0, T0, times, amounts, STRIKE_CB, 0.0, 0.0, curve, p)
        calls.append(tfg.cbb_option_price(*args, option_type="call"))
        puts.append(tfg.cbb_option_price(*args, option_type="put"))
    assert np.all(np.diff(calls) > 0)
    assert np.all(np.diff(puts) > 0)


@pytest.mark.parametrize("fn, extra", [
    (tfg.zcb_option_price, (0.0, T0, TN, STRIKE_ZC, 0.0, 0.0)),
])
def test_option_type_invalide(curve, params, fn, extra):
    with pytest.raises(ValueError):
        fn(*extra, curve, params, option_type="straddle")


# ---------------------------------------------------------------------------
# Options : formules fermees vs Monte-Carlo
# ---------------------------------------------------------------------------

def test_option_zcb_formule_vs_monte_carlo(curve, params):
    ferme = tfg.zcb_option_price(0.0, T0, TN, STRIKE_ZC, 0.0, 0.0, curve, params)
    mc, se = tfg.monte_carlo_option_price(
        T0,
        lambda x, y: np.maximum(
            tfg.zero_coupon_price(T0, TN, x, y, curve, params) - STRIKE_ZC, 0.0),
        400_000, curve, params, seed=42, control_maturity=TN)
    assert abs(mc - ferme) < 4 * se


def test_option_cbb_formule_vs_monte_carlo(curve, params, bond):
    """L'hypothese log-normale sur Bbar est une approximation : on tolere
    l'ecart de modele (< 2% en relatif, comme le papier), pas seulement
    l'erreur statistique."""
    times, amounts = bond
    fut = times > T0
    ferme = tfg.cbb_option_price(0.0, T0, times, amounts, STRIKE_CB, 0.0, 0.0,
                                 curve, params, option_type="call")
    mc, se = tfg.monte_carlo_option_price(
        T0,
        lambda x, y: np.maximum(
            tfg.coupon_bond_price(T0, times[fut], amounts[fut], x, y, curve, params)
            - STRIKE_CB, 0.0),
        400_000, curve, params, seed=42, control_maturity=TN)
    assert abs(mc - ferme) / ferme < 0.02


def test_variable_de_controle_reduit_la_variance(curve, params):
    payoff = lambda x, y: np.maximum(
        tfg.zero_coupon_price(T0, TN, x, y, curve, params) - STRIKE_ZC, 0.0)
    _, se_brut = tfg.monte_carlo_option_price(
        T0, payoff, 100_000, curve, params, seed=5)
    _, se_cv = tfg.monte_carlo_option_price(
        T0, payoff, 100_000, curve, params, seed=5, control_maturity=TN)
    assert se_cv < se_brut / 3
