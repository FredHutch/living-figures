from copy import deepcopy
from living_figures.bio.fom.widgets.microbiome import MicrobiomeAbund
from living_figures.bio.fom.widgets.microbiome import StHashedDataFrame
from living_figures.bio.fom.widgets.microbiome import Ordination
from living_figures.bio.fom.widgets.microbiome import AbundantOrgs
from living_figures.bio.fom.widgets.microbiome import AlphaDiversity
from living_figures.bio.fom.widgets.microbiome import BetaDiversity
from living_figures.bio.fom.widgets.microbiome import DifferentialAbundance
from living_figures.bio.fom.widgets.microbiome import SingleOrganism
from living_figures.bio.fom.widgets.microbiome.base_widget import BaseMicrobiomeExplorer # noqa
import widgets.streamlit as wist


class MicrobiomeExplorer(BaseMicrobiomeExplorer):
    """
    Widget used for the analysis of microbiome data.

    Input data:
        - Microbiome abundance data, from a variety of file formats
        - Sample annotation metadata
        - Microbe anotation metadata

    Types of analysis:
        - Ordination of samples
        - Visualization of microbial abundances (stacked bars, etc.)
        - Comparison of the abundance of a single microbe across samples
        - Testing for significant differences in organism abundances
          between groups of samples
    """

    id = "microbiome-explorer"
    subtitle = "Microbiome Explorer"

    children = [

        wist.StExpander(
            id="data",
            label="Input Data",
            expanded=True,
            children=[
                MicrobiomeAbund(id="abund"),
                wist.StDownloadDataFrame(
                    target="abund",
                    label="Download Abundances",
                    index=True
                ),
                StHashedDataFrame(
                    id="annots",
                    label="Sample Annotations"
                ),
                wist.StDownloadDataFrame(
                    target="annots",
                    label="Download Annotations"
                )
            ]
        ),
        wist.StDuplicator(
            id='plots',
            children=[
                deepcopy(wist.StSelector(
                    id=f"plot_{i}",
                    disable_sidebar=True,
                    options=[
                        AbundantOrgs(id="abundant_orgs"),
                        Ordination(id="ordination"),
                        AlphaDiversity(id="alpha_diversity"),
                        BetaDiversity(id="beta_diversity"),
                        DifferentialAbundance(id="differential_abundance"),
                        SingleOrganism(id="single_organism")
                    ]
                ))
                for i in range(20)
            ],
            value=[True] + [False for _ in range(19)]
        )
    ]

    requirements = [
        "living-figures", "statsmodels"
    ]
    pyodide_requirements = ["statsmodels"]

    extra_imports = [
        "from scipy.spatial import distance",
        "from scipy import stats",
        "from scipy.stats import entropy, spearmanr, pearsonr, f_oneway",
        "from living_figures.helpers import parse_numeric, is_numeric",
        "from statsmodels.stats.multitest import multipletests",
        "import numpy as np",
        "import pandas as pd",
        "from plotly.subplots import make_subplots",
        "import plotly.express as px",
        "import plotly.graph_objects as go",
        "from typing import Union, Any, List",
        "from widgets.base.exceptions import WidgetFunctionException",
        "from widgets.base.helpers import parse_dataframe_string",
        "from living_figures.helpers.scaling import convert_text_to_scalar",
        "from living_figures.helpers.sorting import sort_table",
        "from living_figures.bio.fom.utilities import parse_taxon_abundances",
        "from living_figures.bio.fom.widgets.microbiome.base_widget import BaseMicrobiomeExplorer", # noqa
        "from hashlib import md5",
        "from sklearn.decomposition import PCA",
        "from sklearn.manifold import TSNE"
    ]

    def run_self(self):

        self.update_options()

        self.clone_button(sidebar=True)

        # Link to the online documentation
        docs_url = "https://living-figures.com/post/microbiome-explorer/"
        self.sidebar_container.markdown(
            f"[Microbiome Explorer Documentation]({docs_url})"
        )


if __name__ == "__main__":
    w = MicrobiomeExplorer()
    w.run()
