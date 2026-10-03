# Contexte — Pricer d'options sur OAT sous un modèle gaussien à deux facteurs

Document de cadrage du mémoire : objectif, contrat, modèle, calibration, données, conventions. Le livrable
est le notebook unique `main/oat_option_pricer.ipynb` ; l'état d'avancement est dans `PLAN.md`.

---

## 1. Objectif

Construire, calibrer et valider un **pricer d'options européennes sur OAT** dans le **modèle G2++** de Brigo et
Mercurio (*Interest Rate Models — Theory and Practice*, 2e éd., 2006, section 4.2, `doc/Brigo D., Mercurio F. ...pdf`),
dans la lecture de Russo, Giacometti & Fabozzi (*Closed-Form Solution for Defaultable Bond Options under a
Two-Factor Gaussian Model for Risky Rates Modeling*, draft, `doc/13. Russo et al....pdf`) :

- facteur 1 : taux sans risque, Hull-White 1F sur la courbe €STR ;
- facteur 2 : spread court OAT–€STR, Hull-White 1F, modélisé directement comme facteur de risque de marché.

**Sources** : le livre est la référence du modèle (G2++, mesure forward, prix exact par le théorème 4.2.3,
Hull-White et Jamshidian au chapitre 3, pratique de calibration en 4.2.7, intensités aux chapitres 21-22) ; le
papier de Russo et al., dont les équations 12 à 24 sont celles du G2++, l'est pour trois choix : le second facteur
lu comme spread de crédit, l'approximation à poids gelés, la calibration du spread sur la courbe risquée.

Nature du livrable : mémoire de recherche. Chaque étape est justifiée, vérifiée et lisible, pas optimisée.

**Question de recherche** : faut-il modéliser le spread OAT–€STR comme un facteur de risque à part pour pricer
une option européenne sur OAT, et peut-on en identifier les paramètres avec les données disponibles ?

| | Hypothèse | Verdict du notebook |
|---|---|---|
| H1 | La courbe OAT identifie le facteur spread (procédure de Russo et al.) | rejetée (§9.1) |
| H2 | L'historique l'identifie, sous la mesure de pricing comme sous la mesure historique | confirmée pour la mesure de pricing (GMM et filtre de Kalman : $a_y^Q \approx 0$, $\sigma_y$ 33,7 / 33,1 bp, $\rho$ 0,13 / 0,15), rejetée pour la mesure historique (vitesses non identifiées, problème de persistance) ; $\rho$ instable, tests J et de Ljung-Box rejetés (§9-10) |
| H3 | Le facteur spread renchérit sensiblement l'option | confirmée : +17 % à la monnaie ; vols réalisées cohérentes (§12) |
| H4 | Cet effet exige deux facteurs | rejetée : un Hull-White 1F à la volatilité totale reproduit les prix à 1,9 % près (§12) |
| H5 | L'approximation à poids gelés de Russo et al. est assez précise | confirmée à la monnaie (0,12 % du prix exact) ; rejetée en dehors : −3,0 % / +4,3 % à 1 an sur call 110 % / put 90 % (§11) |

Ordre du notebook : résumé et introduction ; I. données et courbes (1-3) ; II. modèle et évaluation (4-7) ;
III. calibration et estimation (8 facteur taux, 9 facteur spread par GMM, 10 filtre de Kalman) ; IV. validation (11),
résultats (12), conclusion (13) ; références. Les chiffres cités sont recalculés hors du notebook par
`bmad-output/reference/chiffres_cites.py`.

## 2. Le contrat

- **Option vanille collatéralisée** (€STR), telle qu'elle se traite en banque d'investissement : call / put
  européen sur l'OAT, actualisé au taux €STR.
- **Sous-jacent** : OAT 4,10 % 25/05/2046 (FR0014015MU5). **Échéances** : 1, 2, 5, 7 et 10 ans.
- **Strike clean**, exprimé en % du **forward clean** (à la monnaie = forward clean). En interne, strike dirty
  $X = K + CC(T_0)$, le coupon couru à l'échéance étant connu.
