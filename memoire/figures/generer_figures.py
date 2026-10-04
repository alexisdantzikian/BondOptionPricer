"""
Régénère les figures du mémoire LaTeX à partir du notebook main/oat_option_pricer.ipynb.

Le notebook est exécuté tel quel, cellule par cellule, dans un même espace de noms ; chaque appel à
plt.show() enregistre la figure courante en PDF vectoriel, à la largeur du texte, en Times New Roman, avec
la virgule décimale et les notations du mémoire. Aucun calcul n'est modifié.

Lancer depuis la racine du dépôt :
    uv run python memoire/figures/generer_figures.py
"""
import json
import locale
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates
import matplotlib.pyplot as plt

RACINE = Path(__file__).resolve().parents[2]
SORTIE = Path(__file__).resolve().parent
NOTEBOOK = RACINE / "main" / "oat_option_pricer.ipynb"

# cellule de code du notebook -> nom du fichier PDF
NOMS = {2: "donnees", 4: "courbe_estr", 6: "courbe_oat", 17: "calibration_taux", 20: "spread_historique",
        25: "regimes", 28: "kalman", 31: "validation", 33: "resultats", 35: "sensibilites"}

for loc in ("fr_FR.UTF-8", "fr_FR", "French_France.1252"):
    try:
        locale.setlocale(locale.LC_NUMERIC, loc)
        break
    except locale.Error:
        pass

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman"], "mathtext.fontset": "stix",
    "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7,
    "legend.fontsize": 7, "axes.formatter.use_locale": True, "axes.unicode_minus": True,
    "pdf.fonttype": 42,
})


def franciser(s):
    """Notations et typographie du mémoire, hors des segments mathématiques déjà balisés."""
    morceaux = s.split("$")
    for k in range(0, len(morceaux), 2):                       # indices pairs : hors mode math
        t = morceaux[k]
        t = t.replace("Sigma_B^2", r"$\bar\Sigma_B^2$").replace("sigma_y", r"$\sigma_y$")
        t = re.sub(r"\ba_y\b", r"$a_y$", t)
        t = re.sub(r"\bT0\b", r"$T_0$", t)
        t = re.sub(r"(\d)\.(\d)", r"\1,\2", t)
        t = re.sub(r"(\d) ?%", "\\1\u00a0%", t)
        t = re.sub(r"\bbp\b", "pb", t)
        t = re.sub(r"(?<![\w)])-(\d)", "\u2212\\1", t)
        t = t.replace(" - ", " \u2212 ")
        morceaux[k] = t
    return "$".join(morceaux)


def etiquette_maturite(lab):
    """Graduations des cartes de chaleur : maturités en années, mois en dessous d'un an."""
    try:
        v = float(lab.replace("\u2212", "-").replace(",", "."))
    except ValueError:
        return lab
    return f"{round(v * 12)} m" if v < 1 else f"{v:g}".replace(".", ",")


def mettre_en_forme(fig):
    largeur, _ = fig.get_size_inches()
    trois_panneaux = largeur >= 16
    fig.set_size_inches((6.5, 2.7) if trois_panneaux else (6.5, 2.6) if largeur >= 12 else (4.8, 2.6))
    for ax in fig.axes:
        ax.set_title(franciser(ax.get_title()))
        ax.set_xlabel(franciser(ax.get_xlabel()))
        ax.set_ylabel(franciser(ax.get_ylabel()))
        if ax.images:                                           # cartes de chaleur : graduations textuelles
            ax.set_yticks(ax.get_yticks(), [etiquette_maturite(t.get_text()) for t in ax.get_yticklabels()])
            xlab = [etiquette_maturite(t.get_text()) for t in ax.get_xticklabels()]
            if trois_panneaux:                                  # une graduation sur deux, faute de place
                xlab = [lab if k % 2 == 0 else "" for k, lab in enumerate(xlab)]
            ax.set_xticks(ax.get_xticks(), xlab)
        if isinstance(ax.xaxis.get_major_formatter(), matplotlib.dates.AutoDateFormatter) or \
                isinstance(ax.xaxis.get_major_locator(), matplotlib.dates.AutoDateLocator):
            ax.xaxis.set_major_locator(matplotlib.dates.YearLocator(2 if trois_panneaux else 1))
            ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y"))
        leg = ax.get_legend()
        if leg is not None:                                     # légende recréée à la nouvelle taille
            poignees, textes = ax.get_legend_handles_labels()
            titre = franciser(leg.get_title().get_text())
            ax.legend(poignees, [franciser(t) for t in textes], title=titre or None,
                      ncol=2 if len(textes) > 4 or (trois_panneaux and len(textes) > 2) else 1,
                      fontsize=6.5, title_fontsize=6.5, loc="best")
    fig.tight_layout()


cellule_courante = None


def show(*args, **kwargs):
    fig = plt.gcf()
    mettre_en_forme(fig)
    nom = NOMS.get(cellule_courante, f"cellule_{cellule_courante:02d}")
    fig.savefig(SORTIE / f"{nom}.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"[figure] {nom}.pdf", file=sys.stderr)


plt.show = show

if __name__ == "__main__":
    import os
    os.chdir(RACINE)
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    espace = {"__name__": "__main__", "display": print}
    for i, c in enumerate(nb["cells"]):
        if c["cell_type"] != "code":
            continue
        cellule_courante = i
        exec(compile("".join(c["source"]), f"<cellule {i}>", "exec"), espace)
