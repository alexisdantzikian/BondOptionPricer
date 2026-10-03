# Exécution de référence du notebook (story 6.1)

| Élément | Valeur |
|---|---|
| Date d'exécution | 2026-10-01 |
| Commit `HEAD` | `697d567082203dcad4a9f659b88c76bd087a694a` |
| Notebook | `main/oat_option_pricer.ipynb` (33 cellules, 19 cellules de code) |
| Commande | `uv run jupyter nbconvert --to notebook --execute --inplace main/oat_option_pricer.ipynb` |
| Python | 3.12.13 (environnement `uv`, `uv.lock`) |
| Durée, exécution 1 | 37 s (horodatage du journal nbconvert) |
| Durée, exécution 2 | 36 s (idem) |
| Durée, exécution 3 | 36 s (chronométrée par `date +%s`) |
| Compteurs d'exécution | 1 → 19, séquentiels, aucune erreur |

**Référence NFR-007 : ≈ 36 s** pour une exécution complète (seuil : ≤ 10 min, et pas plus de +50 %, soit
≈ 54 s, par ajout).

## Fichiers

- `sorties_reference.txt` — sorties texte de chaque cellule de code (flux stdout, `text/plain`, sans les
  images), repérées par `=== §<section> | <première ligne utile>`.
- `extraire_sorties.py` — produit ce format : `uv run python bmad-output/reference/extraire_sorties.py
  <notebook> > <sortie>`. Outil de vérification, non importé par le notebook.

## Comparaisons

- Exécution 3 contre exécution 2 : **identiques**.
- Exécution 2 contre le notebook commité à `HEAD` : **identiques**.
- Exécution 1 contre exécution 2 : identiques en contenu. La première version du script séparait les
  morceaux du flux stdout par un saut de ligne, et le noyau ne découpe pas stdout de la même façon d'une
  exécution à l'autre (exemple : « définie positive = » / « True » au §10). Le script concatène désormais les
  morceaux tels quels, et les comparaisons ci-dessus sont faites avec cette version.

## Utilisation par les stories suivantes

```bash
uv run python bmad-output/reference/extraire_sorties.py main/oat_option_pricer.ipynb > <scratchpad>/sorties.txt
diff bmad-output/reference/sorties_reference.txt <scratchpad>/sorties.txt
```

Le repère d'une cellule ne dépend pas de son indice : une cellule insérée apparaît comme un bloc ajouté.

## Concordance des chiffres cités (depuis le 03/10/2026)

L'ancienne annexe B du notebook (cellule `CHIFFRES`) est devenue `chiffres_cites.py` : le script exécute toutes
les cellules du notebook, recalcule chaque chiffre cité dans le résumé, la lecture des résultats et la
conclusion au format du texte, puis liste les nombres de ces textes absents de la liste (seuls des nombres
structurels doivent y rester : années, strikes, numéros de section).

```bash
uv run python bmad-output/reference/chiffres_cites.py
```

Les sorties de référence ci-dessus (`sorties_reference.txt`, story 6.1) datent d'avant la réécriture et ne
servent plus de point de comparaison.
