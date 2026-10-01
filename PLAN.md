# Plan — état d'avancement du notebook `main/oat_option_pricer.ipynb`

Le cadrage (contrat, modèle, calibration, conventions) est dans `CONTEXTE.md`. Le notebook est séquentiel :
chaque section = un markdown (théorie, justification) + une cellule bibliothèque + une cellule de contrôles.
La planification détaillée (PRD, architecture, stories, registre des décisions) est dans `bmad-output/`.

## Sections

| # | Section | État |
|---|---|---|
| 1 | Données de marché, courbe repo fictive à structure par terme (1 semaine → 1 an), règle de financement long terme, historiques coupés au 08/09/2026 | fait |
| 2 | Courbe €STR (bootstrap, spline sur log P) | fait |
| 3 | Courbe OAT (NSS, multi-départ), sous-jacent OAT 2046, coupon couru à une date future | fait |
| 4 | Briques gaussiennes | fait |
| 5 | Hull-White 1F, options sur obligation, Jamshidian, swaptions | fait |
| 6 | Facteur taux : diagonale co-terminale 20 ans (tenors interpolés) | fait |
| 7 | Modèle à deux facteurs ; $\bar r = r + y$ justifié par le recouvrement en valeur de marché | fait |
| 8 | Option vanille : forward repo, hypothèse de financement au-delà du dernier tenor coté (8.2), recentrage, strike clean, formule fermée | fait |
| 9 | Facteur spread : non-identification par la courbe (9.1), moments historiques (9.2), GMM à pondération diagonale et test J (9.3), biais de la vitesse historique (9.4) | fait |
| 10 | Monte-Carlo exact recentré | fait |
| 11 | Résultats et sensibilités (repo en translations, sigma_y, rho, a_y), cellule « Chiffres cités », lecture des résultats | fait |
| 12 | Conclusion et limites | fait |

## Reste à faire

1. **Courbe repo de marché** : la courbe actuelle est fictive. Une courbe de marché du 08/09/2026 se branche en
   remplaçant `data/repo_fictif.csv` au même format (`Tenor,Spread_bp`, tenors en W / M / Y, spread du taux
   zéro repo contre le taux zéro €STR, en bp) et en pointant `FICHIER_REPO` (§1) vers le nouveau fichier ;
   relancer ensuite le notebook et le contrôle de concordance texte / `CHIFFRES` (§11-12).
2. **Données Bloomberg dans un dépôt public** : `data/market data bloom.xlsx` et les sorties du notebook sont
   publiés sur GitHub ; rendre le dépôt privé, ou retirer les données du suivi (et de l'historique).
3. Extensions possibles : estimation jointe des dynamiques historique et risque-neutre par filtre de Kalman ;
   second facteur de spread pour la volatilité du court terme ; régimes pour l'instabilité de $\rho$.
