# Product Requirements Document (PRD)

**Project Name:** BondOptionPricer — options européennes sur OAT sous un modèle gaussien à deux facteurs
**Version:** 1.0
**Date:** 2026-10-01
**Author:** l'auteur du mémoire, rédigé avec Claude Code (workflow `bmad-prd`) (PM)
**Status:** brouillon à valider par l'auteur
**Track:** BMad Method

> Source de vérité pour le *quoi* et le *pourquoi* ; le *comment* relève du document d'architecture.
> Le cadrage détaillé (modèle, formules, conventions) est dans [`CONTEXTE.md`](../CONTEXTE.md) et n'est pas
> recopié ici. Débordements et questions ouvertes : `addendum.md`. Décisions : `decision-log.md`.
> Les titres de section restent en anglais : les skills BMAD et le validateur les cherchent sous ce nom.

---

## Executive Summary — Synthèse

**Problem Statement :** le mémoire price des options vanilles collatéralisées sur l'OAT 4,10 % 2046 dont le
prix, aux échéances longues, dépend d'abord du forward, donc de l'hypothèse de financement en repo. Or la
courbe repo utilisée est **fictive** (€STR + 5 bp à tous les tenors), et les chiffres cités dans la lecture des
résultats (§11) et la conclusion (§12) sont **écrits en dur** : ils ne suivent pas les sorties du notebook.
Tant que ces deux points restent ouverts, les résultats ne sont pas défendables devant le jury.

**Proposed Solution :** brancher une courbe repo de marché au format existant, fixer et documenter
l'hypothèse de financement au-delà d'un an, puis rendre chaque chiffre cité dans le texte traçable à une
sortie imprimée du notebook et réécrire §11-12 sur ces sorties. En parallèle, fiabiliser l'estimation du
facteur spread : correction du biais de petit échantillon de la vitesse AR(1), estimation conjointe de
$(a_y, \sigma_y, \rho)$ par la méthode des moments généralisée, ancrage théorique du spread dans le cadre
crédit à intensité (cours de Monfort, Pegoraro et Renne, `doc/econo modele affine.pdf`).

**Business Value :** un mémoire dont chaque prix repose sur des données de marché identifiées et dont chaque
affirmation chiffrée se vérifie en ré-exécutant le notebook.

**Target Outcome :** le notebook `main/oat_option_pricer.ipynb` s'exécute de bout en bout depuis un noyau
neuf, tous ses contrôles passent, la courbe repo est une courbe de marché datée du 08/09/2026, et 100 % des
chiffres cités en §11-12 correspondent aux sorties à l'arrondi affiché près.

---

## Project Overview — Vue d'ensemble

### Background — Contexte
Mémoire de recherche (MS FGDR) : reconstruction, calibration et validation du modèle gaussien à deux
facteurs corrélés de Russo, Giacometti & Fabozzi sur données françaises — Hull-White 1F sur la courbe €STR
(facteur taux), Hull-White 1F sur le spread court OAT–€STR (facteur spread). Le contrat est celui d'un desk
de banque d'investissement : call / put européen sur l'OAT, strike clean en % du forward clean, forward
cash-and-carry au taux €STR + spread repo, actualisation €STR. Projet **brownfield** : les 12 sections du
notebook sont écrites et exécutées (voir `PLAN.md`).

### Current State → Desired State — Existant → cible
- **Existant :** chaîne complète données → courbes → modèle → calibration → pricer fermé → Monte-Carlo →
  résultats, validée par des contrôles numériques ; courbe repo fictive signalée comme telle ; §11-12
  rédigés sur les sorties obtenues avec cette courbe fictive.
- **Cible :** même chaîne sur une courbe repo de marché, hypothèse de financement long terme explicite,
  texte de §11-12 aligné et vérifiable sur les sorties, `CONTEXTE.md` et `PLAN.md` à jour.

### Stakeholders — Parties prenantes
| Stakeholder | Role | Interest | Influence |
|-------------|------|----------|-----------|
| Auteur du mémoire | décide, rédige, soutient | résultats défendables, code qu'il maîtrise | décisionnaire unique |
| Jury du mémoire | évalue | justification de chaque étape, contrôles visibles, cohérence texte / chiffres | évalue le livrable |
| Claude Code | implémente les stories `ready-for-dev` | stories autonomes, critères vérifiables | exécutant |

---

## Goals and Objectives — Objectifs

### Business Goals — Objectifs du mémoire
1. **G1 — Prix ancrés sur le marché :** chaque prix d'option repose sur des courbes recalées et un forward
   issu d'une courbe repo de marché identifiée (source, date).
2. **G2 — Rigueur vérifiable :** chaque brique du pricer est contrôlée par une sortie numérique (recalage,
   parité, cas limite, Jamshidian, Monte-Carlo).
3. **G3 — Lisibilité académique :** chaque étape est justifiée dans un markdown, au format du cours, avec un
   code que l'auteur peut expliquer ligne à ligne.
4. **G4 — Reproductibilité :** les chiffres du texte se retrouvent en ré-exécutant le notebook.

### User Goals — Objectifs des lecteurs
1. **Jury :** suivre le raisonnement section par section et vérifier chaque affirmation chiffrée sur une
   sortie du notebook.
2. **Auteur :** défendre chaque hypothèse — en particulier celle de financement — par un markdown et une
   sensibilité chiffrée.

---

## Functional Requirements — Exigences fonctionnelles