- **Forward repo** : cash-and-carry au taux €STR + spread repo,
  $F = \big[\bar B^M(0) - \sum_{T_i \le T_0} K_i P^{repo}(0,T_i)\big] / P^{repo}(0,T_0)$,
  $P^{repo} = P^M e^{-s^{repo}(T)T}$. La courbe repo (`data/repo_fictif.csv`) est **fictive**, faute de
  cotations : +20 bp à 3 semaines contre l'€STR, puis linéaire jusqu'à +75 bp à 10 ans. Les options sont
  limitées à 10 ans pour que la courbe couvre toutes les échéances : elle n'est jamais prolongée (§7.2 du
  notebook). La section 12 mesure l'effet de son niveau (translations de −25 à +25 bp, financement
  au taux de l'OAT). Une courbe de marché la remplacera au même format, sans modifier le code.
- Aucune comparaison avec les résultats chiffrés du papier ni avec des options cotées.

## 3. Le modèle

$$\bar r(t) = \bar\alpha(t) + x(t) + y(t),\qquad dx = -a_x x\,dt + \sigma_x dW_x,\qquad dy = -a_y y\,dt + \sigma_y dW_y,
\qquad dW_x dW_y = \rho\,dt.$$

- G2++ de Brigo et Mercurio (éq. 4.4-4.5 ; $a, b, \sigma, \eta$ dans le livre pour $a_x, a_y, \sigma_x, \sigma_y$).
- $r = \alpha + x$ recale la courbe €STR, $\bar\alpha$ recale directement la courbe OAT :
  $\int_0^T\bar\alpha = -\log\bar P^M(0,T) + \tfrac12\bar V(0,T)$ (Brigo et Mercurio, corollaire 4.2.1).
- Briques : $H_a(t,T) = (1-e^{-a\tau})/a$, $V_{a,\sigma}$, terme croisé $V_{xy}$, $\bar V = V_x + V_y + V_{xy}$.
- Zéro-coupons log-affines en $(x,y)$ (Brigo et Mercurio, théorème 4.2.1 ; Russo éq. 16-24) ; obligation à coupons et durations stochastiques
  $D_x, D_y$ (éq. 28-31).

## 4. La formule de pricing

1. $C = P(0,T_0)\,\mathbb E^{T_0}[(\bar B(T_0) - X)^+]$, mesure $T_0$-forward €STR.
2. Laissé à lui-même, le modèle donne une espérance forward $M = \sum_i K_i\,\mathbb E^{T_0}[\bar P(T_0,T_i)]$
   (fermée, décalages de Girsanov $\mu_x,\mu_y$) qui ne coïncide pas avec $F$ : on **recentre** la moyenne de
   $y(T_0)$ d'une constante $\delta$ telle que $\sum_i m_i(\delta) = F$.
3. **Prix exact** (Brigo et Mercurio, théorème 4.2.3, adapté aux deux courbes, à la mesure forward €STR et au
   recentrage) : intégrale de Gauss-Hermite sur $y(T_0)$ ; sachant $y$, $x(T_0)$ est gaussien, $x^\ast$ résout
   $\bar B(T_0) = X$ (Newton) et l'espérance du payoff est fermée. Call et put calculés séparément ; égal à
   Jamshidian en un facteur ; convergé dès 16 nœuds.
4. **Approximation de Russo et al.**, gardée pour comparaison et pour la décomposition de $\bar\Sigma_B^2$ :
   hypothèse lognormale à poids gelés, poids à leur **valeur forward recentrée** $w_i = m_i(\delta)/F$,
   $C \approx P(0,T_0)\,[F\Phi(d_1) - X\Phi(d_2)]$ (Black sur le forward repo). Parité
   $C - P = P(0,T_0)(F^{clean} - K)$.

## 5. Calibration

- **Facteur taux** : $(a_x,\sigma_x)$ conjointement sur la diagonale co-terminale 20 ans (maturité du
  sous-jacent) des swaptions ATM, expiries 1 à 15 ans, tenors non cotés interpolés linéairement en vol normale
  (objectif de Brigo et Mercurio 4.2.7 et de Russo éq. 55), sur les **prix exacts de Jamshidian** (éq. 3.44-3.46),
  meilleur de plusieurs départs : $a_x = 0{,}01067$, $\sigma_x = 0{,}7367\,\%$ (à poids gelés : 0,01051 et 0,7352 %). Les expiries 12 et 15 ans dépassent les options mais identifient $a_x$ : restreinte
  aux expiries 1 à 10 ans, la diagonale le pousse contre sa borne inférieure. Surface complète en diagnostic.
