# Plan d'implémentation : Analyse surendettement départemental

**Branche** : `001-surendettement-analysis` | **Date** : 2026-05-20 | **Spec** : [specs/001-surendettement-analysis/spec.md](./spec.md)

---

## Résumé

Construire un rapport Quarto reproductible qui analyse la corrélation entre les conditions économiques départementales (chômage, pauvreté, minimas sociaux, logement, démographie) et le taux de surendettement des ménages en France métropolitaine (96 départements). L'approche technique repose sur un pipeline Python en 4 scripts (acquisition → nettoyage → fusion → validation), un modèle OLS avec diagnostic VIF et analyse de lag t-1, et une série de visualisations choroplèthes et analytiques intégrées dans `index.qmd`.

**Millésime de référence** : 2021 (goulot d'étranglement FiLoSoFi + RP).  
**Source surendettement** : extraction PDF des Synthèses annuelles BdF (pas d'API département dans WebStat IFI).  
**GeoJSON** : `gregoiredavid/france-geojson` (96 métropole, WGS84).

---

## Contexte technique

**Language/Version** : Python 3.11 + Quarto ≥ 1.4

**Dépendances principales** :
- `pandas`, `geopandas` — manipulation de données et géospatiale
- `matplotlib`, `plotly` — visualisation
- `statsmodels` — modèles OLS
- `scikit-learn` — normalisation z-score, ACP si nécessaire
- `requests`, `pdfplumber`, `openpyxl` — acquisition et extraction de données

**Stockage** : CSV/Parquet pour l'analytique ; GeoJSON pour les couches géographiques.  
Répertoires : `data/raw/` (brut, gitignorés), `data/processed/` (nettoyé/fusionné), `data/geo/` (cartographie).

**Tests** : Pas de tests unitaires. La validation est réalisée par `scripts/04_validate.py` (invariants de données) et par le rendu Quarto sans erreur.

**Plateforme cible** : Linux/macOS. Rendu HTML statique publié sur le site du projet.

**Objectifs de performance** : Rendu Quarto < 5 minutes ; couverture ≥ 90 % des 96 départements pour chaque variable.

**Contraintes** : Données ouvertes uniquement (BdF, INSEE, DREES, data.gouv.fr) ; toutes les sources accessibles programmatiquement ; aucune modification manuelle des fichiers bruts.

**Échelle** : 96 départements × ~5 années × ~15 variables ≈ jeu analytique < 10 Mo.

---

## Vérification constitution

*GATE : À valider avant le début de l'implémentation. Re-vérifié après la conception Phase 1.*

| Principe | Statut | Notes |
|---|---|---|
| **I. Intégrité des données** — sources officielles uniquement, aucune modification manuelle | ✅ | Pipeline scriptable complet ; données brutes gitignorées et non modifiées |
| **II. Reproductibilité** — exécution de bout en bout depuis les sources brutes | ✅ | 4 scripts numérotés + `requirements.txt` pinné + `quickstart.md` documenté |
| **III. Transparence méthodologique** — choix OLS, lag t-1, variables tous documentés | ✅ | Justifications dans `research.md` et `data-model.md` ; pondération score fragilité issue de la littérature (H-06) |
| **IV. Clarté des visualisations** — titre + axes + source + caption obligatoires | ✅ | Contrat de visualisation dans `contracts/data-contracts.md` §3 ; contrôle à chaque `render` |
| **V. Discipline de périmètre** — 96 départements métropolitains, pas de feature creep | ✅ | DOM exclus par code ; Gini limité à 2019 sans imputation ; régression spatiale explicitement hors périmètre (H-07) |

**Résultat** : ✅ Aucune violation. Implémentation autorisée.

---

## Structure du projet

### Documentation (cette feature)

```text
specs/001-surendettement-analysis/
├── plan.md              # Ce fichier
├── research.md          # Phase 0 — décisions techniques et sources
├── data-model.md        # Phase 1 — schéma analytique et conventions
├── quickstart.md        # Phase 1 — guide de démarrage
├── contracts/
│   └── data-contracts.md  # Contrats entrée/sortie/visualisation
└── tasks.md             # Phase 2 — liste de tâches (à générer avec /speckit.tasks)
```

### Code source (racine du dépôt)

```text
data/
├── raw/                      # Fichiers bruts téléchargés (gitignorés)
│   ├── bdf/                  # PDFs synthèses surendettement BdF
│   ├── filosofi/             # FiLoSoFi INSEE (ZIP CSV + SUPRA XLSX)
│   ├── chomage/              # Chômage localisé TCRD INSEE
│   ├── rp/                   # Bases infracommunales RP 2021
│   └── minimas/              # RSA, prime d'activité (DREES/France Travail)
├── processed/                # Données nettoyées et jeu analytique
│   ├── surendettement.csv
│   ├── filosofi.csv
│   ├── chomage.csv
│   ├── rp_menages.csv
│   ├── rp_logement.csv
│   ├── rp_population.csv
│   ├── minimas_sociaux.csv
│   ├── analytical_dataset.csv   ← jeu analytique principal
│   └── coverage_report.csv      ← rapport de couverture
└── geo/
    └── departements.geojson     ← contours simplifiés (gregoiredavid)

scripts/
├── 01_download.py    # Acquisition : BdF PDFs, INSEE ZIPs, GeoJSON
├── 02_clean.py       # Nettoyage + normalisation par source
├── 03_merge.py       # Fusion + calcul lags + score fragilité
└── 04_validate.py    # Contrôles qualité + rapport de couverture

index.qmd             # Rapport Quarto principal (source de vérité)
requirements.txt      # Dépendances Python pinnées
```

**Décision de structure** : Projet de type « pipeline de données + rapport analytique ». Structure plate (pas de `src/`), scripts numérotés pour l'exécution séquentielle, `index.qmd` comme unique fichier Quarto.

---

## Décisions techniques clés (synthèse de research.md)

| Question | Décision | Référence |
|---|---|---|
| Source surendettement département | Extraction PDF Synthèses annuelles BdF | `research.md` §1 |
| Gini au niveau département | D9/D1 (`GI21`) comme proxy ; Gini exact disponible uniquement pour 2019 (SUPRA) | `research.md` §2 |
| Chômage localisé | Page HTML INSEE 2012804 + fichiers TCRD (avec contournement anti-bot documenté) | `research.md` §2 |
| Millésime de référence | 2021 (goulot FiLoSoFi + RP) | `research.md` §3 |
| GeoJSON départements | `gregoiredavid/france-geojson` — WGS84, champ `code`, 96 métropole | `research.md` §4 |
| Modèle statistique | OLS — régression spatiale hors périmètre (H-07) | `research.md` §5 |
| Normalisation | Brute (primaire) + z-score (secondaire pour bêta) ; lags construits avant normalisation | `research.md` §6 |

---

## Phases d'implémentation

### Phase A — Pipeline de données (scripts 01 à 04)

**Livrable** : `data/processed/analytical_dataset.csv` valide, `coverage_report.csv`

Séquence :
1. `01_download.py` — téléchargement des 7 sources dans `data/raw/`
2. `02_clean.py` — nettoyage par source → fichiers intermédiaires `data/processed/`
3. `03_merge.py` — fusion sur `(dep_code, annee)`, calcul des lags et du score fragilité
4. `04_validate.py` — vérification des invariants (96 depts, taux de couverture, plages de valeurs)

### Phase B — EDA dans index.qmd

**Livrable** : Sections EDA du rapport (FR-011 à FR-014)

Contenu :
- Tableau de couverture des données manquantes (FR-014)
- Matrice de corrélation Pearson + Spearman avec p-values (FR-011)
- Distributions par variable — histogrammes + boxplots (FR-012)
- Tendances temporelles 2017–2021 pour surendettement + 2 variables clés (FR-013)

### Phase C — Modélisation OLS

**Livrable** : Tableaux de résultats OLS dans le rapport (FR-015 à FR-019)

Contenu :
- Modèle OLS de base : 6 prédicteurs (chômage, revenu médian, pauvreté, RSA, locataires, familles mono)
- Modèles avec lag t-1 (chômage t-1, pauvreté t-1) — comparaison AIC/Wald (SC-005)
- Diagnostic VIF pour chaque spécification (FR-017)
- ACP si VIF ≥ 10 pour plusieurs variables simultanément (FR-018)
- Tableaux standardisés : coeff + SE + p + R² ajusté + N (FR-019)

### Phase D — Cartographie et visualisations

**Livrable** : ≥ 10 visualisations conformes FR-024 (SC-004)

Cartes choroplèthes (≥ 6) :
1. Taux de surendettement 2021 (FR-020)
2. Évolution surendettement 2018–2021 (FR-020)
3. Taux de chômage 2021 (FR-021)
4. Taux de pauvreté 2021 (FR-021)
5. Part RSA 2021 (FR-021)
6. Part locataires 2021 (FR-021)
7. Score composite de fragilité (FR-022)

Graphiques analytiques (≥ 4) :
1. Matrice de corrélation (EDA)
2. Scatter plots : surendettement vs chômage, pauvreté, RSA, locataires (FR-023)
3. Distributions des variables clés (FR-012)
4. Comparaison visuelle score fragilité vs taux surendettement (SC-007)

---

## Suivi de complexité

> Aucune violation de la constitution identifiée. Table vide.

| Violation | Pourquoi nécessaire | Alternative plus simple rejetée parce que |
|---|---|---|
| — | — | — |