> Format : `FR-### : PRIORITÉ — capacité`. Les FR-001 à FR-012 décrivent l'existant (statut **fait**) : elles
> servent de contrat de non-régression pour les travaux qui suivent. Les identifiants sont immuables.

### FR-001: Données de marché figées au 08/09/2026 — MUST
**Description :** le notebook charge les données Bloomberg de clôture du 08/09/2026 (courbe OIS €STR, cube
de swaptions ATM, liste des OAT, historiques de rendements) et coupe les historiques à cette date.
**Critères d'acceptation (Acceptance Criteria) :**
- Les 32 taux OIS €STR, le cube 21 expiries × 14 tenors et les 19 titres OAT sont chargés et affichés.
- Aucune observation historique n'est postérieure au 08/09/2026.
- $t = 0$ est le règlement du 10/09/2026 dans toutes les sections.
**Related Epic:** EPIC-001 — **Statut :** fait

### FR-002: Courbe €STR recalée sur les swaps OIS — MUST
**Description :** une courbe d'actualisation sans risque est construite par bootstrap des swaps OIS €STR.
**Critères d'acceptation (Acceptance Criteria) :**
- Les swaps OIS cotés sont repricés au pair par la courbe ; l'écart maximal est imprimé.
- Les facteurs d'actualisation sont définis et décroissants de 0 à 50 ans.
**Related Epic:** EPIC-001 — **Statut :** fait

### FR-003: Courbe OAT et sous-jacent OAT 2046 — MUST
**Description :** une courbe zéro-coupon OAT est ajustée sur les prix dirty des OAT cotées ; l'OAT 4,10 %
25/05/2046 est valorisée et son coupon couru est calculable à une date future.
**Critères d'acceptation (Acceptance Criteria) :**
- L'erreur de prix par titre de l'ajustement est imprimée.
- Le prix dirty modèle de l'OAT 2046 à $t=0$ est imprimé à côté de son prix de marché.
- Le coupon couru à chaque échéance d'option (1 à 15 ans) est imprimé.
**Related Epic:** EPIC-001 — **Statut :** fait

### FR-004: Pricer Hull-White 1F et contrôle de Jamshidian — MUST
**Description :** le modèle 1F price zéro-coupons, options sur obligation à coupons et swaptions ; la
formule utilisée par le pricer 2F est contrôlée par la décomposition exacte de Jamshidian en 1F.
**Critères d'acceptation (Acceptance Criteria) :**
- Le modèle 1F recale exactement la courbe €STR (écart imprimé).
- L'écart entre l'option 1F du pricer et Jamshidian est imprimé pour l'OAT 2046.
**Related Epic:** EPIC-002 — **Statut :** fait

### FR-005: Calibration du facteur taux sur la diagonale co-terminale 20 ans — MUST
**Description :** $(a_x, \sigma_x)$ sont calibrés conjointement sur les swaptions ATM dont expiry + tenor =
20 ans, expiries 1 à 15 ans, tenors non cotés interpolés en volatilité normale.
**Critères d'acceptation (Acceptance Criteria) :**
- Les paramètres retenus et l'erreur de vol par expiry sont imprimés.
- L'erreur sur la surface complète est imprimée en diagnostic.
**Related Epic:** EPIC-002 — **Statut :** fait

### FR-006: Modèle à deux facteurs recalé sur la courbe OAT — MUST
**Description :** le modèle 2F (taux + spread corrélés) recale exactement la courbe OAT à $t=0$.
**Critères d'acceptation (Acceptance Criteria) :**
- L'écart entre zéro-coupons risqués du modèle et de la courbe OAT est imprimé.
- Les durations stochastiques $D_x, D_y$ de l'OAT 2046 sont contrôlées par différences finies.
**Related Epic:** EPIC-002 — **Statut :** fait

### FR-007: Calibration du facteur spread — MUST
**Description :** $(a_y, \sigma_y)$ sont estimés sur la structure par terme des volatilités historiques du
spread OAT–€STR (tenors 5-30 ans), $\rho$ sur la corrélation des variations quotidiennes au tenor 20 ans ;
le notebook montre que la calibration sur la courbe OAT n'identifie pas ces paramètres.
**Critères d'acceptation (Acceptance Criteria) :**
- La démonstration de non-identification est chiffrée (solution $\rho=-1$, $a_y=a_x$, $\sigma_y=\sigma_x$).
- Les paramètres retenus, leur fenêtre (01/2021 → 08/09/2026) et l'exclusion du tenor 2 ans sont imprimés.
- La fourchette historique de $\rho$ selon le tenor et la fenêtre est imprimée.
**Related Epic:** EPIC-002 — **Statut :** fait

### FR-008: Forward repo par cash-and-carry — MUST
**Description :** le forward dirty de l'OAT 2046 à chaque échéance est calculé par cash-and-carry au taux
€STR + spread repo, à partir d'une courbe de spread repo lue dans un fichier de données.
**Critères d'acceptation (Acceptance Criteria) :**
- Les forwards dirty, coupon couru et forward clean sont imprimés pour 1, 2, 5, 7, 10, 12 et 15 ans.
- Avec un spread repo nul et $\sigma_y = 0$, le forward égale l'espérance forward du modèle (écart < 1e-10).
**Related Epic:** EPIC-003 — **Statut :** fait

