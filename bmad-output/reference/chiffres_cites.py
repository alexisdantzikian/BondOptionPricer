"""
Concordance entre le texte et les calculs du notebook main/oat_option_pricer.ipynb.

Exécute toutes les cellules de code du notebook, recalcule chaque chiffre cité dans le résumé, la lecture des
résultats et la conclusion, au format du texte, puis signale tout nombre de ces trois textes absent de la liste
(les nombres structurels, comme les années ou les numéros de section, y apparaissent normalement).

Usage, depuis la racine du dépôt : uv run python bmad-output/reference/chiffres_cites.py   (environ 1 min 30 s)
"""
import contextlib, io, os, re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nbformat

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
nb = nbformat.read(os.path.join(RACINE, "main", "oat_option_pricer.ipynb"), as_version=4)
os.chdir(os.path.join(RACINE, "main"))
plt.show = lambda *a, **k: plt.close("all")
with contextlib.redirect_stdout(io.StringIO()):
    for cellule in nb.cells:
        if cellule.cell_type == "code":
            exec(cellule.source, globals())

import math

def _fr(x, nd=0, signe=False, unite=""):
    """Nombre formaté comme dans le texte : nd décimales, virgule décimale, signe moins typographique, unité après une espace."""
    v = round(float(x), nd)
    s = f"{abs(v):.{nd}f}".replace(".", ",")
    s = ("−" if v < 0 else "+" if signe and v > 0 else "") + s
    return s + (f" {unite}" if unite else "")

def _plage(valeurs, nd=0, signe=False, unite=""):
    """Valeur commune si le minimum et le maximum s'arrondissent pareil, sinon « a à b »."""
    a, b = _fr(min(valeurs), nd, signe), _fr(max(valeurs), nd, signe)
    return (a if a == b else f"{a} à {b}") + (f" {unite}" if unite else "")

def _rapport(scen, cle):
    """Pour chaque scénario : (valeur du paramètre cle du modèle, call ATM / call ATM du cas retenu - 1, par échéance)."""
    t = atm_table(scen)
    return [(getattr(m.p, cle), t.loc[l] / _base - 1) for l, (m, rp) in scen.items()]

_T1, _TL = f"{ECHEANCES[0]:g} ans", f"{ECHEANCES[-1]:g} ans"   # première et dernière échéance
_base = pd.Series({f"{T0:g} ans": opts[T0].price(opts[T0].F_clean) * 100 for T0 in ECHEANCES})     # cas retenu

# --- repo : cas central = courbe retenue (repo, opts) ; scénarios bas et haut repérés par leur niveau de spread à 1 an
_t_repo = atm_table({l: (m_cal, rp) for l, rp in scen_repo.items()})
_niv = {l: rp.s(1.0) * 1e4 for l, rp in scen_repo.items() if l != "taux OAT"}
_bas, _haut = min(_niv, key=_niv.get), max(_niv, key=_niv.get)

# --- sensibilités sigma_y, rho, a_y (scénarios repérés par la valeur du paramètre)
_sy, _rho, _ay = _rapport(scen_sy, "s_y"), _rapport(scen_rho, "rho"), _rapport(scen_ay, "a_y")
_x2 = next(r for v, r in _sy if np.isclose(v, 2 * p_cal.s_y))
_d2 = next(r for v, r in _sy if np.isclose(v, 0.5 * p_cal.s_y))
_rlo = next(r for v, r in _rho if np.isclose(v, RHO_MIN))
_rhi = next(r for v, r in _rho if np.isclose(v, RHO_MAX))
_a_int = max(v for v, r in _ay if not np.isclose(v, p_cal.a_y) and v < 1.0)
_ecart_int = max(r.abs().max() for v, r in _ay if not np.isclose(v, p_cal.a_y) and v <= _a_int)
_baisse_1 = max(-r.min() for v, r in _ay if np.isclose(v, 1.0))

