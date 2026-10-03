# Plan — état d'avancement du notebook `main/oat_option_pricer.ipynb`

Le cadrage (question de recherche, hypothèses, contrat, modèle, calibration, conventions) est dans `CONTEXTE.md`.
Le notebook est rédigé comme un mémoire : résumé, introduction, quatre parties, conclusion, références. Chaque
section expose la théorie puis la met en œuvre ; seules les validations scientifiques y figurent. La
planification détaillée (PRD, architecture, stories, registre des décisions) est dans `bmad-output/`.

## Sections

| # | Section | État |
|---|---|---|
| — | Résumé ; introduction : problématique, cadre et sources (Brigo-Mercurio, Russo et al., cours de Monfort), hypothèses H1-H5, contrat, plan, notations | fait |
| 1 | Données de marché, courbe repo fictive linéaire (+20 bp à 3 semaines → +75 bp à 10 ans), historiques coupés au 08/09/2026 | fait |
| 2 | Courbe €STR (bootstrap, spline sur log P) | fait |
| 3 | Courbe OAT (Nelson-Siegel-Svensson), sous-jacent OAT 2046, coupon couru à une date future | fait |
| 4 | Moments gaussiens | fait |
| 5 | Hull-White à un facteur, options sur obligation (poids gelés, Jamshidian), swaptions | fait |
| 6 | Modèle à deux facteurs ; $\bar r = r + y$ justifié par le recouvrement en valeur de marché | fait |
| 7 | Option vanille (échéances 1 à 10 ans) : forward repo sans extrapolation (7.2), recentrage et sa lecture économique (7.3), prix exact de Brigo-Mercurio (7.4), approximation à poids gelés de Russo et al. (7.5) | fait |
| 8 | Facteur taux : prix exacts de Jamshidian, diagonale co-terminale 20 ans (tenors interpolés), expiries 1 à 15 ans nécessaires à l'identification de $a_x$, meilleur de plusieurs départs | fait |
| 9 | Facteur spread : non-identification par la courbe (9.1), moments historiques, ACP et robustesse par fenêtre (9.2), GMM à pondération diagonale et test J (9.3) | fait |
| 10 | Filtre de Kalman : espace-état, vraisemblance, inversion au tenor 20 ans, test sur données simulées, estimation, Ljung-Box | fait |
| 11 | Validation : prix exact contre Jamshidian (un facteur) et Monte-Carlo exact recentré, erreur de l'approximation à poids gelés | fait |
| 12 | Résultats par hypothèse : effet du spread (H3), équivalent à un facteur (H4), contrôle par les vols réalisées, sensibilités (dont GMM contre Kalman) ; lecture des résultats | fait |
| 13 | Conclusion : verdict sur H1-H5, limites, perspectives ; références | fait |

La concordance entre le texte et les calculs se vérifie hors du notebook :
`uv run python bmad-output/reference/chiffres_cites.py` (≈ 1 min 30 s).

## Reste à faire

1. **Courbe repo de marché** : la courbe actuelle est fictive. Une courbe de marché du 08/09/2026 se branche en
   remplaçant `data/repo_fictif.csv` au même format (`Tenor,Spread_bp`, tenors en W / M / Y, spread du taux
   zéro repo contre le taux zéro €STR, en bp, jusqu'à 10 ans au moins) et en pointant `FICHIER_REPO` (§1) vers
   le nouveau fichier ; relancer ensuite le notebook et le contrôle de concordance.
2. **Données Bloomberg dans un dépôt public** : `data/market data bloom.xlsx` et les sorties du notebook sont
   publiés sur GitHub ; rendre le dépôt privé, ou retirer les données du suivi (et de l'historique).
3. Extensions possibles : facteur de pente par courbe et erreurs de mesure autocorrélées, que réclament les
   résidus du filtre de Kalman ; régimes pour l'instabilité de $\rho$ ; produits sensibles à l'écart entre les
   courbes, où la structure à deux facteurs compterait (H4).