- **Facteur spread** :
  - la procédure du papier (fit de la courbe OAT, éq. 56-57) n'identifie rien : $\bar P^\ast = \bar P^M e^{-\bar V/2}$,
    elle minimise la convexité, solution exacte $\rho = -1$, $a_y = a_x$, $\sigma_y = \sigma_x$ ; Brigo et Mercurio
    font le même constat pour les intensités (22.7.2) et fixent la corrélation sur l'historique ;
  - retenu : $(a_y,\sigma_y,\rho)$ estimés **ensemble par la méthode des moments généralisée** (§9.3) sur
    12 moments des variations quotidiennes : les volatilités annualisées du spread OAT–€STR aux tenors
    5-30 ans (modèle $\sigma_y H_{a_y}(\tau)/\tau$, dont la structure par terme identifie la vitesse de retour
    risque-neutre) et les corrélations spread / swap €STR de même tenor (modèle $\rho$) ; covariance des
    moments par bootstrap par blocs mobiles. Pondération **diagonale** retenue : la pondération efficace
    $S^{-1}$, avec des erreurs de moments très corrélées entre tenors, donne des poids négatifs et un $\rho$
    hors de toutes les corrélations observées (biais d'Altonji et Segal, 1996) ; elle sert au test J de
    Hansen, qui rejette le spread à un facteur. Robustesse : ajustement de la structure par terme des vols
    fenêtre par fenêtre (2021-2026, trois ans, un an) ; historiques 01/2021 → 08/09/2026 ; tenor 2 ans exclu
    (rupture du générique le 22/01/2024) ;
  - un seul facteur de spread : l'ACP des variations quotidiennes du spread (scikit-learn) donne 86 % de la
    variance à la première composante, de chargements presque égaux ; la deuxième (pente, 8 %) reste hors modèle ;
  - **filtre de Kalman** (section 10, cours I.2-I.3), en contrôle de la GMM : modèle espace-état des 12 séries
    (swaps €STR et spreads aux tenors 5-30 ans, centrés), états $(x, y)$, chargements $H_{a^Q}(\tau)/\tau$,
    dynamique historique d'Ornstein-Uhlenbeck discrétisée exactement (vitesses $a^P$), erreurs i.i.d. par série,
    initialisation stationnaire ; statsmodels, L-BFGS. La vraisemblance libre a plusieurs maxima, selon la série
    qu'elle ajuste exactement : les taux à 20 ans sont donc supposés observés sans erreur (inversion de
    Chen-Scott). Résultats : $a_x^Q = 0{,}0118$ (swaptions : 0,0107), $a_y^Q$ à sa borne, $\sigma_x = 0{,}775\,\%$,
    $\sigma_y = 0{,}331\,\%$, $\rho = 0{,}151$ ; vitesses historiques non significatives ; test sur 48 échantillons
    simulés : paramètres risque-neutres, volatilités et $\rho$ retrouvés, vitesses historiques biaisées vers le
    haut et très dispersées (médianes 0,82 et 0,62 pour 0,2) ; Ljung-Box rejette les erreurs i.i.d. ; avec ces
    paramètres, le call à la monnaie change de +0,5 % ;
  - méthodes (GMM, filtre de Kalman, inversion, problème de persistance, pricing à intensité) tirées du cours de Monfort, Pegoraro et
    Renne, *Econometrics of Commodity and Asset Pricing*, cours 5 (ENSAE 2025-2026),
    `doc/econo modele affine.pdf`.

## 6. Validation

