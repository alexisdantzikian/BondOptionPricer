# Project Context — BondOptionPricer

> La **constitution** du projet, chargée par chaque skill de planification BMAD. Le cadrage
> détaillé (contrat, modèle, formule, calibration, données, conventions) reste dans
> [`CONTEXTE.md`](../CONTEXTE.md) et l'avancement section par section dans [`PLAN.md`](../PLAN.md) :
> ce document les résume et fixe les règles, il ne les duplique pas. Toute décision qui change le
> périmètre met ce fichier à jour et s'ajoute à `decision-log.md`.

- **Track:** bmad-method
- **Created:** 2026-10-01T20:37:05Z
- **Nature :** brownfield — le notebook existe, ses 12 sections sont faites.

---

## Project Goal

Mémoire de recherche : un **pricer d'options européennes vanilles collatéralisées (€STR) sur OAT**
(sous-jacent OAT 4,10 % 25/05/2046, échéances 1-2-5-7-10-12-15 ans) dans le **modèle gaussien à deux
facteurs corrélés** de Russo, Giacometti & Fabozzi — Hull-White 1F sur l'€STR, Hull-White 1F sur le
spread court OAT–€STR — calibré sur données Bloomberg et validé (Jamshidian en 1F, Monte-Carlo exact).

**Terminé et réussi =** le notebook s'exécute de bout en bout, chaque étape est justifiée par un
markdown et vérifiée par une cellule de contrôles, et les chiffres cités dans le texte correspondent aux
sorties du notebook.

## Primary Users

- **Le jury du mémoire** : lit le notebook ; a besoin de justifications, de contrôles visibles et de
  résultats lisibles, pas de performance.
- **L'auteur** : présente et défend le mémoire ; a besoin d'un code simple qu'il maîtrise ligne à ligne.

## Scope

État : sections 1 à 12 faites (données → courbes → briques gaussiennes → HW1F/Jamshidian → calibration
du facteur taux → modèle 2F → option vanille et forward repo → calibration du facteur spread →
Monte-Carlo → résultats → conclusion). Travail restant, d'après `PLAN.md` :

1. **Courbe repo de marché** à la place de `data/repo_fictif.csv` (même format `Tenor,Spread_bp`), avec
   l'hypothèse de financement au-delà d'un an documentée — elle fixe le forward des échéances longues.
2. **Chiffres de la lecture des résultats (§11) et de la conclusion (§12)** : aujourd'hui écrits en dur,
   à relire ou à relier aux sorties après le changement de courbe repo.
3. Extensions possibles : $\sigma_x(t)$ constante par morceaux bootstrappée sur la diagonale ; second
   facteur de spread pour la volatilité du court terme.

## Core Constraints

- **Un seul notebook** : `main/oat_option_pricer.ipynb`, en français. `main/main.ipynb` est un brouillon
  qu'on ne touche pas.
- **Format académique** du colab « Hull & White 1F » de `doc/` : par section, un markdown (théorie,
  justification) → une cellule bibliothèque (docstring, petite classe) → une cellule d'exécution qui
  imprime les contrôles.
- **Code simple** : NumPy, SciPy, pandas, matplotlib. Pas de package Python, pas de pytest, pas de LaTeX
  séparé ; la vérification passe par les cellules de contrôles.
- Python 3.12 via `uv` (`pyproject.toml`, `uv.lock`).
- Données figées : Bloomberg, clôture du 08/09/2026, règlement 10/09/2026 ($t=0$), ACT/365.
- Les décisions de modélisation se prennent et se justifient **dans le notebook**.

## Non-Goals

- **Aucune option à barrière / knock-out** : le contrat est une option vanille.
- **Aucune comparaison externe** : ni avec les chiffres du papier de Russo et al., ni avec des options
  cotées (Eurex).
- Pas de pricer de production : ni optimisation de performance, ni API, ni interface, ni packaging.
- Pas de tests automatisés ni de CI.

## Key Stakeholders / Roles

- **Décide et rédige** : l'auteur du mémoire (seul).
- **Implémente** : Claude Code, dans le notebook, à partir des stories `ready-for-dev`.
- **Évalue** : le jury du mémoire.

## Glossary

- **€STR** : taux court sans risque de la zone euro ; courbe OIS bootstrappée, actualisation des options.
- **OAT** : obligation assimilable du Trésor ; courbe Nelson-Siegel-Svensson ajustée sur les prix dirty.
- **Spread court** $y$ : second facteur, écart instantané OAT–€STR.
- **Forward repo** $F$ : prix à terme cash-and-carry au taux €STR + spread repo.
- **Strike clean / dirty** : $K$ en % du forward clean ; en interne $X = K + CC(T_0)$.
- **Recentrage** $\delta$ : décalage de la moyenne de $y(T_0)$ pour que l'espérance forward du modèle égale $F$.
- **Poids gelés** : hypothèse lognormale de Russo & Fabozzi, poids figés à $w_i = m_i(\delta)/F$.
- **Diagonale co-terminale 20 ans** : swaptions ATM dont expiry + tenor = 20 ans, cible du facteur taux.
- **Jamshidian** : décomposition exacte d'une option sur obligation à coupons en 1F, contrôle de la formule.

---

## Decision Thread

Les décisions courantes vivent dans [`decision-log.md`](./decision-log.md). La première entrée est le
choix du track. Les décisions antérieures à BMAD sont dans `CONTEXTE.md` (§2 à §9).

## Planning Status (count-based)

- **Track:** bmad-method
- **Stories defined:** 11 (`epics.md`, `stories/`)
- **Stories done:** 5 (6.1, 8.1, 8.2, 8.3, 6.2)
- **Stories remaining:** 6 (Epic 5 en attente de la courbe repo et de Q1 ; 6.3-6.5 bloquées par l'Epic 5)

_Ce document planifie le travail. L'implémentation passe par des stories `ready-for-dev` ; le plugin de
planification n'écrit ni ne teste de code._
