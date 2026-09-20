# Contexte — Pricer d'options sur OAT sous un modèle gaussien à deux facteurs

Document de cadrage du mémoire. Il fixe l'objectif, le modèle, les notations, les formules de référence,
les écarts assumés par rapport au papier répliqué, les données et les conventions. Le plan de travail
(structure du notebook, étapes, tests) est dans `PLAN.md`.

---

## 1. Objectif

Construire, calibrer et valider un **pricer d'options européennes sur obligations d'État françaises (OAT)**
dans un **modèle gaussien à deux facteurs corrélés** :

- facteur 1 : taux sans risque (Hull-White 1F, courbe €STR) ;
- facteur 2 : spread de crédit souverain (intensité de défaut, Hull-White 1F sur l'intensité).

Le travail réplique **Russo, Giacometti & Fabozzi — *Closed-Form Solution for Defaultable Bond Options under
a Two-Factor Gaussian Model for Risky Rates Modeling*** (draft, `doc/13. Russo et al....pdf`), avec **un écart
central** : chez Russo l'option est **knock-out au défaut** (valeur nulle pour le porteur) ; ici on prix
**l'option sans knock-out**. Cet écart change la mesure de pricing et la formule fermée (§ 5).

Nature du livrable : mémoire de recherche académique. Chaque étape doit être **justifiée, vérifiée et
lisible**, pas optimisée. Un notebook unique, séquentiel, où chaque brique est testée avant d'être utilisée.

---

## 2. Cadre théorique

### 2.1 Taux risqué, intensité, recouvrement (Duffie-Singleton, Lando)

Cadre réduit à intensité, hypothèse *Recovery of Market Value* (RMV) : au défaut, le porteur perd une
fraction $L$ (loss given default) de la valeur de marché de l'obligation juste avant défaut, $RR = 1 - L$.
Le prix d'un zéro-coupon risqué s'écrit alors comme un zéro-coupon sans risque actualisé au **taux risqué**

$$\bar r(t) = r(t) + s(t), \qquad s(t) = L\,\lambda(t),$$

$$\bar P(t,T) = \mathbb E^{\mathbb Q}\Big[e^{-\int_t^T \bar r(u)\,du}\,\Big|\,\mathcal F_t\Big].$$

$\lambda$ est l'intensité de défaut risque-neutre. Remarque importante pour une signature souveraine
(Russo p. 8) : le spread observé contient d'autres primes (liquidité, préférence pour le collatéral, etc.) ;
le modèle gaussien autorise $s(t) < 0$, ce qui n'est pas absurde pour le spread OAT–€STR à court terme.
$\lambda$ n'est donc **pas** une pure intensité de défaut — à écrire clairement dans le mémoire.

### 2.2 Le modèle (Russo éq. 7-15)

$$\bar r(t) = \bar\alpha(t) + x(t) + L\,y(t),$$

$$dx = -a_x\,x\,dt + \sigma_x\,dW_x, \quad x(0)=0, \qquad dy = -a_y\,y\,dt + \sigma_y\,dW_y, \quad y(0)=0,
\qquad dW_x\,dW_y = \rho\,dt.$$

- $r(t) = \alpha(t) + x(t)$ : taux sans risque, HW1F ; $\alpha$ recale la courbe €STR.
- $\lambda(t) = \beta(t) + y(t)$ ; $\bar\alpha = \alpha + L\beta$ recale **directement** la courbe OAT.
- Paramètres : $(a_x, \sigma_x)$ taux, $(a_y, \sigma_y)$ crédit, $\rho$ corrélation, $L$ **input** (pas calibré).
- Seul le produit $L\,\sigma_y$ est identifiable par les prix : $L$ est une convention (40 % pour les CDS
  souverains d'Europe de l'Ouest), qu'on traite en **paramètre de sensibilité**.

### 2.3 Briques gaussiennes (notation unifiée)

Pour un OU de paramètres $(a,\sigma)$, $\tau = T - t$ :

$$H_a(t,T) = \frac{1-e^{-a\tau}}{a}, \qquad
V_a(t,T) = \frac{\sigma^2}{a^2}\Big[\tau - H_a - \tfrac{a}{2}H_a^2\Big]
= \frac{\sigma^2}{a^2}\Big[\tau + \tfrac{2}{a}e^{-a\tau} - \tfrac{1}{2a}e^{-2a\tau} - \tfrac{3}{2a}\Big].$$

$H$ = duration stochastique du zéro-coupon ($-\partial_x \log P = H$), $V = \mathrm{Var}[\int_t^T x\,du\,|\,\mathcal F_t]$.

Terme croisé (Russo éq. 20) :

$$V_{xy}(t,T) = \frac{2 L\rho\,\sigma_x\sigma_y}{a_x a_y}\Big[\tau - H_x - H_y + \frac{1-e^{-(a_x+a_y)\tau}}{a_x+a_y}\Big],
\qquad \bar V(t,T) = V_x + L^2 V_y + V_{xy} = \mathrm{Var}\Big[\int_t^T (x + Ly)\,du\,\Big|\,\mathcal F_t\Big].$$

Moments de $(x(T), y(T))$ conditionnels à $t$ (identiques sous toutes les mesures utilisées, seule la moyenne bouge) :

$$\mathrm{Var}\,x(T) = \sigma_x^2\frac{1-e^{-2a_x\tau}}{2a_x}, \quad
\mathrm{Var}\,y(T) = \sigma_y^2\frac{1-e^{-2a_y\tau}}{2a_y}, \quad
\mathrm{Cov}(x(T),y(T)) = \rho\sigma_x\sigma_y\frac{1-e^{-(a_x+a_y)\tau}}{a_x+a_y}.$$

### 2.4 Recalage des courbes

$$\alpha(t) = f^M(0,t) + \frac{\sigma_x^2}{2a_x^2}\big(1-e^{-a_x t}\big)^2,$$

$$\bar\alpha(t) = \bar f^M(0,t) + \frac{\sigma_x^2}{2a_x^2}\big(1-e^{-a_x t}\big)^2
+ L^2\frac{\sigma_y^2}{2a_y^2}\big(1-e^{-a_y t}\big)^2
+ \frac{L\rho\sigma_x\sigma_y}{a_x a_y}\big(1-e^{-a_x t}\big)\big(1-e^{-a_y t}\big).$$

Équivalent en intégrale (plus stable numériquement, c'est ce qu'on code) :
$\int_0^T \bar\alpha = -\log \bar P^M(0,T) + \tfrac12 \bar V(0,T)$.

### 2.5 Prix des zéro-coupons (Russo éq. 16-24)

$$P(t,T) = \frac{P^M(0,T)}{P^M(0,t)}\exp\Big(-H_x(t,T)\,x(t) + \tfrac12\big[V_x(t,T) - V_x(0,T) + V_x(0,t)\big]\Big),$$

$$\bar P(t,T) = \frac{\bar P^M(0,T)}{\bar P^M(0,t)}\exp\Big(-H_x(t,T)\,x(t) - L\,H_y(t,T)\,y(t)
+ \tfrac12\big[\bar V(t,T) - \bar V(0,T) + \bar V(0,t)\big]\Big).$$

Les deux sont **log-affines** en $(x,y)$ : c'est ce qui rend les options (presque) fermées. On vérifie
numériquement $P(0,T)=P^M(0,T)$, $\bar P(0,T)=\bar P^M(0,T)$ et $-\partial_x\log\bar P = H_x$, $-\partial_y\log\bar P = L H_y$.

### 2.6 Obligation à coupons et durations stochastiques (Russo éq. 28-31)

Flux $K_i$ aux dates $T_i$ (coupon, plus nominal au dernier). $\bar B(t) = \sum_{T_i>t} K_i \bar P(t,T_i)$,

$$D_x(t) = \frac{\sum_i K_i \bar P(t,T_i) H_x(t,T_i)}{\bar B(t)}, \qquad
D_y(t) = \frac{\sum_i K_i \bar P(t,T_i) H_y(t,T_i)}{\bar B(t)}.$$

$D_x, D_y$ dépendent de $(x,y)$ via les poids — c'est **l'unique source d'approximation** du pricer
(« poids gelés » / hypothèse lognormale approchée).

---

## 3. Options : formule de Russo (knock-out)

Prix (éq. 34) : $\mathbb E^{\mathbb Q}\big[e^{-\int_t^{T_0}\bar r}\,(\bar B(T_0)-X)^+\big]$.
L'actualisation au taux **risqué** $\bar r = r + L\lambda$ encode le knock-out : la prime de survie
$e^{-L\int\lambda}$ tue la valeur en cas de défaut. Numéraire naturel = $\bar P(\cdot,T_0)$
(« mesure forward de survie »), sous laquelle le forward $\bar B(t)/\bar P(t,T_0)$ est martingale.
Avec poids gelés en $t$ :

$$\bar\Sigma_B^2 = \bar D_x^2\,\mathrm{Var}\,x(T_0) + L^2 \bar D_y^2\,\mathrm{Var}\,y(T_0)
+ 2L\,\bar D_x\bar D_y\,\mathrm{Cov}(x(T_0),y(T_0)), \qquad
\bar D_\cdot = \sum_{T_i>T_0} w_i\,H_\cdot(T_0,T_i),\quad w_i = \frac{K_i\bar P(t,T_i)}{\sum_j K_j\bar P(t,T_j)}.$$

(Russo écrit $\bar\Sigma_B^2 = \int_t^{T_0}\bar\sigma_B(u)^2du$ et dit qu'une intégration numérique est
nécessaire ; avec les poids gelés $H(u,T_i)-H(u,T_0) = e^{-a(T_0-u)}H(T_0,T_i)$ et l'intégrale est fermée
— on le montre et on garde la quadrature comme contrôle.)

$$C^{KO} = \bar B(t)\,\Phi(d_1) - X\,\bar P(t,T_0)\,\Phi(d_2), \qquad
d_{1,2} = \frac{\log\frac{\bar B(t)}{X\bar P(t,T_0)} \pm \tfrac12\bar\Sigma_B^2}{\bar\Sigma_B}.$$

Ici $\bar B(t)$ ne somme que les flux postérieurs à $T_0$. Put par parité (éq. 59).

---

## 4. Écart assumé : option **sans** knock-out

### 4.1 Définition retenue

$$C = \mathbb E^{\mathbb Q}\Big[e^{-\int_t^{T_0} r(u)\,du}\,\big(\bar B(T_0) - X\big)^+\Big].$$

Actualisation au taux **sans risque** ; payoff sur la valeur de marché (pré-défaut) de l'OAT à $T_0$.
Interprétation : option collatéralisée, dont la contrepartie n'est pas l'émetteur de l'obligation, et dont
le règlement à $T_0$ se fait sur le prix de marché de l'OAT — le porteur de l'option ne perd pas sa prime
si l'émetteur fait défaut pendant la vie de l'option. C'est exactement « Russo sans knock-out, à payoff
inchangé ». On écarte la version « default-protected » de Schönbucher (exercice immédiat au défaut au
prix de recouvrement), qui n'a pas de forme fermée (Russo p. 12) : elle est mentionnée en limite.

### 4.2 Conséquence mathématique

Changement de numéraire vers $P(\cdot,T_0)$ (mesure $T_0$-forward **sans risque** $\mathbb Q^{T_0}$) :

$$C = P(t,T_0)\,\mathbb E^{T_0}\big[(\bar B(T_0)-X)^+\big].$$

Sous $\mathbb Q^{T_0}$, $\bar B(t)/P(t,T_0)$ **n'est pas une martingale** : le prix pré-défaut $\bar B$
a un drift $\bar r = r + s$, pas $r$. L'espérance forward doit être calculée explicitement. Comme
$\bar P(T_0,T_i)$ est log-affine en $(x(T_0),y(T_0))$ gaussien sous $\mathbb Q^{T_0}$, elle est fermée.

Moyennes sous $\mathbb Q^{T_0}$ (décalage de Girsanov par la vol du zéro-coupon sans risque $\sigma_x H_x(u,T_0)$) :

$$\mu_x = x(t)e^{-a_x\tau} - \frac{\sigma_x^2}{2a_x^2}\big(1-e^{-a_x\tau}\big)^2, \qquad
\mu_y = y(t)e^{-a_y\tau} - \frac{\rho\sigma_x\sigma_y}{a_x}\Big[\frac{1-e^{-a_y\tau}}{a_y} - \frac{1-e^{-(a_x+a_y)\tau}}{a_x+a_y}\Big],
\quad \tau = T_0 - t.$$

Espérance forward **exacte** de chaque flux, puis de l'obligation :

$$m_i = \mathbb E^{T_0}[\bar P(T_0,T_i)] = A_i \exp\Big(-H_x^i\mu_x - L H_y^i\mu_y
+ \tfrac12\mathrm{Var}\big(H_x^i x(T_0) + L H_y^i y(T_0)\big)\Big), \qquad
M = \sum_{T_i > T_0} K_i\,m_i,$$

où $A_i$ est la partie déterministe de $\bar P(T_0,T_i)$ et $H^i_\cdot = H_\cdot(T_0,T_i)$.
Variance de $\log\bar B(T_0)$ avec poids gelés : même $\bar\Sigma_B^2$ qu'au § 3.

$$\boxed{C = P(t,T_0)\big[M\,\Phi(d_1) - X\,\Phi(d_2)\big], \qquad
d_{1,2} = \frac{\log(M/X) \pm \tfrac12\bar\Sigma_B^2}{\bar\Sigma_B}}, \qquad
\text{Put} = C - P(t,T_0)\,(M - X).$$

### 4.3 Lecture économique

- $M \ne \bar B(t)/P(t,T_0)$ : le forward « sans risque » du prix risqué contient l'accrétion attendue du
  spread sur $[t,T_0]$ et un terme de covariance taux/spread. On montre $M \to \bar B(t)/\bar P(t,T_0)$-like
  dans les cas limites.
- **Valeur de la protection contre le défaut** $= C - C^{KO}$ : deux effets, numéraire ($P > \bar P$) et
  forward ($M$ vs $\bar B/\bar P$). Attendu $\ge 0$, à vérifier par Monte-Carlo.
- Cas limites de contrôle : $L \to 0$ ⇒ HW1F pur ; $\sigma_y \to 0$ ⇒ spread déterministe,
  $C = P(t,T_0)\,\mathbb E^{T_0}[(\text{HW1F})^+]$ avec spread additif ; $\rho$ modifie $\mu_y$ et le terme croisé.

---

## 5. Calibration

### 5.1 Étape 1 — taux : $(a_x,\sigma_x)$ sur swaptions ATM (Russo éq. 53-55, Russo & Torri 2018, cours)

- Instruments : swaptions EUR ATM, vols **normales** (Bachelier) Bloomberg. Prix ATM en Bachelier :
  $A\,\sigma_N\sqrt{T_0/2\pi}$, $A$ = annuité.
- Prix modèle : swaption payeuse = put sur l'obligation « jambe fixe + nominal » de strike 1, sous HW1F.
  **Deux méthodes** : (i) approximation duration stochastique / poids gelés (Russo & Fabozzi 2016 — celle
  qu'on sera obligés d'utiliser en 2F), (ii) **Jamshidian, exact en 1F** — sert de contrôle et quantifie
  l'erreur de (i) selon expiry/tenor.
- Objectif : racine de la somme des erreurs relatives au carré (éq. 55). L-BFGS-B bornée, multi-départs.
- Jeu : surface complète (diagnostic de la limite structurelle du 1F) **et** diagonale co-terminale
  $T_0 + n = T^\star$ (Russo ; argument de couverture du cours), $T^\star$ = maturité de l'OAT sous-jacente.
  Les paramètres retenus pour le pricing sont ceux de la diagonale.

### 5.2 Étape 2 — crédit : $(a_y,\sigma_y,\rho)$

**(a) Réplication Russo (éq. 56-57).** Fit de la courbe ZC risquée par $\bar P^\ast(0,T_i) = e^{-\int_0^{T_i}\bar\alpha}$
sur une grille de $\rho \in \{-1,\dots,1\}$, $(a_y,\sigma_y)$ optimisés à chaque nœud, on garde le RMSE minimal.

**Critique à démontrer numériquement.** $\bar\alpha$ recale la courbe risquée *par construction* :
$\bar P^\ast(0,T) = \bar P^M(0,T)\,e^{-\frac12\bar V(0,T)}$ exactement. L'erreur à minimiser est donc
$|e^{-\frac12\bar V(0,T)} - 1|$ : l'étape 2 de Russo **minimise la convexité totale** $\bar V = V_x + L^2V_y + V_{xy}$
de la courbe risquée. $V_x$ étant fixé par l'étape 1, l'optimum pousse vers $\rho < 0$ pour que le terme croisé
compense $V_x$ — ce qui est cohérent avec les $\rho$ négatifs des bons ratings dans les Exhibits 3-4. Ce n'est
pas de l'information sur la volatilité du spread. On trace le profil du RMSE (plat en $(a_y,\sigma_y)$,
dégénéré en $\rho$) et on conclut à la non-identification. (L'éq. 57 du draft, $\exp\{-\sum_j T_j\bar\alpha(T_j)/T_i\}$,
est de plus dimensionnellement douteuse — on l'implémente telle quelle et telle qu'elle devrait être.)

