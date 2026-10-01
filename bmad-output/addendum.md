# PRD Addendum — BondOptionPricer

**Companion to:** `prd.md`
**Version:** 1.0
**Date:** 2026-10-01

> Notes de travail qui alourdiraient le PRD. La source de vérité sur le *quoi* reste `prd.md` ; les
> décisions vont dans `decision-log.md`.

---

## Open Questions

| # | Question | Owner | Needed By | Status |
|---|----------|-------|-----------|--------|
| Q1 | Quelle hypothèse de financement au-delà du dernier tenor de repo coté (FR-014) ? Options : (a) spread plat au niveau du dernier tenor coté ; (b) raccordement linéaire vers le spread OAT–€STR de la courbe risquée (financement au taux de l'OAT à l'horizon long) ; (c) spread repo constant fixé par jugement de desk. Pour mémoire, sur la courbe fictive, le call ATM 15 ans vaut 1,0 à 2,9 entre −25 et +15 bp, et 13,5 avec un financement au taux de l'OAT. | auteur | avant STORY-002 | close le 2026-10-01 : (a) « plat », choix délégué par l'auteur |
| Q2 | Source et format exacts de la courbe repo de marché (ticker Bloomberg, tenors disponibles, taux repo ou spread contre €STR, base de taux) ? | auteur | avant STORY-001 | ouverte — en attendant, courbe fictive à structure par terme (1W-1Y) |
| Q3 | Faut-il réaliser FR-018 ($\sigma_x(t)$ par morceaux) dans le mémoire, ou la laisser en perspective ? | auteur | — | close le 2026-10-01 : non (voir `decision-log.md`) |
| Q4 | Le dépôt GitHub `alexisdantzikian/BondOptionPricer` est-il privé ? Il suit `data/market data bloom.xlsx`. | auteur | avant tout push de la courbe repo | close le 2026-10-01 : **public** — le classeur Bloomberg et les sorties du notebook sont publiés ; rendre le dépôt privé ou retirer `data/` (et purger l'historique) relève de l'auteur |
| Q5 | Durée d'exécution actuelle du notebook (référence de NFR-007) — mesurée par STORY-004. | Claude Code | STORY-004 | ouverte |

---

## Deferred Requirements (parked, not cut)

- **FR-019 :** second facteur de spread pour reproduire la volatilité plus élevée du court terme et une
  volatilité légèrement croissante avec le tenor ($a_y$ bute sur sa borne) — *reason deferred:* change le
  modèle étudié (deux facteurs) ; reste une perspective de §12.
- **Courbe repo à plusieurs dates :** recalculer le forward sur un historique de courbes repo — *reason
  deferred:* le mémoire travaille à une seule date (08/09/2026).

---

## Detailed Acceptance Criteria Overflow

### FR-015 — chiffres cités en §11-12 sur la courbe fictive (inventaire de départ)
Chiffres actuellement écrits en dur, à rattacher à une sortie libellée :
- Forward clean OAT 2046 : 90,2 à 1 an, 71,8 à 15 ans.
- Recentrage $\delta$ : −1 bp à 1 an, près de 590 bp à 15 ans — sortie du §10 (paramètres calibrés :
  −1,0 et 587,9 bp). Attention : la sortie du §8 imprime −4,3 et 1 003,8 bp avec des paramètres spread
  provisoires ; la sortie récapitulative doit imprimer la valeur avec les paramètres retenus.
- Sensibilité repo : −4 % à +1 % sur le call ATM 1 an entre −25 et +15 bp ; 1,0 à 2,9 à 15 ans ; 13,5 si
  financement au taux de l'OAT.
- Variance : 18 % pour le spread, 11 % pour le terme croisé ; $\bar\Sigma_B$ +18 % contre le facteur taux
  seul ; call ATM +18 % à toutes les échéances.
- $\sigma_y$ ×2 : +28 % ; $\sigma_y$ ÷2 : −10 %.
- $\rho$ entre 0,06 et 0,43 : −3 % à +10 %.
- $a_y$ entre 0,001 et 0,19 : moins de 5 % ; $a_y = 1$ : jusqu'à −10 %.
- Monte-Carlo : intervalle de confiance 0,4 à 0,5 % ; poids gelés en 0 : 2 % à 10-12 ans ; hors de la
  monnaie à 5 ans : 1,5 % (call 110 %), 2 % (put 90 %).
- Profil : maximum du call ATM à 5 ans ; volatilité de prix maximale vers 7 ans.
- §12 : « environ 18 % », « 1,5 à 2 % », « 0,06 à 0,43 », « +5 bp à tous les tenors ».

---

### FR-020 — biais de la vitesse AR(1) : simulation exploratoire (2026-10-01)
Simulation hors notebook (4 000 marches aléatoires par longueur, MCO avec constante,
$a = -252\log\hat\phi$), à reproduire dans le notebook par STORY-011 :

| Fenêtre | n | $a$ AR(1) observé (tenor 20 ans) | moyenne si $a = 0$ | 5-95 % si $a = 0$ | rang observé |
|---|---|---|---|---|---|
| 2021-2026 | 1 453 | 0,192 | 0,94 | [0,03 ; 2,43] | 13 % |
| 3 ans | 764 | 0,966 | 1,80 | [0,10 ; 4,83] | 33 % |
| 1 an | 257 | 5,028 | 5,46 | [0,19 ; 14,2] | 56 % |

Avec une vraie vitesse de 0,2, l'intervalle 5-95 % pour n = 1 453 est [0,18 ; 2,81] : l'AR(1) ne sépare pas
0 de 0,2. Le biais croît en 1/n (Kendall : $-(1+3\phi)/n$ sur $\phi$), d'où la hausse de la vitesse quand la
fenêtre raccourcit.

### FR-021 — points techniques pour l'architecture
- Moments : 6 volatilités du spread (tenors 5, 10, 15, 20, 25, 30 ans) + 6 corrélations spread / swap €STR
  de même tenor ; 3 paramètres, 9 degrés de sur-identification. Les corrélations croisées entre tenors de
  spread (égales à 1 dans un modèle à un facteur) sont exclues : elles rejetteraient le modèle par
  construction.
- Écart avec l'estimation actuelle attendu surtout sur $\rho$ : 0,152 au tenor 20 ans seul, corrélations
  de 0,064 à 0,162 selon le tenor sur 2021-2026.
- Le tenor 2 ans reste exclu (rupture du générique le 22/01/2024).

## Prioritization Working Notes

MoSCoW posé directement, sans RICE : 7 nouvelles exigences, ordre imposé par les dépendances (la courbe
repo conditionne la réécriture de §11-12). Arbitrages non évidents : FR-018 et FR-019 en Won't — voir
`decision-log.md`.

### FR-018 — effet estimé de $\sigma_x(t)$ par morceaux (2026-10-01)
Ordre de grandeur, à partir des résidus de la diagonale 20 ans (§6) et d'une part de variance taux ≈ 72 %
(+ 11 % croisée) : call ATM ≈ 0,77 × l'erreur relative de vol. 1 an : +2,3 bp → ≈ −2,7 % ; 2 ans : ≈ +0,8 % ;
5 ans : ≈ +0,6 % ; 7 ans : ≈ +0,4 % ; 10 ans : ≈ +0,1 % ; 12 ans : ≈ −1,0 % ; 15 ans : ≈ −1,5 %. Le résidu à
1 an est en partie dû à l'interpolation du tenor 19 ans (non coté).

---

## Supporting Research / References

- `CONTEXTE.md` — cadrage complet (contrat, modèle, formule, calibration, données, conventions).
- `PLAN.md` — avancement par section et reste à faire.
- `doc/13. Russo et al._DefaultableBondOptions_DRAFT.pdf` — modèle de référence (théorie seulement).
- `doc/Hull & White 1F.ipynb` — format académique de référence du notebook.
- `doc/econo modele affine.pdf` — Monfort, Pegoraro et Renne, *Econometrics of Commodity and Asset
  Pricing*, cours 5 (ENSAE 2025-2026). Utilisé : GMM sur moments (slide 8), persistence problem et
  corrections de biais (slides 46-55), pricing RMV et intensités P/Q (Prop. II.1 à II.3), décomposition
  crédit / liquidité des spreads souverains (Monfort-Renne 2014, slides 99-104). Écarté : filtre de Kalman
  et inversion de Chen-Scott (perspective seulement), régimes cachés.

---

## Glossary

Voir `project-context.md` (section Glossary).