### FR-009: Recentrage du modèle sur le forward repo — MUST
**Description :** la moyenne de $y(T_0)$ est décalée d'une constante $\delta$ pour que l'espérance forward du
prix de l'OAT égale le forward repo.
**Critères d'acceptation (Acceptance Criteria) :**
- $\delta$ est imprimé par échéance, en bp.
- L'écart $E[\bar B]$ recentré $- F$ est inférieur à 1e-10 à toutes les échéances.
**Related Epic:** EPIC-003 — **Statut :** fait

### FR-010: Formule fermée call / put à strike clean — MUST
**Description :** le pricer donne le prix d'un call et d'un put européens de strike clean exprimé en % du
forward clean (Black sur le forward repo, volatilité $\bar\Sigma_B$, poids gelés à leur valeur forward recentrée).
**Critères d'acceptation (Acceptance Criteria) :**
- La parité $C - P = P(0,T_0)(F^{clean} - K)$ tient à 1e-8 près pour K = 90, 100 et 110 %.
- Avec $\sigma_y \to 0$, le call à la monnaie égale le Black 1F de la section 5 à 1e-8 près.
- Quand $T_0 \to 0$, le call tend vers sa valeur intrinsèque actualisée (écart < 1e-6).
**Related Epic:** EPIC-003 — **Statut :** fait

### FR-011: Validation par Monte-Carlo exact recentré — MUST
**Description :** un Monte-Carlo exact du vecteur gaussien $(x(T_0), y(T_0), \int x, \int y)$, sans
discrétisation et avec recentrage, valide la formule fermée.
**Critères d'acceptation (Acceptance Criteria) :**
- Prix Monte-Carlo, intervalle de confiance et écart à la formule fermée imprimés par strike et échéance.
- À la monnaie, l'écart reste dans l'intervalle de confiance à toutes les échéances.
- La graine est fixée : deux exécutions donnent les mêmes chiffres.
**Related Epic:** EPIC-003 — **Statut :** fait

### FR-012: Résultats et sensibilités — MUST
**Description :** le notebook produit le prix à la monnaie par échéance et ses sensibilités au spread repo,
à $\sigma_y$, à $\rho$ et à $a_y$, ainsi que la décomposition de la variance de $\bar\Sigma_B$.
**Critères d'acceptation (Acceptance Criteria) :**
- Les tableaux de résultats couvrent les 7 échéances.
- La sensibilité au repo couvre au moins −25 / +15 bp et un financement au taux de l'OAT.
**Related Epic:** EPIC-004 — **Statut :** fait

### FR-013: Courbe repo de marché — MUST
**Description :** le forward est calculé sur une courbe de spread repo de marché (OAT contre €STR) à la date
du 08/09/2026, fournie par l'auteur au format existant `Tenor,Spread_bp`.
**Critères d'acceptation (Acceptance Criteria) :**
- Remplacer la courbe ne demande de modifier qu'un fichier de données et, au plus, son chemin à un seul
  endroit du notebook.
- La source et la date de la courbe sont citées dans le markdown de la section 1.
- Les sorties de la section 8 affichent la courbe utilisée et ne portent plus la mention « fictif ».
- Tous les contrôles des sections 8 et 10 passent sur la nouvelle courbe.
**Related Epic:** EPIC-005

### FR-014: Hypothèse de financement au-delà du dernier tenor liquide — MUST
**Description :** le notebook énonce et justifie l'hypothèse de financement retenue au-delà d'un an (là où
le repo à terme n'est plus liquide) et l'applique explicitement dans le calcul du forward.
**Critères d'acceptation (Acceptance Criteria) :**
- Le markdown de la section 8.2 énonce l'hypothèse (règle d'extrapolation du spread au-delà du dernier
  tenor coté) et sa justification.
- Le spread effectivement utilisé à chaque échéance d'option (1 à 15 ans) est imprimé.
- La sensibilité de FR-012 reste présentée autour de cette hypothèse.
**Related Epic:** EPIC-005

### FR-015: Chiffres cités traçables aux sorties — MUST
**Description :** chaque chiffre cité dans la lecture des résultats (§11) et la conclusion (§12) se retrouve
dans une sortie imprimée du notebook.
**Critères d'acceptation (Acceptance Criteria) :**
- Une sortie récapitule, avec un libellé, chaque chiffre cité en §11-12.
- Pour chaque chiffre du texte, la valeur de la sortie arrondie comme dans le texte est identique.
- Un chiffre qui ne peut pas être produit par le notebook est retiré du texte.
**Related Epic:** EPIC-006

### FR-016: Lecture des résultats et conclusion à jour — MUST
**Description :** §11 « Lecture des résultats » et §12 « Conclusion et limites » sont réécrits sur les sorties
obtenues avec la courbe repo de marché.
**Critères d'acceptation (Acceptance Criteria) :**
- Les conclusions qualitatives (profil par échéance, poids du facteur spread, rôle du financement) sont
  revérifiées et corrigées si les nouvelles sorties les contredisent.
- La limite « courbe repo fictive » est remplacée par la limite de l'hypothèse de FR-014.
- La perspective « remplacer la courbe repo fictive » est retirée.
**Related Epic:** EPIC-006

### FR-017: Documents de cadrage à jour — SHOULD
**Description :** `CONTEXTE.md` et `PLAN.md` décrivent l'état final (courbe repo, hypothèse de financement,
reste à faire).
**Critères d'acceptation (Acceptance Criteria) :**
- `CONTEXTE.md` §2 et §7 ne mentionnent plus de courbe fictive et citent la source repo.
- `CONTEXTE.md` §5 et §9 décrivent l'estimateur GMM retenu pour le facteur spread et la correction du
  biais de la vitesse historique.
