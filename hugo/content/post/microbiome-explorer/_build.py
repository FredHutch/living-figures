#!/usr/bin/env python3

from copy import deepcopy
import logging
from pathlib import Path
import sys
from living_figures.bio.fom.widgets.microbiome import MicrobiomeExplorer
import os

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logging.info("Saving HTML for the Microbiome Explorer")

logging.info("Instantiating the object")
blank_browser = MicrobiomeExplorer()

# Get the list of options
options = blank_browser._get_child(
    "plots"
).children[0].get_attr("options")

# Show one example of each option
blank_browser._get_child("plots").set_value(
    [True for _ in options] + [False for _ in range(20 - len(options))]
)
for i, option in enumerate(options):
    blank_browser._get_child("plots").children[i]._get_child("_selector_menu").set_value(option.label)

folder = Path(os.path.dirname(os.path.realpath(__file__)))
fp = folder / "MicrobiomeExplorer-base.html"
logging.info(f"Saving to {fp}")
blank_browser.to_html(Path(fp))

# Make a static render for each of the test datasets
data_dir = Path("src/living_figures/bio/fom/widgets/microbiome/example_data/curatedMetagenomicData/")
for abund_fp in data_dir.glob("*.abund.csv"):

    # Make a copy of the blank widget
    org_browser = deepcopy(blank_browser)

    # Load the abundance and annotation information
    logging.info(f"Loading data from {abund_fp}")
    org_browser._get_child("data", "abund").parse_files(abund_fp)
    annot_fp = Path(str(abund_fp.absolute()).replace(".abund.csv", ".annot.csv"))
    logging.info(f"Loading data from {annot_fp}")
    org_browser._get_child("data", "annots").parse_files(annot_fp)

    # Save the widget with data populated
    fp = folder / f"PanEpigenome-{abund_fp.name.replace('.abund.csv', '')}.html"
    logging.info(f"Saving to {fp}")
    org_browser.to_html(Path(fp))
