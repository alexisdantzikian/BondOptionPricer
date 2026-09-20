# Plan de travail — notebook `main/oat_option_pricer.ipynb`

Un seul notebook, séquentiel : chaque section = un markdown (théorie, justification) + une cellule de code +
une vérification numérique **avant** de passer à la suivante. Le notebook `main/main.ipynb` (HW1F) est conservé
comme brouillon ; ses briques sont reprises et corrigées dans le nouveau. Le cadre théorique est dans `CONTEXTE.md`.

Convention de code : fonctions pures, paramètres explicites (`params = dict(a_x=…, s_x=…, a_y=…, s_y=…, rho=…, L=…)`),
NumPy/SciPy/pandas/matplotlib uniquement. Pas d'optimisation prématurée.

---

## 0. Préalables (avant de coder)

### 0.1 Export Bloomberg — tout au 08/09/2026, clôture

| # | Quoi | Ticker / écran | Champs | Priorité |
|---|---|---|---|---|
| 1 | OAT nominales en vie (hors OATi, OAT€i, strips, maturité > 6 mois) | `FRTR Govt` → liste (SRCH ou `ALLQ`), ou `YCGT0014 Index` → membres | ISIN, COUPON, MATURITY, PX_LAST (clean), PX_DIRTY_MID ou accrued, YLD_YTM_MID, ISSUE_DT, date de règlement | **Indispensable** |
| 2 | Courbe ZC souveraine France Bloomberg (contrôle) | `YCGT0014 Index` (CURV → zero rates) ou `F910` / `I25` | tenor, taux ZC | Utile |
| 3 | Historique quotidien 2021-01 → 2026-09 | `GTFRF2Y/5Y/10Y/30Y Govt` (YLD_YTM_MID) et `EESWE2/5/10/30 BGN Curncy` (PX_LAST) | séries alignées | **Indispensable** (étape 2b) |
| 4 | CDS France 5Y | `FRTR CDS EUR SR 5Y D14 Corp` | PX_LAST, historique optionnel | Optionnel |
| 5 | Options sur future OAT | `OATA Comdty` → `OMON` | vols implicites ATM des 2-3 premières échéances, prix du future, CTD | Optionnel (extension) |
| 6 | Confirmation du cube de vols | `VCUB` EUR | €STR-based ou Euribor 6M ? normal ATM ? | À noter |

Format : onglets supplémentaires du fichier `data/market data bloom.xlsx` (`OAT`, `OAT_ZC`, `HIST`, `CDS`, `OATA`) ou fichiers séparés dans `data/`.

### 0.2 Environnement Windows
- `uv venv --python 3.12 .venv-win` (le `.venv` mac est inutilisable) ; deps : numpy, scipy, pandas, openpyxl, matplotlib, jupyter.
- `requirements.txt` / `pyproject.toml` minimal, `.gitignore` (`.venv*`, `__pycache__`, `.ipynb_checkpoints`).

---

## 1. Données de marché
**Objectif** : charger, convertir, décrire. Un tableau + un graphique par jeu (courbe €STR, surface de vols en heatmap, courbe OAT / spread).
**Vérifs** : tenors convertis correctement ; vols en décimal ; dates OAT → maturités en années ; spread OAT–€STR par tenor plausible (quelques dizaines de bp à 10Y).

## 2. Courbe sans risque €STR
**Théorie** : bootstrap OIS pilier par pilier (équation de pricing du swap), $P^M(0,T)$, $f^M(0,t) = -\partial_T\log P^M$.
**Décision à prendre ici** : interpolation. Comparer (i) spline cubique sur taux ZC (notebook actuel), (ii) spline sur $\log P$, (iii) interpolation monotone (PCHIP) sur $\log P$. Critère : forward instantané continu, sans oscillation, en particulier sur la zone 20Y→50Y inversée. Tracer $R(T)$, $f^M(0,T)$ pour les trois.
**Vérifs** : re-pricing des swaps à 0 ; $f^M$ vs différences finies de $\log P$ ; absence de forwards aberrants.