- `PLAN.md` « Reste à faire » ne liste que les travaux réellement ouverts.
**Related Epic:** EPIC-006

### FR-018: Volatilité du facteur taux constante par morceaux — WON'T (cette version)
**Description :** $\sigma_x(t)$ constante par morceaux, calibrée par bootstrap sur la diagonale co-terminale
20 ans. Abandonnée : pour une option européenne, seule compte la variance intégrée jusqu'à $T_0$ ;
$\sigma_x(t)$ revient à recaler $\sigma_x$ échéance par échéance, et l'effet est borné par les résidus de la
diagonale (2,3 bp de vol au plus, moins de 3 % sur le call à la monnaie).
**Critères d'acceptation (Acceptance Criteria) :**
- Sans objet ; la limite correspondante est rédigée en §12 (STORY-007).
**Related Epic:** EPIC-007 (abandonné)

### FR-019: Second facteur de spread — WON'T (cette version)
**Description :** un second facteur de spread pour reproduire la volatilité plus élevée du court terme.
**Critères d'acceptation (Acceptance Criteria) :**
- Sans objet dans cette version : reste une perspective de §12.
**Related Epic:** — (voir Out of Scope)

---

### FR-020: Vitesse de retour historique corrigée du biais de petit échantillon — SHOULD
**Description :** la vitesse de retour historique du spread (AR(1) sur le niveau, §9.2) est présentée avec
son biais de petit échantillon et une version corrigée, pour montrer que sa variation selon la fenêtre
vient du biais (« persistence problem », Monfort-Pegoraro-Renne, slides 46-55) et non de la dynamique.
**Critères d'acceptation (Acceptance Criteria) :**
- Pour chaque fenêtre (2021-2026, 3 ans, 1 an), le notebook imprime la vitesse AR(1) estimée, la
  distribution de cet estimateur sous une vitesse nulle simulée sur la même longueur (moyenne, 5 % et
  95 %) et le rang de la valeur observée dans cette distribution.
- Une vitesse corrigée du biais (inférence indirecte ou bootstrap) est imprimée par fenêtre.
- Le markdown du §9.2 conclut sur la compatibilité de la vitesse historique avec $a_y \approx 0$ et
  rappelle qu'elle n'entre pas dans le pricing.
- Graine fixée : deux exécutions donnent les mêmes chiffres.
**Related Epic:** EPIC-008

### FR-021: Estimation conjointe de $(a_y, \sigma_y, \rho)$ par GMM — SHOULD
**Description :** $(a_y, \sigma_y, \rho)$ sont estimés ensemble par la méthode des moments généralisée sur
les moments d'ordre 2 des variations quotidiennes : volatilités du spread aux tenors 5 à 30 ans (modèle :
$\sigma_y H_{a_y}(\tau)/\tau$) et corrélations spread / swap €STR de même tenor (modèle : $\rho$ à tous les
tenors). Cet estimateur devient l'estimateur retenu du facteur spread ; l'estimation en deux temps actuelle
est imprimée en comparaison.
**Critères d'acceptation (Acceptance Criteria) :**
- Les estimations, leurs écarts-types et la fenêtre (01/2021 → 08/09/2026) sont imprimés.
- La statistique de sur-identification (J de Hansen) et sa p-value sont imprimées et commentées, y compris
  si elles rejettent la structure à un facteur.
- Les moments ajustés et observés sont imprimés côte à côte, par tenor.
- Le traitement de $a_y$ à sa borne inférieure est explicite (écart-type non standard signalé).
- Les sections 10 et 11 utilisent les paramètres GMM ; tous les contrôles (NFR-002) passent.
**Related Epic:** EPIC-008

### FR-022: Ancrage théorique et interprétation du facteur spread — SHOULD
**Description :** le texte relie le taux OAT $\bar r = r + y$ au cadre crédit à intensité et interprète $y$.
**Critères d'acceptation (Acceptance Criteria) :**
- Le markdown du §7 montre qu'en convention de recouvrement en valeur de marché (RMV, Duffie-Singleton ;
  Monfort-Pegoraro-Renne, Prop. II.1-II.2) le prix d'un zéro-coupon risqué est la formule sans risque au
  taux $r + \tilde\lambda$, d'où $\bar r = r + y$ ; seul le produit perte × intensité est identifié par les
  prix, ce qui justifie de modéliser directement le spread, sans paramètre de perte séparé.
- Le markdown du §9.2 relie l'invariance des volatilités et corrélations par changement de mesure au
  résultat du cours (intensité identique sous P et Q si le défaut n'est pas pricé, dynamiques différentes).
- Le markdown du §9 indique que le spread OAT–€STR mêle crédit, liquidité et effets d'offre (Monfort-Renne,
  2014) et que le pricing n'a besoin que du total.
- Aucun paramètre de perte (L) n'est introduit dans le modèle ni dans les sorties (NFR-005).
**Related Epic:** EPIC-008

---

## Non-Functional Requirements — Exigences non fonctionnelles