# --- Monte-Carlo : trajectoires déjà simulées à la section 11 (aucun nouveau tirage)
_mc = {T0: mcs[T0].price(oat46, opts[T0].F, True, opts[T0].delta) for T0 in ECHEANCES}         # (prix, demi-largeur IC 95 %)
_ic_rel = [ic / p for p, ic in _mc.values()]
_dans_ic = all(abs(_base[f"{T0:g} ans"] / 100 - p) <= ic for T0, (p, ic) in _mc.items())
_en0 = pd.Series({T0: curve.df(T0) * black(opts[T0].F, opts[T0].F, m_cal.sigma_B(0, T0, oat46)) / opts[T0].price(opts[T0].F_clean) - 1 for T0 in ECHEANCES})

_s2 = (hist_oat[2] - hist_estr[2]).loc[:"2022-12-31"].dropna()                  # avant la rupture du générique 2 ans (22/01/2024)

CHIFFRES = {
    f"spread repo du cas central, au premier tenor coté ({repo_data['tenor'].iloc[0]})": _fr(repo.spread[0] * 1e4, 0, True, "bp"),
    f"spread repo du cas central, au dernier tenor coté ({repo.T_max:g} ans)": _fr(repo.spread[-1] * 1e4, 0, True, "bp"),
    "translation de la courbe repo, scénario bas": _fr(_niv[_bas] - float(repo.s(1.0)) * 1e4, 0, True, "bp"),
    "translation de la courbe repo, scénario haut": _fr(_niv[_haut] - float(repo.s(1.0)) * 1e4, 0, True, "bp"),
    "forward clean à 1 an": _fr(opts[1.0].F_clean * 100, 1),
    f"forward clean à {_TL}": _fr(opts[ECHEANCES[-1]].F_clean * 100, 1),
    "recentrage delta à 1 an (bp)": _fr(opts[1.0].delta * 1e4, 0),
    f"recentrage delta à {_TL} (bp)": _fr(opts[ECHEANCES[-1]].delta * 1e4, 0),
    "call ATM 1 an, repo bas / central - 1": _fr((_t_repo.loc[_bas, _T1] / _base[_T1] - 1) * 100, 0, True, "%"),
    "call ATM 1 an, repo haut / central - 1": _fr((_t_repo.loc[_haut, _T1] / _base[_T1] - 1) * 100, 0, True, "%"),
    f"call ATM {_TL}, repo bas / central - 1": _fr((_t_repo.loc[_bas, _TL] / _base[_TL] - 1) * 100, 0, True, "%"),
    f"call ATM {_TL}, repo haut / central - 1": _fr((_t_repo.loc[_haut, _TL] / _base[_TL] - 1) * 100, 0, True, "%"),
    f"call ATM {_TL}, cas central": _fr(_base[_TL], 1),
    f"call ATM {_TL}, repo bas": _fr(_t_repo.loc[_bas, _TL], 1),
    f"call ATM {_TL}, repo haut": _fr(_t_repo.loc[_haut, _TL], 1),
    f"call ATM {_TL}, financement au taux de l'OAT": _fr(_t_repo.loc["taux OAT", _TL], 1),
    "part du spread dans la variance de Sigma_B": _plage(res["part spread"] * 100, 0, unite="%"),
    "part du terme croisé": _plage(res["part croisée"] * 100, 0, unite="%"),
    "Sigma_B 2F / taux seul - 1": _plage((res["Sigma_B 2F"] / res["Sigma_B taux seul"] - 1) * 100, 0, unite="%"),
    "call ATM 2F / taux seul - 1 (toutes échéances)": _plage(res["2F / taux seul - 1"] * 100, 0, unite="%"),
    "sigma_y x 2 : hausse du call ATM": _plage(_x2 * 100, 0, unite="%"),
    "sigma_y / 2 : baisse du call ATM": _plage(-_d2 * 100, 0, unite="%"),
    "sigma_y retenu (bp par an)": _fr(p_cal.s_y * 1e4, 1),
    "écart-type de sigma_y (bp par an)": _fr(GMM["se"]["s_y"] * 1e4, 1),
    "rho retenu": _fr(p_cal.rho, 2),
    "écart-type de rho": _fr(GMM["se"]["rho"], 2),
    "J de Hansen (GMM efficace)": _fr(GMM["J"], 1),
    "degrés de liberté du test J": _fr(GMM["dof"], 0),
    "spread OAT - €STR 2 ans moyen, 2021-2022": _fr(_s2.mean() * 1e4, 0, unite="bp"),
    "part des jours à spread 2 ans négatif, 2021-2022": _fr((_s2 < 0).mean() * 100, 0, unite="%"),
    "résidu maximal de la diagonale 20 ans (bp de vol normale)": _fr(tab_diag["residu_bp"].abs().max(), 1),
    "rho, borne basse de la fourchette historique": _fr(RHO_MIN, 2),
    "rho, borne haute": _fr(RHO_MAX, 2),
    "call ATM à rho = borne basse / retenu - 1": _plage(_rlo * 100, 0, True, "%"),
    "call ATM à rho = borne haute / retenu - 1": _plage(_rhi * 100, 0, True, "%"),
    "a_y retenu": _fr(p_cal.a_y, 3),
    "a_y du scénario intermédiaire le plus élevé": _fr(_a_int, 2),
    "écart du call ATM pour a_y jusqu'au scénario intermédiaire, majorant": _fr(math.ceil(_ecart_int * 100), 0, unite="%"),
    "a_y du scénario de retour rapide": _fr(max(v for v, r in _ay), 0),
    "baisse du call ATM pour a_y = 1, majorant": _fr(math.ceil(_baisse_1 * 100), 0, unite="%"),
    "IC 95 % relatif du Monte-Carlo à la monnaie, minimum": _fr(min(_ic_rel) * 100, 1),
    "IC 95 % relatif du Monte-Carlo à la monnaie, maximum": _fr(max(_ic_rel) * 100, 1, unite="%"),
    "écart ATM exact / MC dans l'IC à toutes les échéances": "oui" if _dans_ic else "non",
    "poids gelés en 0 / exact - 1 à la monnaie, maximum sur les échéances": _fr(_en0.abs().max() * 100, 1, unite="%"),
    "échéance de cet écart maximal": f"{_en0.abs().idxmax():g} ans",
    "poids gelés recentrés / exact - 1 à la monnaie, maximum": _fr(ERR.loc["call 100%"].abs().max(), 2, unite="%"),
    **{f"poids gelés / exact - 1, {opt}, {T}": _fr(ERR.loc[opt, T], 1, True, "%") for opt in ("call 110%", "put 90%") for T in ERR.columns},
    "échéance du call ATM maximal": f"{res.loc[res['call ATM 2F'].idxmax(), 'T0']:g} ans",
    "échéance de Sigma_B maximal": f"{res.loc[res['Sigma_B 2F'].idxmax(), 'T0']:g} ans",
    "échéance maximale": f"{max(ECHEANCES):g} ans",
    "sigma_x retenu": _fr(p_cal.s_x * 100, 2, unite="%"),
    "sigma_eq du 1F équivalent": _fr(s_eq * 100, 2, unite="%"),
    "sigma_eq / sigma_x - 1": _fr((s_eq / p_cal.s_x - 1) * 100, 0, unite="%"),
    "1F équivalent / 2F - 1 sur le call ATM, écart maximal": _fr(eq["1F équivalent / 2F - 1"].abs().max() * 100, 1, unite="%"),
    "vol du swap €STR 20 ans, modèle (bp)": _fr(VOLS.loc["modèle calibré", "swap €STR"], 0),
    "vol du taux OAT 20 ans, modèle (bp)": _fr(VOLS.loc["modèle calibré", "OAT"], 0),
    "vol du swap €STR 20 ans, réalisée (bp)": _fr(VOLS.loc["réalisé", "swap €STR"], 0),
    "vol du taux OAT 20 ans, réalisée (bp)": _fr(VOLS.loc["réalisé", "OAT"], 0),
    "rapport OAT / €STR, modèle": _fr(VOLS.loc["modèle calibré", "OAT / €STR"], 2),
    "rapport OAT / €STR, réalisé": _fr(VOLS.loc["réalisé", "OAT / €STR"], 2),
    "poids gelés / Jamshidian - 1 sur la diagonale, maximum": _fr(tab_diag["gelé/exact - 1 (%)"].abs().max(), 2, unite="%"),
}

