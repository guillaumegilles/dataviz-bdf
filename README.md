# dataviz-bdf — Inclusion financière des ménages français

Analyse de la corrélation entre les conditions économiques départementales
(chômage, pauvreté, minimas sociaux, logement, démographie) et le taux de
surendettement des ménages en France métropolitaine (96 départements).

## Résultats

Consulter le rapport Quarto : `index.html` (après exécution du pipeline)

## Installation

```bash
git clone https://github.com/guillaumegilles/dataviz-bdf.git
cd dataviz-bdf
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

## Données

Les données brutes (`data/raw/`) ne sont pas versionnées.
Voir [quickstart.md](specs/001-surendettement-analysis/quickstart.md) pour le détail.

> ⚠️ Si le téléchargement du chômage localisé INSEE échoue (anti-bot),
> télécharger manuellement depuis <https://www.insee.fr/fr/statistiques/2012804>
> et placer le fichier dans `data/raw/chomage/`.

## Exécution

```bash
python scripts/01_download.py   # Téléchargement des sources
python scripts/02_clean.py      # Nettoyage par source
python scripts/03_merge.py      # Fusion → analytical_dataset.csv
python scripts/04_validate.py   # Validation + coverage_report.csv
quarto render index.qmd         # Génération du rapport HTML
```

## Mise à jour des données

Modifier les URLs dans `scripts/01_download.py` pour pointer vers les
millésimes les plus récents, puis relancer les étapes 2 à 5.

## Structure

```
data/raw/          # Sources brutes (gitignorées)
data/processed/    # Données nettoyées et jeu analytique
data/geo/          # GeoJSON départements (contours)
scripts/           # Pipeline de données (01 → 04)
  01_download.py   # Téléchargement de toutes les sources
  02_clean.py      # Nettoyage et normalisation par source
  03_merge.py      # Fusion et calcul du score_fragilite
  04_validate.py   # Validation du contrat de données
index.qmd          # Rapport Quarto (source de vérité)
specs/             # Spécifications et plan technique
```

## Références

- [Constitution du projet](.specify/memory/constitution.md)
- [Spécification](specs/001-surendettement-analysis/spec.md)
- [Plan technique](specs/001-surendettement-analysis/plan.md)
- [Guide de démarrage](specs/001-surendettement-analysis/quickstart.md)
- [Contrats de données](specs/001-surendettement-analysis/contracts/data-contracts.md)
