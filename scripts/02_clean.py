#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
02_clean.py — Nettoyage par source de données
Exécution : python scripts/02_clean.py

Chaque fonction de nettoyage est indépendante : si une source est absente,
un avertissement est affiché et l'exécution continue normalement.

Sorties dans data/processed/ :
  surendettement.csv   — BdF API WebStat 2019–2024 (mensuel agrégé annuel)
  filosofi.csv         — FiLoSoFi 2021 (revenu, pauvreté, interdécile)
  filosofi_gini.csv    — FiLoSoFi SUPRA 2019 (Gini)
  chomage.csv          — Chômage localisé INSEE
  rp_menages.csv       — RP 2021 structure ménages
  rp_logement.csv      — RP 2021 logement
  rp_population.csv    — RP 2021 population / démographie
  minimas_sociaux.csv  — RSA, prime d'activité, ASS/ASPA
"""

import pathlib
import re
import unicodedata
import warnings

import pandas as pd

ROOT      = pathlib.Path(__file__).parent.parent
RAW       = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Utilitaires partagés
# ---------------------------------------------------------------------------

def load_dep_ref() -> pd.DataFrame:
    """Charge la table de référence des 96 départements."""
    return pd.read_csv(PROCESSED / "dep_ref.csv", dtype=str)


def normalize_name(name: str) -> str:
    """Normalise un nom de département : minuscules, sans accents, tirets → espaces."""
    if not isinstance(name, str):
        return ""
    # décomposer les caractères accentués
    nfkd = unicodedata.normalize("NFKD", name.lower())
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    # unifier séparateurs
    ascii_str = re.sub(r"[-_''`]", " ", ascii_str)
    ascii_str = re.sub(r"\s+", " ", ascii_str).strip()
    return ascii_str


# ---------------------------------------------------------------------------
# T011 — BdF : API WebStat CSV → surendettement.csv
# ---------------------------------------------------------------------------

def clean_surendettement():
    """Agrège les données mensuelles BdF (API WebStat) en totaux annuels par département.

    Lit data/raw/bdf/surendettement_api.csv (délimiteur ;), extrait l'année
    depuis time_period (YYYY-MM), somme les obs_value mensuelles par
    (dep_code, annee), et filtre les années complètes (2019–2024).
    Produit data/processed/surendettement.csv.
    """
    print("\n=== Nettoyage BdF — surendettement ===")

    api_csv = RAW / "bdf" / "surendettement_api.csv"
    if not api_csv.exists():
        print(f"  ⚠️  {api_csv.name} absent — ignorer bloc BdF")
        pd.DataFrame(
            columns=["dep_code", "dep_nom", "annee", "suren_depot_nb",
                     "source_url", "source_millesime"]
        ).to_csv(PROCESSED / "surendettement.csv", index=False)
        return

    dep_ref = load_dep_ref()
    print(f"  ↳ Chargement {api_csv.name} …")
    df = pd.read_csv(api_csv, sep=";", encoding="utf-8-sig")

    # series_key "IFI.M.D01.SUREN.DEPOT" → dep_code "01", "2A", etc.
    df["dep_code"] = df["series_key"].str.split(".").str[2].str[1:]

    # time_period "2019-01" → annee 2019
    df["annee"] = df["time_period"].str[:4].astype(int)

    # Garder uniquement les années complètes 2019–2024
    ANNEES_COMPLETES = list(range(2019, 2025))
    df = df[df["annee"].isin(ANNEES_COMPLETES)]

    # Agréger : somme mensuelle → total annuel par département
    df_annual = (
        df.groupby(["dep_code", "annee"], as_index=False)["obs_value"]
        .sum()
        .rename(columns={"obs_value": "suren_depot_nb"})
    )
    df_annual["suren_depot_nb"] = df_annual["suren_depot_nb"].round().astype(int)

    # Joindre les noms de département
    df_annual = df_annual.merge(dep_ref[["dep_code", "dep_nom"]], on="dep_code", how="left")

    # Métadonnées source
    df_annual["source_url"] = df_annual["dep_code"].apply(
        lambda c: f"https://webstat.banque-france.fr/fr/catalogue/ifi/IFI.M.D{c}.SUREN.DEPOT"
    )
    df_annual["source_millesime"] = df_annual["annee"].astype(str)

    cols = ["dep_code", "dep_nom", "annee", "suren_depot_nb", "source_url", "source_millesime"]
    df_annual = df_annual[cols].sort_values(["annee", "dep_code"])

    # Contrôle qualité
    nb_dep_par_annee = df_annual.groupby("annee")["dep_code"].count()
    for annee, nb in nb_dep_par_annee.items():
        flag = "✓" if nb == 96 else "⚠️ "
        print(f"  {flag} {annee} : {nb}/96 départements")

    df_annual.to_csv(PROCESSED / "surendettement.csv", index=False)
    print(f"  ✓ surendettement.csv — {len(df_annual)} lignes")


# ---------------------------------------------------------------------------
# T012 — FiLoSoFi : revenu médian, pauvreté, interdécile, Gini
# ---------------------------------------------------------------------------

def clean_filosofi():
    """Nettoie les données FiLoSoFi 2021 et SUPRA 2019."""
    print("\n=== Nettoyage FiLoSoFi ===")

    filosofi_dir = RAW / "filosofi"
    dep_ref = load_dep_ref()

    # ── FiLoSoFi 2021 ────────────────────────────────────────────────────
    pattern = list(filosofi_dir.glob("**/*cc*filosofi*2021*.csv"))
    # Filtre : fichier de niveau département (pas commune, pas EPCI)
    dep_files = [
        f for f in pattern
        if not any(x in f.stem.lower() for x in ["epci", "iris", "arr"])
    ]

    if not dep_files:
        print(f"  ⚠️  Aucun fichier FiLoSoFi 2021 trouvé dans {filosofi_dir}")
        pd.DataFrame(
            columns=["dep_code", "revenu_median_uc", "taux_pauvrete",
                     "interdecile_d9d1", "annee", "source_url", "source_millesime"]
        ).to_csv(PROCESSED / "filosofi.csv", index=False)
    else:
        filepath = dep_files[0]
        print(f"  ↳ Chargement {filepath.name} …")
        try:
            df = pd.read_csv(filepath, sep=";", dtype={"CODGEO": str}, low_memory=False)
        except Exception:
            df = pd.read_csv(filepath, dtype={"CODGEO": str}, low_memory=False)

        # Filtre : ne conserver que les lignes de niveau département
        mask_dep = df["CODGEO"].str.match(r"^([0-9]{2}|2[AB])$", na=False)
        df = df[mask_dep].copy()

        # Renommages
        rename_map = {}
        cols = df.columns.str.upper().tolist()
        for raw_col, new_col in [
            ("MED21",  "revenu_median_uc"),
            ("TP6021", "taux_pauvrete"),
            ("GI21",   "interdecile_d9d1"),
        ]:
            # Chercher la colonne (insensible à la casse, avec variantes numériques)
            matches = [c for c in df.columns if c.upper().startswith(raw_col)]
            if matches:
                rename_map[matches[0]] = new_col

        df = df.rename(columns=rename_map)
        df = df.rename(columns={"CODGEO": "dep_code"})
        df["annee"] = 2021
        df["source_url"] = "https://www.insee.fr/fr/statistiques/7756729"
        df["source_millesime"] = "2021"

        keep_cols = ["dep_code"] + [
            c for c in ["revenu_median_uc", "taux_pauvrete", "interdecile_d9d1"]
            if c in df.columns
        ] + ["annee", "source_url", "source_millesime"]
        df = df[keep_cols]

        df.to_csv(PROCESSED / "filosofi.csv", index=False)
        print(f"  ✓ filosofi.csv — {len(df)} lignes, colonnes : {df.columns.tolist()}")

    # ── FiLoSoFi SUPRA 2019 (Gini) ───────────────────────────────────────
    supra_files = list(filosofi_dir.glob("**/*SUPRA*")) + list(
        filosofi_dir.glob("**/*supra*")
    )
    if not supra_files:
        print("  ⚠️  Aucun fichier SUPRA 2019 trouvé — filosofi_gini.csv vide")
        pd.DataFrame(
            columns=["dep_code", "gini", "annee", "source_url", "source_millesime"]
        ).to_csv(PROCESSED / "filosofi_gini.csv", index=False)
        return

    supra_path = supra_files[0]
    print(f"  ↳ Chargement SUPRA : {supra_path.name} …")
    try:
        # Essayer plusieurs onglets pour trouver les données départementales
        gini_df = None
        try:
            xls = pd.ExcelFile(supra_path)
            for sheet in xls.sheet_names:
                df_sheet = xls.parse(sheet, dtype=str)
                if any("DEP" in str(c).upper() or "GIN" in str(c).upper()
                       for c in df_sheet.columns):
                    gini_df = df_sheet
                    break
        except Exception:
            gini_df = pd.read_csv(supra_path, sep=";", dtype=str, low_memory=False)

        if gini_df is not None and not gini_df.empty:
            # Trouver colonne code géo et gini
            codgeo_col = next(
                (c for c in gini_df.columns if "cod" in c.lower() or c.upper() == "DEP"),
                None,
            )
            gini_col = next(
                (c for c in gini_df.columns
                 if "gini" in c.lower() or "gi19" in c.lower()),
                None,
            )
            if codgeo_col and gini_col:
                gini_df = gini_df.rename(
                    columns={codgeo_col: "dep_code", gini_col: "gini"}
                )
                mask = gini_df["dep_code"].str.match(
                    r"^([0-9]{2}|2[AB])$", na=False
                )
                gini_df = gini_df[mask][["dep_code", "gini"]].copy()
                gini_df["annee"] = 2019
                gini_df["source_url"] = "https://www.insee.fr/fr/statistiques/6036907"
                gini_df["source_millesime"] = "2019"
                gini_df.to_csv(PROCESSED / "filosofi_gini.csv", index=False)
                print(f"  ✓ filosofi_gini.csv — {len(gini_df)} lignes")
                return
    except Exception as exc:
        print(f"  ⚠️  Extraction Gini SUPRA échouée : {exc}")

    pd.DataFrame(
        columns=["dep_code", "gini", "annee", "source_url", "source_millesime"]
    ).to_csv(PROCESSED / "filosofi_gini.csv", index=False)


# ---------------------------------------------------------------------------
# T013 — Chômage localisé INSEE → chomage.csv
# ---------------------------------------------------------------------------

def clean_chomage():
    """Nettoie les données de chômage localisé INSEE."""
    print("\n=== Nettoyage Chômage localisé ===")

    chomage_dir = RAW / "chomage"
    # Chercher un fichier Excel TCRD
    excel_files = (
        list(chomage_dir.glob("**/*.xlsx"))
        + list(chomage_dir.glob("**/*.xls"))
        + list(chomage_dir.glob("**/*.csv"))
    )
    # Filtrer les fichiers pertinents (TCRD ou taux-chomage)
    excel_files = [
        f for f in excel_files
        if any(kw in f.stem.upper()
               for kw in ["TCRD", "CHOM", "TAUX", "LOCALIS"])
    ] or excel_files  # si aucun filtre, prendre tous

    if not excel_files:
        print(f"  ⚠️  Aucun fichier chômage dans {chomage_dir} — chomage.csv vide")
        print("  💡 Télécharger depuis : https://www.insee.fr/fr/statistiques/2012804")
        pd.DataFrame(
            columns=["dep_code", "chomage_taux",
                     "source_url", "source_millesime"]
        ).to_csv(PROCESSED / "chomage.csv", index=False)
        return

    filepath = excel_files[0]
    print(f"  ↳ Chargement {filepath.name} …")

    try:
        if filepath.suffix in (".xlsx", ".xls"):
            df_raw = pd.read_excel(filepath, header=None, dtype=str)
        else:
            df_raw = pd.read_csv(filepath, dtype=str, sep=None, engine="python")

        # ── Détecter la structure du fichier ──────────────────────────────
        # Les fichiers TCRD INSEE ont généralement :
        # - Lignes d'en-tête (codes trimestres ou années)
        # - Colonne 0 : code département (01..95, 2A, 2B)
        # - Colonnes suivantes : taux de chômage par trimestre

        # Trouver la première ligne avec des codes département
        dep_mask_regex = r"^([0-9]{2}|2[AB])$"
        header_row = None
        for i, row in df_raw.iterrows():
            if row.iloc[0] in ["01", "02", "1", "2"] or re.match(
                dep_mask_regex, str(row.iloc[0])
            ):
                header_row = i
                break

        if header_row is None:
            print("  ⚠️  Structure du fichier TCRD non reconnue")
            pd.DataFrame(
                columns=["dep_code", "chomage_taux",
                         "source_url", "source_millesime"]
            ).to_csv(PROCESSED / "chomage.csv", index=False)
            return

        # En-têtes : ligne précédente
        col_headers = df_raw.iloc[header_row - 1].tolist() if header_row > 0 else []
        df = df_raw.iloc[header_row:].copy()
        df.columns = range(len(df.columns))

        # Filtrer lignes département (96 métropolitains, exclure 971-976)
        mask = df[0].apply(
            lambda x: bool(re.match(dep_mask_regex, str(x).strip()))
        )
        df = df[mask].copy()
        df = df.rename(columns={0: "dep_code"})
        df["dep_code"] = df["dep_code"].str.zfill(2)

        # Convertir colonnes numériques en taux
        numeric_cols = df.columns[1:]
        records: list[dict] = []

        # Identifier la colonne Q4 2024 si présente, sinon prendre la dernière colonne
        ref_col_idx = None
        if header_row and header_row > 0:
            headers_row = df_raw.iloc[header_row - 1].tolist()
            for ci, h in enumerate(headers_row):
                if h and "2024" in str(h):
                    ref_col_idx = ci  # index de colonne dans df (0-basé, identique au raw)
                    break

        for _, row in df.iterrows():
            dep_code = row["dep_code"]
            # Priorité : colonne de référence Q4 2024 ; sinon moyenne de toutes
            if ref_col_idx is not None and ref_col_idx in numeric_cols:
                try:
                    val = float(str(row[ref_col_idx]).replace(",", ".").strip())
                    chomage_taux = val if 0 < val < 30 else None
                except (ValueError, TypeError):
                    chomage_taux = None
            else:
                chomage_taux = None

            if chomage_taux is None:
                # Repli : moyenne de toutes les colonnes numériques disponibles
                values: list[float] = []
                for col in numeric_cols:
                    try:
                        val = float(str(row[col]).replace(",", ".").strip())
                        if 0 < val < 30:
                            values.append(val)
                    except (ValueError, TypeError):
                        pass
                chomage_taux = round(sum(values) / len(values), 2) if values else None

            if chomage_taux is not None:
                records.append({
                    "dep_code":         dep_code,
                    # Pas d'annee → jointure sur dep_code seul dans 03_merge.py
                    # (taux de référence Q4 2024 diffusé sur toutes les années)
                    "chomage_taux":     round(chomage_taux, 2),
                    "source_url":       "https://www.insee.fr/fr/statistiques/2012804",
                    "source_millesime": "2024",
                })

        if records:
            result = pd.DataFrame(records)
            result.to_csv(PROCESSED / "chomage.csv", index=False)
            print(f"  ✓ chomage.csv — {len(result)} lignes")
        else:
            print("  ⚠️  Aucune donnée extraite du fichier TCRD")
            pd.DataFrame(
                columns=["dep_code", "chomage_taux",
                         "source_url", "source_millesime"]
            ).to_csv(PROCESSED / "chomage.csv", index=False)

    except Exception as exc:
        print(f"  ✗ Erreur nettoyage chômage : {exc}")
        pd.DataFrame(
            columns=["dep_code", "chomage_taux",
                     "source_url", "source_millesime"]
        ).to_csv(PROCESSED / "chomage.csv", index=False)


# ---------------------------------------------------------------------------
# T014 — RP 2021 : ménages, logement, population
# ---------------------------------------------------------------------------

def clean_rp():
    """Nettoie les bases infracommunales RP 2021 et agrège au niveau département."""
    print("\n=== Nettoyage RP 2021 ===")

    rp_dir = RAW / "rp"

    def load_rp_base(pattern: str, label: str) -> pd.DataFrame | None:
        files = list(rp_dir.glob(f"**/{pattern}"))
        if not files:
            print(f"  ⚠️  Fichier {pattern} non trouvé")
            return None
        print(f"  ↳ Chargement {files[0].name} …")
        try:
            # Les fichiers RP INSEE utilisent souvent ';' comme séparateur
            df = pd.read_csv(files[0], sep=";", dtype=str, low_memory=False)
            if "CODGEO" in df.columns:
                # Extraire le code département (2 premiers caractères)
                df["DEP"] = df["CODGEO"].str[:2]
            return df
        except Exception as exc:
            print(f"  ✗ Erreur chargement {label} : {exc}")
            return None

    dep_pattern = r"^([0-9]{2}|2[AB])$"

    # ── Ménages ──────────────────────────────────────────────────────────
    df_men = load_rp_base("*menages*2021*.csv", "ménages")
    if df_men is not None and "DEP" in df_men.columns:
        mask = df_men["DEP"].str.match(dep_pattern, na=False)
        # Filtrer les 96 départements métropolitains seulement
        df_men = df_men[mask].copy()
        num_cols = [c for c in df_men.columns
                    if c not in ("CODGEO", "DEP", "IRIS", "COM", "REG", "ARR",
                                 "CV", "TRIRIS", "GRD_QUART", "TYP_IRIS",
                                 "MODIF_IRIS", "LAB_IRIS", "UU2020", "AU2020",
                                 "REG", "DEP", "COM", "IRIS")
                    and df_men[c].str.replace(r"[\d.,\s]", "", regex=True).eq("").all()]

        # Agréger au niveau département
        try:
            df_dep_men = df_men.copy()
            for col in df_dep_men.columns:
                if col not in ("DEP",):
                    try:
                        df_dep_men[col] = pd.to_numeric(
                            df_dep_men[col].str.replace(",", "."), errors="coerce"
                        )
                    except Exception:
                        pass
            df_dep_men = df_dep_men.groupby("DEP", as_index=False)[
                [c for c in df_dep_men.select_dtypes("number").columns]
            ].sum()
            df_dep_men = df_dep_men.rename(columns={"DEP": "dep_code"})

            # Calculer les taux si colonnes disponibles
            cols_up = {c.upper(): c for c in df_dep_men.columns}

            def safe_ratio(num_col: str, denom_col: str, pct: float = 100.0):
                n = cols_up.get(num_col)
                d = cols_up.get(denom_col)
                if n and d:
                    return (df_dep_men[n] / df_dep_men[d].replace(0, float("nan"))) * pct
                return None

            for rate_col, num_key, denom_key in [
                ("part_familles_mono", "C21_FAMMONO", "C21_FAM"),
                ("part_menages_1pers", "C21_MENPSEUL", "C21_MEN"),
            ]:
                ratio = safe_ratio(num_key, denom_key)
                if ratio is not None:
                    df_dep_men[rate_col] = ratio.round(2)

            df_dep_men["annee"] = 2021
            df_dep_men["source_url"] = "https://www.insee.fr/fr/statistiques/8268828"
            df_dep_men["source_millesime"] = "2021"
            df_dep_men.to_csv(PROCESSED / "rp_menages.csv", index=False)
            print(f"  ✓ rp_menages.csv — {len(df_dep_men)} lignes")
        except Exception as exc:
            print(f"  ✗ Erreur agrégation ménages : {exc}")

    # ── Logement ─────────────────────────────────────────────────────────
    df_log = load_rp_base("*logement*2021*.csv", "logement")
    if df_log is not None and "DEP" in df_log.columns:
        mask = df_log["DEP"].str.match(dep_pattern, na=False)
        df_log = df_log[mask].copy()
        try:
            df_dep_log = df_log.copy()
            for col in df_dep_log.columns:
                if col != "DEP":
                    try:
                        df_dep_log[col] = pd.to_numeric(
                            df_dep_log[col].str.replace(",", "."), errors="coerce"
                        )
                    except Exception:
                        pass
            df_dep_log = df_dep_log.groupby("DEP", as_index=False)[
                [c for c in df_dep_log.select_dtypes("number").columns]
            ].sum()
            df_dep_log = df_dep_log.rename(columns={"DEP": "dep_code"})

            cols_up = {c.upper(): c for c in df_dep_log.columns}

            def safe_ratio_log(num_col, denom_col, pct=100.0):
                n = cols_up.get(num_col)
                d = cols_up.get(denom_col)
                if n and d:
                    return (df_dep_log[n] / df_dep_log[d].replace(0, float("nan"))) * pct
                return None

            for rate_col, num_key, denom_key in [
                ("part_locataires",   "P21_RP_LOC",    "P21_RP"),
                ("part_hlm",          "P21_RP_LOCHLMV", "P21_RP"),
                ("taux_surpeuplement","P21_RP_SPOC",   "P21_RP"),
            ]:
                ratio = safe_ratio_log(num_key, denom_key)
                if ratio is not None:
                    df_dep_log[rate_col] = ratio.round(2)

            df_dep_log["annee"] = 2021
            df_dep_log["source_url"] = "https://www.insee.fr/fr/statistiques/8268838"
            df_dep_log["source_millesime"] = "2021"
            df_dep_log.to_csv(PROCESSED / "rp_logement.csv", index=False)
            print(f"  ✓ rp_logement.csv — {len(df_dep_log)} lignes")
        except Exception as exc:
            print(f"  ✗ Erreur agrégation logement : {exc}")

    # ── Population ───────────────────────────────────────────────────────
    df_pop = load_rp_base("*population*2021*.csv", "population")
    if df_pop is not None and "DEP" in df_pop.columns:
        mask = df_pop["DEP"].str.match(dep_pattern, na=False)
        df_pop = df_pop[mask].copy()
        try:
            df_dep_pop = df_pop.copy()
            for col in df_dep_pop.columns:
                if col != "DEP":
                    try:
                        df_dep_pop[col] = pd.to_numeric(
                            df_dep_pop[col].str.replace(",", "."), errors="coerce"
                        )
                    except Exception:
                        pass
            df_dep_pop = df_dep_pop.groupby("DEP", as_index=False)[
                [c for c in df_dep_pop.select_dtypes("number").columns]
            ].sum()
            df_dep_pop = df_dep_pop.rename(columns={"DEP": "dep_code"})

            cols_up = {c.upper(): c for c in df_dep_pop.columns}

            def safe_ratio_pop(num_col, denom_col, pct=100.0):
                n = cols_up.get(num_col)
                d = cols_up.get(denom_col)
                if n and d:
                    return (df_dep_pop[n] / df_dep_pop[d].replace(0, float("nan"))) * pct
                return None

            # Part 25-54 ans
            age_25_54_cols = [
                k for k in cols_up
                if re.match(r"P21_POP(25|30|35|40|45|50)(29|34|39|44|49|54)?", k)
            ]
            pop_col = cols_up.get("P21_POP")
            if age_25_54_cols and pop_col:
                df_dep_pop["part_25_54"] = (
                    df_dep_pop[[cols_up[c] for c in age_25_54_cols]].sum(axis=1)
                    / df_dep_pop[pop_col].replace(0, float("nan")) * 100
                ).round(2)

            for rate_col, num_key, denom_key in [
                ("part_65plus", "P21_POP65P", "P21_POP"),
            ]:
                ratio = safe_ratio_pop(num_key, denom_key)
                if ratio is not None:
                    df_dep_pop[rate_col] = ratio.round(2)

            df_dep_pop["annee"] = 2021
            df_dep_pop["source_url"] = "https://www.insee.fr/fr/statistiques/8268806"
            df_dep_pop["source_millesime"] = "2021"
            df_dep_pop.to_csv(PROCESSED / "rp_population.csv", index=False)
            print(f"  ✓ rp_population.csv — {len(df_dep_pop)} lignes")
        except Exception as exc:
            print(f"  ✗ Erreur agrégation population : {exc}")

    # Créer des fichiers vides si les sources n'étaient pas disponibles
    for fname in ("rp_menages.csv", "rp_logement.csv", "rp_population.csv"):
        if not (PROCESSED / fname).exists():
            print(f"  ⚠️  {fname} non généré — fichier vide créé")
            pd.DataFrame(columns=["dep_code", "annee"]).to_csv(
                PROCESSED / fname, index=False
            )


# ---------------------------------------------------------------------------
# T015 — Minimas sociaux → minimas_sociaux.csv
# ---------------------------------------------------------------------------

def clean_minimas():
    """Nettoie les données de minimas sociaux."""
    print("\n=== Nettoyage Minimas sociaux ===")

    minimas_dir = RAW / "minimas"
    dep_ref = load_dep_ref()

    files = (
        list(minimas_dir.glob("**/*.xlsx"))
        + list(minimas_dir.glob("**/*.xls"))
        + list(minimas_dir.glob("**/*.csv"))
    )

    if not files:
        print(
            f"  ⚠️  Aucun fichier dans {minimas_dir} "
            "— création d'un placeholder avec NaN"
        )
        placeholder = dep_ref[["dep_code"]].copy()
        placeholder["annee"] = 2021
        placeholder["rsa_taux"] = float("nan")
        placeholder["prime_activite_taux"] = float("nan")
        placeholder["ass_aspa_taux"] = float("nan")
        placeholder["source_url"] = (
            "https://drees.solidarites-sante.gouv.fr/"
            "jeux-de-donnees/indicateurs-sociaux-departementaux-isd-mise-0"
        )
        placeholder["source_millesime"] = "N/A"
        placeholder.to_csv(PROCESSED / "minimas_sociaux.csv", index=False)
        print("  ℹ️  minimas_sociaux.csv créé avec NaN — à remplacer si données disponibles")
        return

    filepath = files[0]
    print(f"  ↳ Chargement {filepath.name} …")
    try:
        if filepath.suffix in (".xlsx", ".xls"):
            df = pd.read_excel(filepath, dtype=str)
        else:
            df = pd.read_csv(filepath, dtype=str, sep=None, engine="python")

        # Tentative de mapping des colonnes
        col_map = {}
        for col in df.columns:
            col_up = col.upper()
            if "RSA" in col_up and "TAUX" in col_up:
                col_map[col] = "rsa_taux"
            elif "RSA" in col_up and "ALLOC" in col_up:
                col_map[col] = "rsa_nb"
            elif "PRIME" in col_up or "PA_" in col_up:
                col_map[col] = "prime_activite_taux"
            elif "ASS" in col_up or "ASPA" in col_up:
                col_map[col] = "ass_aspa_taux"
            elif re.match(r"(DEP|COD|GEO)", col_up):
                col_map[col] = "dep_code"

        df = df.rename(columns=col_map)

        if "dep_code" not in df.columns:
            print("  ⚠️  Colonne code département non identifiée")
            raise ValueError("dep_code manquant")

        mask = df["dep_code"].str.match(r"^([0-9]{2}|2[AB])$", na=False)
        df = df[mask].copy()
        df["annee"] = 2021
        df["source_url"] = "https://drees.solidarites-sante.gouv.fr/"
        df["source_millesime"] = "2021"

        keep = ["dep_code", "annee"] + [
            c for c in ["rsa_taux", "prime_activite_taux", "ass_aspa_taux"]
            if c in df.columns
        ] + ["source_url", "source_millesime"]
        df = df[keep]

        # Compléter avec NaN si colonnes manquantes
        for col in ("rsa_taux", "prime_activite_taux", "ass_aspa_taux"):
            if col not in df.columns:
                df[col] = float("nan")

        df.to_csv(PROCESSED / "minimas_sociaux.csv", index=False)
        print(f"  ✓ minimas_sociaux.csv — {len(df)} lignes")

    except Exception as exc:
        print(f"  ✗ Erreur minimas : {exc} — placeholder créé")
        placeholder = dep_ref[["dep_code"]].copy()
        placeholder["annee"] = 2021
        placeholder["rsa_taux"] = float("nan")
        placeholder["prime_activite_taux"] = float("nan")
        placeholder["ass_aspa_taux"] = float("nan")
        placeholder["source_url"] = ""
        placeholder["source_millesime"] = "N/A"
        placeholder.to_csv(PROCESSED / "minimas_sociaux.csv", index=False)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  02_clean.py — Nettoyage des sources de données")
    print("=" * 60)

    clean_surendettement()
    clean_filosofi()
    clean_chomage()
    clean_rp()
    clean_minimas()

    print("\n" + "=" * 60)
    print("  Fichiers produits dans data/processed/ :")
    for fname in [
        "surendettement.csv", "filosofi.csv", "filosofi_gini.csv",
        "chomage.csv", "rp_menages.csv", "rp_logement.csv",
        "rp_population.csv", "minimas_sociaux.csv",
    ]:
        path = PROCESSED / fname
        if path.exists():
            nb = sum(1 for _ in open(path)) - 1
            print(f"  ✓ {fname} ({nb} lignes)")
        else:
            print(f"  ✗ {fname} non généré")
    print()


if __name__ == "__main__":
    main()
