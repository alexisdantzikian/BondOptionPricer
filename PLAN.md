# Plan — état d'avancement du notebook `main/oat_option_pricer.ipynb`

Le cadrage (contrat, modèle, calibration, conventions) est dans `CONTEXTE.md`. Le notebook est séquentiel :
chaque section = un markdown (théorie, justification) + une cellule bibliothèque + une cellule de contrôles.

## Sections

| # | Section | État |
|---|---|---|
| 1 | Données de marché, courbe repo (fictive), historiques coupés au 08/09/2026 | fait |
| 2 | Courbe €STR (bootstrap, spline sur log P) | fait |
| 3 | Courbe OAT (NSS, multi-départ), sous-jacent OAT 2046, coupon couru à une date future | fait |
| 4 | Briques gaussiennes | fait |
| 5 | Hull-White 1F, options sur obligation, Jamshidian, swaptions | fait |
| 6 | Facteur taux : diagonale co-terminale 20 ans (tenors interpolés) | fait |
| 7 | Modèle à deux facteurs | fait |
| 8 | Option vanille : forward repo, recentrage, strike clean, formule fermée | fait |
| 9 | Facteur spread : non-identification par la courbe, structure par terme des vols | fait |
| 10 | Monte-Carlo exact recentré | fait |
| 11 | Résultats et sensibilités (repo, sigma_y, rho, a_y) | fait |
| 12 | Conclusion et limites | fait |

## Reste à faire

1. **Courbe repo de marché** : remplacer `data/repo_fictif.csv` (même format : `Tenor,Spread_bp`, spread du
   taux zéro repo contre le taux zéro €STR, en bp). Au-delà d'un an, documenter l'hypothèse de financement
   retenue : elle détermine le forward des échéances longues.
2. Relire les chiffres cités dans la lecture des résultats (section 11) et la conclusion après ce changement.
3. Extensions possibles : $\sigma_x(t)$ constante par morceaux bootstrappée sur la diagonale ; second facteur
   de spread pour la volatilité du court terme.
