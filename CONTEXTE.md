# Contexte — Pricer d'options sur OAT sous un modèle gaussien à deux facteurs

Document de cadrage du mémoire : objectif, contrat, modèle, calibration, données, conventions. Le livrable
est le notebook unique `main/oat_option_pricer.ipynb` ; l'état d'avancement est dans `PLAN.md`.

---

## 1. Objectif

Construire, calibrer et valider un **pricer d'options européennes sur OAT** dans le **modèle gaussien à deux
facteurs corrélés** de Russo, Giacometti & Fabozzi (*Closed-Form Solution for Defaultable Bond Options under a
Two-Factor Gaussian Model for Risky Rates Modeling*, draft, `doc/13. Russo et al....pdf`) :

- facteur 1 : taux sans risque, Hull-White 1F sur la courbe €STR ;
- facteur 2 : spread court OAT–€STR, Hull-White 1F, modélisé directement comme facteur de risque de marché.

Nature du livrable : mémoire de recherche. Chaque étape est justifiée, vérifiée et lisible, pas optimisée.

## 2. Le contrat

- **Option vanille collatéralisée** (€STR), telle qu'elle se traite en banque d'investissement : call / put
  européen sur l'OAT, actualisé au taux €STR.
- **Sous-jacent** : OAT 4,10 % 25/05/2046 (FR0014015MU5). **Échéances** : 1, 2, 5, 7, 10, 12 et 15 ans.
- **Strike clean**, exprimé en % du **forward clean** (à la monnaie = forward clean). En interne, strike dirty
  $X = K + CC(T_0)$, le coupon couru à l'échéance étant connu.
- **Forward repo** : cash-and-carry au taux €STR + spread repo,
  $F = \big[\bar B^M(0) - \sum_{T_i \le T_0} K_i P^{repo}(0,T_i)\big] / P^{repo}(0,T_0)$,
  $P^{repo} = P^M e^{-s^{repo}(T)T}$. La courbe repo (`data/repo_fictif.csv`) est **fictive**, faute de
  cotations : de +2 bp à 1 semaine à +6 bp à 1 an contre l'€STR, cotée jusqu'à 1 an comme un marché de repo à
  terme. Au-delà, le repo n'est pas liquide : le spread est maintenu au niveau du dernier tenor coté
  (`FINANCEMENT_LONG = "plat"`, §8.2 du notebook), hypothèse dont le §11 mesure l'effet (translations de
  −25 à +25 bp, financement au taux de l'OAT). Une courbe de marché la remplacera au même format, sans
  modifier le code.
- Aucune comparaison avec les résultats chiffrés du papier ni avec des options cotées.

## 3. Le modèle

$$\bar r(t) = \bar\alpha(t) + x(t) + y(t),\qquad dx = -a_x x\,dt + \sigma_x dW_x,\qquad dy = -a_y y\,dt + \sigma_y dW_y,
\qquad dW_x dW_y = \rho\,dt.$$

- $r = \alpha + x$ recale la courbe €STR, $\bar\alpha$ recale directement la courbe OAT :
  $\int_0^T\bar\alpha = -\log\bar P^M(0,T) + \tfrac12\bar V(0,T)$.
- Briques : $H_a(t,T) = (1-e^{-a\tau})/a$, $V_{a,\sigma}$, terme croisé $V_{xy}$, $\bar V = V_x + V_y + V_{xy}$.
- Zéro-coupons log-affines en $(x,y)$ (Russo éq. 16-24) ; obligation à coupons et durations stochastiques
  $D_x, D_y$ (éq. 28-31).

## 4. La formule de pricing

1. $C = P(0,T_0)\,\mathbb E^{T_0}[(\bar B(T_0) - X)^+]$, mesure $T_0$-forward €STR.
2. Laissé à lui-même, le modèle donne une espérance forward $M = \sum_i K_i\,\mathbb E^{T_0}[\bar P(T_0,T_i)]$
   (fermée, décalages de Girsanov $\mu_x,\mu_y$) qui ne coïncide pas avec $F$ : on **recentre** la moyenne de
   $y(T_0)$ d'une constante $\delta$ telle que $\sum_i m_i(\delta) = F$.
3. Hypothèse lognormale à poids gelés (Russo & Fabozzi), poids gelés à leur **valeur forward recentrée**
   $w_i = m_i(\delta)/F$ ; $\bar\Sigma_B^2 = \bar D_x^2\mathrm{Var}\,x + \bar D_y^2\mathrm{Var}\,y + 2\bar D_x\bar D_y\mathrm{Cov}$.
4. $C = P(0,T_0)\,[F\Phi(d_1) - X\Phi(d_2)]$ (Black sur le forward repo), put par parité
   $C - P = P(0,T_0)(F^{clean} - K)$.

## 5. Calibration

- **Facteur taux** : $(a_x,\sigma_x)$ conjointement sur la diagonale co-terminale 20 ans (maturité du
  sous-jacent) des swaptions ATM, expiries 1 à 15 ans, tenors non cotés interpolés linéairement en vol normale
  (objectif Russo éq. 55). Surface complète en diagnostic. Contrôle Jamshidian.
