"""
Extrait les sorties texte d'un notebook, cellule de code par cellule de code.

Usage : uv run python bmad-output/reference/extraire_sorties.py <notebook.ipynb> > <sortie.txt>

Chaque cellule de code est repérée par sa section (dernier titre « ## N. » rencontré) et par sa première
ligne utile (après les guillemets d'une docstring), jamais par son indice. Seules les sorties texte sont
gardées (flux stdout, text/plain des résultats) : les images sont exclues.
Outil de vérification des stories BMAD ; il n'est pas importé par le notebook.
"""
import json
import re
import sys


def premiere_ligne(source):
    """Première ligne non vide, en sautant les guillemets d'ouverture d'une docstring."""
    for ligne in source.splitlines():
        ligne = ligne.strip()
        if ligne and ligne not in ('"""', "'''"):
            return ligne.strip('"').strip("'").strip() or ligne
    return "(cellule vide)"


def extraire(chemin):
    nb = json.load(open(chemin, encoding="utf-8"))
    section, blocs = "0", []
    for cellule in nb["cells"]:
        source = "".join(cellule["source"])
        if cellule["cell_type"] == "markdown":
            for ligne in source.splitlines():
                m = re.match(r"^##\s+(\d+)\.", ligne)
                if m:
                    section = m.group(1)
            continue
        if cellule["cell_type"] != "code":
            continue
        # le noyau découpe stdout en morceaux variables d'une exécution à l'autre : on les concatène tels quels
        texte, lignes = "", [f"=== §{section} | {premiere_ligne(source)}"]
        for sortie in cellule.get("outputs", []):
            if sortie["output_type"] == "stream" and sortie.get("name") == "stdout":
                texte += "".join(sortie["text"])
            elif sortie["output_type"] in ("execute_result", "display_data"):
                plain = sortie.get("data", {}).get("text/plain")
                if plain and "image/png" not in sortie.get("data", {}):
                    texte += "".join(plain) + "\n"
            elif sortie["output_type"] == "error":
                texte += f"ERREUR : {sortie.get('ename')} : {sortie.get('evalue')}\n"
        if texte.strip():
            lignes.append(texte.rstrip("\n"))
        blocs.append("\n".join(lignes))
    return "\n".join(blocs) + "\n"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(extraire(sys.argv[1]))
