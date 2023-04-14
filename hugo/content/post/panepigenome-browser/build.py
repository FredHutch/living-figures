#!/usr/bin/env python3

from copy import deepcopy
import logging
from pathlib import Path
from zipfile import ZipFile
import pandas as pd
import sys
from living_figures.bio.epigenome.widgets import PanEpiGenomeBrowser
import os

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logging.info("Saving HTML for the Pan-Epigenome Browser")

logging.info("Instantiating the object")
blank_browser = PanEpiGenomeBrowser()
folder = Path(os.path.dirname(os.path.realpath(__file__)))

fp = folder / "PanEpigenome-base.html"
logging.info(f"Saving to {fp}")
blank_browser.to_html(Path(fp))

# Make a static render for each of the test datasets
data_dir = Path("src/living_figures/bio/epigenome/test_data")
for org_folder in data_dir.iterdir():
    if not org_folder.is_dir():
        continue

    # Make a copy of the blank widget
    org_browser = deepcopy(blank_browser)

    # Load the epigenome information
    motif_csvs = list(org_folder.rglob('*.motifs.csv'))
    org_browser._get_child("files", "pacbio").parse_files(motif_csvs)

    # Load the genome annotations
    org_annots = pd.read_csv(
        org_folder / "genome_annots.csv"
    )
    annot_cnames = [cname for cname in org_annots.columns.values if cname != 'genome']
    org_browser.set(
        path=["files", "genomes_annot"],
        value=org_annots,
        update=False
    )
    org_browser.set(
        path=["columns", "annotations", "label_genomes_by"],
        attr="options",
        value=annot_cnames,
        update=False
    )
    org_browser.set(
        path=["columns", "annotations", "annot_genomes_by"],
        attr="options",
        value=annot_cnames,
        update=False
    )
    org_browser.set(
        path=["columns", "annotations", "annot_genomes_by"],
        value=["BioProject"],
        update=False
    )
    org_browser.set(
        path=["columns", "contents", "title"],
        value=org_folder.name.replace("_", " "),
        update=False
    )

    # Save the widget with data populated
    fp = folder / f"PanEpigenome-{org_folder.name}.html"
    logging.info(f"Saving to {fp}")
    org_browser.to_html(Path(fp))

    # Add all of the input files into a ZIP
    zip_path = folder / f"{org_folder.name}.raw_data.zip"
    logging.info(f"Creating zip archive of raw data: {zip_path}")
    with ZipFile(zip_path, 'w') as zip_object:

        for fp in motif_csvs:
            zip_object.write(fp)
        zip_object.write(org_folder / "genome_annots.csv")

    logging.info(f"Number of genomes: {len(motif_csvs):,}")
    n_motifs = org_browser.get(
        ["files", "pacbio"]
    )["motifString"].unique().shape[0]
    logging.info(f"Number of motifs: {n_motifs:,}")
    logging.info("")
