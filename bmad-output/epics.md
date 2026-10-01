# Epics — BondOptionPricer

> La CARTE des epics : un index, pas un objet de contexte. Le détail de chaque story est dans
> `stories/{epic}.{story}.{slug}.story.md`.
>
> Track: BMad Method
> Sources: `prd.md` (v1.2), `architecture.md` (v1.0), `decision-log.md`

Les epics 1 à 4 (données et courbes, modèle et calibration, pricer, résultats) décrivent l'existant —
FR-001 à FR-012, statut « fait » — et servent de contrat de non-régression ; ils n'ont pas de story.
L'epic 7 ($\sigma_x(t)$ par morceaux) est abandonné [Source: decision-log.md, 2026-10-01]. Les numéros
d'epic reprennent ceux du PRD.

---

## Epic 5: Courbe repo de marché

**Goal :** le forward de l'OAT 2046 repose sur une courbe repo de marché datée du 08/09/2026 et sur une
hypothèse de financement long terme explicite.

**In scope (cited) :**
- FR-013 — courbe repo de marché, remplaçable par un seul fichier [Source: prd.md#FR-013]
- FR-014 — hypothèse de financement au-delà du dernier tenor liquide [Source: prd.md#FR-014]
- FR-012 — sensibilités repo recentrées sur la courbe de marché [Source: prd.md#FR-012]
- NFR-006 — remplaçabilité des données [Source: prd.md#NFR-006]

**Architecture touchpoints :** §1 Données (`FICHIER_REPO`, `FINANCEMENT_LONG`), §8 Option
(`repo_curve`), §11 sensibilités [Source: architecture.md#ADR-008]

**Out of scope :** réécriture de la lecture des résultats et de la conclusion (Epic 6).

**Stories (ordered) :**

| ID | Slug | Intent | Status |
|------|------|--------|--------|
| 5.1 | courbe-repo-marche | Brancher `data/repo_marche.csv` à la place de la courbe fictive | backlog — attend la courbe (Q2) |
| 5.2 | financement-long-terme | Règle `FINANCEMENT_LONG`, spread par échéance, scénarios repo en translations | backlog — attend Q1 |
| 5.3 | retrait-mentions-fictif | Retirer toute mention de courbe fictive du notebook | backlog — suit 5.2 |

**Cross-epic dependencies :**
- Blocked by : Epic 6 (6.2) — sérialisation du notebook [Source: architecture.md#ADR-012]
- Blocks : Epic 6 (6.3, 6.4, 6.5) — §11-12 se réécrivent sur les sorties finales

---

## Epic 6: Cohérence du texte avec les sorties

**Goal :** chaque chiffre de §11-12 se retrouve dans une sortie libellée, le texte et les documents de
cadrage décrivent l'état final.

**In scope (cited) :**
- FR-015 — chiffres cités traçables [Source: prd.md#FR-015]
- FR-016 — §11-12 réécrits [Source: prd.md#FR-016]
- FR-017 — `CONTEXTE.md`, `PLAN.md` à jour [Source: prd.md#FR-017]
- NFR-001, NFR-002, NFR-003, NFR-007 — exécution, contrôles, reproductibilité, durée [Source: prd.md#NFR-001]

**Architecture touchpoints :** §11 (cellule `CHIFFRES`, markdown « Lecture des résultats »), §12,
cadrage, `bmad-output/reference/` [Source: architecture.md#ADR-009]

**Out of scope :** toute modification de calcul (Epics 5 et 8).

**Stories (ordered) :**

| ID | Slug | Intent | Status |
|------|------|--------|--------|
| 6.1 | execution-reference | Exécuter le notebook actuel et figer ses sorties et sa durée comme référence | done |
| 6.2 | cellule-chiffres-cites | Ajouter la cellule `CHIFFRES` en fin de §11 | done |
| 6.3 | lecture-resultats | Réécrire « Lecture des résultats » (§11) sur les sorties finales | ready-for-dev — bloquée par 5.3 |
| 6.4 | conclusion-limites | Réécrire §12 (résultats, limites, perspectives) | ready-for-dev — bloquée par 6.3 |
| 6.5 | cadrage-contexte-plan | Mettre à jour `CONTEXTE.md` et `PLAN.md` | ready-for-dev — bloquée par 6.4 |

**Cross-epic dependencies :**
- Blocked by : Epic 8 (8.3) pour 6.2 ; Epic 5 (5.3) pour 6.3
- Blocks : Epic 8 (8.1) — 6.1 fournit la référence de comparaison

---

## Epic 8: Estimation du facteur spread

**Goal :** $(a_y, \sigma_y, \rho)$ estimés par une GMM unique avec leur incertitude, vitesse historique
expliquée par le biais de petit échantillon, spread ancré dans le cadre crédit à intensité.

**In scope (cited) :**
- FR-020 — biais de la vitesse AR(1) [Source: prd.md#FR-020]
- FR-021 — GMM sur $(a_y, \sigma_y, \rho)$, estimateur retenu [Source: prd.md#FR-021]
- FR-022 — cadre RMV, crédit / liquidité [Source: prd.md#FR-022]
- NFR-003, NFR-005, NFR-007 [Source: prd.md#NFR-003]

**Architecture touchpoints :** §7 markdown, §9 (9.2, 9.3 nouvelle, 9.4 nouvelle), §11 scénario $a_y$
[Source: architecture.md#ADR-010]

**Out of scope :** filtre de Kalman, régimes cachés, second facteur de spread [Source: prd.md#out-of-scope].

**Stories (ordered) :**

| ID | Slug | Intent | Status |
|------|------|--------|--------|
| 8.1 | biais-ar1 | §9.4 : distribution simulée de l'estimateur AR(1) et vitesse corrigée | done |
| 8.2 | gmm-spread | §9.3 : GMM retenue, `p_cal` construit ici, scénario a_y du §11 | done |
| 8.3 | cadre-rmv | Markdowns §7 et §9 : cadre RMV, invariance P/Q, crédit / liquidité | done |

**Cross-epic dependencies :**
- Blocked by : Epic 6 (6.1) — référence d'exécution
- Blocks : Epic 6 (6.2 puis 6.3-6.4) — la GMM change $\rho$ et donc les chiffres de §10-12

---

## Ordre d'exécution (largeur de vague 1 sur le notebook)

`6.1 → 8.1 → 8.2 → 8.3 → 6.2 → [courbe repo + Q1] 5.1 → 5.2 → 5.3 → 6.3 → 6.4 → 6.5`
[Source: architecture.md#séquencement-des-stories-largeur-1-adr-012]

## Delivery Tracking (count-based)

- Total stories : 11
- Done : 5 (6.1, 8.1, 8.2, 8.3, 6.2 — 2026-10-01)
- Remaining : 6 (backlog en attente de la courbe repo et de Q1 : 5.1, 5.2, 5.3 ; ready-for-dev bloquées par l'epic 5 : 6.3, 6.4, 6.5)
- Completion rate : 5 / 11

## Notes

- Toutes les stories de code partagent `main/oat_option_pricer.ipynb` : le contrôle de recouvrement BMAD
  signale donc des conflits entre elles ; ils sont **voulus** et résolus par la chaîne de dépendances
  ci-dessus (une story à la fois) [Source: architecture.md#ADR-012].
- Les stories 6.1 → 8.3 → 6.2 peuvent être faites tout de suite ; l'epic 5 attend la courbe repo (Q2) et
  la décision de financement long terme (Q1) [Source: addendum.md#open-questions].
