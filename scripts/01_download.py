#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
01_download.py — Téléchargement de toutes les sources de données
Exécution : python scripts/01_download.py

Sources :
  - Banque de France : synthèses surendettement 2018–2023 (PDFs)
  - INSEE FiLoSoFi 2021 + SUPRA 2019
  - INSEE Chômage localisé (TCRD)
  - INSEE RP 2021 (ménages, population, logement, activité)
  - DREES / France Travail : minimas sociaux (RSA, prime d'activité)
  - GeoJSON départements (gregoiredavid/france-geojson)
"""

import os
import requests
import zipfile
import io
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
RAW  = ROOT / "data" / "raw"
GEO  = ROOT / "data" / "geo"

# ---------------------------------------------------------------------------
# Headers anti-bot pour INSEE
# ---------------------------------------------------------------------------
HEADERS_INSEE = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
    ),
    "Referer":    "https://www.insee.fr/fr/statistiques/2012804",
    "Accept":     (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*"
    ),
}

RESULTS: dict[str, bool] = {}   # label → succès


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------

def download_file(url: str, dest, headers: dict | None = None, label: str = "") -> bool:
    """Télécharge un fichier si non déjà présent. Retourne True si succès."""
    dest = pathlib.Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"  ✓ Déjà présent : {dest.name}")
        RESULTS[label or dest.name] = True
        return True
    print(f"  ↓ Téléchargement {label or dest.name} …")
    try:
        resp = requests.get(url, headers=headers, timeout=60, stream=True)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"  ✓ {dest.name} ({dest.stat().st_size // 1024} Ko)")
        RESULTS[label or dest.name] = True
        return True
    except Exception as exc:
        print(f"  ✗ ERREUR {label or dest.name} : {exc}")
        RESULTS[label or dest.name] = False
        return False


def download_zip(
    url: str, dest_dir, label: str = "", headers: dict | None = None
) -> bool:
    """Télécharge et décompresse un ZIP. Retourne True si succès."""
    dest_dir = pathlib.Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"  ↓ Téléchargement ZIP {label} …")
    try:
        resp = requests.get(url, headers=headers, timeout=120)
        resp.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            z.extractall(dest_dir)
        print(f"  ✓ ZIP extrait dans {dest_dir}")
        RESULTS[label] = True
        return True
    except Exception as exc:
        print(f"  ✗ ERREUR ZIP {label} : {exc}")
        RESULTS[label] = False
        return False


# ---------------------------------------------------------------------------
# T005 — Bloc BdF : PDFs synthèses surendettement 2018–2023
# ---------------------------------------------------------------------------

def download_bdf():
    """Télécharge les synthèses nationales de surendettement BdF 2018–2023."""
    print("\n=== BdF — Synthèses surendettement ===")
    dest_dir = RAW / "bdf"

    pdfs = {
        2023: "https://www.banque-france.fr/system/files/2024-03/SUREN-2023_Rapport-d_activite-des-commissions_web_0.pdf",
        2022: "https://www.banque-france.fr/system/files/2023-06/SUREN-2022-synthese-nationale.pdf",
        2021: "https://www.banque-france.fr/system/files/2022-06/SUREN-2021-synthese-nationale.pdf",
        2020: "https://www.banque-france.fr/system/files/2021-06/suren_2020_synthese_nationale.pdf",
        2019: "https://www.banque-france.fr/system/files/2020-06/suren_2019_synthese_nationale.pdf",
        2018: "https://www.banque-france.fr/system/files/2019-06/suren_2018_synthese_nationale.pdf",
    }

    bdf_headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
        ),
        "Referer": "https://www.banque-france.fr/fr/publications-et-statistiques/publications/synthese-nationale-des-rapports-dactivite-des-commissions-de-surendettement",
        "Accept": "application/pdf,*/*",
    }

    for annee, url in pdfs.items():
        dest = dest_dir / f"synthese_{annee}.pdf"
        download_file(url, dest, headers=bdf_headers, label=f"BdF synthèse {annee}")


# ---------------------------------------------------------------------------
# T006 — Bloc FiLoSoFi : revenus et inégalités départementales
# ---------------------------------------------------------------------------

def download_filosofi():
    """Télécharge les fichiers FiLoSoFi 2021 et SUPRA 2019."""
    print("\n=== INSEE — FiLoSoFi ===")
    dest_dir = RAW / "filosofi"

    download_zip(
        "https://www.insee.fr/fr/statistiques/fichier/7756729/base-cc-filosofi-2021-geo2024_csv.zip",
        dest_dir,
        label="FiLoSoFi 2021",
        headers=HEADERS_INSEE,
    )

    download_zip(
        "https://www.insee.fr/fr/statistiques/fichier/6036907/indic-struct-distrib-revenu-2019-SUPRA.zip",
        dest_dir,
        label="FiLoSoFi SUPRA 2019",
        headers=HEADERS_INSEE,
    )


# ---------------------------------------------------------------------------
# T007 — Bloc chômage localisé INSEE (TCRD)
# ---------------------------------------------------------------------------

def download_chomage():
    """Télécharge les fichiers chômage localisé INSEE (TCRD).
    Affiche un avertissement et l'URL manuelle si le téléchargement échoue.
    """
    print("\n=== INSEE — Chômage localisé (TCRD) ===")
    dest_dir = RAW / "chomage"

    urls_tcrd = [
        "https://www.insee.fr/fr/statistiques/fichier/2012804/TCRD_035.zip",
        "https://www.insee.fr/fr/statistiques/fichier/2012804/TCRD_035.xls",
    ]

    success = False
    for url in urls_tcrd:
        filename = pathlib.Path(url).name
        dest = dest_dir / filename
        if dest.exists():
            print(f"  ✓ Déjà présent : {dest.name}")
            RESULTS["Chômage TCRD"] = True
            success = True
            break
        print(f"  ↓ Tentative : {url}")
        try:
            resp = requests.get(url, headers=HEADERS_INSEE, timeout=60, stream=True)
            resp.raise_for_status()
            # Si c'est un ZIP, décompresser
            if url.endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                    z.extractall(dest_dir)
                print(f"  ✓ ZIP extrait dans {dest_dir}")
            else:
                dest_dir.mkdir(parents=True, exist_ok=True)
                with open(dest, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"  ✓ {dest.name} ({dest.stat().st_size // 1024} Ko)")
            RESULTS["Chômage TCRD"] = True
            success = True
            break
        except Exception as exc:
            print(f"  ✗ Échec ({exc})")

    if not success:
        print(
            "\n  ⚠️  Téléchargement TCRD bloqué (protection anti-bot INSEE)."
            "\n  Télécharger manuellement depuis :"
            "\n    https://www.insee.fr/fr/statistiques/2012804"
            "\n  et placer le fichier Excel dans : data/raw/chomage/"
        )
        RESULTS["Chômage TCRD"] = False


# ---------------------------------------------------------------------------
# T008 — Bloc RP 2021 : bases infracommunales
# ---------------------------------------------------------------------------

def download_rp():
    """Télécharge les 4 bases infracommunales RP 2021."""
    print("\n=== INSEE — RP 2021 (bases infracommunales) ===")
    dest_dir = RAW / "rp"

    zips = {
        "RP menages 2021":     "https://www.insee.fr/fr/statistiques/fichier/8268828/base-ic-menages-2021_csv.zip",
        "RP population 2021":  "https://www.insee.fr/fr/statistiques/fichier/8268806/base-ic-population-2021_csv.zip",
        "RP activite 2021":    "https://www.insee.fr/fr/statistiques/fichier/8268843/base-ic-activite-2021_csv.zip",
        "RP logement 2021":    "https://www.insee.fr/fr/statistiques/fichier/8268838/base-ic-logement-2021_csv.zip",
    }

    for label, url in zips.items():
        download_zip(url, dest_dir, label=label, headers=HEADERS_INSEE)


# ---------------------------------------------------------------------------
# T009 — Bloc minimas sociaux (DREES / France Travail)
# ---------------------------------------------------------------------------

def download_minimas():
    """Télécharge les données de minimas sociaux DREES / France Travail.
    Si indisponibles, affiche les instructions de téléchargement manuel.
    """
    print("\n=== DREES / France Travail — Minimas sociaux ===")
    dest_dir = RAW / "minimas"

    # Tentatives d'URLs connues pour les données RSA départementales
    urls = [
        # DREES - allocataires de minima sociaux
        (
            "https://drees.solidarites-sante.gouv.fr/sites/default/files/2023-07/"
            "er1314.xlsx",
            dest_dir / "drees_minimas_sociaux.xlsx",
            "DREES minimas sociaux",
        ),
        # Open data France Travail (ancien Pôle Emploi) — allocataires RSA
        (
            "https://statistiques.francetravail.org/stmt/tele?file=DEFM_DEP.zip",
            dest_dir / "DEFM_DEP.zip",
            "France Travail RSA dép.",
        ),
    ]

    success = False
    for url, dest, label in urls:
        if dest.exists():
            print(f"  ✓ Déjà présent : {dest.name}")
            RESULTS[label] = True
            success = True
            break
        try:
            resp = requests.get(url, timeout=60, stream=True)
            resp.raise_for_status()
            dest_dir.mkdir(parents=True, exist_ok=True)
            if str(dest).endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                    z.extractall(dest_dir)
                print(f"  ✓ ZIP extrait dans {dest_dir}")
            else:
                with open(dest, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"  ✓ {dest.name} ({dest.stat().st_size // 1024} Ko)")
            RESULTS[label] = True
            success = True
            break
        except Exception as exc:
            print(f"  ✗ {label} : {exc}")
            RESULTS[label] = False

    if not success:
        print(
            "\n  ⚠️  Téléchargement des minimas sociaux échoué."
            "\n  Sources alternatives :"
            "\n    - DREES indicateurs sociaux départ. :"
            "\n      https://drees.solidarites-sante.gouv.fr/jeux-de-donnees/indicateurs-sociaux-departementaux-isd-mise-0"
            "\n    - Open data France Travail :"
            "\n      https://statistiques.francetravail.org/stmt/defm"
            "\n  Placer les fichiers dans : data/raw/minimas/"
        )
        RESULTS["Minimas sociaux"] = False


# ---------------------------------------------------------------------------
# T010 — Bloc GeoJSON : contours départements
# ---------------------------------------------------------------------------

def download_geo():
    """Télécharge le GeoJSON des départements métropolitains (version simplifiée)."""
    print("\n=== GeoJSON — Départements France métropolitaine ===")

    GEO_URL = (
        "https://raw.githubusercontent.com/gregoiredavid/france-geojson/"
        "master/departements-version-simplifiee.geojson"
    )
    download_file(GEO_URL, GEO / "departements.geojson", label="GeoJSON départements")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  01_download.py — Téléchargement des sources de données")
    print("=" * 60)

    download_bdf()
    download_filosofi()
    download_chomage()
    download_rp()
    download_minimas()
    download_geo()

    # ── Rapport de synthèse ──────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  Rapport de synthèse")
    print("=" * 60)
    success = [k for k, v in RESULTS.items() if v]
    failed  = [k for k, v in RESULTS.items() if not v]

    print(f"\n  ✓ Réussis  ({len(success)}) : {', '.join(success) if success else '—'}")
    print(f"  ✗ Échoués ({len(failed)}) : {', '.join(failed) if failed else '—'}")

    if failed:
        print(
            "\n  ⚠️  Des sources ont échoué. Le pipeline de nettoyage (02_clean.py)"
            "\n     ignorera gracieusement les fichiers manquants."
        )
    else:
        print("\n  🎉 Tous les téléchargements ont réussi !")

    print()


if __name__ == "__main__":
    main()