_est = atm_table(scen_est)
_q = np.quantile(MC_KAL, [0.05, 0.95], axis=0)
CHIFFRES.update({
    "ACP du spread : part de la première composante": _fr(acp.explained_variance_ratio_[0] * 100, 0, unite="%"),
    "ACP du spread : part de la deuxième composante": _fr(acp.explained_variance_ratio_[1] * 100, 0, unite="%"),
    "Kalman : sigma_y (bp par an)": _fr(KAL.params[5] * 100, 1),
    "Kalman : rho": _fr(KAL.params[6], 2),
    "Kalman : a_x^Q": _fr(KAL.params[0], 4),
    "swaptions : a_x": _fr(A_X, 4),
    "Kalman : a_x^P et a_y^P": f"{_fr(KAL.params[2], 2)} et {_fr(KAL.params[3], 2)}",
    "Kalman : écarts-types de a_x^P et a_y^P": f"{_fr(KAL.bse[2], 2)} et {_fr(KAL.bse[3], 2)}",
    "test simulé : médianes de a_x^P et a_y^P (vraie valeur 0,2)": f"{_fr(np.median(MC_KAL[:, 2]), 2)} et {_fr(np.median(MC_KAL[:, 3]), 2)}",
    "test simulé : vitesses historiques entre (quantiles 5 % et 95 %)": f"{_fr(_q[0, 2:4].min(), 1)} et {_fr(_q[1, 2:4].max(), 1)}",
    "call ATM, Kalman / GMM - 1": _plage((_est.loc["filtre de Kalman"] / _est.loc["GMM (retenue)"] - 1) * 100, 1, True, "%"),
    "demi-vie d'une vitesse de 0,2 (ans)": _fr(np.log(2) / 0.2, 1),
})

