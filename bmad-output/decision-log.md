# Decision Log — BondOptionPricer

Registre des décisions prises au fil des workflows BMAD, en ajout seul. Chaque skill (brief, PRD,
architecture, stories) y ajoute ses décisions pour que le raisonnement reste visible et cohérent.

**Utilisation :** ajouter chaque nouvelle entrée en haut du registre (la plus récente d'abord). Ne jamais
réécrire ni supprimer une entrée : la remplacer par une nouvelle entrée qui y renvoie.

## Format d'une entrée

```
### AAAA-MM-JJ — <titre court>
- **Decision:** <ce qui est décidé>
- **Rationale:** <pourquoi ; alternatives envisagées>
- **Made by:** <skill/workflow, ex. bmad-init, prd, architecture>
- **Supersedes:** <lien vers l'entrée remplacée, le cas échéant>
```

---

### 2026-10-01 — GMM : pondération diagonale retenue (ADR-013)
- **Decision:** L'estimateur retenu du facteur spread est la GMM à pondération diagonale
  $W_1 = \mathrm{diag}(S)^{-1}$ : $a_y = 0{,}001$ (borne), $\sigma_y = 0{,}3374\,\%$ (é.-t. 0,0182 %),
  $\rho = 0{,}130$ (é.-t. 0,040). La GMM efficace $S^{-1}$ ne sert qu'au test J
  ($J = 73{,}7$, 10 ddl, p = 8,7e-12 : rejet du spread à un facteur).
- **Rationale:** Le déclencheur d'ADR-010 s'est produit : la GMM efficace donnait $\rho = 0{,}028$, sous
  les six corrélations observées, par des poids implicites négatifs, dus aux erreurs de moments corrélées
  à 0,8-0,98 entre tenors (biais d'Altonji et Segal, 1996). La pondération diagonale donne un $\rho$ dans
  l'enveloppe des moments ; l'écart à l'estimation en deux temps (0,152, tenor 20 ans seul) vient de la
  prise en compte des autres tenors. Effet : call ATM −0,4 % à −0,9 % selon l'échéance.
- **Made by:** Claude Code pendant la story 8.2. Décision d'architecture à faire valider par l'auteur.
- **Supersedes:** la règle de pondération d'ADR-010 (entrée « Architecture v1.0 »)

### 2026-10-01 — Backlog : 11 stories compilées (`epics.md`, `stories/`)
- **Decision:** Epics 5 (repo, 3 stories), 6 (cohérence, 5), 8 (spread, 3). Ordre :
  `6.1 → 8.1 → 8.2 → 8.3 → 6.2 → 5.1 → 5.2 → 5.3 → 6.3 → 6.4 → 6.5`. 8 stories `ready-for-dev` (6.x, 8.x),
  3 en `backlog` (5.x : attendent la courbe repo Q2 et la décision Q1 ; 5.2 spécifiée avec la règle
  « plat », à mettre à jour si Q1 en retient une autre). Le contrôle de recouvrement signale 45 conflits,
  tous sur `main/oat_option_pricer.ipynb` : voulus et sérialisés par la chaîne de dépendances (ADR-012).
  Architecture v1.1 : `tab_diag, mc, mcs, res, fwd, scen_repo, scen_sy, scen_rho, scen_ay` promus en noms
  publics (lus par `CHIFFRES` sans recalcul) ; contrainte ajoutée aux Dev Notes de 5.2 et 8.2.
- **Rationale:** Choix tranchés pendant la compilation et retenus :
  - 6.1 crée `bmad-output/reference/extraire_sorties.py`, réutilisé par toutes les stories pour comparer
    leurs sorties.
  - 6.4 ne cite que des chiffres présents dans `CHIFFRES` : la limite $\sigma_x(t)$ cite le résidu de
    2,3 bp, pas l'effet « < 3 % ».
  - 6.4 vérifie si le spread 2 ans négatif tient surtout à 2021-2023, avant la rupture du générique.
  - 5.1 impose des tenors en W / M / Y (`tenor_years` lit « 1D » comme 1 an et échoue sur ON / TN).
  - 8.1 prévoit une vitesse corrigée nulle sur les trois fenêtres, donc le scénario $a_y = 0{,}2$ au §11.
  - 8.3 remplace la phrase du §7 « sans l'interpréter comme une intensité de défaut » pour qu'elle reste
    compatible avec le cadre RMV.
- **Made by:** bmad-epics-and-stories
- **Supersedes:** none

### 2026-10-01 — Architecture v1.0 : 12 ADR (`architecture.md`)
- **Decision:**
  - ADR-001 notebook unique, monolithe en couches, dépendances descendantes.
  - ADR-002 interface entre cellules = contrat de noms publics (§6) ; aucune lecture de noms transitoires.
  - ADR-003 unités (décimal, années ACT/365, prix pour 1, ×100 à l'affichage) ; `p_cal` construit une
    seule fois en §9.3.
  - ADR-004 noyau séquentiel ; graines littérales, 2 (AR(1)) et 3 (bootstrap GMM) réservées.
  - ADR-005 contrôles imprimés « libellé : valeur (seuil) » ; `assert` réservé aux données d'entrée.
  - ADR-006 nommage existant imposé (classes en minuscules, constantes en majuscules), français,
    commits « Notebook : … ».
  - ADR-007 pas d'AuthN/AuthZ ; pas de push dans les stories (Q4).
  - ADR-008 courbe repo dans `data/repo_marche.csv`, `FICHIER_REPO` seul point d'entrée, règle longue
    `FINANCEMENT_LONG` (défaut « plat », autre valeur après Q1), sensibilités par translations −25 / −10 /
    0 / +10 / +25 bp + financement au taux OAT.
  - ADR-009 cellule `CHIFFRES` en fin de §11, texte statique, concordance vérifiée hors notebook.
  - ADR-010 §9 réorganisé (9.3 GMM retenue : 12 moments, bootstrap par blocs de 20 jours, deux étapes,
    J de Hansen, borne de a_y ; 9.4 biais AR(1) par inférence indirecte avec nombres aléatoires communs).
  - ADR-011 édition par cellule (jamais par indice), `nbconvert --execute --inplace`, notebook commité
    avec sorties, un commit par story.
  - ADR-012 aucune story parallèle sur le notebook (largeur de vague 1).
- **Rationale:** voir `architecture.md` §3 et §9 ; drivers NFR-004 (fichier unique), NFR-001/003,
  NFR-002, FR-015, NFR-006.
- **Made by:** bmad-architecture
- **Supersedes:** none

### 2026-10-01 — Estimation du facteur spread : GMM retenue, biais AR(1) corrigé, cadre RMV
- **Decision:** Nouvel EPIC-008 (FR-020 à FR-022, Should). (1) La vitesse AR(1) du §9.2 est présentée avec
  son biais de petit échantillon et une version corrigée. (2) $(a_y, \sigma_y, \rho)$ sont estimés
  conjointement par GMM sur les volatilités du spread et les corrélations spread / €STR des tenors 5-30 ans ;
  **la GMM devient l'estimateur retenu**, l'estimation en deux temps reste imprimée en comparaison. (3) Le
  §7 et le §9 ancrent $\bar r = r + y$ dans le cadre RMV et interprètent $y$ (crédit + liquidité), sans
  paramètre de perte. EPIC-008 se termine avant la réécriture de §11-12.
- **Rationale:** Demande de l'auteur après lecture du cours de Monfort, Pegoraro et Renne
  (`doc/econo modele affine.pdf`). Une simulation montre que les trois vitesses AR(1) (0,19 ; 0,97 ; 5,03)
  sont compatibles avec une vitesse nulle : leur variation selon la fenêtre est le biais en 1/n. La GMM
  remplace deux estimations séparées par une seule procédure, donne des écarts-types et un test de la
  structure à un facteur ; elle utilise toutes les corrélations au lieu du seul tenor 20 ans. Écarté :
  Kalman / Chen-Scott (modèle homogène dans le temps et primes de risque à estimer, contraire à la
  simplicité du notebook), régimes cachés (perte de la formule fermée).
- **Made by:** auteur + bmad-prd (mise à jour v1.2)
- **Supersedes:** none

### 2026-10-01 — Pas de volatilité $\sigma_x(t)$ par morceaux
- **Decision:** FR-018 passe de Could à Won't ; EPIC-007 est abandonné (STORY-009, STORY-010 retirées). La
  perspective du §12 devient une limite : pour des options européennes, $\sigma_x(t)$ par morceaux revient à
  recaler $\sigma_x$ échéance par échéance, effet borné par les résidus de la diagonale.
- **Rationale:** Décision de l'auteur. Une option européenne ne dépend de $\sigma_x(\cdot)$ que par la variance
  intégrée jusqu'à $T_0$ (le profil n'importe que pour une bermudienne). L'effet se limite aux résidus du fit
  constant (2,3 bp de vol au plus), soit moins de 3 % sur le call ATM — bien en deçà de l'hypothèse de
  financement ou de l'incertitude sur $\rho$.
- **Made by:** auteur (revue du PRD)
- **Supersedes:** l'entrée « PRD : priorités des nouvelles exigences » pour FR-018 uniquement

### 2026-10-01 — PRD : priorités des nouvelles exigences
- **Decision:** Must pour la courbe repo de marché (FR-013), l'hypothèse de financement long terme (FR-014),
  la traçabilité des chiffres cités (FR-015) et la réécriture de §11-12 (FR-016) ; Should pour la mise à
  jour de `CONTEXTE.md` / `PLAN.md` (FR-017) ; Could pour $\sigma_x(t)$ par morceaux (FR-018) ; Won't pour
  un second facteur de spread (FR-019).
- **Rationale:** Aux échéances longues le prix dépend d'abord du forward, donc du repo : sans FR-013/014
  les résultats ne sont pas défendables, sans FR-015/016 le texte n'est pas vérifiable. FR-018 améliore le
  recalage sans changer la thèse ; FR-019 changerait le modèle à deux facteurs étudié. FR-018 reste à
  confirmer par l'auteur (`addendum.md`, Q3).
- **Made by:** bmad-prd
- **Supersedes:** none

### 2026-10-01 — PRD : l'existant comme contrat de non-régression
- **Decision:** Les FR-001 à FR-012 décrivent les capacités déjà livrées (sections 1 à 11) avec le statut
  « fait » ; leurs critères d'acceptation reprennent les contrôles imprimés par le notebook. Les
  titres de section du PRD restent en anglais (repères des skills BMAD), le contenu est en français.
- **Rationale:** Projet brownfield : les stories à venir modifient des sections existantes ; il faut un
  critère explicite de ce qui ne doit pas casser.
- **Made by:** bmad-prd
- **Supersedes:** none

### 2026-10-01 — Décisions antérieures à BMAD reprises telles quelles
- **Decision:** Le cadrage de `CONTEXTE.md` fait foi : option vanille collatéralisée €STR (jamais de
  knock-out), forward repo au taux €STR + spread repo, strike clean, échéances 1-2-5-7-10-12-15 ans,
  facteur taux sur la diagonale co-terminale 20 ans, facteur spread par la structure par terme des
  volatilités du spread, aucune comparaison externe (papier, options cotées). Le livrable reste un seul
  notebook au format académique.
- **Rationale:** Ces choix sont déjà justifiés et implémentés dans les sections 1 à 12 du notebook ; la
  planification BMAD part de cet existant (brownfield) au lieu de le rediscuter.
- **Made by:** bmad-init
- **Supersedes:** none

### 2026-10-01 — Langue des documents : français
- **Decision:** Les artefacts BMAD sont rédigés en français (`config.yaml` → `languages`).
- **Rationale:** Le mémoire, `CONTEXTE.md`, `PLAN.md` et le notebook sont en français.
- **Made by:** bmad-init
- **Supersedes:** none

### 2026-10-01 — Track selected: bmad-method
- **Decision:** Initialized this project on the **bmad-method** track.
- **Rationale:** Choix de l'auteur. Signaux de taille : un seul rédacteur, aucune contrainte de conformité
  ou d'infrastructure, un projet existant avec 3 chantiers restants — l'heuristique aurait suggéré Quick
  Flow. Le track BMad Method est retenu pour disposer d'un PRD et d'un document d'architecture qui
  formalisent les exigences du mémoire et la structure du notebook avant de découper les stories.
- **Made by:** bmad-init
- **Supersedes:** none
