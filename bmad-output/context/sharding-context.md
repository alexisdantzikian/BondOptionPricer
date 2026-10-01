# Sharding context — BondOptionPricer (brief commun aux auteurs de stories)

À lire avant de compiler une story. Sources de vérité : `bmad-output/prd.md` (v1.2),
`bmad-output/architecture.md` (v1.0), `bmad-output/addendum.md`, `bmad-output/decision-log.md`,
`bmad-output/project-context.md`, `bmad-output/epics.md`.

## Format d'une story

- Fichier : `bmad-output/stories/{epic}.{story}.{slug}.story.md`, gabarit
  `C:/Users/alexd/.claude/plugins/cache/bmad-method-harness/bmad-planning-orchestrator/0.5.0/skills/bmad-epics-and-stories/templates/story.template.md`.
- Titres de section du gabarit **en anglais, inchangés** (`## Story`, `## Acceptance Criteria`, `## Tasks /
  Subtasks`, `## Dev Notes`, `## Testing`, `## Dependency Maps`, `## Owned File/Module Scope`,
  `## Learnings from Previous Stories`, `## Dev Agent Record`) ; garder le commentaire HTML d'en-tête et les
  commentaires LOCKED. **Contenu en français.**
- Ligne d'en-tête supplémentaire après `**Slug:**` : `**PRD :** STORY-0NN` (identifiant d'esquisse du PRD).
- Story : « En tant que **…**, je veux **…**, afin de **…**. »
- Acceptance Criteria : 3 à 7, numérotés, vérifiables par lecture d'une sortie, d'un `git diff` ou d'une
  recherche plein texte. Pas de critère vague.
- Tasks : cases à cocher, chacune terminée par `(AC: #N)`.
- Dev Notes : chaque fait cité `[Source: prd.md#FR-0NN]`, `[Source: architecture.md#ADR-0NN]`,
  `[Source: architecture.md#6-api-specifications--interfaces]`, `[Source: addendum.md#…]`,
  `[Source: decision-log.md, 2026-10-01]`, `[Source: main/oat_option_pricer.ipynb §9.2]`,
  `[Source: doc/econo modele affine.pdf, slide N]` ; ses propres déductions marquées `[Inference]`.
  Donner le détail concret nécessaire : noms, signatures, formules, seuils, emplacement des cellules,
  texte attendu en substance.
- Testing : stratégie seulement (que vérifier, comment), jamais d'exécution ni de chiffre de couverture.
  Le « test » ici = protocole de vérification de `architecture.md` §7 « Testing strategy ».
- Owned File/Module Scope : **une puce par fichier, le chemin en premier** (le contrôleur ne lit que le
  premier mot de chaque puce), puis ` — ` et le détail des cellules possédées. Ex. :
  `` - `main/oat_option_pricer.ipynb` — §9.3 M + B + E (nouvelles), §9.2 E (bloc paramètres retenus) ``.
  Ajouter une ligne non puce : « Fichier partagé et contesté : sérialisé par la chaîne de dépendances
  (architecture ADR-012). »
- Dev Agent Record : laissé vide.
- Taille : une session d'agent (2-8 h). Objet de contexte autonome, ~3 000 à 8 000 tokens selon la story.
- Statut : `ready-for-dev` si tout est spécifiable maintenant ; `backlog` si une entrée externe manque
  (Epic 5 : courbe repo Q2, décision Q1), avec la raison en commentaire.

## Règles transverses LOCKED (architecture.md §3) à rappeler dans les Dev Notes concernées

- ADR-001 notebook unique `main/oat_option_pricer.ipynb`, sections « markdown → bibliothèque →
  exécution », pas de `.py`, `main/main.ipynb` intouché.
- ADR-002 ne lire que des noms publics (liste en architecture §6) ; déclarer tout nouveau nom public.
- ADR-003 unités : temps en années ACT/365 depuis `DATE_VAL`, taux décimaux zéro continus, prix pour 1
  en interne et ×100 à l'affichage, bp seulement à l'affichage ; `params` dataclass ; `p_cal` construit
  uniquement en §9.3 (après 8.2).
- ADR-004 graines littérales : 0 et 1 (§10, existantes), 2 (AR(1), §9.4), 3 (bootstrap GMM, §9.3).
- ADR-005 contrôles imprimés `libellé : valeur   (seuil)` ; `assert` seulement pour les données d'entrée.
- ADR-006 nommage : classes en minuscules snake_case, fonctions snake_case, constantes en MAJUSCULES ;
  français pour markdown, docstrings, commentaires, libellés ; interdits : « knock-out », paramètre de
  perte L, chiffres du papier de Russo, options cotées. Commit : `Notebook : …` ou `Cadrage : …`.
- ADR-007 pas de `git push`.
- ADR-011 éditer cellule par cellule (NotebookEdit ou script nbformat jetable dans le scratchpad), jamais
  le JSON à la main ; désigner une cellule par section + rôle ou première ligne de docstring, **jamais par
  indice** ; puis `uv run jupyter nbconvert --to notebook --execute --inplace main/oat_option_pricer.ipynb` ;
  commiter le notebook avec ses sorties ; un commit par story.
- ADR-012 une story à la fois sur le notebook.