### NFR-001: Exécution complète depuis un noyau neuf — MUST (Reliability)
**Description :** le notebook s'exécute de la première à la dernière cellule sans erreur, dans l'ordre.
**Acceptance / Threshold :** 0 erreur ; compteurs d'exécution séquentiels de 1 au nombre de cellules de code.
**Measurement Method :** exécution par `nbconvert --execute` dans l'environnement `uv`, puis lecture des
compteurs d'exécution.

### NFR-002: Contrôles numériques respectés — MUST (Reliability)
**Description :** tous les contrôles imprimés respectent leur seuil après chaque changement.
**Acceptance / Threshold :** parités et cas limites ≤ 1e-8 ; recentrage ≤ 1e-10 ; écart à la monnaie
formule / Monte-Carlo dans l'intervalle de confiance à toutes les échéances.
**Measurement Method :** lecture des sorties des cellules de contrôles (sections 2 à 10).

### NFR-003: Reproductibilité — MUST (Reliability)
**Description :** deux exécutions complètes donnent les mêmes chiffres.
**Acceptance / Threshold :** sorties identiques entre deux exécutions ; dépendances figées par `uv.lock`.
**Measurement Method :** deux exécutions successives, comparaison des sorties texte.

### NFR-004: Format académique du notebook — MUST (Maintainability)
**Description :** un seul notebook, en français, au format du colab « Hull & White 1F » de `doc/`.
**Acceptance / Threshold :** chaque section = un markdown (théorie, justification) → une cellule
bibliothèque (docstring, petite classe ou fonctions) → une cellule d'exécution qui imprime ses contrôles ;
aucun package Python, test pytest ou document LaTeX ajouté ; aucune dépendance hors `pyproject.toml`
actuel ; `main/main.ipynb` inchangé.
**Measurement Method :** revue de la structure des cellules ; `git diff` sur `pyproject.toml` et
`main/main.ipynb`.

### NFR-005: Cadrage éditorial — MUST (Usability)
**Description :** le texte respecte les choix de cadrage du mémoire.
**Acceptance / Threshold :** 0 occurrence de « knock-out » ; 0 chiffre tiré du papier de Russo et al. ;
0 comparaison à des options cotées.
**Measurement Method :** recherche plein texte dans le notebook, `CONTEXTE.md` et `PLAN.md`.

### NFR-006: Remplaçabilité des données — MUST (Maintainability)
**Description :** une donnée de marché se remplace sans toucher à la logique du pricer.
**Acceptance / Threshold :** remplacer la courbe repo = 1 fichier de données modifié, 0 ligne de logique
modifiée.
**Measurement Method :** `git diff` du changement de courbe.

### NFR-007: Durée d'exécution — SHOULD (Performance)
**Description :** le notebook reste ré-exécutable pendant la rédaction.
**Acceptance / Threshold :** exécution complète ≤ 10 minutes sur le poste de l'auteur ; aucun ajout ne
l'allonge de plus de 50 %.
**Measurement Method :** chronométrage de l'exécution `nbconvert` avant et après chaque epic.

### NFR-008: Confidentialité des données — SHOULD (Security)
**Description :** les données Bloomberg et la courbe repo ne sont pas diffusées au-delà de ce que la
licence permet.
**Acceptance / Threshold :** dépôt distant privé, ou données de marché exclues du suivi git.
**Measurement Method :** visibilité du dépôt GitHub et contenu de `git ls-files data/`.

---

## Epics and User Stories (Outline) — Epics et stories

> Esquisse. Les fichiers de stories `ready-for-dev` seront compilés par `bmad-epics-and-stories`. Pas de
> points ni d'estimation : livraison comptée en nombre de stories. EPIC-001 à EPIC-004 décrivent l'existant
> et n'ont pas de story à produire.

### EPIC-001: Données et courbes — fait
**Business Value :** socle de marché de tout le pricer. **User Segments :** jury.
**Related Requirements :** FR-001, FR-002, FR-003

### EPIC-002: Modèle et calibration — fait
**Business Value :** dynamique des taux et du spread calibrée et justifiée. **User Segments :** jury.
**Related Requirements :** FR-004, FR-005, FR-006, FR-007

### EPIC-003: Pricer de l'option vanille — fait
**Business Value :** prix fermé validé par Jamshidian et Monte-Carlo. **User Segments :** jury, auteur.
**Related Requirements :** FR-008, FR-009, FR-010, FR-011

### EPIC-004: Résultats et sensibilités — fait (chiffres à revoir via EPIC-006)
**Business Value :** lecture économique des prix. **User Segments :** jury.
**Related Requirements :** FR-012

### EPIC-005: Courbe repo de marché
**Business Value :** ancrer le forward — premier déterminant du prix aux longues échéances — sur le marché.
**User Segments :** auteur, jury.
**Related Requirements :** FR-013, FR-014, NFR-006

**User Stories (sketch) :**
- **STORY-001 :** En tant qu'auteur, je veux brancher la courbe repo de marché en remplaçant un seul fichier,
  afin que le forward repose sur le marché sans toucher au pricer.
  - Étant donné la courbe de marché au format `Tenor,Spread_bp`, quand le notebook est ré-exécuté, alors
    les sorties de la section 8 affichent cette courbe et tous les contrôles passent.
- **STORY-002 :** En tant qu'auteur, je veux énoncer et appliquer l'hypothèse de financement au-delà du
  dernier tenor liquide, afin de pouvoir la défendre devant le jury.
  - Étant donné l'hypothèse choisie, quand la section 8 s'exécute, alors le spread utilisé à chaque
    échéance d'option est imprimé et le markdown 8.2 la justifie.