## 3. Courbe OAT (risquée)
**Théorie** : bootstrap / fit de $\bar P^M(0,T)$ à partir des prix dirty des OAT (moindres carrés sur un paramétrage lisse de $\log\bar P$ — Nelson-Siegel-Svensson ou spline pénalisée — parce que les maturités ne sont pas régulières et qu'on veut un $\bar f^M$ propre), comparaison avec la courbe ZC Bloomberg (export #2).
Spread ZC $\bar R(T) - R(T)$ et spread forward $\bar f^M - f^M$ : c'est la partie déterministe du modèle crédit. Discussion : spread court potentiellement négatif (liquidité, collatéral) → justification du modèle gaussien.
**Vérifs** : re-pricing des OAT (erreur en prix < quelques cents) ; $\bar f^M$ régulier ; $\bar P \le P$ ou explication.

## 4. Briques gaussiennes
`H(a,t,T)`, `V(a,s,t,T)`, `V_xy`, `Vbar`, moments de $(x(T),y(T))$, covariances avec $\int x$, $\int y$ (pour le MC exact).
**Vérifs** : limites $a\to0$ ; $\tfrac12\partial_T V(0,T)$ = terme de convexité de $\alpha$ ; $V$ par quadrature numérique de $\int\int e^{-a|u-v|}$ ; symétrie / positivité de la matrice de covariance 4×4.

## 5. Hull-White 1 facteur (facteur taux seul)
5.1 $\alpha$, $\int\alpha$, $P(t,T,x)$ — recalage exact, $-\partial_x\log P = H$.
5.2 Obligation à coupons, $D_x$, forward, $\Sigma_B$ (fermée + quadrature Gauss-Legendre), Black.
5.3 **Jamshidian** : $x^\ast$ tel que $B(T_0,x^\ast)=X$, décomposition en options sur ZC (formule HW exacte).
5.4 Swaption = option sur jambe fixe ; Bachelier ATM ; tableau erreur (poids gelés vs Jamshidian) sur toute la surface, en bp de vol normale. **Conclusion attendue** : erreur croissante en tenor et expiry, à documenter — c'est le coût de l'approximation qu'on emporte en 2F.
**Vérifs** : recalage, parité, limite $\sigma\to0$, un flux ⇒ formule HW du ZC, ATM ⇒ payeuse = receveuse.

## 6. Calibration étape 1 : $(a_x,\sigma_x)$
6.1 Objectif RMSE relatif (éq. 55), L-BFGS-B bornée, avec Jamshidian comme pricer (exact) **et** avec poids gelés (pour voir l'impact sur les paramètres calibrés).
6.2 Surface complète : carte des résidus expiry × tenor en bp — limite structurelle du 1F.
6.3 Diagonale co-terminale $T^\star$ = maturité de l'OAT sous-jacente (et 2-3 autres $T^\star$ pour montrer la dépendance) ; plancher expiry ≥ 1Y justifié.
6.4 Stabilité multi-départs ; sensibilité aux paramètres (Russo & Torri).
**Livrable** : $(a_x^\ast,\sigma_x^\ast)$ retenus + tableau comparatif.
**Extension (fin)** : $\sigma_x(t)$ constante par morceaux bootstrappée sur la diagonale (cours § 6.3.7).

## 7. Modèle à deux facteurs
7.1 $\int\bar\alpha$, $\bar\alpha(t)$, $\bar P(t,T,x,y)$ ; décomposition $\bar\alpha - \alpha = L\beta$ (spread forward + convexités croisées).
7.2 Obligation risquée, $D_x, D_y$, $\bar\Sigma_B$ (fermée + quadrature).
7.3 Graphiques : effet de $\rho$, $\sigma_y$, $a_y$, $L$ sur $\bar\Sigma_B$ ; décomposition $\bar\Sigma_B^2 = \Sigma_x^2 + L^2\Sigma_y^2 + \text{croisé}$.
**Vérifs** : recalage $\bar P(0,T)=\bar P^M$ ; dérivées $\partial_x,\partial_y$ par différences finies ; $L\to0$ ⇒ section 5.

## 8. Options sur OAT — formules fermées
8.1 Knock-out (Russo éq. 50-52) : implémentation, parité (éq. 59).
8.2 **Sans knock-out** : dérivation complète dans le markdown (changement de mesure, $\mu_x,\mu_y$, $m_i$, $M$, formule encadrée du `CONTEXTE.md` § 4.2), implémentation, parité.
8.3 Cas limites : $L\to0$ ⇒ HW1F (8.1 = 8.2 = section 5) ; $\sigma_y\to0$ ; $\rho=0$ ; $T_0\to0$ ⇒ valeur intrinsèque.
8.4 Valeur de la protection $C - C^{KO}$ : signe, décomposition numéraire / forward.
**Vérifs** : les trois cas limites ; $M$ vs $\bar B/\bar P$ vs $\bar B/P$ (tableau).

## 9. Calibration étape 2 : $(a_y,\sigma_y,\rho)$
9.1 Réplication Russo : $\bar P^\ast$ (éq. 57 telle quelle, et version corrigée $e^{-\int\bar\alpha}$), grille $\rho\in\{-1,-0.9,\dots,1\}$, optimisation $(a_y,\sigma_y)$ par nœud, tableau RMSE(ρ).
9.2 Diagnostic d'identification : identité $\bar P^\ast = \bar P^M e^{-\bar V/2}$ démontrée puis vérifiée numériquement ; surface RMSE en $(\sigma_y,\rho)$ à $a_y$ fixé ; conclusion.
9.3 Calibration historique : séries de spreads par tenor ; AR(1)/MLE OU → $a_y$ ; vol → $L\sigma_y$ → $\sigma_y$ à $L=40\,\%$ ; $\rho$ historique. Robustesse (tenor, fenêtre). Discussion P vs Q.
9.4 Jeu de paramètres retenu + comparaison aux ordres de grandeur de Russo (Exhibits 3-4) et au CDS 5Y.

## 10. Monte-Carlo de validation
10.1 Simulation **exacte** du vecteur gaussien $(x(T_0),y(T_0),\int_t^{T_0}x,\int_t^{T_0}y)$ (Cholesky, $N=10^5$-$10^6$, variables antithétiques).
10.2 Payoff $(\bar B(T_0)-X)^+$ avec $\bar P(T_0,T_i)$ fermé ; actualisation $e^{-\int r}$ (non-KO) et $e^{-\int\bar r}$ (KO) sur les mêmes trajectoires ; IC 95 %.
10.3 Contrôle Euler (pas fin) sur un cas.
10.4 Erreur de l'hypothèse lognormale par strike (80 %→120 % du forward) et par expiry : « smile » implicite ; comparer à Russo (< 2 %).

## 11. Résultats
11.1 Cas central : OAT benchmark, options 1Y/2Y/5Y, call/put, strikes autour du forward. Tableau KO vs non-KO vs HW1F seul.
11.2 Sensibilités : $L\in\{20,40,60,80\,\%\}$ (format Exhibit 7), $\rho$, $\sigma_y$, $a_y$, maturité de l'obligation.
11.3 Grecques par différences finies : delta taux ($x$), delta spread ($y$), vega $\sigma_x$, $\sigma_y$.
11.4 Décomposition de la variance taux / crédit / croisé.

## 12. Extensions (si temps) et conclusion
- $\sigma_x(t)$ par morceaux ; comparaison aux vols implicites des options sur future OAT ; option default-protected (discussion sans formule).
- Limites : poids gelés, spread gaussien, $L$ conventionnel, calibration P-mesure, pas de day-count.

---

## Ordre d'exécution et jalons

| Jalon | Sections | Dépend de |
|---|---|---|
| J1 — socle taux | 0.2, 1 (€STR + vols), 2, 4, 5, 6 | données déjà disponibles → **on démarre tout de suite** |
| J2 — courbe OAT | 1 (OAT), 3 | export #1 (#2) |
| J3 — 2F et formules | 7, 8 | J1, J2 |
| J4 — calibration crédit | 9 | export #3, J3 |
| J5 — validation et résultats | 10, 11 | J3, J4 |
| J6 — extensions, relecture | 12 | J5 |

Tant que les exports #1 et #3 ne sont pas là, J2-J4 peuvent être prototypés avec une courbe de spread synthétique (spread ZC $\bar R - R$ = 30 bp + 2 bp/an) clairement signalée, puis rebranchés.