## Carte actuelle du notebook (33 cellules ; indices donnés pour repère seulement)

| Section | Cellules (rôle) | Noms publics fournis |
|---|---|---|
| en-tête | M (objectif, plan, notations) | — |
| §1 Données | M ; E « Chargement des données de marché » (`load_estr`, `load_cube`, `load_oat`, `load_history`, `load_repo`) ; E figures | `estr, cube, oat, hist_oat, hist_estr, repo_data, DATE_OBS, DATE_VAL, FICHIER, FICHIER_REPO, tenor_years` |
| §2 €STR | M ; B+E | `curve, zc_curve` |
| §3 OAT | M ; B+E | `risky, oat_curve, bond, oat46, dirty46, ECHEANCES` |
| §4 Briques | M ; B+E | `params, H, V, V_xy, V_bar, var_factor, cov_xy, cov_factor_int, cov_cross_int, swap_xy` |
| §5 HW1F | M ; B ; E | `hw1f_model, black, swaption, bachelier_atm, atm_rate` |
| §6 Facteur taux | M ; B ; E | `A_X = 0.01052, S_X = 0.7353 %` |
| §7 Modèle 2F | M ; B (`hw2f_model`) ; E (`p_test`) | `hw2f_model, p_test` |
| §8 Option | M (8.1 à 8.5) ; B « Option européenne sur OAT : forward repo… » (`repo_curve`, `forward_repo`, `forward_means`, `forward_flows`, `recentrage`, `oat_option`) ; E (`repo = repo_curve(curve, repo_data[...])`, tableau avec `p_test`, parités, cas limites) | `repo_curve, forward_repo, forward_flows, recentrage, oat_option, repo` |
| §9 Spread | M (9.1 non-identification, 9.2 calibration historique, paragraphe AR(1)) ; B+E « Facteur spread : procédure de calibration sur la courbe OAT… » (9.1) ; E 9.2 (`ar1_speed`, `spread_stats`, `fit_vol_term_structure`, fenêtres, **PARAMÈTRES RETENUS** `A_Y, S_Y, RHO, p_cal`, `RHO_MIN, RHO_MAX`, figure) | `ar1_speed, spread_stats, fit_vol_term_structure, est, fits, fenetres, TENORS, T_SJ, RHO_MIN, RHO_MAX, A_Y, S_Y, RHO, p_cal` |
| §10 Monte-Carlo | M ; B (`hw2f_mc`) ; E (`m_cal`, `opts`, graines 0 et 1) | `hw2f_mc, m_cal, opts` |
| §11 Résultats | M ; E (décomposition de variance, 2F contre taux seul) ; E sensibilités (`atm_table`, `scen_repo` plats −25/0/+5/+15 bp + « taux OAT », `scen_sy`, `scen_rho` avec `RHO_MIN/RHO_MAX`, `scen_ay` avec `est["2021-2026"].loc[T_SJ, "a_y AR(1)"]`) ; M « Lecture des résultats » (chiffres en dur) | `atm_table` |
| §12 | M « Conclusion et limites » | — |

Valeurs actuelles utiles : $a_y = 0{,}0010$ (borne), $\sigma_y = 0{,}3367\,\%$, $\rho = 0{,}152$ (20 ans) ;
fourchette $\rho$ 0,064 → 0,434 ; AR(1) au tenor 20 ans : 0,192 (2021-2026, n = 1 453), 0,966 (3 ans,
n = 764), 5,028 (1 an, n = 257) ; corrélations 2021-2026 par tenor : 5 ans 0,064, 10 ans 0,162,
15 ans 0,118, 20 ans 0,152, 25 ans 0,148, 30 ans 0,124 ; vols du spread 2021-2026 (bp/an) : 33,9 ;
32,7 ; 33,2 ; 33,1 ; 33,1 ; 34,2. Tenor 2 ans exclu (rupture du générique le 22/01/2024).
Mentions « fictif » : §1 M, §1 E (libellé), §8 E (libellé), §11 M d'introduction, §11 E sensibilités
(commentaire et libellé « cas central +5 bp »), §11 M « Lecture des résultats », §12 M (limite 1 et
perspectives).

## Ordre et dépendances

`6.1 → 8.1 → 8.2 → 8.3 → 6.2 → 5.1 → 5.2 → 5.3 → 6.3 → 6.4 → 6.5` (architecture §4 « Séquencement »).
Chaque story est Blocked-by la précédente de la chaîne (sérialisation du notebook) en plus de ses
dépendances de fond.

## Learnings (travaux antérieurs, commits 18af878 → d5d12cc)

- Le notebook a été réécrit et ré-exécuté par `nbconvert --execute --inplace` ; il s'exécute aujourd'hui
  sans erreur (19 cellules de code, compteurs 1 → 19).
- Les historiques sont coupés au 08/09/2026 dans `load_history` ; la colonne de dates est reconstruite.
- La cellule §8 E imprime $\delta$ avec `p_test` (provisoire) ; les valeurs citées dans le texte viennent
  du §10 avec `p_cal` (−1,0 bp à 1 an, 587,9 bp à 15 ans).
- Les chiffres de §11-12 sont écrits en dur ; inventaire dans `addendum.md` (FR-015).