- **STORY-003 :** En tant que membre du jury, je veux que plus aucune mention de courbe fictive ne subsiste,
  afin de savoir que les prix reposent sur des données de marché.
  - Étant donné le notebook ré-exécuté, quand je cherche « fictif », alors aucune occurrence ne décrit la
    courbe utilisée.

### EPIC-006: Cohérence du texte avec les sorties
**Business Value :** chaque affirmation chiffrée du mémoire est vérifiable. **User Segments :** jury.
**Related Requirements :** FR-015, FR-016, FR-017, NFR-001, NFR-002, NFR-003

**User Stories (sketch) :**
- **STORY-004 :** En tant qu'auteur, je veux une exécution de référence avant tout changement, afin de
  mesurer ce que la courbe de marché déplace.
  - Étant donné le notebook actuel, quand il est ré-exécuté, alors ses sorties sont conservées comme
    référence et sa durée d'exécution est notée.
- **STORY-005 :** En tant que membre du jury, je veux retrouver chaque chiffre de §11-12 dans une sortie
  libellée, afin de le vérifier sans refaire le calcul.
  - Étant donné la lecture des résultats, quand je prends un chiffre cité, alors une sortie l'imprime avec
    la même valeur arrondie.
- **STORY-006 :** En tant qu'auteur, je veux une lecture des résultats (§11) réécrite sur les nouvelles
  sorties, afin que mes conclusions tiennent sur des données de marché.
  - Étant donné les sorties sur la courbe de marché, quand je relis §11, alors chaque chiffre et chaque
    tendance décrite y correspond.
- **STORY-007 :** En tant qu'auteur, je veux une conclusion (§12) à jour, afin que limites et perspectives
  reflètent l'état final.
  - Étant donné la courbe de marché branchée, quand je relis §12, alors la limite repo porte sur
    l'hypothèse de financement et non plus sur une courbe fictive.
  - Étant donné l'abandon de FR-018, quand je relis §12, alors la perspective « $\sigma_x(t)$ par morceaux »
    est remplacée par une limite : pour des options européennes elle revient à recaler $\sigma_x$ par
    échéance, effet borné par les résidus de la diagonale (2,3 bp de vol au plus).
  - Étant donné EPIC-008 terminé, quand je relis §12, alors la limite « le spread peut devenir négatif » est
    nuancée (spread OAT–€STR 2 ans négatif en moyenne sur 2021-2026 dans les données), la limite
    « calibration mixte » cite les écarts-types GMM et le test J, et l'estimation jointe des dynamiques
    historique et risque-neutre par filtre de Kalman figure en perspective.
- **STORY-008 :** En tant qu'auteur, je veux `CONTEXTE.md` et `PLAN.md` à jour, afin que le cadrage décrive
  le livrable final.
  - Étant donné les epics 5 et 6 terminés, quand je lis « Reste à faire », alors seuls des travaux ouverts y
    figurent.

