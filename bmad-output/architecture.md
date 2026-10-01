# System Architecture: BondOptionPricer

**Document Version:** 1.0
**Date:** 2026-10-01
**Author:** Winston (Architect), workflow `bmad-architecture`, pour l'auteur du mémoire
**Track:** BMad Method
**Status:** Draft — à valider par l'auteur
**Source PRD:** `bmad-output/prd.md` (v1.2)

> Source unique des décisions techniques transverses. Chaque story compilée ensuite hérite des décisions
> **LOCKED** ci-dessous. Le « système » est un notebook Jupyter de recherche : les notions d'API, de base
> de données ou de déploiement sont transposées (contrat de noms entre cellules, objets en mémoire,
> exécution locale) et dites explicitement quand elles sont sans objet. Titres de section en anglais
> (repères du validateur BMAD), contenu en français.

---

## Table of Contents

1. [System Overview](#1-system-overview--vue-densemble)
2. [Architecture Pattern](#2-architecture-pattern--motif)
3. [Architecture Decision Records](#3-architecture-decision-records)
4. [Component Design](#4-component-design--composants)
5. [Data Model](#5-data-model--modèle-de-données)
6. [API Specifications](#6-api-specifications--interfaces)
7. [FR / NFR Coverage Matrix](#7-fr--nfr-coverage-matrix)
8. [Technology Stack](#8-technology-stack)
9. [Trade-off Analysis](#9-trade-off-analysis)
10. [Deployment Architecture](#10-deployment-architecture--exécution)
11. [Future Considerations](#11-future-considerations)

---

## 1. System Overview — Vue d'ensemble

### Purpose
Le notebook `main/oat_option_pricer.ipynb` charge les données de marché du 08/09/2026, construit les courbes
€STR et OAT, calibre le modèle gaussien à deux facteurs (taux, spread), price des calls / puts européens
collatéralisés sur l'OAT 4,10 % 2046 par formule fermée, les valide (Jamshidian, Monte-Carlo exact) et
présente résultats et sensibilités. Chaque étape est justifiée (markdown) et contrôlée (sorties imprimées).

### Scope
**In Scope (travaux de cette version) :**
- courbe repo de marché et hypothèse de financement long terme (EPIC-005) ;
- estimation du facteur spread : biais AR(1), GMM retenue, cadre RMV (EPIC-008) ;
- traçabilité des chiffres cités et réécriture de §11-12, documents de cadrage (EPIC-006).

**Out of Scope :** $\sigma_x(t)$ par morceaux (FR-018), second facteur de spread (FR-019), package Python,
tests automatisés, API, interface, déploiement (voir PRD, Out of Scope).

### Architectural Drivers
1. **NFR-004 : notebook unique au format académique** — impose un monolithe en un seul fichier `.ipynb`,
   des sections « markdown → bibliothèque → exécution » et un code lisible ligne à ligne. Conséquence
   majeure : un seul fichier JSON pour tout le code, donc **aucune édition parallèle** (ADR-012).
2. **NFR-001 / NFR-003 : exécution complète et reproductible** — impose un état strictement séquentiel,
   des graines explicites et une ré-exécution intégrale après chaque story (ADR-004, ADR-011).
3. **NFR-002 : contrôles numériques** — impose une convention unique de contrôles imprimés (ADR-005).
4. **FR-015 : chiffres cités traçables** — impose une sortie récapitulative unique (ADR-009).
5. **NFR-006 : remplaçabilité des données** — impose un point d'entrée unique pour la courbe repo
   (ADR-008).

### Stakeholders & Constraints (from project-context.md)
- **Users :** jury du mémoire (lecteur), auteur (soutient, doit maîtriser le code).
- **Team :** un rédacteur + Claude Code comme exécutant ; pas d'équipe de développement.
- **Existing constraints :** Python 3.12 via `uv` ; NumPy, SciPy, pandas, matplotlib ; pas de package,
  pytest ni LaTeX ; `main/main.ipynb` intouché ; aucun « knock-out », aucun chiffre du papier de Russo,
  aucun paramètre de perte L ; données Bloomberg figées au 08/09/2026.

---

## 2. Architecture Pattern — Motif

**Pattern :** **monolithe en couches** (layered monolith) — un seul notebook, sections ordonnées comme des
couches, dépendances uniquement descendantes.

```
§1 Données ──► §2 Courbe €STR ──► §3 Courbe OAT, OAT 2046
                    │                     │
                    ▼                     ▼
               §4 Briques gaussiennes (H, V, variances, params)
                    │
                    ▼
        §5 HW1F, Jamshidian ──► §6 Calibration facteur taux (A_X, S_X)
                    │
                    ▼
               §7 Modèle 2F (hw2f_model)
                    │
                    ▼
        §8 Repo, forward, recentrage, oat_option
                    │
                    ▼
        §9 Calibration facteur spread (A_Y, S_Y, RHO, p_cal)
                    │
                    ▼
        §10 Monte-Carlo ──► §11 Résultats, sensibilités, CHIFFRES ──► §12 Conclusion (markdown)
```

**Justification :**
- Le livrable est imposé (NFR-004, décision de l'auteur du 20/09/2026) : un seul notebook lu de haut en
  bas par le jury. Les couches suivent l'ordre de l'exposé.
- Une seule personne maintient le code ; aucun besoin de modularité au-delà des sections.

**Alternatives considered :**
- **Package Python + notebook mince :** rejeté — explicitement refusé par l'auteur, contraire à NFR-004.
- **Plusieurs notebooks (un par chapitre) :** rejeté — le livrable est un notebook unique ; l'état
  partagé devrait transiter par des fichiers intermédiaires.
- **Script générateur `nbformat` comme source de vérité :** rejeté — le notebook commité reste la source ;
  un script `nbformat` jetable peut servir d'outil d'édition (ADR-011).

**Application :** chaque section possède ses cellules ; une cellule ne lit que des **noms publics** de
sections antérieures (ADR-002) ; §12 et la « Lecture des résultats » sont du markdown statique.

---

## 3. Architecture Decision Records

| ADR | Title | Status | Drives |
|-----|-------|--------|--------|
| ADR-001 | Notebook unique, monolithe en couches, dépendances descendantes | Accepted | NFR-004 |
| ADR-002 | Interface entre cellules = contrat de noms publics (pas de REST / GraphQL / gRPC) | Accepted | FR-001→022, NFR-001 |
| ADR-003 | Modèle de données en mémoire : unités, conventions, jeux de paramètres | Accepted | FR-008→012, FR-021 |
| ADR-004 | Gestion de l'état : noyau séquentiel, graines explicites | Accepted | NFR-001, NFR-003 |
| ADR-005 | Convention de contrôles imprimés (équivalent « error/response ») | Accepted | NFR-002 |
| ADR-006 | Conventions de nommage et de langue | Accepted | NFR-004, NFR-005 |
| ADR-007 | Sécurité : pas d'AuthN/AuthZ ; confidentialité des données | Accepted | NFR-008 |
| ADR-008 | Courbe repo : fichier unique, règle long terme, scénarios | Accepted | FR-013, FR-014, FR-012, NFR-006 |
| ADR-009 | Chiffres cités : cellule récapitulative, texte statique | Accepted | FR-015, FR-016 |
| ADR-010 | Estimation du facteur spread : GMM retenue, biais AR(1) par simulation | Accepted | FR-020, FR-021, FR-022 |
| ADR-011 | Édition, exécution et commit du notebook | Accepted | NFR-001, NFR-003, NFR-004 |
| ADR-012 | Pas de parallélisme sur le notebook | Accepted | NFR-004 |

### ADR-001: Notebook unique, monolithe en couches

**Status:** Accepted   **Drives:** NFR-004

**Context:** l'auteur impose un notebook unique au format du colab « Hull & White 1F » (`doc/`), lisible
par un jury, sans package ni tests.

**Decision:** tout le code du pricer vit dans `main/oat_option_pricer.ipynb`. Les sections 1 à 12 gardent
leur ordre. Chaque section = un markdown (théorie, justification) puis, s'il y a du code, une cellule
bibliothèque (docstring de tête, fonctions / petites classes) puis une ou plusieurs cellules d'exécution
qui impriment des contrôles. Une nouvelle sous-section (ex. §9.3) suit le même triplet.

**Consequences — LOCKED for all stories :**
- Aucun fichier `.py` importé par le notebook, aucun nouveau notebook, `main/main.ipynb` non modifié.
- Une cellule ne dépend que de sections antérieures ; aucune référence vers l'avant.
- Easier : lecture linéaire par le jury, état reproductible. Accepted cost : fichier unique non
  fusionnable (ADR-012). Mitigation : stories sérialisées, un commit par story.

**Alternatives :** voir §2.

**Revisit when :** jamais pendant le mémoire.

### ADR-002: Interface entre cellules = contrat de noms publics

**Status:** Accepted   **Drives:** FR-001 à FR-022, NFR-001

**Context:** il n'y a ni service ni API REST, GraphQL ou gRPC ; l'« interface » d'une section est
l'ensemble des noms Python qu'elle laisse dans le noyau. Le notebook actuel réutilise des noms transitoires
d'une cellule à l'autre (`rows`, `k`, `T0`, `o`, `K`), ce qui rend l'ordre d'exécution fragile.

**Decision:** les noms listés en §6 (« Noms publics ») sont le contrat. Une story :
- ne renomme ni ne supprime un nom public existant, ne change pas sa signature sauf si §6 le prévoit ;
- ne lit, dans une cellule nouvelle ou modifiée, **que** des noms publics de sections antérieures (jamais
  `rows`, `k`, `o`, `T0`, `K`, `x0`, `h`, `nom`… d'une autre cellule) ;
- déclare dans §6 tout nouveau nom public qu'elle crée (les noms internes restent locaux à la cellule ou
  préfixés par `_`).

**Consequences — LOCKED :** contrat de noms de §6 ; tout ajout de nom public passe par une mise à jour de
ce document (Update). Easier : stories indépendantes du détail des autres cellules. Accepted cost : un
peu de verbosité.

**Alternatives :** REST / GraphQL / gRPC — sans objet ; variables globales libres — cause actuelle de
fragilité.

**Revisit when :** une story doit lire un nom transitoire — le promouvoir en nom public d'abord.

### ADR-003: Modèle de données en mémoire

**Status:** Accepted   **Drives:** FR-008 à FR-012, FR-021

**Context:** les sections échangent des courbes, des paramètres et des prix ; une confusion d'unité (bp
contre décimal, prix pour 1 contre pour 100) fausse silencieusement les résultats.

**Decision:**
- Temps en années ACT/365 depuis `DATE_VAL` (10/09/2026) ; taux en décimal, zéro continus ; bp et % **à
  l'affichage seulement**.
- Prix internes pour un nominal de 1 ; multipliés par 100 à l'affichage (« prix pour 100 »).
- Strike : `K` clean en valeur absolue (pour 1) ; dans les tableaux, en % du forward clean.
- Paramètres du modèle : uniquement via la dataclass immuable `params(a_x, s_x, a_y, s_y, rho)` ;
  variantes par `dataclasses.replace`.
- Jeu retenu : `p_cal`, construit **une seule fois**, en §9.3 (ADR-010), à partir de `A_X, S_X`
  (§6) et `A_Y, S_Y, RHO` (§9.3). Aucune autre cellule ne réassigne ces noms.

**Consequences — LOCKED :** ces unités et ces noms ; tout nouveau tableau imprimé indique son unité dans
son titre. Easier : contrôles comparables entre sections. Accepted cost : conversions explicites.

**Alternatives :** unités mixtes au fil de l'eau — rejeté (source d'erreurs).

**Revisit when :** jamais.

### ADR-004: Gestion de l'état — noyau séquentiel, graines explicites

**Status:** Accepted   **Drives:** NFR-001, NFR-003

**Context:** la state management d'un notebook est l'état global du noyau ; une exécution dans le désordre
ou un tirage non graîné rend les chiffres non reproductibles.

**Decision:** le notebook est toujours validé par une exécution complète depuis un noyau neuf, de haut en
bas (ADR-011). Tout tirage aléatoire passe par `np.random.default_rng(<graine littérale>)` créé dans la
cellule qui l'utilise. Graines existantes : 0 et 1 (§10). Nouvelles graines réservées : **2** (simulation
AR(1), §9.4), **3** (bootstrap GMM, §9.3). Pas d'état caché : pas de cache disque, pas de lecture des
sorties d'une exécution précédente.

**Consequences — LOCKED :** graines ci-dessus ; une cellule n'écrit aucun fichier hors `bmad-output/`
(et seulement depuis un script hors notebook).

**Alternatives :** graines globales `np.random.seed` — rejeté (couplage entre cellules).

**Revisit when :** jamais.

### ADR-005: Convention de contrôles imprimés

**Status:** Accepted   **Drives:** NFR-002

**Context:** il n'y a pas de réponses ni de codes d'erreur ; la « réponse » d'une cellule d'exécution est
sa sortie, et la validation du jury passe par la lecture des contrôles.

**Decision:**
- Une cellule d'exécution imprime chaque contrôle sous la forme `libellé : valeur   (seuil ou référence)`,
  ou un tableau pandas dont le titre donne l'unité et la référence.
- `assert` est réservé à l'intégrité des **données d'entrée** (format, dates, colonnes) : l'exécution
  s'arrête si les données sont corrompues. Un contrôle de modèle (parité, recalage, Monte-Carlo) ne lève
  pas d'exception : il s'imprime et se lit.
- Les seuils sont ceux de NFR-002 ; un contrôle nouveau énonce son seuil dans sa ligne.

**Consequences — LOCKED :** format ci-dessus pour toute cellule nouvelle ou modifiée. Easier : vérification
par lecture, cohérente avec le colab de référence. Accepted cost : un contrôle cassé n'arrête pas
l'exécution. Mitigation : protocole de vérification de chaque story (§7, Testing strategy).

**Alternatives :** `assert` sur chaque contrôle — rejeté (masque la valeur au jury, change le style du
notebook).

**Revisit when :** un contrôle cassé passe inaperçu dans une story.

### ADR-006: Conventions de nommage et de langue

**Status:** Accepted   **Drives:** NFR-004, NFR-005

**Context:** les stories ajoutent du code dans un notebook déjà cohérent ; le style doit rester uniforme.

**Decision (naming convention, constatée dans le notebook et désormais imposée) :**
- Classes : minuscules en snake_case (`zc_curve`, `oat_curve`, `bond`, `hw1f_model`, `hw2f_model`,
  `repo_curve`, `oat_option`, `hw2f_mc`, `params`).
- Fonctions : snake_case, verbe ou nom de l'objet calculé (`forward_repo`, `recentrage`,
  `spread_stats`) ; français ou anglais selon l'usage déjà établi dans la section.
- Constantes de configuration et paramètres retenus : MAJUSCULES (`DATE_VAL`, `FICHIER_REPO`,
  `ECHEANCES`, `TENORS`, `T_SJ`, `A_X`, `S_X`, `A_Y`, `S_Y`, `RHO`).
- Symboles : `a_x, s_x, a_y, s_y, rho` ; `T0` échéance de l'option ; `K` strike clean ; `X` strike
  dirty ; `F` forward dirty ; `F_clean` ; `delta` recentrage.
- Langue : markdown, docstrings, commentaires et libellés imprimés en **français** ; vocabulaire de
  `project-context.md` (Glossary). Interdits (NFR-005) : « knock-out », paramètre de perte L, chiffres
  du papier de Russo, options cotées.
- Messages de commit : `Notebook : <ce qui change>` (ou `Cadrage : …` pour `CONTEXTE.md` / `PLAN.md`).

**Consequences — LOCKED :** ces conventions pour tout code et tout texte nouveaux.

**Alternatives :** PEP 8 strict (classes en CamelCase) — rejeté : renommerait l'existant pour rien.

**Revisit when :** jamais.

### ADR-007: Sécurité — pas d'AuthN/AuthZ ; confidentialité des données

**Status:** Accepted   **Drives:** NFR-008

**Context:** notebook local, mono-utilisateur, sans réseau ni secret ; seule question de sécurité : la
licence des données Bloomberg, suivies par git, et un dépôt GitHub de visibilité inconnue (Q4).

**Decision:** pas d'authentification ni d'autorisation (sans objet). Aucune clé, aucun appel réseau dans
le notebook. Les données de marché restent dans `data/`. Aucune story ne pousse vers le dépôt distant ;
le push reste une action de l'auteur, après réponse à Q4. La courbe repo de marché porte en commentaire
sa source et sa date, sans identifiant personnel.

**Consequences — LOCKED :** pas de `git push` dans les stories ; pas de nouvelle donnée hors `data/`.

**Alternatives :** chiffrer ou exclure `data/` — décision de l'auteur (Q4), hors stories.

**Revisit when :** réponse à Q4.

### ADR-008: Courbe repo — fichier unique, règle long terme, scénarios

**Status:** Accepted   **Drives:** FR-012, FR-013, FR-014, NFR-006

**Context:** la courbe fictive est lue depuis `data/repo_fictif.csv` (§1, `FICHIER_REPO`) ; `repo_curve`
interpole linéairement et extrapole plat (`np.interp`). La courbe de marché couvrira probablement
jusqu'à un an ; l'hypothèse au-delà (Q1) est un choix de l'auteur. Les sensibilités du §11 sont des
courbes plates −25 / 0 / +5 / +15 bp autour d'un « cas central +5 bp ».

**Decision:**
- La courbe de marché est le fichier `data/repo_marche.csv`, **même format** (`Tenor,Spread_bp`, lignes
  de commentaire `#` en tête donnant source, ticker et date). `FICHIER_REPO` (§1) est le **seul** point
  qui le désigne. `data/repo_fictif.csv` est supprimé du dépôt (l'historique git le garde).
- La règle au-delà du dernier tenor coté est choisie par une constante `FINANCEMENT_LONG` définie en §1 à
  côté de `FICHIER_REPO`, et appliquée **uniquement** dans `repo_curve.s`. Valeur initiale `"plat"`
  (comportement actuel). Toute autre valeur n'est ajoutée qu'après la réponse de l'auteur à Q1.
- `repo_curve` expose `T_max` (dernier tenor coté) ; le §8 imprime le spread utilisé à chaque échéance
  d'option et signale celles au-delà de `T_max`.
- Sensibilités repo (§11) : **translations parallèles** de la courbe retenue de −25, −10, 0, +10, +25 bp
  (même règle long terme), plus le scénario « financement au taux de l'OAT » existant.

**Consequences — LOCKED :** remplacer la courbe = remplacer le fichier et, une fois, `FICHIER_REPO` ;
aucun autre chemin de fichier repo dans le notebook ; le mot « fictif » disparaît du code et du texte à la
fin d'EPIC-005.

**Alternatives :** écrire l'hypothèse longue comme des lignes du CSV — rejeté : mélange cotations et
hypothèse, et la règle ne serait plus lisible dans le notebook ; garder les scénarios plats absolus —
rejeté : ils n'ont plus de sens autour d'une courbe de marché non plate.

**Revisit when :** réponse à Q1 ; courbe de marché couvrant 15 ans.

### ADR-009: Chiffres cités — cellule récapitulative, texte statique

**Status:** Accepted   **Drives:** FR-015, FR-016

**Context:** les chiffres de « Lecture des résultats » (§11) et de §12 sont écrits en dur ; Jupyter ne
sait pas injecter des variables dans un markdown sans extension.

**Decision:**
- Une cellule d'exécution « Chiffres cités » est ajoutée à la fin du §11, juste avant le markdown
  « Lecture des résultats ». Elle construit `CHIFFRES`, un `dict` ordonné `{libellé: valeur formatée}`
  calculé **uniquement** à partir des noms publics (ADR-002), avec l'arrondi et la virgule décimale du
  texte (ex. `"90,2"`), puis l'imprime en deux colonnes.
- Les valeurs se calculent avec le jeu retenu `p_cal` (pas `p_test`).
- Le markdown reste statique. La concordance texte / `CHIFFRES` est vérifiée **hors notebook** par un
  script jetable (scratchpad) qui cherche chaque valeur formatée dans les markdowns §11-12 ; ce script
  n'est pas commité.

**Consequences — LOCKED :** tout chiffre ajouté à §11-12 a une entrée dans `CHIFFRES` ; un chiffre sans
entrée est retiré du texte (FR-015).

**Alternatives :** extension `python-markdown` / templating — rejeté (dépendance, rendu non garanti) ;
lecture du `.ipynb` par lui-même pour vérifier le texte — rejeté (artifice visible par le jury).

**Revisit when :** jamais.

### ADR-010: Estimation du facteur spread — GMM retenue, biais AR(1) par simulation

**Status:** Accepted   **Drives:** FR-020, FR-021, FR-022

**Context:** §9.2 estime $(a_y, \sigma_y)$ par moindres carrés sur la structure par terme des vols et
$\rho$ au seul tenor 20 ans ; la vitesse AR(1) imprimée en comparaison varie de 0,19 à 5,03 selon la
fenêtre (biais de petit échantillon, `addendum.md`). Décision de l'auteur : GMM retenue, biais documenté.

**Decision — structure du §9 :**
- 9.1 inchangé (non-identification par la courbe OAT).
- 9.2 « Ce que l'historique identifie » : texte existant (moments, invariance P/Q, exclusion du 2 ans),
  complété par FR-022 ; la cellule existante garde `spread_stats`, `fit_vol_term_structure`, `est`,
  `fits`, `RHO_MIN`, `RHO_MAX`, `TENORS`, `T_SJ` et la figure, mais **ne définit plus** `A_Y, S_Y, RHO,
  p_cal` : l'estimation en deux temps y est conservée sous `A_Y_2T, S_Y_2T, RHO_2T` pour comparaison.
- 9.3 « Estimation conjointe par la méthode des moments généralisée » (nouveau markdown + bibliothèque +
  exécution) : définit `A_Y, S_Y, RHO, p_cal` (seul endroit) et `GMM`.
- 9.4 « Vitesse historique et biais de petit échantillon » (nouveau markdown + exécution) : déplace et
  remplace le paragraphe AR(1) actuel.

**Decision — GMM (§9.3) :**
- Données : variations quotidiennes du spread (OAT − €STR) et du swap €STR aux tenors `TENORS` (5 à
  30 ans), fenêtre 2021-01-01 → `DATE_OBS`, dates communes à tous les tenors.
- 12 moments : 6 volatilités annualisées (écart-type × √252, ddof = 1) contre $\sigma_y H_{a_y}(\tau)/\tau$ ;
  6 corrélations spread / €STR de même tenor contre $\rho$.
- Covariance des moments $S$ (12 × 12) par **bootstrap par blocs mobiles** des jours (blocs de 20 jours,
  500 tirages, graine 3).
- Étape 1 : $W_1 = \mathrm{diag}(S)^{-1}$ ; étape 2 : $W_2 = S^{-1}$. Retenu : étape 2 si
  $\mathrm{cond}(S) < 10^{8}$, sinon étape 1 (et le notebook le dit).
- Bornes : $a_y \in [0{,}001 ; 5]$, $\sigma_y > 0$, $\rho \in [-1, 1]$ (`least_squares` sur
  $W^{1/2} g(\theta)$).
- Sorties : estimations, écarts-types $(G'WG)^{-1}G'WSWG(G'WG)^{-1}$ (G par différences finies), statistique
  $J = g'S^{-1}g$ et p-value $\chi^2(12 - k)$ avec $k$ paramètres libres, moments ajustés et observés,
  comparaison avec l'estimation en deux temps. Si $a_y$ est à sa borne, écarts-types et $J$ sont calculés
  à $a_y$ fixé ($k = 2$) et le notebook le signale.

**Decision — biais AR(1) (§9.4) :**
- Pour chaque fenêtre de `fenetres` : vitesse observée (fonction `ar1_speed` existante), distribution de
  l'estimateur sous une vraie vitesse nulle (2 000 trajectoires de même longueur, graine 2, trajectoires
  simulées par `scipy.signal.lfilter`), moyenne, quantiles 5 % et 95 %, rang de la valeur observée.
- Vitesse corrigée par **inférence indirecte** : $a$ tel que la moyenne simulée de l'estimateur égale la
  valeur observée, mêmes chocs pour tous les $a$ (nombres aléatoires communs), recherche par `brentq` sur
  $[0 ; 20]$ ; si la valeur observée est sous la moyenne à $a = 0$, la vitesse corrigée vaut 0 (borne).
- Conclusion imprimée et rédigée : compatibilité avec $a_y \approx 0$ ; cette vitesse n'entre pas dans le
  pricing.

**Consequences — LOCKED :** `A_Y, S_Y, RHO, p_cal` viennent de §9.3 et de nulle part ailleurs ; les
fourchettes de sensibilité de $\rho$ au §11 restent `RHO_MIN, RHO_MAX` (fenêtres et tenors) ; le scénario
« a_y AR(1) » du §11 lit désormais la vitesse **corrigée** de la fenêtre 2021-2026 si elle est non nulle,
sinon il est remplacé par $a_y = 0{,}2$ (ordre de grandeur de l'estimateur brut) et le libellé le dit.

**Alternatives :** Newey-West + méthode delta pour $S$ — rejeté (algèbre propre aux corrélations, plus de
code) ; correction de Kendall analytique — rejeté (sous-estime le biais près de la racine unitaire, slide
53) ; filtre de Kalman — hors périmètre (PRD).

**Revisit when :** la GMM rejette fortement *et* déplace $\rho$ hors de `[RHO_MIN, RHO_MAX]`.

### ADR-011: Édition, exécution et commit du notebook

**Status:** Accepted   **Drives:** NFR-001, NFR-003, NFR-004

**Context:** le notebook est un fichier JSON avec sorties ; les indices de cellules changent dès qu'on en
insère.

**Decision:**
- Édition cellule par cellule avec l'outil d'édition de notebook (NotebookEdit) ou un script `nbformat`
  jetable dans le scratchpad ; jamais d'édition manuelle du JSON.
- Une cellule se désigne par **section + rôle** (« §9.3, bibliothèque ») ou par la première ligne de sa
  docstring, **jamais par son indice**.
- Après chaque story : `uv run jupyter nbconvert --to notebook --execute --inplace main/oat_option_pricer.ipynb`
  puis vérification (§7, Testing strategy).
- Le notebook est commité **avec ses sorties** (les contrôles sont la preuve). Un commit par story, sur
  `main`, message selon ADR-006. Pas de push (ADR-007).

**Consequences — LOCKED :** cette procédure pour toute story qui touche le notebook.

**Alternatives :** notebook commité sans sorties — rejeté (le jury lit les sorties).

**Revisit when :** jamais.

### ADR-012: Pas de parallélisme sur le notebook

**Status:** Accepted   **Drives:** NFR-004

**Context:** BMAD planifie des vagues de stories parallèles sur des périmètres de fichiers disjoints ; ici
toutes les stories de code partagent un seul fichier JSON, non fusionnable de façon fiable.

**Decision:** les stories qui modifient `main/oat_option_pricer.ipynb` s'exécutent **une à la fois**
(largeur de vague 1). Les périmètres de cellules (§4) servent à la revue et à limiter les régressions,
pas au parallélisme. Seules des stories ne touchant que `CONTEXTE.md` / `PLAN.md` peuvent être planifiées
à côté — en pratique STORY-008 dépend de toutes les autres.

**Consequences — LOCKED :** `maxParallel` effectif = 1 pour le notebook ; ordre des stories en §4
(« Séquencement »).

**Alternatives :** worktrees + fusion manuelle du JSON — rejeté (conflits de sorties et d'identifiants
de cellules).

**Revisit when :** jamais.

---

## 4. Component Design — Composants

### Component Overview
Un composant = une section du notebook (ou un document de cadrage). Rôles des cellules : **M** markdown,
**B** bibliothèque, **E** exécution. Les composants modifiés par cette version sont détaillés ensuite.

| Section | Cellules | Fournit (noms publics, voir §6) | Requiert | Modifiée par |
|---|---|---|---|---|
| §1 Données | M, E (chargement), E (figures) | `estr, cube, oat, hist_oat, hist_estr, repo_data, DATE_OBS, DATE_VAL, FICHIER_REPO, FINANCEMENT_LONG, tenor_years` | fichiers `data/` | STORY-001, STORY-002, STORY-003 |
| §2 Courbe €STR | M, B+E | `curve` | §1 | — |
| §3 Courbe OAT | M, B+E | `risky, oat46, dirty46, bond, ECHEANCES` | §1, §2 | — |
| §4 Briques | M, B+E | `params, H, V, V_xy, V_bar, var_factor, cov_xy, cov_factor_int, cov_cross_int, swap_xy, ferme` | — | — |
| §5 HW1F | M, B, E | `hw1f_model, black, swaption, bachelier_atm, atm_rate` | §2-§4 | — |
| §6 Facteur taux | M, B, E | `A_X, S_X` | §1, §2, §5 | — |
| §7 Modèle 2F | M, B, E | `hw2f_model, p_test` | §4, §5, §6 | STORY-013 (M) |
| §8 Option | M, B, E | `repo_curve, forward_repo, forward_flows, recentrage, oat_option, repo` | §1-§7 | STORY-001, STORY-002, STORY-003 |
| §9 Facteur spread | M, B+E (9.1), E (9.2), M+B+E (9.3), M+E (9.4) | `est, fits, RHO_MIN, RHO_MAX, TENORS, T_SJ, A_Y_2T, S_Y_2T, RHO_2T, A_Y, S_Y, RHO, p_cal, GMM, AR1` | §1, §4, §6, §7 | STORY-011, STORY-012, STORY-013 |
| §10 Monte-Carlo | M, B, E | `hw2f_mc, m_cal, opts` | §8, §9 | — (ré-exécuté) |
| §11 Résultats | M, E (tableaux), E (sensibilités), E (chiffres cités), M (lecture) | `CHIFFRES` | §8-§10 | STORY-002 (sensibilités repo), STORY-005, STORY-006 |
| §12 Conclusion | M | — | `CHIFFRES` | STORY-007 |
| Cadrage | `CONTEXTE.md`, `PLAN.md` | — | tout | STORY-008 |

### Component: §1 Données
**Responsibility :** charger toutes les données et la configuration (chemins, dates, règle repo longue).
**Interfaces Provided :** `repo_data` (colonnes `tenor, T, spread` en décimal), `FICHIER_REPO`,
`FINANCEMENT_LONG`. **Interfaces Required :** `data/market data bloom.xlsx`, `data/repo_marche.csv`.
**Data Owned :** DataFrames de marché. **ADRs :** ADR-003, ADR-007, ADR-008.
**NFRs Addressed :** NFR-006 → un seul chemin repo ; NFR-005 → markdown sans « fictif » après STORY-003.

### Component: §8 Option sur OAT
**Responsibility :** forward repo, recentrage, prix fermé.
**Interfaces Provided :** `repo_curve(curve, T, spread)` avec `.s(T)`, `.df(T)`, `.T_max` ; `oat_option`.
**Interfaces Required :** `repo_data`, `FINANCEMENT_LONG`, `curve`, `risky`, `oat46`, `dirty46`.
**ADRs :** ADR-003, ADR-008. **NFRs :** NFR-002 → parités, recentrage, cas limites inchangés.

### Component: §9 Facteur spread
**Responsibility :** estimer $(a_y, \sigma_y, \rho)$ et justifier la méthode.
**Interfaces Provided :** `A_Y, S_Y, RHO, p_cal` (§9.3 seulement), `GMM` (dict de résultats), `AR1`
(DataFrame du biais par fenêtre), `RHO_MIN, RHO_MAX`, `est`, `T_SJ`, `TENORS`.
**Interfaces Required :** `hist_oat, hist_estr, DATE_OBS, H, params, A_X, S_X`.
**ADRs :** ADR-004 (graines 2 et 3), ADR-010. **NFRs :** NFR-003, NFR-007.

### Component: §11 Résultats
**Responsibility :** tableaux, sensibilités, `CHIFFRES`, lecture des résultats.
**Interfaces Provided :** `CHIFFRES`. **Interfaces Required :** `p_cal, m_cal, opts, repo, repo_data,
RHO_MIN, RHO_MAX, est, AR1, GMM, T_SJ, ECHEANCES`.
**ADRs :** ADR-008 (scénarios repo), ADR-009, ADR-010 (scénario a_y). **NFRs :** FR-015.

### Séquencement des stories (largeur 1, ADR-012)
1. **STORY-004** — exécution de référence (aucune modification du notebook) ;
2. **STORY-011** → **STORY-012** → **STORY-013** (EPIC-008, indépendant de la courbe repo) ;
3. **STORY-005** — cellule `CHIFFRES` (sa structure ne dépend pas du repo ; ses valeurs suivront) ;
4. *(attente de la courbe repo et de la réponse à Q1)* **STORY-001** → **STORY-002** → **STORY-003** ;
5. **STORY-006** → **STORY-007** — réécriture de §11-12 sur les sorties finales ;
6. **STORY-008** — `CONTEXTE.md`, `PLAN.md`.

### Périmètre de cellules par story (Owned scope)
| Story | Cellules possédées |
|---|---|
| STORY-004 | aucune ; produit `bmad-output/reference/` |
| STORY-011 | §9.2 M (paragraphe AR(1) retiré), §9.4 M + E (nouvelles) |
| STORY-012 | §9.2 M (paragraphe estimation), §9.2 E (bloc « paramètres retenus » → `*_2T`), §9.3 M + B + E (nouvelles), §11 E sensibilités (scénario a_y, ADR-010) |
| STORY-013 | §7 M, §9 M (intro, 9.2 invariance P/Q) |
| STORY-005 | §11 E « Chiffres cités » (nouvelle) |
| STORY-001 | `data/repo_marche.csv` (nouveau), `data/repo_fictif.csv` (supprimé), §1 E (`FICHIER_REPO`) |
| STORY-002 | §1 E (`FINANCEMENT_LONG`), §8 M (8.2), §8 B (`repo_curve`), §8 E, §11 E sensibilités (scénarios repo) |
| STORY-003 | §1 M, §1 E (libellé), §8 E (libellé), §11 M d'introduction |
| STORY-006 | §11 M « Lecture des résultats », §11 E « Chiffres cités » (entrées) |
| STORY-007 | §12 M, §11 E « Chiffres cités » (entrées de §12) |
| STORY-008 | `CONTEXTE.md`, `PLAN.md` |

---

## 5. Data Model — Modèle de données

> Régi par ADR-003. Pas de base de données : les entités sont des objets du noyau, la persistance est le
> fichier `.ipynb` (sources + sorties) et les fichiers de `data/`.

### Entity: `repo_data` (DataFrame)
**Attributes :** `tenor` (str, ex. `"3M"`), `T` (float, années), `spread` (float, décimal, zéro continu
repo − zéro €STR). **Constraints :** `T` strictement croissant ; au moins un tenor ≤ 1 an.
**Source :** `data/repo_marche.csv` — colonnes `Tenor,Spread_bp`, commentaires `#` (source, ticker,
date 08/09/2026).

### Entity: `repo_curve`
**Attributes :** `curve` (courbe €STR), `T`, `spread`, `T_max` (= `T[-1]`), règle `FINANCEMENT_LONG`.
**Methods :** `s(T)` spread appliqué, `df(T)` = $P^M(0,T)e^{-s(T)T}$. **Relationships :** utilisée par
`forward_repo`, `oat_option`, scénarios du §11.

### Entity: `params` (dataclass immuable)
**Attributes :** `a_x, s_x, a_y, s_y, rho` (float). **Instances nommées :** `p_test` (provisoire, §7-8),
`p_cal` (retenu, §9.3).

### Entity: `GMM` (dict, §9.3)
**Attributes :** `theta` (dict `a_y, s_y, rho`), `se` (dict, mêmes clés ; `None` pour un paramètre à sa
borne), `J` (float), `p_value` (float), `dof` (int), `etape` (1 ou 2), `cond_S` (float),
`borne_a_y` (bool), `moments` (DataFrame : `tenor, vol_obs, vol_mod, corr_obs, corr_mod`), `n` (int).

### Entity: `AR1` (DataFrame, §9.4)
**Index :** fenêtre (`"2021-2026"`, `"3 ans"`, `"1 an"`). **Columns :** `n`, `a_obs`, `moy_a0`, `q05_a0`,
`q95_a0`, `rang_obs`, `a_corrige`.

### Entity: `CHIFFRES` (dict ordonné, §11)
**Attributes :** clé = libellé français (ex. `"forward clean 1 an"`), valeur = chaîne formatée comme dans
le texte (virgule décimale, unité incluse si le texte l'inclut).

### Storage Strategy
- **Primary store :** fichiers de `data/` (lecture seule depuis le notebook) ; notebook commité avec
  sorties (ADR-011).
- **Cache :** aucun (ADR-004).
- **File :** `bmad-output/reference/` — sorties texte de l'exécution de référence (STORY-004) et script
  d'extraction `extraire_sorties.py` réutilisé par chaque story pour comparer ses sorties, hors notebook.
- **Retention / backup :** historique git local.

---

## 6. API Specifications — Interfaces

> Pas d'API REST, GraphQL ni gRPC, pas de versionnage d'API : l'interface est le **contrat de noms
> publics** du noyau (ADR-002). AuthN : sans objet (ADR-007).

### Noms publics existants (LOCKED, ne pas renommer)
`np, pd, plt` · `estr, cube, oat, hist_oat, hist_estr, repo_data, DATE_OBS, DATE_VAL, FICHIER, FICHIER_REPO,
tenor_years` · `curve, zc_curve` · `risky, oat_curve, bond, oat46, dirty46, ECHEANCES` · `params, H, V,
V_xy, V_bar, var_factor, cov_xy, cov_factor_int, cov_cross_int, swap_xy` · `hw1f_model, black, swaption,
bachelier_atm, atm_rate` · `A_X, S_X` · `hw2f_model, p_test` · `repo_curve, forward_repo, forward_means,
forward_flows, recentrage, oat_option, repo` · `ar1_speed, spread_stats, fit_vol_term_structure, est, fits,
fenetres, TENORS, T_SJ, RHO_MIN, RHO_MAX` · `A_Y, S_Y, RHO, p_cal` (déplacés en §9.3) · `hw2f_mc, m_cal,
opts` · `atm_table`.

### Noms existants promus en noms publics (v1.1, story 6.2)
Lus par la cellule `CHIFFRES` sans être recalculés, pour ne pas diverger des tableaux imprimés :
`tab_diag` (§6, colonne `residu_bp`) · `mc` (§10, Monte-Carlo à 5 ans), `mcs` (§10, dict `T0 → hw2f_mc`) ·
`res` (§11, tableau par échéance), `fwd` (§11, forwards clean par scénario repo), `scen_repo` (dict
libellé → `repo_curve`), `scen_sy`, `scen_rho`, `scen_ay` (dicts libellé → `(modèle, repo)`).
**LOCKED :** les stories 5.2 et 8.2, qui modifient `scen_repo` et `scen_ay`, gardent ces noms et cette
structure ; aucune cellule ne les réassigne après le §11.

### Nouveaux noms publics
| Nom | Section | Signature / type | Story |
|---|---|---|---|
| `FINANCEMENT_LONG` | §1 | `str`, valeur initiale `"plat"` | STORY-002 |
| `repo_curve.T_max` | §8 | `float` | STORY-002 |
| `A_Y_2T, S_Y_2T, RHO_2T` | §9.2 | `float` (estimation en deux temps) | STORY-012 |
| `spread_moments` | §9.3 | `(hist_oat, hist_estr, tenors, start) -> (m_obs: ndarray[12], dS: ndarray[n,6], dR: ndarray[n,6])` | STORY-012 |
| `model_moments` | §9.3 | `(theta: ndarray[3], tenors) -> ndarray[12]` | STORY-012 |
| `moments_cov_bootstrap` | §9.3 | `(dS, dR, bloc=20, n_boot=500, seed=3) -> ndarray[12,12]` | STORY-012 |
| `gmm_spread` | §9.3 | `(m_obs, S, tenors) -> dict` (entité `GMM`) | STORY-012 |
| `GMM` | §9.3 | `dict` (§5) | STORY-012 |
| `simulate_ar1_speeds` | §9.4 | `(a, n, n_sim=2000, seed=2) -> ndarray[n_sim]` | STORY-011 |
| `ar1_corrige` | §9.4 | `(a_obs, n, n_sim=2000, seed=2) -> float` | STORY-011 |
| `AR1` | §9.4 | `DataFrame` (§5) | STORY-011 |
| `CHIFFRES` | §11 | `dict[str, str]` (§5) | STORY-005 |

### Signatures inchangées
`repo_curve(curve, T, spread)` garde sa signature ; la règle longue est lue dans `FINANCEMENT_LONG`
(ADR-008). `oat_option(m, bd, dirty, repo, T0)` et `.price(K, call=True)` inchangés.

### Error convention
Voir ADR-005 : `assert` pour l'intégrité des données d'entrée, contrôles de modèle imprimés.

### Performance
Aucune cible de latence ; seule contrainte : durée d'exécution complète (NFR-007). Coûts attendus des
ajouts : bootstrap GMM (500 × 12 statistiques sur ≈ 1 450 jours) et simulation AR(1) (2 000 trajectoires ×
3 fenêtres, plus ≈ 30 évaluations `brentq`) — de l'ordre de la seconde à la dizaine de secondes avec
`lfilter`.

---

## 7. FR / NFR Coverage Matrix

| ID | Type | Requirement | Component(s) | ADR(s) | Status |
|----|------|-------------|--------------|--------|--------|
| FR-001 | FR | Données figées au 08/09/2026 | §1 | ADR-003, ADR-005 | Addressed (existant) |
| FR-002 | FR | Courbe €STR recalée | §2 | ADR-003 | Addressed (existant) |
| FR-003 | FR | Courbe OAT, OAT 2046 | §3 | ADR-003 | Addressed (existant) |
| FR-004 | FR | HW1F, Jamshidian | §5 | ADR-005 | Addressed (existant) |
| FR-005 | FR | Facteur taux, diagonale 20 ans | §6 | ADR-003 | Addressed (existant) |
| FR-006 | FR | Modèle 2F recalé | §7 | ADR-003 | Addressed (existant) |
| FR-007 | FR | Calibration du spread (non-identification, historique) | §9.1, §9.2 | ADR-010 | Addressed (existant, réorganisé) |
| FR-008 | FR | Forward repo | §8 | ADR-008 | Addressed |
| FR-009 | FR | Recentrage | §8 | ADR-003 | Addressed (existant) |
| FR-010 | FR | Formule fermée, strike clean | §8 | ADR-003, ADR-005 | Addressed (existant) |
| FR-011 | FR | Monte-Carlo exact | §10 | ADR-004 | Addressed (existant) |
| FR-012 | FR | Résultats et sensibilités | §11 | ADR-008, ADR-010 | Addressed (scénarios repo et a_y modifiés) |
| FR-013 | FR | Courbe repo de marché | §1, §8 | ADR-008, ADR-007 | Addressed |
| FR-014 | FR | Hypothèse de financement long terme | §1, §8 | ADR-008 | Partial — règle « plat » par défaut, choix final suspendu à Q1 |
| FR-015 | FR | Chiffres cités traçables | §11 | ADR-009 | Addressed |
| FR-016 | FR | §11-12 réécrits | §11, §12 | ADR-009, ADR-006 | Addressed |
| FR-017 | FR | Cadrage à jour | `CONTEXTE.md`, `PLAN.md` | ADR-006 | Addressed |
| FR-018 | FR | $\sigma_x(t)$ par morceaux | — | — | Deferred — Won't (décision de l'auteur) |
| FR-019 | FR | Second facteur de spread | — | — | Deferred — Won't |
| FR-020 | FR | Biais de la vitesse AR(1) | §9.4 | ADR-010, ADR-004 | Addressed |
| FR-021 | FR | GMM sur $(a_y, \sigma_y, \rho)$ | §9.3 | ADR-010, ADR-003 | Addressed |
| FR-022 | FR | Cadre RMV, crédit / liquidité | §7, §9 | ADR-006, ADR-010 | Addressed |
| NFR-001 | NFR | Reliability — exécution complète | tout le notebook | ADR-004, ADR-011 | Addressed |
| NFR-002 | NFR | Reliability — contrôles respectés | cellules E | ADR-005 | Addressed |
| NFR-003 | NFR | Reliability — reproductibilité | §9.3, §9.4, §10 | ADR-004 | Addressed |
| NFR-004 | NFR | Maintainability — format académique | tout | ADR-001, ADR-006, ADR-011 | Addressed |
| NFR-005 | NFR | Usability — cadrage éditorial | markdowns, `CHIFFRES` | ADR-006 | Addressed |
| NFR-006 | NFR | Maintainability — remplaçabilité des données | §1 | ADR-008 | Addressed |
| NFR-007 | NFR | Performance — durée d'exécution | §9.3, §9.4 | ADR-010 | Addressed (référence mesurée par STORY-004) |
| NFR-008 | NFR | Security — confidentialité des données | `data/`, git | ADR-007 | Partial — dépend de Q4 |

### Detailed NFR notes (per driver)
- **NFR-004 (format, fichier unique)** : ADR-001 fixe le motif, ADR-012 en tire la conséquence sur le
  parallélisme, ADR-011 la procédure d'édition. Maintainability : frontières de module = sections,
  documentation = markdowns + `CONTEXTE.md`.
- **NFR-001 / NFR-003 (reliability)** : ré-exécution intégrale depuis un noyau neuf à chaque story,
  graines littérales réservées. Pas de redundancy, failover ni backup au-delà de git : sans objet pour un
  notebook local.
- **NFR-002** : un format de contrôle unique ; les nouveaux contrôles (J, moments ajustés, rang AR(1),
  spread repo par échéance) suivent ADR-005.
- **NFR-007 (performance)** : seuls ajouts coûteux bornés en §6 ; mesurés avant / après par la story
  concernée contre la référence STORY-004.
- **Scalability** : sans objet (un utilisateur, un jeu de données fixe) ; aucune décision de scaling.
- **Availability** : sans objet (pas de service : ni uptime, ni monitoring, ni RTO / RPO) ; le notebook
  s'exécute à la demande sur le poste de l'auteur.
- **Security** : ADR-007.

### Testing strategy (stratégie de vérification, exécutée par chaque story)
1. Exécution complète (`nbconvert --execute --inplace`) : 0 erreur, compteurs d'exécution séquentiels
   (NFR-001).
2. Lecture des contrôles des sections 2 à 10 contre les seuils de NFR-002 ; comparaison des sorties texte
   avec `bmad-output/reference/` : seules les sections attendues par la story changent.
3. Recherche plein texte : « knock-out », « fictif » (après EPIC-005), « L = », chiffres du papier (NFR-005).
4. `git diff --stat` : seuls les fichiers du périmètre de la story ; `main/main.ipynb` et `pyproject.toml`
   inchangés (NFR-004).
5. Pour STORY-006 / STORY-007 : script jetable de concordance texte / `CHIFFRES` (ADR-009).

---

## 8. Technology Stack

| Layer | Choice | Version | Rationale (→ driver) | ADR |
|-------|--------|---------|----------------------|-----|
| Langage | Python | 3.12 (`uv`, `uv.lock`) | imposé par le cadrage, environnement figé (NFR-003) | ADR-011 |
| Calcul | NumPy | `uv.lock` | déjà utilisé ; vectorisation des moments et du bootstrap | ADR-010 |
| Calcul | SciPy (`optimize.least_squares`, `optimize.brentq`, `stats.chi2`, `signal.lfilter`) | `uv.lock` | déjà une dépendance ; `lfilter` simule les AR(1) sans boucle Python (NFR-007) ; `chi2` pour la p-value de J | ADR-010 |
| Données | pandas, openpyxl | `uv.lock` | lecture Excel / CSV existante | ADR-003, ADR-008 |
| Figures | matplotlib | `uv.lock` | déjà utilisé | ADR-001 |
| Exécution | Jupyter, nbconvert, nbformat, ipykernel | `uv.lock` | exécution complète en ligne de commande (NFR-001) | ADR-011 |
| Database | aucune | — | données fixes en fichiers | ADR-003 |

**Alternatives considered :** `statsmodels` (GMM, AR) — rejeté : nouvelle dépendance (NFR-004) pour
quelques dizaines de lignes de NumPy ; `numba` pour la simulation — rejeté : `lfilter` suffit.

---

## 9. Trade-off Analysis

### Trade-off: texte statique + `CHIFFRES` contre texte généré
**Decision :** texte statique, cellule récapitulative, vérification hors notebook (ADR-009).
**Options :** (A) markdown statique — lisible, aucune dépendance, désynchronisation possible ; (B) markdown
généré (extension, `IPython.display.Markdown`) — toujours synchrone, mais texte du mémoire dans du code.
**Rationale :** le jury lit un texte rédigé ; NFR-004 interdit les dépendances.
**Accepted :** Benefit lisibilité / Cost vérification manuelle / Mitigation script de concordance.
**Revisit when :** une désynchronisation échappe à STORY-006 ou STORY-007.

### Trade-off: covariance des moments par bootstrap par blocs contre Newey-West
**Decision :** bootstrap par blocs mobiles (ADR-010).
**Options :** (A) bootstrap — même code pour vols et corrélations, gère l'autocorrélation ; coût
d'exécution, dépend de la longueur de bloc ; (B) Newey-West + méthode delta — rapide, mais dérivées des
corrélations à écrire à la main.
**Rationale :** simplicité du code (NFR-004) à coût d'exécution acceptable (NFR-007).
**Revisit when :** $S$ mal conditionnée (`cond_S` ≥ 1e8) — l'étape 1 est alors retenue.

### Trade-off: GMM comme estimateur retenu contre complément
**Decision :** retenu (décision de l'auteur, `decision-log.md`).
**Options :** (A) GMM retenue — une seule procédure, incertitude chiffrée ; déplace $\rho$ et tous les
prix ; (B) GMM en complément — aucun prix ne bouge, mais deux estimateurs à défendre.
**Accepted :** Cost : §10-12 à relire ; Mitigation : EPIC-008 avant la réécriture de §11-12.

### Trade-off: correction du biais AR(1) par simulation contre Kendall
**Decision :** inférence indirecte par simulation (ADR-010).
**Options :** (A) simulation — exacte à l'erreur Monte-Carlo près, valable près de la racine unitaire ;
(B) Kendall $-(1+3\phi)/n$ — une ligne, mais sous-estime le biais quand $\phi \to 1$ (slide 53).

### Trade-off: sérialisation contre parallélisme
**Decision :** largeur de vague 1 sur le notebook (ADR-012).
**Accepted :** Benefit : aucun conflit de fusion / Cost : durée totale plus longue / Mitigation : stories
courtes, un commit chacune.

### Trade-off: règle longue du repo en code contre lignes de CSV
**Decision :** constante `FINANCEMENT_LONG` + `repo_curve.s` (ADR-008).
**Accepted :** Benefit : le CSV ne contient que des cotations, l'hypothèse est lisible dans le notebook /
Cost : changer d'hypothèse touche le code (une constante).

---

## 10. Deployment Architecture — Exécution

### Environments
Un seul environnement : le poste de l'auteur, environnement virtuel `uv` (`.venv`). Pas de staging ni de
production ; pas d'hébergement ni d'infrastructure distante.

### Topology
Notebook exécuté localement par `uv run jupyter nbconvert --to notebook --execute --inplace
main/oat_option_pricer.ipynb` ; lecture interactive dans Jupyter.

### Strategy
- **Deployment method :** sans objet ; la « livraison » est le commit du notebook avec sorties (ADR-011).
- **Rollback :** `git revert` du commit de la story.
- **Scaling :** sans objet.

---

## 11. Future Considerations

**Anticipated changes :**
- Réponse à Q1 : nouvelle valeur de `FINANCEMENT_LONG` dans `repo_curve.s` (ADR-008).
- Réponse à Q4 : éventuelle exclusion de `data/` du suivi (ADR-007).
- Perspectives du mémoire (non planifiées) : estimation jointe P / Q par filtre de Kalman, régimes cachés
  pour l'instabilité de $\rho$, second facteur de spread.

**Revisit triggers (aggregated from ADRs) :** réponse à Q1 ; réponse à Q4 ; `cond_S` ≥ 1e8 ; $\rho$ GMM
hors `[RHO_MIN, RHO_MAX]` ; désynchronisation texte / `CHIFFRES` détectée ; durée d'exécution au-delà de
NFR-007.

---

## Appendix

### Glossary
Voir `project-context.md` (Glossary). Ajouts : **GMM** méthode des moments généralisée ; **J de Hansen**
statistique de sur-identification ; **bootstrap par blocs mobiles** rééchantillonnage de blocs de jours
consécutifs ; **inférence indirecte** correction d'un estimateur biaisé par simulation de sa loi ;
**RMV** recouvrement en valeur de marché.

### References
- PRD : `bmad-output/prd.md` (v1.2) ; addendum : `bmad-output/addendum.md`
- Decision log : `bmad-output/decision-log.md`
- Project context : `bmad-output/project-context.md`
- Cadrage : `CONTEXTE.md`, `PLAN.md`
- Cours : `doc/econo modele affine.pdf` (Monfort, Pegoraro, Renne, cours 5)

### Document History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-10-01 | Winston (Architect) | Initial architecture |
| 1.1 | 2026-10-01 | bmad-epics-and-stories | §6 : `tab_diag, mc, mcs, res, fwd, scen_repo, scen_sy, scen_rho, scen_ay` promus en noms publics ; §5 : `bmad-output/reference/` contient aussi `extraire_sorties.py` (story 6.1) |

---

**END OF DOCUMENT** — prêt pour `bmad-epics-and-stories` une fois validé.
