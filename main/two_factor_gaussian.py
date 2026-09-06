"""
Modele gaussien a deux facteurs pour les taux risques.

Implementation de la partie "diffusion" du papier

    V. Russo, R. Giacometti, F. J. Fabozzi,
    "Closed-Form Solution for Defaultable Bond Options under a Two-Factor
     Gaussian Model for Risky Rates Modeling" (draft),
    cf. doc/13. Russo et al._DefaultableBondOptions_DRAFT.pdf

Les numeros d'equations cites dans les docstrings renvoient a ce draft.

Dynamique (eq. 11-14)
---------------------
    rbar(t) = alphabar(t) + x(t) + L * y(t)
    dx(t)   = -a_x x(t) dt + sigma_x dW_x(t),   x(0) = 0
    dy(t)   = -a_y y(t) dt + sigma_y dW_y(t),   y(0) = 0
    dW_x dW_y = rho dt

L est la perte en cas de defaut (L = 1 - RR), supposee constante, et
alphabar(t) est la fonction deterministe qui recale exactement la courbe
des taux risques observee (eq. 15).

Remarque utile pour l'implementation : ce modele est exactement un G2++
dont la volatilite du second facteur est eta = L * sigma_y. Toutes les
formules fermees classiques du G2++ (variance de l'integrale du taux
court, prix ZC) s'appliquent donc directement, ce qui sert ici de
controle croise des formules du papier (eq. 16-24).

Ce module ne contient QUE le modele de diffusion et le pricing des
sous-jacents. Les formules d'options (eq. 40-52) viendront dans un second
temps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.stats import norm

__all__ = [
    "TwoFactorGaussianParams",
    "Curve",
    "h_factor",
    "g_x",
    "g_y",
    "c_xy",
    "p_xy",
    "variance_integrated_rate",
    "alpha_bar",
    "integral_alpha_bar",
    "short_rate",
    "zero_coupon_price",
    "coupon_bond_cashflows",
    "coupon_bond_price",
    "duration_zcb",
    "duration_cbb",
    "forward_duration_zcb",
    "forward_duration_cbb",
    "step_covariance",
    "SimulationResult",
    "simulate",
    "zcb_option_volatility",
    "cbb_option_volatility",
    "zcb_option_price",
    "cbb_option_price",
    "monte_carlo_option_price",
]

_TINY = 1e-12


# ---------------------------------------------------------------------------
# Parametres du modele
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TwoFactorGaussianParams:
    """Parametres du modele gaussien a deux facteurs.

    Parameters
    ----------
    a_x, sigma_x : vitesse de retour a la moyenne et volatilite du facteur
        sans risque x(t).
    a_y, sigma_y : idem pour le facteur de credit y(t) (l'intensite).
    rho : correlation instantanee entre dW_x et dW_y, dans [-1, 1].
    L : perte en cas de defaut, L = 1 - RR, dans [0, 1].

    La volatilite effective du second facteur dans la dynamique de rbar
    est ``eta = L * sigma_y`` (cf. eq. 13).
    """

    a_x: float
    sigma_x: float
    a_y: float
    sigma_y: float
    rho: float
    L: float

    def __post_init__(self) -> None:
        if self.a_x <= 0 or self.a_y <= 0:
            raise ValueError("a_x et a_y doivent etre strictement positifs.")
        if self.sigma_x < 0 or self.sigma_y < 0:
            raise ValueError("sigma_x et sigma_y doivent etre positifs.")
        if not -1.0 <= self.rho <= 1.0:
            raise ValueError("rho doit appartenir a [-1, 1].")
        if not 0.0 <= self.L <= 1.0:
            raise ValueError("L doit appartenir a [0, 1].")

    @property
    def eta(self) -> float:
        """Volatilite effective du second facteur : eta = L * sigma_y."""
        return self.L * self.sigma_y

    @property
    def recovery_rate(self) -> float:
        """Taux de recouvrement RR = 1 - L."""
        return 1.0 - self.L


# ---------------------------------------------------------------------------
# Courbe de taux (risquee ou sans risque)
# ---------------------------------------------------------------------------


@dataclass
class Curve:
    """Courbe zero-coupon en composition continue.

    Sert a la fois pour la courbe sans risque et pour la courbe risquee
    d'un emetteur : c'est elle qui fournit Pbar_M(0, T) et le taux
    forward instantane fbar_M(0, t) de l'eq. 15.

    Parameters
    ----------
    tenors : maturites en annees, strictement croissantes et > 0.
    zero_rates : taux zero-coupon continus associes.
    interpolation : "cubic" (spline C2 sur les taux, forwards continus)
        ou "linear" (interpolation lineaire sur les taux).

    Extrapolation
    -------------
    Hors de la plage des piliers, la courbe est prolongee de facon a garder
    le forward instantane f(t) = R(t) + t R'(t) CONTINU, et a repricer
    exactement les piliers.

    - Au-dela de t_max : forward plat, f(t) = f(t_max). D'ou
          R(t) = [R(t_max) t_max + f(t_max) (t - t_max)] / t.

    - En deca de t_min : forward AFFINE, pas plat. Un forward constant y
      est impossible sans casser quelque chose : l'integrale du forward sur
      [0, t_min] vaut R(t_min) t_min, impose par le marche, donc un forward
      constant vaudrait necessairement R(t_min) et sauterait a f(t_min).
      On prend donc la seule affine qui reprice et raccorde :
          f(t) = f_0 + (f(t_min) - f_0) t / t_min,  f_0 = 2 R(t_min) - f(t_min),
          R(t) = f_0 + (f(t_min) - f_0) t / (2 t_min).

    Consequence : f est continu sur ]0, +inf[, et alpha_bar (eq. 15) l'est
    aussi. Les facteurs d'actualisation sont inchanges sur [t_min, t_max].
    """

    tenors: np.ndarray
    zero_rates: np.ndarray
    interpolation: Literal["cubic", "linear"] = "cubic"

    def __post_init__(self) -> None:
        self.tenors = np.asarray(self.tenors, dtype=float)
        self.zero_rates = np.asarray(self.zero_rates, dtype=float)
        if self.tenors.ndim != 1 or self.tenors.shape != self.zero_rates.shape:
            raise ValueError("tenors et zero_rates doivent etre 1D de meme taille.")
        if np.any(np.diff(self.tenors) <= 0):
            raise ValueError("tenors doit etre strictement croissant.")
        if self.tenors[0] <= 0:
            raise ValueError("tenors doit etre strictement positif.")
        if self.interpolation == "cubic":
            if self.tenors.size < 4:
                raise ValueError("l'interpolation cubique demande >= 4 piliers.")
            self._spline = CubicSpline(self.tenors, self.zero_rates, extrapolate=False)
        elif self.interpolation == "linear":
            if self.tenors.size < 2:
                raise ValueError("l'interpolation lineaire demande >= 2 piliers.")
            self._slopes = np.diff(self.zero_rates) / np.diff(self.tenors)
        else:
            raise ValueError("interpolation doit valoir 'cubic' ou 'linear'.")

        # Raccords d'extrapolation. Calcules via _interp_core uniquement :
        # passer par zero_rate / instantaneous_forward creerait une recursion,
        # ces methodes dependant justement des quantites calculees ici.
        self._tmin = float(self.tenors[0])
        self._tmax = float(self.tenors[-1])
        r_min, d_min = self._interp_core(np.array(self._tmin))
        r_max, d_max = self._interp_core(np.array(self._tmax))
        self._z_min, self._z_max = float(r_min), float(r_max)
        self._f_min = self._z_min + self._tmin * float(d_min)   # f(t_min+)
        self._f_max = self._z_max + self._tmax * float(d_max)   # f(t_max-)
        self._f_0 = 2.0 * self._z_min - self._f_min             # f(0+), cf. docstring

    @classmethod
    def from_discount_factors(
        cls,
        tenors: Sequence[float],
        discount_factors: Sequence[float],
        interpolation: Literal["cubic", "linear"] = "cubic",
    ) -> "Curve":
        """Construit la courbe a partir de facteurs d'actualisation."""
        t = np.asarray(tenors, dtype=float)
        df = np.asarray(discount_factors, dtype=float)
        if np.any(df <= 0):
            raise ValueError("les facteurs d'actualisation doivent etre > 0.")
        return cls(t, -np.log(df) / t, interpolation)

    @classmethod
    def flat(
        cls, rate: float, max_tenor: float = 50.0, n_points: int = 51
    ) -> "Curve":
        """Courbe plate, utile pour les tests et les cas ecole."""
        t = np.linspace(max_tenor / n_points, max_tenor, n_points)
        return cls(t, np.full_like(t, float(rate)), "linear")

    # -- interpolation interne --------------------------------------------

    def _interp_core(self, t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """(R, dR/dt) par interpolation pure. ``t`` doit etre dans
        [t_min, t_max] ; aucune extrapolation ici."""
        if self.interpolation == "cubic":
            return self._spline(t), self._spline(t, 1)
        r = np.interp(t, self.tenors, self.zero_rates)
        idx = np.clip(
            np.searchsorted(self.tenors, t, side="right") - 1, 0, self._slopes.size - 1
        )
        return r, self._slopes[idx]

    def _r_and_dr(self, t):
        """(R(0, t), dR/dt) avec extrapolation a forward continu.

        Point d'entree unique de zero_rate / zero_rate_derivative /
        instantaneous_forward : les trois regimes (court, interpole, long)
        y sont traites une seule fois, ce qui garantit que la derivee
        renvoyee est bien celle du taux renvoye.
        """
        t = np.asarray(t, dtype=float)
        tmin, tmax = self._tmin, self._tmax
        r_in, d_in = self._interp_core(np.clip(t, tmin, tmax))

        # Court terme : forward affine (cf. docstring de la classe).
        slope_lo = (self._f_min - self._f_0) / (2.0 * tmin)
        r_lo = self._f_0 + slope_lo * t
        d_lo = np.full_like(t, slope_lo)

        # Long terme : forward plat.
        t_safe = np.where(t > 0.0, t, 1.0)
        r_hi = (self._z_max * tmax + self._f_max * (t - tmax)) / t_safe
        d_hi = (self._f_max - r_hi) / t_safe

        r = np.where(t < tmin, r_lo, np.where(t > tmax, r_hi, r_in))
        d = np.where(t < tmin, d_lo, np.where(t > tmax, d_hi, d_in))
        return r, d

    # -- accesseurs -------------------------------------------------------

    def zero_rate(self, t):
        """Taux zero-coupon continu R(0, t)."""
        t = np.asarray(t, dtype=float)
        r, _ = self._r_and_dr(t)
        return r if t.ndim else float(r)

    def zero_rate_derivative(self, t):
        """Derivee dR(0, t)/dt."""
        t = np.asarray(t, dtype=float)
        _, d = self._r_and_dr(t)
        return d if t.ndim else float(d)

    def discount(self, t):
        """Facteur d'actualisation P_M(0, t) (= Pbar_M pour une courbe risquee)."""
        t = np.asarray(t, dtype=float)
        df = np.exp(-self.zero_rate(t) * t)
        df = np.where(t <= 0.0, 1.0, df)
        return df if t.ndim else float(df)

    def instantaneous_forward(self, t):
        """Taux forward instantane f_M(0, t) = R(0, t) + t R'(0, t).

        Continu partout, y compris aux deux piliers extremes.
        """
        t = np.asarray(t, dtype=float)
        r, d = self._r_and_dr(t)
        f = r + t * d
        return f if t.ndim else float(f)


# ---------------------------------------------------------------------------
# Briques deterministes du modele (eq. 20-24)
# ---------------------------------------------------------------------------


def h_factor(a: float, t, T):
    """H_i(t, T) = (1 - exp(-a (T - t))) / a  (eq. 23-24).

    C'est aussi la duration stochastique du ZC par rapport au facteur i.
    """
    tau = np.asarray(T, dtype=float) - np.asarray(t, dtype=float)
    if abs(a) < _TINY:
        return tau
    return -np.expm1(-a * tau) / a


def g_x(t, T, p: TwoFactorGaussianParams):
    """G_x(t, T), composante convexite du facteur sans risque (eq. 21)."""
    tau = np.asarray(T, dtype=float) - np.asarray(t, dtype=float)
    h = h_factor(p.a_x, t, T)
    return np.exp(
        -(p.sigma_x**2) / (2.0 * p.a_x**2) * (h - tau)
        - (p.sigma_x**2) / (4.0 * p.a_x) * h**2
    )


def g_y(t, T, p: TwoFactorGaussianParams):
    """G_y(t, T), composante convexite du facteur de credit (eq. 22).

    La volatilite utilisee est eta = L * sigma_y.
    """
    tau = np.asarray(T, dtype=float) - np.asarray(t, dtype=float)
    h = h_factor(p.a_y, t, T)
    return np.exp(
        -(p.eta**2) / (2.0 * p.a_y**2) * (h - tau)
        - (p.eta**2) / (4.0 * p.a_y) * h**2
    )


def c_xy(t, T, p: TwoFactorGaussianParams):
    """C_{x,y}(t, T), composante de correlation du prix ZC (eq. 20)."""
    tau = np.asarray(T, dtype=float) - np.asarray(t, dtype=float)
    hx = h_factor(p.a_x, t, T)
    hy = h_factor(p.a_y, t, T)
    ab = p.a_x + p.a_y
    return np.exp(
        p.L * p.rho * p.sigma_x * p.sigma_y / (p.a_x * p.a_y)
        * (tau - hx - hy - np.expm1(-ab * tau) / ab)
    )


def p_xy(t, T, x, y, p: TwoFactorGaussianParams):
    """P_xy(t, T) = P_x P_y C_xy  (eq. 17-19).

    x et y sont les valeurs des facteurs en t ; ils peuvent etre des
    scalaires ou des tableaux (broadcasting numpy).
    """
    hx = h_factor(p.a_x, t, T)
    hy = h_factor(p.a_y, t, T)
    px = g_x(t, T, p) * np.exp(-hx * np.asarray(x, dtype=float))
    py = g_y(t, T, p) * np.exp(-hy * p.L * np.asarray(y, dtype=float))
    return px * py * c_xy(t, T, p)


def variance_integrated_rate(t, T, p: TwoFactorGaussianParams):
    """Variance de l'integrale du taux court risque.

    V(t, T) = Var[ int_t^T (x(u) + L y(u)) du | F_t ], forme fermee G2++
    avec eta = L sigma_y. Utilisee pour alphabar et comme controle des
    eq. 20-24.
    """
    tau = np.asarray(T, dtype=float) - np.asarray(t, dtype=float)
    a, b = p.a_x, p.a_y
    s, e = p.sigma_x, p.eta
    term_x = (s**2 / a**2) * (
        tau + 2.0 / a * np.exp(-a * tau) - 1.0 / (2.0 * a) * np.exp(-2.0 * a * tau) - 1.5 / a
    )
    term_y = (e**2 / b**2) * (
        tau + 2.0 / b * np.exp(-b * tau) - 1.0 / (2.0 * b) * np.exp(-2.0 * b * tau) - 1.5 / b
    )
    term_xy = (2.0 * p.rho * s * e / (a * b)) * (
        tau + np.expm1(-a * tau) / a + np.expm1(-b * tau) / b - np.expm1(-(a + b) * tau) / (a + b)
    )
    return term_x + term_y + term_xy


def alpha_bar(t, curve: Curve, p: TwoFactorGaussianParams):
    """alphabar(t), fonction de recalage sur la courbe risquee (eq. 15)."""
    t = np.asarray(t, dtype=float)
    ex = -np.expm1(-p.a_x * t)
    ey = -np.expm1(-p.a_y * t)
    return (
        curve.instantaneous_forward(t)
        + p.sigma_x**2 / (2.0 * p.a_x**2) * ex**2
        + p.eta**2 / (2.0 * p.a_y**2) * ey**2
        + p.L * p.rho * p.sigma_x * p.sigma_y / (p.a_x * p.a_y) * ex * ey
    )


def integral_alpha_bar(T, curve: Curve, p: TwoFactorGaussianParams):
    """int_0^T alphabar(u) du, en forme fermee.

    Obtenue en imposant Pbar(0, T) = Pbar_M(0, T) :
        int_0^T alphabar = -log Pbar_M(0, T) + 0.5 V(0, T).
    Evite toute quadrature dans la simulation Monte Carlo.
    """
    T = np.asarray(T, dtype=float)
    return -np.log(curve.discount(T)) + 0.5 * variance_integrated_rate(0.0, T, p)


def short_rate(t, x, y, curve: Curve, p: TwoFactorGaussianParams):
    """Taux court risque rbar(t) = alphabar(t) + x(t) + L y(t) (eq. 11)."""
    return alpha_bar(t, curve, p) + np.asarray(x, dtype=float) + p.L * np.asarray(y, dtype=float)


# ---------------------------------------------------------------------------
# Prix des sous-jacents
# ---------------------------------------------------------------------------


def zero_coupon_price(t, T, x, y, curve: Curve, p: TwoFactorGaussianParams):
    """Prix Pbar(t, T) d'un ZC defaultable (eq. 16).

        Pbar(t, T) = [Pbar_M(0,T) / Pbar_M(0,t)]
                     * [P_xy(0,t) / P_xy(0,T)] * P_xy(t,T)

    Par construction Pbar(0, T) = Pbar_M(0, T) : la courbe risquee est
    repliquee exactement.
    """
    t_arr = np.asarray(t, dtype=float)
    T_arr = np.asarray(T, dtype=float)
    market = curve.discount(T_arr) / curve.discount(t_arr)
    # x(0) = y(0) = 0 : P_xy(0, .) se reduit a G_x G_y C_xy.
    ratio0 = p_xy(0.0, t_arr, 0.0, 0.0, p) / p_xy(0.0, T_arr, 0.0, 0.0, p)
    return market * ratio0 * p_xy(t_arr, T_arr, x, y, p)


def coupon_bond_cashflows(
    coupon_rate: float,
    payment_times: Sequence[float],
    notional: float = 1.0,
    accrual_start: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Echeancier d'une obligation a coupons (cf. definition avant eq. 28).

        K_i = K * tau(T_{i-1}, T_i)          pour i = 1 .. n-1
        K_n = K * tau(T_{n-1}, T_n) + 1      pour i = n

    Les fractions d'annee tau sont deduites des ecarts entre dates de
    paiement ; ``accrual_start`` (defaut : 0) fixe le debut de la premiere
    periode.

    Returns
    -------
    (times, amounts) : dates de paiement et montants K_i, en unites de
    ``notional``.
    """
    times = np.asarray(payment_times, dtype=float)
    if times.ndim != 1 or times.size == 0:
        raise ValueError("payment_times doit etre une sequence 1D non vide.")
    if np.any(np.diff(times) <= 0):
        raise ValueError("payment_times doit etre strictement croissant.")
    start = 0.0 if accrual_start is None else float(accrual_start)
    if times[0] <= start:
        raise ValueError("la premiere date de paiement doit suivre accrual_start.")
    accruals = np.diff(np.concatenate(([start], times)))
    amounts = coupon_rate * accruals
    amounts[-1] += 1.0
    return times, notional * amounts


def coupon_bond_price(
    t, payment_times, amounts, x, y, curve: Curve, p: TwoFactorGaussianParams
):
    """Prix Bbar(t, T_n) = somme_i K_i Pbar(t, T_i) d'une obligation
    a coupons defaultable (eq. 28).

    Seuls les flux strictement posterieurs a t sont pris en compte.
    ``x`` et ``y`` peuvent etre des tableaux : le prix est alors calcule
    pour chaque etat des facteurs.
    """
    t = float(t)
    times = np.asarray(payment_times, dtype=float)
    amounts = np.asarray(amounts, dtype=float)
    mask = times > t
    if not np.any(mask):
        raise ValueError("aucun flux posterieur a t.")
    times, amounts = times[mask], amounts[mask]
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    # Axe -1 reserve aux flux, les axes de gauche aux etats des facteurs.
    dfs = zero_coupon_price(t, times, x[..., None], y[..., None], curve, p)
    return np.sum(amounts * dfs, axis=-1)


# ---------------------------------------------------------------------------
# Durations stochastiques (eq. 26-27, 30-31 et durations forward)
# ---------------------------------------------------------------------------


def duration_zcb(t, T, p: TwoFactorGaussianParams) -> tuple:
    """Durations stochastiques (DP_x, DP_y) du ZC defaultable (eq. 26-27).

    Renvoie H_x(t, T) et H_y(t, T), au sens de la diffusion de l'eq. 25 :

        dPbar / Pbar = rbar dt - sigma_x DP_x dW_x - L sigma_y DP_y dW_y

    Attention a la convention : le facteur L est explicite dans l'eq. 25,
    donc DP_y = H_y et non L H_y. La sensibilite brute est, elle,
    -(1/Pbar) dPbar/dy = L H_y (le draft ecrit l'eq. 27 sans ce L).
    """
    return h_factor(p.a_x, t, T), h_factor(p.a_y, t, T)


def duration_cbb(
    t, payment_times, amounts, x, y, curve: Curve, p: TwoFactorGaussianParams
) -> tuple:
    """Durations stochastiques (DB_x, DB_y) de l'obligation a coupons (eq. 30-31).

    Moyennes des H_x(t, T_i) / H_y(t, T_i) ponderees par les flux
    actualises K_i Pbar(t, T_i). Meme convention que :func:`duration_zcb` :
    le facteur L reste explicite dans la diffusion (eq. 29), DB_y est donc
    la moyenne ponderee des H_y et non des L H_y.

    Note : le draft ecrit un C_i au denominateur des eq. 30-31 ; il s'agit
    d'une coquille, le denominateur est bien somme_i K_i Pbar(t, T_i),
    c'est-a-dire Bbar(t, T_n).
    """
    t = float(t)
    times = np.asarray(payment_times, dtype=float)
    amounts = np.asarray(amounts, dtype=float)
    mask = times > t
    if not np.any(mask):
        raise ValueError("aucun flux posterieur a t.")
    times, amounts = times[mask], amounts[mask]
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    weights = amounts * zero_coupon_price(t, times, x[..., None], y[..., None], curve, p)
    total = np.sum(weights, axis=-1)
    d_x = np.sum(weights * h_factor(p.a_x, t, times), axis=-1) / total
    d_y = np.sum(weights * h_factor(p.a_y, t, times), axis=-1) / total
    return d_x, d_y


def forward_duration_zcb(t, T0, Tn, p: TwoFactorGaussianParams) -> tuple:
    """Durations forward du ZC (section "Options on defaultable zero-coupon bonds").

        DP_i(t, T0, Tn) = H_i(t, Tn) - H_i(t, T0)
    """
    return (
        h_factor(p.a_x, t, Tn) - h_factor(p.a_x, t, T0),
        h_factor(p.a_y, t, Tn) - h_factor(p.a_y, t, T0),
    )


def forward_duration_cbb(
    t, T0, payment_times, amounts, x, y, curve: Curve, p: TwoFactorGaussianParams
) -> tuple:
    """Durations forward de l'obligation a coupons (eq. avant 47).

        DB_i(t, T0, Tn) = sum_i K_i Pbar(t, T_i) [H_i(t, T_i) - H_i(t, T0)]
                          / sum_i K_i Pbar(t, T_i)

    Seuls les flux posterieurs a T0 (date d'exercice) sont retenus : ce
    sont ceux que porte le sous-jacent forward.
    """
    times = np.asarray(payment_times, dtype=float)
    amounts = np.asarray(amounts, dtype=float)
    mask = times > float(T0)
    if not np.any(mask):
        raise ValueError("aucun flux posterieur a T0.")
    d_x, d_y = duration_cbb(t, times[mask], amounts[mask], x, y, curve, p)
    return d_x - h_factor(p.a_x, t, T0), d_y - h_factor(p.a_y, t, T0)


# ---------------------------------------------------------------------------
# Simulation exacte de la diffusion
# ---------------------------------------------------------------------------


def step_covariance(dt: float, p: TwoFactorGaussianParams) -> np.ndarray:
    """Matrice de covariance conditionnelle du vecteur (x, y, I_x, I_y).

    Sur un pas de longueur ``dt``, avec
        I_x = int_t^{t+dt} x(u) du,   I_y = int_t^{t+dt} y(u) du,
    les parties stochastiques de (x, y, I_x, I_y) sont gaussiennes
    centrees, de covariance donnee ici en forme fermee. Cela permet une
    simulation exacte (sans biais de discretisation) du couple
    facteurs / actualisation, quel que soit le pas.
    """
    if dt < 0:
        raise ValueError("dt doit etre positif.")
    a, b = p.a_x, p.a_y
    sx, sy, rho = p.sigma_x, p.sigma_y, p.rho
    ab = a + b
    ea, eb = -np.expm1(-a * dt), -np.expm1(-b * dt)      # 1 - exp(-a dt)
    e2a, e2b = -np.expm1(-2 * a * dt), -np.expm1(-2 * b * dt)
    eab = -np.expm1(-ab * dt)

    v_x = sx**2 * e2a / (2 * a)
    v_y = sy**2 * e2b / (2 * b)
    c_x_y = rho * sx * sy * eab / ab

    c_x_ix = sx**2 / a * (ea / a - e2a / (2 * a))
    c_y_iy = sy**2 / b * (eb / b - e2b / (2 * b))
    c_x_iy = rho * sx * sy / b * (ea / a - eab / ab)
    c_y_ix = rho * sx * sy / a * (eb / b - eab / ab)

    v_ix = sx**2 / a**2 * (dt - 2 * ea / a + e2a / (2 * a))
    v_iy = sy**2 / b**2 * (dt - 2 * eb / b + e2b / (2 * b))
    c_ix_iy = rho * sx * sy / (a * b) * (dt - ea / a - eb / b + eab / ab)

    return np.array(
        [
            [v_x, c_x_y, c_x_ix, c_x_iy],
            [c_x_y, v_y, c_y_ix, c_y_iy],
            [c_x_ix, c_y_ix, v_ix, c_ix_iy],
            [c_x_iy, c_y_iy, c_ix_iy, v_iy],
        ]
    )


def _robust_cholesky(cov: np.ndarray) -> np.ndarray:
    """Facteur de Cholesky, avec repli spectral si la matrice est
    numeriquement semi-definie (pas tres court, |rho| = 1)."""
    try:
        return np.linalg.cholesky(cov)
    except np.linalg.LinAlgError:
        w, v = np.linalg.eigh(cov)
        return v @ np.diag(np.sqrt(np.clip(w, 0.0, None)))


@dataclass
class SimulationResult:
    """Trajectoires simulees du modele.

    Attributes
    ----------
    times : (n_steps + 1,) grille temporelle, times[0] = 0.
    x, y : (n_paths, n_steps + 1) facteurs.
    int_x, int_y : (n_paths, n_steps + 1) integrales cumulees
        int_0^t x(u) du et int_0^t y(u) du.
    """

    times: np.ndarray
    x: np.ndarray
    y: np.ndarray
    int_x: np.ndarray
    int_y: np.ndarray
    curve: Curve
    params: TwoFactorGaussianParams

    def integrated_short_rate(self) -> np.ndarray:
        """int_0^t rbar(u) du pour chaque trajectoire et chaque date."""
        p = self.params
        return integral_alpha_bar(self.times, self.curve, p) + self.int_x + p.L * self.int_y

    def discount_factors(self) -> np.ndarray:
        """Facteur d'actualisation stochastique exp(-int_0^t rbar(u) du).

        Sous l'hypothese de recovery of market value, c'est aussi le
        deflateur risque : il porte a la fois l'actualisation sans risque
        et la survie.
        """
        return np.exp(-self.integrated_short_rate())

    def short_rates(self) -> np.ndarray:
        """Taux court risque rbar(t) le long des trajectoires."""
        return short_rate(self.times, self.x, self.y, self.curve, self.params)


def simulate(
    times: Sequence[float],
    n_paths: int,
    curve: Curve,
    p: TwoFactorGaussianParams,
    seed: int | None = None,
    antithetic: bool = False,
) -> SimulationResult:
    """Simule exactement le modele sur la grille ``times``.

    Le schema est exact : sur chaque pas, (x, y, I_x, I_y) est tire dans sa
    loi gaussienne conditionnelle exacte (cf. :func:`step_covariance`), il
    n'y a donc aucun biais de discretisation, y compris sur le terme
    d'actualisation. La grille peut etre grossiere si seules les dates
    d'exercice et de paiement importent.

    Parameters
    ----------
    times : dates de la grille, croissantes ; 0 est ajoute en tete s'il
        manque.
    n_paths : nombre de trajectoires (arrondi au pair superieur si
        ``antithetic``).
    antithetic : active les variables antithetiques (reduction de variance).

    Returns
    -------
    SimulationResult
    """
    times = np.asarray(times, dtype=float)
    if times.ndim != 1 or times.size == 0:
        raise ValueError("times doit etre une sequence 1D non vide.")
    if np.any(np.diff(times) <= 0):
        raise ValueError("times doit etre strictement croissant.")
    if times[0] < 0:
        raise ValueError("times doit etre positif.")
    if times[0] > 0:
        times = np.concatenate(([0.0], times))
    if n_paths <= 0:
        raise ValueError("n_paths doit etre strictement positif.")

    n_steps = times.size - 1
    if antithetic:
        n_paths += n_paths % 2
        n_base = n_paths // 2

    rng = np.random.default_rng(seed)
    x = np.zeros((n_paths, n_steps + 1))
    y = np.zeros((n_paths, n_steps + 1))
    int_x = np.zeros((n_paths, n_steps + 1))
    int_y = np.zeros((n_paths, n_steps + 1))

    # Sur une grille uniforme la covariance conditionnelle ne depend que du
    # pas : on ne factorise qu'une fois par valeur distincte de dt.
    chol_cache: dict[float, np.ndarray] = {}

    for k in range(n_steps):
        dt = times[k + 1] - times[k]
        key = round(float(dt), 12)
        chol = chol_cache.get(key)
        if chol is None:
            chol = _robust_cholesky(step_covariance(dt, p))
            chol_cache[key] = chol
        if antithetic:
            z = rng.standard_normal((n_base, 4))
            z = np.concatenate([z, -z], axis=0)
        else:
            z = rng.standard_normal((n_paths, 4))
        shocks = z @ chol.T

        hx = h_factor(p.a_x, 0.0, dt)  # (1 - exp(-a_x dt)) / a_x
        hy = h_factor(p.a_y, 0.0, dt)
        decay_x, decay_y = np.exp(-p.a_x * dt), np.exp(-p.a_y * dt)

        x_prev, y_prev = x[:, k], y[:, k]
        x[:, k + 1] = x_prev * decay_x + shocks[:, 0]
        y[:, k + 1] = y_prev * decay_y + shocks[:, 1]
        int_x[:, k + 1] = int_x[:, k] + x_prev * hx + shocks[:, 2]
        int_y[:, k + 1] = int_y[:, k] + y_prev * hy + shocks[:, 3]

    return SimulationResult(times, x, y, int_x, int_y, curve, p)


# ---------------------------------------------------------------------------
# Volatilites integrees et prix d'options (eq. 38-52)
# ---------------------------------------------------------------------------


def zcb_option_volatility(t, T0, Tn, p: TwoFactorGaussianParams):
    """Volatilite integree Sigmabar_P(t, T0, Tn) du ZC defaultable (eq. 40).

    Racine de l'integrale, sur [t, T0], de la variance instantanee du prix
    forward Pbar(u, T0, Tn). L'integrale est ici en forme fermee.
    """
    ax, ay, sx, sy, L, rho = p.a_x, p.a_y, p.sigma_x, p.sigma_y, p.L, p.rho
    u = np.asarray(Tn, dtype=float) - np.asarray(T0, dtype=float)
    v = np.asarray(T0, dtype=float) - np.asarray(t, dtype=float)
    ex, ey = -np.expm1(-ax * u), -np.expm1(-ay * u)
    var = (
        sx**2 / (2.0 * ax**3) * ex**2 * -np.expm1(-2.0 * ax * v)
        + L**2 * sy**2 / (2.0 * ay**3) * ey**2 * -np.expm1(-2.0 * ay * v)
        + 2.0 * L * rho * sx * sy / (ax * ay * (ax + ay))
        * ex * ey * -np.expm1(-(ax + ay) * v)
    )
    return np.sqrt(np.maximum(var, 0.0))


def cbb_option_volatility(
    t, T0, payment_times, amounts, x, y, curve: Curve,
    p: TwoFactorGaussianParams, n_nodes: int = 64,
):
    """Volatilite integree Sigmabar_B(t, T0, Tn) de l'obligation a coupons
    (eq. 47-48).

    Contrairement au cas ZC, l'integrale n'a pas de primitive elementaire :
    elle est evaluee par quadrature de Gauss-Legendre a ``n_nodes`` noeuds
    sur [t, T0], comme l'indique le papier.

    Les poids des flux sont geles a leur valeur en t (approximation
    standard de "freezing") : seules les durations forward H_i(u, .)
    dependent de la variable d'integration u. Seuls les flux posterieurs
    a T0 interviennent, ce sont ceux que porte le forward.

    ``x`` et ``y`` peuvent etre des tableaux : la quadrature est alors
    vectorisee sur les etats des facteurs.
    """
    t, T0 = float(t), float(T0)
    if T0 <= t:
        raise ValueError("T0 doit etre strictement superieur a t.")
    times = np.asarray(payment_times, dtype=float)
    amounts = np.asarray(amounts, dtype=float)
    mask = times > T0
    if not np.any(mask):
        raise ValueError("aucun flux posterieur a T0.")
    times, amounts = times[mask], amounts[mask]

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    w = amounts * zero_coupon_price(t, times, x[..., None], y[..., None], curve, p)
    w = w / np.sum(w, axis=-1, keepdims=True)              # poids gelés en t

    nodes, weights = np.polynomial.legendre.leggauss(n_nodes)
    half = 0.5 * (T0 - t)
    u = (half * nodes + 0.5 * (T0 + t))[:, None]           # (n_nodes, 1)

    # H_i(u, T_j) - H_i(u, T0), de forme (n_nodes, n_flux)
    dx = h_factor(p.a_x, u, times[None, :]) - h_factor(p.a_x, u, T0)
    dy = h_factor(p.a_y, u, times[None, :]) - h_factor(p.a_y, u, T0)

    db_x = np.tensordot(w, dx, axes=([-1], [1]))           # (..., n_nodes)
    db_y = np.tensordot(w, dy, axes=([-1], [1]))

    sigma2 = (
        p.sigma_x**2 * db_x**2
        + p.eta**2 * db_y**2
        + 2.0 * p.rho * p.sigma_x * p.eta * db_x * db_y
    )
    var = half * np.sum(weights * sigma2, axis=-1)
    return np.sqrt(np.maximum(var, 0.0))


def _black_call(forward_value, strike_value, vol):
    """Call de Black en variables non actualisees.

    ``forward_value`` = valeur en t des flux du sous-jacent posterieurs a
    T0 ; ``strike_value`` = X * Pbar(t, T0). Renvoie F Phi(d1) - K Phi(d2).
    """
    F = np.asarray(forward_value, dtype=float)
    K = np.asarray(strike_value, dtype=float)
    vol = np.asarray(vol, dtype=float)
    safe = np.maximum(vol, _TINY)
    d1 = (np.log(F / K) + 0.5 * safe**2) / safe
    price = F * norm.cdf(d1) - K * norm.cdf(d1 - safe)
    return np.where(vol > _TINY, price, np.maximum(F - K, 0.0))


def zcb_option_price(
    t, T0, Tn, strike, x, y, curve: Curve, p: TwoFactorGaussianParams,
    option_type: str = "call",
):
    """Prix d'une option europeenne knock-out sur ZC defaultable (eq. 42).

        Call = Pbar(t, Tn) Phi(d1) - X Pbar(t, T0) Phi(d2)

    Le put s'obtient par la parite call-put defaultable (eq. 58) :
        Put = Call + X Pbar(t, T0) - Pbar(t, Tn).

    L'option est supposee sans valeur en cas de defaut : la composante de
    protection contre le defaut n'est pas evaluee ici (cf. papier).
    """
    if option_type not in ("call", "put"):
        raise ValueError("option_type doit valoir 'call' ou 'put'.")
    p_tn = zero_coupon_price(t, Tn, x, y, curve, p)
    p_t0 = zero_coupon_price(t, T0, x, y, curve, p)
    vol = zcb_option_volatility(t, T0, Tn, p)
    call = _black_call(p_tn, strike * p_t0, vol)
    return call if option_type == "call" else call + strike * p_t0 - p_tn


def cbb_option_price(
    t, T0, payment_times, amounts, strike, x, y, curve: Curve,
    p: TwoFactorGaussianParams, option_type: str = "call", n_nodes: int = 64,
):
    """Prix d'une option europeenne knock-out sur obligation a coupons
    defaultable (eq. 50).

        Call = Bbar(t, Tn) Phi(d1) - X Pbar(t, T0) Phi(d2)

    ou Bbar(t, Tn) designe la valeur en t des seuls flux posterieurs a T0
    (c'est ce que porte le contrat forward). Le put suit la parite eq. 59,
    ecrite ici sous sa forme reduite equivalente :

        Put = Call + X Pbar(t, T0) - somme_{T_i > T0} K_i Pbar(t, T_i).

    L'eq. 59 du papier exprime le meme resultat via une obligation
    auxiliaire de maturite T0 : Bbar(t,T0) - Pbar(t,T0) vaut exactement la
    somme des flux anterieurs a T0, que l'on retranche donc de Bbar(t,Tn).
    """
    if option_type not in ("call", "put"):
        raise ValueError("option_type doit valoir 'call' ou 'put'.")
    times = np.asarray(payment_times, dtype=float)
    amounts = np.asarray(amounts, dtype=float)
    mask = times > float(T0)
    if not np.any(mask):
        raise ValueError("aucun flux posterieur a T0.")
    b_fwd = coupon_bond_price(t, times[mask], amounts[mask], x, y, curve, p)
    p_t0 = zero_coupon_price(t, T0, x, y, curve, p)
    vol = cbb_option_volatility(t, T0, times, amounts, x, y, curve, p, n_nodes)
    call = _black_call(b_fwd, strike * p_t0, vol)
    return call if option_type == "call" else call + strike * p_t0 - b_fwd


def monte_carlo_option_price(
    T0, payoff, n_paths: int, curve: Curve, p: TwoFactorGaussianParams,
    seed: int | None = None, antithetic: bool = True,
    control_maturity: float | None = None,
):
    """Prix Monte-Carlo d'un payoff europeen en T0 (eq. 32-35).

    Sous l'hypothese de recovery of market value, le deflateur
    exp(-int_0^T0 rbar) porte deja la survie : le knock-out au defaut est
    automatique, il n'y a aucun temps de defaut a simuler.

    Le schema de :func:`simulate` etant exact, UN SEUL pas jusqu'a T0
    suffit pour un payoff europeen.

    Parameters
    ----------
    payoff : callable (x, y) -> payoff en T0, evalue sur les facteurs.
    control_maturity : si fourni (typiquement Tn), utilise D * Pbar(T0, Tn)
        comme variable de controle, d'esperance connue Pbar_M(0, Tn).

    Returns
    -------
    (prix, erreur standard)
    """
    sim = simulate([T0], n_paths, curve, p, seed=seed, antithetic=antithetic)
    disc = sim.discount_factors()[:, -1]
    x_t0, y_t0 = sim.x[:, -1], sim.y[:, -1]
    values = disc * np.asarray(payoff(x_t0, y_t0), dtype=float)

    if control_maturity is not None:
        control = disc * zero_coupon_price(T0, control_maturity, x_t0, y_t0, curve, p)
        var = control.var(ddof=1)
        if var > 0:
            beta = np.cov(values, control)[0, 1] / var
            values = values - beta * (control - curve.discount(control_maturity))

    return float(values.mean()), float(values.std(ddof=1) / np.sqrt(values.size))