# --- vitesse de retour des taux imposée, H4 hors de la monnaie, diagonale repricée avec le filtre de Kalman (§12)
_ax = T_AX.div(T_AX.loc[[l for l in T_AX.index if "retenu" in l][0]], axis=1) - 1     # call ATM / retenu - 1, par a_x et échéance
_ax.index = AX["a_x"].values
_res_ax = AX.set_index("a_x")["résidu max de la diagonale (bp)"]
_h4 = H4_HORS.set_index("T0")
CHIFFRES.update({
    "a_x retenu, trois décimales": _fr(A_X, 3),
    "résidu max de la diagonale à a_x = 0,05 (bp)": _fr(_res_ax[0.05], 1),
    "call ATM, écart maximal pour a_x de 0,001 à 0,05, majorant": _fr(math.ceil(_ax.loc[_ax.index <= 0.05].abs().max().max() * 100), 0, unite="%"),
    "résidu max de la diagonale à a_x = 0,2 (bp)": _fr(_res_ax[0.2], 0),
    "call ATM 1 an à a_x = 0,2 / retenu - 1": _fr(_ax.loc[0.2, _T1] * 100, 0, unite="%"),
    f"1F à sigma_eq, plus grand écart de 90 à 110 % à 1 an ({_h4.loc[1.0, 'option']})": _fr(_h4.loc[1.0, "écart max, sigma_eq (%)"], 1, unite="%"),
    "volatilité du 1F ajustée sur le call ATM": _plage(_h4["sigma ajustée (%)"], 2, unite="%"),
    "1F à volatilité ajustée, plus grand écart de 90 à 110 %": _fr(_h4["écart max, sigma ajustée (%)"].abs().max(), 2, unite="%"),
    "Kalman : sigma_x": _fr(KAL.params[4], 2, unite="%"),
    "diagonale repricée avec le filtre de Kalman : écart moyen (bp)": _fr(ECART_KAL.mean(), 1),
    "sigma^Q / sigma^P du facteur taux": _fr(KAPPA, 2),
    "sigma^P - sigma^Q, en écarts-types du filtre": _fr((s_k - s_q) / se_k, 1),
    "baisse du call ATM si sigma_y x sigma^Q / sigma^P": _plage(-C_KAPPA * 100, 0, unite="%"),
})