**(b) Calibration historique (retenue).** Séries quotidiennes (≥ 3 ans) du spread OAT–swap €STR à un ou
plusieurs tenors $\tau$. Dans le modèle, le spread de taux ZC à tenor $\tau$ vaut
$s_\tau(t) = \text{déterministe} + L\,y(t)\,H_y(\tau)/\tau$ : c'est un OU de vitesse $a_y$ et de vol
$L\sigma_y H_y(\tau)/\tau$. Estimation :
  - $a_y$ par régression AR(1) de $s_\tau$ (ou MLE OU), avec l'avertissement **mesure historique ≠ risque-neutre**
    pour la vitesse de retour (la vol est invariante par Girsanov, pas le drift) ;
  - $L\sigma_y$ par la vol des variations quotidiennes, désannualisée, corrigée du facteur $H_y(\tau)/\tau$ ;
  - $\rho$ par la corrélation des variations quotidiennes du swap €STR de même tenor (proxy de $x$) et du spread ;
  - $L = 40\,\%$ fixé (convention CDS souverain Europe de l'Ouest) → $\sigma_y$.
  - Robustesse : plusieurs tenors, plusieurs fenêtres, comparaison avec (a).

### 5.3 Ce qui n'est pas calibré et pourquoi

Pas de marché liquide d'options sur OAT cash ; les options sur **future OAT** (Euronext) existent mais
mêlent option de livraison / CTD — traitées en extension comme **point de comparaison** de la vol totale,
pas comme instrument de calibration.

---

## 6. Validation

1. Tests unitaires de chaque brique (limites $a\to0$, dérivées par différences finies, recalage exact des courbes).
2. HW1F : approximation poids gelés vs **Jamshidian exact** sur toute la surface.
3. 2F : **Monte-Carlo exact** — le vecteur $(x(T_0), y(T_0), \int_t^{T_0}x, \int_t^{T_0}y)$ est gaussien à
   covariance connue ⇒ simulation sans discrétisation ; $\bar P(T_0,T_i)$ fermé ⇒ payoff exact.
   Mêmes trajectoires pour KO (actualisation $e^{-\int\bar r}$) et non-KO ($e^{-\int r}$).
   Mesure l'erreur de l'hypothèse lognormale (par strike : « smile » implicite du modèle) et vérifie $C - C^{KO} \ge 0$.
   Euler fin en second contrôle.
4. Parités call-put (éq. 58-59 pour KO, § 4.2 pour non-KO), cas limites $L\to0$, $\sigma_y\to0$.

---

## 7. Données (Bloomberg, toutes au **08/09/2026**, même heure de clôture)

Déjà dans `data/market data bloom.xlsx` :

| Feuille | Contenu | Usage |
|---|---|---|
| `Worksheet` | Courbe swaps OIS €STR, 33 piliers 1W→50Y, taux en % (`EESWE* BGN Curncy`) | $P^M(0,T)$, $f^M(0,t)$ |
| `Sheet1` | Vols normales ATM swaptions EUR, 22 expiries (1Mo→30Yr) × 14 tenors (1Yr→30Yr), en bp | Étape 1 |

À vérifier : le cube de vols est-il €STR-based ou Euribor 6M-based (Bloomberg VCUB propose les deux) ?
Pour la cohérence avec la courbe d'actualisation, préférer €STR ; sinon documenter la petite base.

À exporter (voir liste précise dans `PLAN.md` § 0) :

1. **OAT nominales** : ISIN, coupon, maturité, prix clean/dirty, rendement — ~15-25 lignes, hors OATi/OAT€i et strips.
2. **Courbe ZC souveraine France Bloomberg** (contrôle du bootstrap).
3. **Historique quotidien** 2021→2026 : rendements OAT 2Y/5Y/10Y/30Y (`GTFRF*Y Govt`) et swaps €STR de mêmes tenors.
4. **CDS France 5Y** (contrôle de l'ordre de grandeur de $L\lambda$) — optionnel.
5. **Options sur future OAT** (`OATA Comdty`) : vols implicites ATM — optionnel, extension.

---

## 8. Conventions et simplifications assumées

- Date de valorisation $t=0$ = 08/09/2026 ; temps en années, fractions d'année simplifiées (ACT/365 ou
  jour/365 par rapport à la date de valorisation), pas de calendrier de jours ouvrés. À dire explicitement.
- Swaps €STR : jambe fixe annuelle, jambe variable au pair ; en dessous de 1 an, un seul flux. Pas de
  convention ACT/360 fine.
- Courbe : bootstrap pilier par pilier, interpolation à choisir sur critère de **régularité du forward**
  (spline cubique sur taux ZC vs spline sur $\log P$ vs monotone) — la courbe €STR est inversée au-delà
  de 20Y, ce qui rend $f^M$ sensible au choix. Décision prise à l'étape 2 du plan, argumentée.
- Sous-jacent : une OAT benchmark réelle (prix clean → dirty pour le payoff ; le strike d'une option sur
  obligation est conventionnellement clean, on documente le choix), plus des obligations génériques pour
  les grilles de sensibilités.
- Constante $\sigma_x$ (Russo). Extension possible : $\sigma_x(t)$ constante par morceaux calibrée par
  bootstrap sur la diagonale (cours § 6.3.7).
- Paramètres toujours passés explicitement aux fonctions (pas de variables globales mutées).
- Environnement : Python 3.12 via `uv` (le `.venv` existant vient de macOS et est inutilisable sous Windows).

---

## 9. Résumé des écarts par rapport à Russo et al.

| Point | Russo et al. | Ce mémoire |
|---|---|---|
| Émetteur | Courbes corporate US par rating | Souverain France (OAT), €STR sans risque |
| Knock-out | Oui (numéraire $\bar P$) | **Non** (numéraire $P$, forward $M$ recalculé) |
| $\bar\Sigma_B$ | Intégration numérique | Fermée sous poids gelés (+ quadrature en contrôle) |
| Contrôle 1F | Aucun | Jamshidian exact |
| Étape 2 | Fit courbe ZC risquée, grille $\rho$ | Répliquée **et** critiquée ; calibration historique retenue |
| Validation | MC 25 000 trajectoires, écart < 2 % | MC exact (sans discrétisation), IC, erreur par strike |
