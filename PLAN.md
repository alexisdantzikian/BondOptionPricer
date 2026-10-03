# Plan — état d'avancement du notebook `main/oat_option_pricer.ipynb`

Le cadrage (question de recherche, hypothèses, contrat, modèle, calibration, conventions) est dans `CONTEXTE.md`.
Le notebook suit l'ordre de la démarche ; chaque section = un markdown (théorie, justification) + une cellule
bibliothèque + une cellule de contrôles. La planification détaillée (PRD, architecture, stories, registre des
décisions) est dans `bmad-output/`.

## Sections

| # | Section | État |
|---|---|---|
| — | Introduction : problématique, G2++ de Brigo-Mercurio et lecture de Russo et al., sources, hypothèses H1-H5, contrat, plan | fait |
| 1 | Données de marché, courbe repo fictive linéaire (+20 bp à 3 semaines → +75 bp à 10 ans), historiques coupés au 08/09/2026 | fait |
| 2 | Courbe €STR (bootstrap, spline sur log P) | fait |
| 3 | Courbe OAT (NSS, multi-départ), sous-jacent OAT 2046, coupon couru à une date future | fait |
| 4 | Briques gaussiennes | fait |
| 5 | Hull-White 1F, options sur obligation, Jamshidian, swaptions | fait |
| 6 | Modèle à deux facteurs ; $\bar r = r + y$ justifié par le recouvrement en valeur de marché (paramètres de test) | fait |
| 7 | Option vanille (échéances 1 à 10 ans) : forward repo sur une courbe qui couvre toutes les échéances, sans extrapolation (7.2), recentrage et sa lecture économique (7.3), prix exact de Brigo-Mercurio (7.4), approximation à poids gelés de Russo et al. (7.5), strike clean (paramètres de test) | fait |
| 8 | Facteur taux : prix exacts de Jamshidian, diagonale co-terminale 20 ans (tenors interpolés), expiries 1 à 15 ans nécessaires à l'identification de $a_x$, meilleur de plusieurs départs | fait |
| 9 | Facteur spread : non-identification par la courbe (9.1), moments historiques et robustesse par fenêtre (9.2), GMM à pondération diagonale et test J (9.3) | fait |
| 10 | Validation : prix exact contre Monte-Carlo exact recentré, erreur de l'approximation à poids gelés contre le prix exact | fait |
| 11 | Résultats par hypothèse : effet du spread (H3), équivalent à un facteur (H4), contrôle par les vols réalisées, sensibilités ; lecture des résultats | fait |
| 12 | Conclusion : verdict sur H1-H5, limites, perspectives | fait |
| A | Annexe : vitesse de retour historique du spread (biais de petit échantillon, inférence indirecte) | fait |
| B | Annexe : chiffres cités dans le texte (concordance texte / calculs) | fait |

## Reste à faire

1. **Courbe repo de marché** : la courbe actuelle est fictive. Une courbe de marché du 08/09/2026 se branche en
   remplaçant `data/repo_fictif.csv` au même format (`Tenor,Spread_bp`, tenors en W / M / Y, spread du taux
   zéro repo contre le taux zéro €STR, en bp, jusqu'à 10 ans au moins) et en pointant `FICHIER_REPO` (§1) vers
   le nouveau fichier ; relancer ensuite le notebook et le contrôle de concordance texte / annexe B.
2. **Données Bloomberg dans un dépôt public** : `data/market data bloom.xlsx` et les sorties du notebook sont
   publiés sur GitHub ; rendre le dépôt privé, ou retirer les données du suivi (et de l'historique).
3. Extensions possibles : estimation jointe des dynamiques historique et risque-neutre par filtre de Kalman ;
   second facteur de spread pour la volatilité du court terme ; régimes pour l'instabilité de $\rho$ ; produits
   sensibles à l'écart entre les courbes, où la structure à deux facteurs compterait (H4).