### EPIC-007: Volatilité du facteur taux par morceaux — abandonné (v1.1)
**Related Requirements :** FR-018 (Won't). STORY-009 et STORY-010 sont retirées ; voir `decision-log.md`.

### EPIC-008: Estimation du facteur spread (§7, §9)
**Business Value :** des paramètres de spread estimés par un seul estimateur standard, avec leur
incertitude, et une vitesse historique dont l'instabilité apparente est expliquée.
**User Segments :** jury, auteur.
**Related Requirements :** FR-020, FR-021, FR-022, NFR-002, NFR-005
**Séquencement :** indépendant de la courbe repo (peut démarrer tout de suite) ; à terminer avant
STORY-005 à STORY-007, car la GMM change $\rho$ et donc les chiffres de §10-12.

**User Stories (sketch) :**
- **STORY-011 :** En tant que membre du jury, je veux voir que la vitesse AR(1) du spread est compatible avec
  une vitesse nulle une fois son biais de petit échantillon pris en compte, afin de ne pas y lire une
  contradiction avec $a_y \approx 0$.
  - Étant donné les trois fenêtres, quand le §9.2 s'exécute, alors la distribution simulée de l'estimateur
    sous vitesse nulle, le rang de la valeur observée et la vitesse corrigée sont imprimés.
- **STORY-012 :** En tant qu'auteur, je veux estimer $(a_y, \sigma_y, \rho)$ ensemble par GMM avec leurs
  écarts-types, afin de défendre une seule procédure d'estimation et son incertitude.
  - Étant donné les variations quotidiennes 2021-2026, quand le §9.2 s'exécute, alors les estimations, les
    écarts-types, le J de Hansen et les moments ajustés sont imprimés, et les sections 10-11 les utilisent.
- **STORY-013 :** En tant que membre du jury, je veux comprendre pourquoi $\bar r = r + y$ et ce que mesure
  $y$, afin de juger le choix de modéliser directement le spread.
  - Étant donné le §7 et le §9, quand je les lis, alors le cadre RMV, l'invariance P/Q des vols et
    corrélations et la composition crédit / liquidité du spread sont exposés, sans paramètre de perte.

---

## Prioritization Summary (MoSCoW) — Priorités

| Priority | Requirements | Rationale |
|----------|--------------|-----------|
| Must | FR-001 à FR-016 ; NFR-001 à NFR-006 | FR-001 à FR-012 : existant à ne pas casser. FR-013 à FR-016 : sans eux, les prix longs reposent sur une hypothèse arbitraire et le texte n'est pas vérifiable. |
| Should | FR-017, FR-020, FR-021, FR-022 ; NFR-007, NFR-008 | FR-017 : cadrage à jour. FR-020 à FR-022 : rigueur de l'estimation du spread (biais, incertitude, ancrage théorique) ; seule FR-021 déplace les prix (via $\rho$). NFR : soutenance et maintenance. |
| Could | — | — |
| Won't (this release) | FR-018, FR-019 | FR-018 : sans effet structurel sur des options européennes (moins de 3 % sur le call ATM). FR-019 : sort du modèle à deux facteurs étudié ; reste une perspective. |

Nouvelles exigences (FR-013 à FR-022) : 4 Must sur 10. Le poids des Must vient de l'existant, conservé comme
contrat de non-régression.

---

## Success Metrics — Indicateurs de réussite

| Metric | Baseline | Target | Measurement Method | Frequency |
|--------|----------|--------|--------------------|-----------|
| Courbe repo | fictive, +5 bp plat | courbe de marché du 08/09/2026, source citée | markdown section 1, fichier de données | à la fin d'EPIC-005 |
| Chiffres de §11-12 conformes aux sorties | non vérifié (écrits en dur) | 100 % | sortie récapitulative de FR-015 contre texte | après chaque ré-exécution |
| Contrôles respectés | tous (courbe fictive) | tous | NFR-002 | après chaque story |
| Exécution complète sans erreur | oui (19 cellules de code) | oui | NFR-001 | après chaque story |
| Mentions de courbe fictive dans le notebook | plusieurs (§1, §8, §11, §12) | 0 | recherche plein texte | à la fin d'EPIC-005 |
| Incertitude des paramètres de spread | fourchettes selon la fenêtre | écarts-types GMM et J de Hansen imprimés | sortie du §9.2 | à la fin d'EPIC-008 |

---

## Assumptions and Dependencies — Hypothèses et dépendances

### Assumptions
1. L'auteur obtient une courbe de spread repo OAT contre €STR à la date du 08/09/2026, au moins jusqu'à 1 an.
2. Au-delà d'un an, aucune cotation de repo à terme n'est liquide : la courbe longue restera une hypothèse
   de financement, choisie par l'auteur (FR-014).
3. L'option est collatéralisée et actualisée au taux €STR (hypothèse CSA de `CONTEXTE.md`).
4. Les données Bloomberg du 08/09/2026 restent les seules données de marché ; aucune autre date n'est
   ajoutée.
5. Le changement de courbe repo ne modifie que le forward et le recentrage, pas la calibration des facteurs.

### Dependencies
| Dependency | Type | Owner | Status | Risk | Mitigation |
|------------|------|-------|--------|------|------------|
| Courbe repo de marché | donnée | auteur | en attente | élevé : bloque EPIC-005 et EPIC-006 | STORY-004 et la préparation de FR-015 avancent sans elle |
| Choix de l'hypothèse de financement long terme | décision | auteur | ouverte | élevé : fixe le forward 2-15 ans | options documentées dans `addendum.md` (Q1) |
| Environnement `uv` (Python 3.12) | technique | auteur | en place | faible | `uv.lock` |

---

## Constraints — Contraintes

- **Technical :** un seul notebook `main/oat_option_pricer.ipynb` ; NumPy, SciPy, pandas, matplotlib ; pas
  de package, pytest ni LaTeX ; Python 3.12 via `uv`.
- **Business :** mémoire de recherche ; option vanille collatéralisée, jamais de knock-out ; aucune
  comparaison externe ; décisions de modélisation justifiées dans le notebook.
- **Timeline :** non communiquée ; les epics 5 et 6 dépendent de la date de réception de la courbe repo.

---

## Out of Scope — Hors périmètre

| Excluded | Reason | Revisit? |
|----------|--------|----------|
| Options à barrière, knock-out | le contrat du mémoire est une option vanille | non |
| Comparaison aux chiffres de Russo et al. ou à des options cotées (Eurex) | choix de cadrage de l'auteur | non |
| Second facteur de spread (FR-019) | sort du modèle à deux facteurs étudié | perspective du mémoire |
| $\sigma_x(t)$ constante par morceaux (FR-018) | options européennes : équivaut à recaler $\sigma_x$ par échéance, effet < 3 % | non |
| Pricer de production : API, interface, performance, packaging | livrable académique | non |
| Tests automatisés, CI | les contrôles sont des sorties du notebook | non |
| Calendrier de place, conventions complètes | simplification assumée (`CONTEXTE.md` §8) | non |
| Modélisation d'un défaut de l'État français | le spread est un facteur de risque de marché | non |

---

## Risks and Mitigations — Risques

| Risk | Impact | Probability | Mitigation | Owner |
|------|--------|-------------|------------|-------|
| Courbe repo non disponible au-delà d'un an | élevé | élevée | hypothèse de financement explicite (FR-014) et sensibilité (FR-012) | auteur |
| La courbe de marché inverse une conclusion qualitative de §11-12 | moyen | moyenne | STORY-004 (référence) puis revérification de chaque tendance (FR-016) | auteur |
| Recentrage $\delta$ très grand aux échéances longues (≈ 1 000 bp à 15 ans sur la courbe fictive) | moyen : le jury peut y voir une tension du modèle | moyenne | expliquer $\delta$ comme l'écart entre la dynamique du modèle et le portage repo, chiffré par échéance | auteur |
| Chiffres du texte désynchronisés après une nouvelle exécution | moyen | élevée sans FR-015 | sortie récapitulative de FR-015 | Claude Code |
| Données Bloomberg dans un dépôt public | élevé (licence) | inconnue | NFR-008 ; vérifier la visibilité du dépôt (Q4) | auteur |
| Le test J rejette la structure à un facteur du spread | faible sur les prix, moyen sur le texte | élevée (≈ 1 450 observations, test puissant) | présenter le rejet comme la limite connue du spread à un facteur (§12, limite 3), estimations lues comme valeurs pseudo-vraies | auteur |
| $a_y$ à sa borne inférieure : écart-type GMM non standard | moyen | élevée ($a_y$ = 0,001 aujourd'hui) | signaler la borne, donner les écarts-types de $(\sigma_y, \rho)$ à $a_y$ fixé (FR-021) | Claude Code |

---

## Traceability Matrix — Traçabilité

| Requirement | Business Goal | Epic | User Story | Status |
|-------------|---------------|------|------------|--------|
| FR-001 | G1, G4 | EPIC-001 | existant (§1) | fait |
| FR-002 | G1, G2 | EPIC-001 | existant (§2) | fait |
| FR-003 | G1, G2 | EPIC-001 | existant (§3) | fait |
| FR-004 | G2 | EPIC-002 | existant (§5) | fait |
| FR-005 | G1, G2 | EPIC-002 | existant (§6) | fait |
| FR-006 | G1, G2 | EPIC-002 | existant (§7) | fait |
| FR-007 | G1, G3 | EPIC-002 | existant (§9) | fait |
| FR-008 | G1 | EPIC-003 | existant (§8) | fait |
| FR-009 | G1, G2 | EPIC-003 | existant (§8) | fait |
| FR-010 | G2 | EPIC-003 | existant (§8) | fait |
| FR-011 | G2 | EPIC-003 | existant (§10) | fait |
| FR-012 | G3 | EPIC-004 | existant (§11) | fait |
| FR-013 | G1 | EPIC-005 | STORY-001, STORY-003 | à faire |
| FR-014 | G1, G3 | EPIC-005 | STORY-002 | à faire |
| FR-015 | G4 | EPIC-006 | STORY-004, STORY-005 | à faire |
| FR-016 | G3, G4 | EPIC-006 | STORY-006, STORY-007 | à faire |
| FR-017 | G3 | EPIC-006 | STORY-008 | à faire |
| FR-018 | — | — | — | abandonné |
| FR-019 | — | — | — | hors périmètre |
| FR-020 | G2, G3 | EPIC-008 | STORY-011 | à faire |
| FR-021 | G1, G2 | EPIC-008 | STORY-012 | à faire |
| FR-022 | G3 | EPIC-008 | STORY-013 | à faire |
| NFR-001 | G4 | (transverse) | toutes | en place |
| NFR-002 | G2 | (transverse) | toutes | en place |
| NFR-003 | G4 | (transverse) | STORY-004 | en place |
| NFR-004 | G3 | (transverse) | toutes | en place |
| NFR-005 | G3 | (transverse) | STORY-006, STORY-007 | en place |
| NFR-006 | G1 | EPIC-005 | STORY-001 | à vérifier |
| NFR-007 | G4 | (transverse) | STORY-004 | à mesurer |
| NFR-008 | — (licence) | (transverse) | — | à vérifier |

---

## Handoff — Suite

- **To Architecture :** décrire la structure du notebook comme un système — sections, flux de données entre
  cellules (courbes → modèle → pricer → résultats), objets partagés, paramètres globaux, emplacement unique
  du chemin de la courbe repo, règle d'extrapolation du spread (FR-014), mécanisme de la sortie
  récapitulative des chiffres cités (FR-015). Pour EPIC-008 : moments retenus et matrice de pondération
  de la GMM (variance de long terme des moments, autocorrélation des variations quotidiennes), traitement de
  la borne de $a_y$, simulation de l'estimateur AR(1) (graine, nombre de tirages, durée d'exécution sous
  NFR-007). Fixer pour chaque story le périmètre de cellules qu'elle possède.
- **To Sprint/Story Planning :** l'esquisse des epics ci-dessus est la source des fichiers de stories.
- **Open questions / overflow :** voir `addendum.md`.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-10-01 | auteur + Claude Code | première version, à partir de `CONTEXTE.md`, `PLAN.md` et du notebook |
| 1.1 | 2026-10-01 | auteur + Claude Code | FR-018 ($\sigma_x(t)$ par morceaux) passe en Won't ; EPIC-007 abandonné, STORY-009/010 retirées ; limite ajoutée à STORY-007 |
| 1.3 | 2026-10-01 | auteur + Claude Code | FR-013 provisoirement satisfaite par une courbe fictive à structure par terme (1W-1Y) dans `data/repo_fictif.csv`, faute de données de marché ; FR-014 : règle « plat » (Q1) ; NFR-008 : dépôt public (Q4), non satisfaite |
| 1.2 | 2026-10-01 | auteur + Claude Code | EPIC-008 « Estimation du facteur spread » : FR-020 (biais AR(1)), FR-021 (GMM, estimateur retenu), FR-022 (cadre RMV, crédit / liquidité) ; STORY-011 à 013 ; FR-017 et STORY-007 complétées |
