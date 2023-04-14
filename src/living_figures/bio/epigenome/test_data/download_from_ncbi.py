#!/usr/bin/env python3
"""Download a set of test data from NCBI."""

# Number of organisms to download data for
NORG = 5

import os
import pandas as pd
import requests

def main(NORG):
    # Table with all of the available datasets
    df = pd.read_csv(
        "https://ftp.ncbi.nlm.nih.gov/pub/supplementary_data/basemodification.csv"
    )

    # Only consider the base modification summary CSVs
    df = df.query("`File Type` == 'BaseModification-MotifsSummary'")

    # For simplicity, filter to the files with clean .csv endings
    df = df.loc[df['URI'].apply(lambda s: s.endswith('.csv') and 'motif' in s)]

    # For each organism with the most 
    for org_name in df['Organism'].value_counts().head(NORG).index.values:

        # Download the available data
        download_org_list(org_name, df.query(f"Organism == '{org_name}'"))


def download_org_list(org_name, org_df):

    # Folder where the files will be downloaded
    org_folder = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        org_name.replace(" ", "_").replace(".", "")
    )

    if not os.path.exists(org_folder):
        os.makedirs(org_folder)

    # Format the genome name
    org_df = org_df.assign(
        genome=org_df.apply(
            lambda r: get_genome_name(r, skip=None),
            axis=1
        )
    )

    # Drop any duplicates
    org_df = org_df.groupby('genome').head(1)

    # Download each genome
    for genome, url in org_df.set_index('genome')['URI'].items():
        genome_fp = os.path.join(org_folder, f"{genome}.motifs.csv")
        print(f"Downloading {genome_fp} from {url}")
        r = requests.get(url, allow_redirects=True)
        with open(genome_fp, 'wb') as handle:
            handle.write(r.content)

    # Write out the table
    org_df.to_csv(
        f"{org_folder}/genome_annots.csv",
        index=None
    )


def get_genome_name(r, skip=None):
    """Pick a name for each genome."""

    for kw in ['Nucleotide Accession', 'SRA Accession', 'BioSample']:
        if not pd.isnull(r[kw]):
            return r[kw].split("|")[0]
    raise Exception(f'Could not figure out name for {r}')


if __name__ == "__main__":
    main(NORG)