Le notebook ne garde que les validations scientifiques ; les contrôles de développeur (quadratures,
différences finies, parités, multi-départs) en ont été retirés le 03/10/2026. Le prix exact coïncide avec
Jamshidian dans le cas limite à un facteur ; il est validé par un Monte-Carlo exact du vecteur gaussien $(x(T_0), y(T_0), \int x, \int y)$ sans discrétisation,
avec recentrage (écarts dans l'intervalle de confiance, après trois contrôles de la simulation) ; l'erreur de l'approximation à poids gelés est ensuite
mesurée contre le prix exact, sans bruit de simulation. Au §12, deux contrôles de la
conclusion : un Hull-White 1F sur la courbe OAT à la volatilité totale $\sigma_{eq}$ (le modèle 2F calibré s'y
ramène à 1,9 % près), et les volatilités réalisées des taux 20 ans (rapport OAT / €STR 1,17 contre 1,18 dans le
modèle). Le script `bmad-output/reference/chiffres_cites.py` exécute le notebook, recalcule chaque chiffre
du résumé, de la lecture des résultats et de la conclusion au format du texte, et signale les nombres du texte
qui n'y figurent pas.

Le recentrage $\delta$ (§7.3) est nul quand le spread repo égale le spread de l'OAT ; sinon il reporte dans la
moyenne du prix la perte que le modèle gaussien ne contient pas (dispersion sans saut). Avec la courbe retenue,
il reste entre −3 et 33 bp.

## 7. Données (Bloomberg, clôture du 08/09/2026, règlement 10/09/2026)

| Source | Contenu |
|---|---|
| `data/market data bloom.xlsx` — `ESTR CURVE` | 32 taux swap OIS €STR, 1W → 50Y |
| — `Swaption cube` | vols normales ATM EUR, 21 expiries × 14 tenors |
| — `Liste OAT` | 19 titres (5 zéro-coupons courts, 14 OAT 2028 → 2072) |
| — `Zield Histo OAT`, `Yield Histo ESTR` | historiques quotidiens 2, 5, 10, 15, 20, 25, 30 ans depuis 01/2021 |
| `data/repo_fictif.csv` | spread repo contre €STR, **fictif** : +20 bp à 3 semaines, linéaire jusqu'à +75 bp à 10 ans |

## 8. Conventions et simplifications

- $t=0$ = 10/09/2026, ACT/365, pas de calendrier ; swaps €STR à jambe fixe annuelle ; OAT à coupon annuel,
  couru ACT/ACT.
- Courbe €STR : bootstrap + spline cubique sur $\log P$. Courbe OAT : Nelson-Siegel-Svensson sur prix dirty,
  pondération par la duration.
- Vols de swaptions supposées cohérentes avec l'actualisation €STR ; rendements génériques de pair utilisés
  comme taux zéro.
- Environnement : Python 3.12 via `uv` (`pyproject.toml`, `uv.lock`) ; NumPy, SciPy, pandas, matplotlib,
  statsmodels (filtre de Kalman, maximum de vraisemblance), scikit-learn (ACP), joblib (test simulé en parallèle).
  Exécution complète : ≈ 1 min 15 s.

## 9. Écarts de méthode par rapport à Russo et al. (et apports de Brigo et Mercurio)

| Point | Russo et al. | Ce mémoire |
|---|---|---|
| Émetteur | courbes corporate US par notation | souverain France, €STR sans risque |
| Contrat et forward | forward et numéraire issus de la courbe risquée | option vanille collatéralisée €STR, forward repo, strike clean |
| Prix de l'option | formule fermée approchée (poids gelés) | prix exact de Brigo et Mercurio (th. 4.2.3) adapté ; poids gelés en comparaison |
| $\bar\Sigma_B$ | intégration numérique | fermée sous poids gelés, poids à leur valeur forward recentrée |
| Calibration du facteur taux | swaptions co-terminales, prix Hull-White | prix exacts de Jamshidian, diagonale de l'OAT (recommandation de Brigo et Mercurio 4.2.7) |
| Lien avec le crédit | spread issu d'une intensité de défaut et d'une perte | spread modélisé directement, justifié par le recouvrement en valeur de marché (seul le produit perte × intensité est identifié) |
| Calibration du spread | fit de la courbe risquée | GMM sur la structure par terme des vols et les corrélations historiques du spread, pondération diagonale, test J ; contrôle par maximum de vraisemblance avec filtre de Kalman |
| Vitesse de retour historique | — | estimée par filtre de Kalman avec la dynamique risque-neutre ; non identifiée sur six ans (test sur données simulées) |
| Nécessité du second facteur | — | testée : avec les paramètres estimés, un 1F à la volatilité totale suffit à 1,9 % près |
| Validation | Monte-Carlo | prix exact validé par Monte-Carlo exact ; erreur de l'approximation mesurée contre le prix exact, par strike et par échéance |