# --- régimes de volatilité du spread (§9.4) et effet sur le prix (§12)
_rq, _rh = REG["quotidiennes"], REG["hebdomadaires"]
_sq, _rhoq = regimes_effectifs(_rq)
_rp = REGP.div(REGP["GMM (retenue)"], axis=0) - 1
_dq, _dh = _rq["tab"]["durée moyenne (jours ouvrés)"], _rh["tab"]["durée moyenne (jours ouvrés)"]
CHIFFRES.update({
    "vol du spread en régime calme et en régime agité (bp par an)": f"{_fr(_rq['tab'].loc['calme', 'vol spread (bp/an)'], 0)} et "
                                                                     f"{_fr(_rq['tab'].loc['agité', 'vol spread (bp/an)'], 0)}",
    "sigma_y en régime calme": _fr(_sq["calme"] * 100, 2, unite="%"),
    "sigma_y en régime agité": _fr(_sq["agité"] * 100, 2, unite="%"),
    "corrélation des browniens commune aux régimes": _fr(_rhoq, 2),
    "call ATM toujours en régime calme, baisse": _plage(-_rp["toujours calme"] * 100, 0, unite="%"),
    "call ATM toujours en régime agité, hausse": _plage(_rp["toujours agité"] * 100, 0, unite="%"),
    "durées moyennes des régimes, variations quotidiennes (jours ouvrés)": f"{_fr(_dq['calme'], 0)} et {_fr(_dq['agité'], 0)}",
    "durées moyennes des régimes, variations hebdomadaires (jours ouvrés)": f"{_fr(_dh['calme'], 0)} et {_fr(_dh['agité'], 0)}",
    "probabilité du régime agité à la date des cours": _fr(_rq["p0"] * 100, 0, unite="%"),
    "call ATM avec régimes quotidiens / retenu - 1, à 1 an (baisse)": _fr(-_rp.loc[1.0, "régimes (quotidiennes)"] * 100, 1, unite="%"),
    "écart des régimes quotidiens décroissant avec l'échéance": "oui" if _rp["régimes (quotidiennes)"].abs().is_monotonic_decreasing else "non",
    "call ATM avec régimes, écart maximal (deux estimations)": _fr(_rp[["régimes (quotidiennes)", "régimes (hebdomadaires)"]].abs().max().max() * 100, 1, unite="%"),
})

print("chiffres cités (valeurs formatées comme dans le texte) :")
for _lib, _val in CHIFFRES.items():
    print(f"  {_lib:<72} {_val}")

valeurs = set()
for v in CHIFFRES.values():
    base = re.sub(r" ?(bp|%|ans)$", "", v)
    valeurs |= {v, base} | {p.strip() for p in re.split(r" à | et ", base)}
textes = {"résumé": nb.cells[0].source.split("## Introduction")[0],
          "lecture des résultats": next(c.source for c in nb.cells if c.source.startswith("### Lecture des résultats")),
          "conclusion": next(c.source for c in nb.cells if c.source.startswith("## 13. Conclusion"))}
print("\nnombres du texte absents de la liste (à vérifier s'ils ne sont pas structurels) :")
for nom, t in textes.items():
    nombres = re.findall(r"[−+]?\d+(?:,\d+)?", t)
    print(f"  {nom} :", sorted({n for n in nombres if n not in valeurs and n.lstrip("+−") not in valeurs and "+" + n not in valeurs}))