- **Facteur spread** :
  - la procédure du papier (fit de la courbe OAT, éq. 56-57) n'identifie rien : $\bar P^\ast = \bar P^M e^{-\bar V/2}$,
    elle minimise la convexité, solution exacte $\rho = -1$, $a_y = a_x$, $\sigma_y = \sigma_x$ ;
  - retenu : $(a_y,\sigma_y,\rho)$ estimés **ensemble par la méthode des moments généralisée** (§9.3) sur
    12 moments des variations quotidiennes : les volatilités annualisées du spread OAT–€STR aux tenors
    5-30 ans (modèle $\sigma_y H_{a_y}(\tau)/\tau$, dont la structure par terme identifie la vitesse de retour
    risque-neutre) et les corrélations spread / swap €STR de même tenor (modèle $\rho$) ; covariance des
    moments par bootstrap par blocs mobiles. Pondération **diagonale** retenue : la pondération efficace
    $S^{-1}$, avec des erreurs de moments très corrélées entre tenors, donne des poids négatifs et un $\rho$
    hors de toutes les corrélations observées (biais d'Altonji et Segal, 1996) ; elle sert au test J de
    Hansen, qui rejette le spread à un facteur. L'estimation en deux temps (vols, puis corrélation au tenor
    20 ans) reste imprimée en comparaison ; historiques 01/2021 → 08/09/2026 ; tenor 2 ans exclu (rupture du
    générique le 22/01/2024) ;
  - la vitesse de retour **historique** (AR(1) du niveau du spread) varie avec la fenêtre par biais de petit
    échantillon ; sa loi est simulée sous une vitesse nulle et elle est corrigée par inférence indirecte :
    compatible avec une vitesse nulle (§9.4) ;
  - méthodes (GMM, biais de petit échantillon, pricing à intensité) tirées du cours de Monfort, Pegoraro et
    Renne, *Econometrics of Commodity and Asset Pricing*, cours 5 (ENSAE 2025-2026),
    `doc/econo modele affine.pdf`.

## 6. Validation

Recalage exact des courbes, dérivées par différences finies, quadratures, parités, cas limites
($\sigma_y \to 0$ ⇒ Black 1F), Jamshidian en 1F, Monte-Carlo exact du vecteur gaussien
$(x(T_0), y(T_0), \int x, \int y)$ sans discrétisation, avec recentrage. La cellule « Chiffres cités » (fin du
§11) imprime chaque chiffre de la lecture des résultats et de la conclusion, formaté comme dans le texte.

## 7. Données (Bloomberg, clôture du 08/09/2026, règlement 10/09/2026)

| Source | Contenu |
|---|---|
| `data/market data bloom.xlsx` — `ESTR CURVE` | 32 taux swap OIS €STR, 1W → 50Y |
| — `Swaption cube` | vols normales ATM EUR, 21 expiries × 14 tenors |
| — `Liste OAT` | 19 titres (5 zéro-coupons courts, 14 OAT 2028 → 2072) |
| — `Zield Histo OAT`, `Yield Histo ESTR` | historiques quotidiens 2, 5, 10, 15, 20, 25, 30 ans depuis 01/2021 |
| `data/repo_fictif.csv` | spread repo contre €STR, tenors 1 semaine → 1 an, **fictif** (structure par terme inventée) |

## 8. Conventions et simplifications

- $t=0$ = 10/09/2026, ACT/365, pas de calendrier ; swaps €STR à jambe fixe annuelle ; OAT à coupon annuel,
  couru ACT/ACT.
- Courbe €STR : bootstrap + spline cubique sur $\log P$. Courbe OAT : Nelson-Siegel-Svensson sur prix dirty,
  pondération par la duration.
- Vols de swaptions supposées cohérentes avec l'actualisation €STR ; rendements génériques de pair utilisés
  comme taux zéro.
- Environnement : Python 3.12 via `uv` (`pyproject.toml`, `uv.lock`).

## 9. Écarts de méthode par rapport à Russo et al.

| Point | Russo et al. | Ce mémoire |
|---|---|---|
| Émetteur | courbes corporate US par notation | souverain France, €STR sans risque |
| Contrat et forward | forward et numéraire issus de la courbe risquée | option vanille collatéralisée €STR, forward repo, strike clean |
| $\bar\Sigma_B$ | intégration numérique | fermée sous poids gelés, poids à leur valeur forward recentrée |
| Contrôle 1F | — | Jamshidian exact |
| Lien avec le crédit | spread issu d'une intensité de défaut et d'une perte | spread modélisé directement, justifié par le recouvrement en valeur de marché (seul le produit perte × intensité est identifié) |
| Calibration du spread | fit de la courbe risquée | GMM sur la structure par terme des vols et les corrélations historiques du spread, pondération diagonale, test J |
| Vitesse de retour historique | — | biais de petit échantillon mesuré par simulation, corrigé par inférence indirecte |
| Validation | Monte-Carlo | Monte-Carlo exact sans discrétisation, IC, erreur par strike et par échéance |
