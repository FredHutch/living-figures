import pandas as pd
import streamlit as st
import numpy as np
import plotly.express as px
import widgets.streamlit as wist
from widgets.base.exceptions import WidgetFunctionException


class Volcano(wist.StreamlitWidget):

    extra_imports = [
        "import pandas as pd",
        "import plotly.express as px",
        "import numpy as np",
        "from io import StringIO",
        "from widgets.base.exceptions import WidgetFunctionException"
    ]

    requirements = ["plotly", "kaleido"]

    selected_columns = []

    children = [
        wist.StDataFrame(
            id="df",
            label="Data Table",
            help="Table of results including the p-value and effect size"
        ),
        *[
            wist.StExpander(
                id=elem,
                label=label,
                expanded=False,
                children=[
                    wist.StSelectString(
                        id="cname",
                        label="Column",
                        help="Select the column to use"
                    ),
                    wist.StString(
                        id="label",
                        label="Label",
                        value=label.split(": ")[-1],
                        help="Label for the axis"
                    ),
                    wist.StSelectString(
                        id="trans",
                        label="Transformation",
                        help="Transformation used (if any)",
                        options=["", "-log10"],
                        value="-log10" if elem == "pval" else ""
                    ),
                    wist.StFloat(
                        id="threshold",
                        label="Threshold",
                        help="Threshold used for filtering. Use 0 to disable.",
                        step=0.00001
                    ),
                    wist.StCheckbox(
                        id="showthreshold",
                        label="Threshold Line",
                        help="Show or hide the threshold line"
                    ),
                    wist.StSelectString(
                        id="marginal",
                        label="Marginal Plot",
                        help="Optionally plot the distribution of values to the side", # noqa
                        value="",
                        options=["histogram", "rug", "box", "violin", ""]
                    )
                ]
            )
            for elem, label in [
                ("pval", "Options: p-value"),
                ("effect", "Options: effect size")
            ]
        ],
        wist.StExpander(
            id="formatting",
            label="Formatting Options",
            expanded=False,
            children=[
                wist.StString(
                    id="title",
                    label="Title",
                    help="Optional title displayed on the top of the plot",
                    value=""
                ),
                wist.StString(
                    id="filter_label",
                    label="Filter Label",
                    help="Label used to indicate whether a point passes the filter", # noqa
                    value="Passes Filter"
                ),
                wist.StSlider(
                    id="threshold_line_opacity",
                    label="Threshold Line Opacity",
                    help="Degree of opacity for the line indicating the threshold", # noqa
                    min_value=0.,
                    max_value=1.,
                    step=0.01,
                    value=0.25
                ),
                wist.StSelectString(
                    id="cmap",
                    label="Point Colors",
                    help="Color map used to color the points in the plot"
                ),
                wist.StInteger(
                    id="width",
                    label="Width",
                    help="Width of the rendered plot",
                    value=600,
                    step=1
                ),
                wist.StInteger(
                    id="height",
                    label="Height",
                    help="Height of the rendered plot",
                    value=400,
                    step=1
                ),
                wist.StSelectString(
                    id="template",
                    label="Template",
                    help="Theme used for formatting",
                    options=[
                        "plotly",
                        "plotly_white",
                        "plotly_dark",
                        "ggplot2",
                        "seaborn",
                        "simple_white",
                        "none"
                    ],
                    value="none"
                )
            ]
        )
    ]

    def run_self(self):

        # Set up the color map using the plotly express palettes
        self.setup_px_cmap()

        # Get the Data Table
        df = self.get(path=["df"])

        # If a Data Table was provided
        if df is not None and df.shape[0] > 0:

            # Update the column name selectors
            self.update_columns(df)

            # Build a set of kwargs which will be used to render the plot
            plot_data = self.start_plot_data(df)

            # Add the filtering logic
            plot_data = self.add_filtering(plot_data)

            # Add styling information
            plot_data = self.add_styling(plot_data)

            # Make a plot and also render the SVG
            fig = self.render_scatter(plot_data)

            # Display the plot
            st.plotly_chart(fig)

            # Show the table of rows which pass the filter (if any)
            if "passes_filter" in plot_data["data_frame"].columns.values:
                if (plot_data["data_frame"]["passes_filter"] == "True").any():
                    st.dataframe(plot_data["data_frame"].query(
                        "passes_filter == 'True'"
                    ).drop(columns=["passes_filter"]))

        self.download_html_button()
        self.download_script_button()

    def render_scatter(self, plot_data):

        # Make a plot
        fig = px.scatter(
            **plot_data
        )

        # Add the threshold lines (if any)
        self.threshold_lines(fig)

        return fig

    def update_columns(self, df):
        """Update the column selectors for the p-value and effect size."""

        self.selected_columns = []

        # Set the menu option to the best guess for the p-value
        self.update_select_menu(
            ["pval", "cname"],
            df,
            criteria=lambda v: isinstance(v, float) and v >= 1 and v >= 0
        )

        self.update_select_menu(
            ["effect", "cname"],
            df,
            criteria=lambda v: isinstance(v, float)
        )

    def setup_px_cmap(self):
        """Set up a multi-select resource with the plotly express palettes."""

        px_cmaps = [
            pal_name
            for pal_name in px.colors.qualitative.__dict__.keys()
            if not pal_name.startswith("_") and pal_name != "swatches"
        ]

        self.set(
            path=["formatting", "cmap"],
            attr="options",
            value=px_cmaps,
            update=False
        )

        self.set(path=["formatting", "cmap"], value=px_cmaps[0])

    def start_plot_data(self, df: pd.DataFrame) -> dict:

        # Get the attributes assigned for the pval and effect columns
        pval = self.all_values(path=["pval"])
        effect = self.all_values(path=["effect"])

        # Add the transformation column name and label
        pval["trans_cname"] = pval['cname'] if pval['trans'] == "" else f"{pval['cname']} ({pval['trans']})" # noqa
        pval["trans_label"] = pval['cname'] if pval['trans'] == "" else f"{pval['label']} ({pval['trans']})" # noqa

        # Set up the plot data
        plot_data = dict(
            data_frame=df.assign(
                # Apply the transformation and create a new column
                **{
                    pval["trans_cname"]: df[pval["cname"]].apply(
                        lambda v: self.transform_pval(v, pval["trans"])
                    )
                }
            ),
            x=effect["cname"],
            y=pval["trans_cname"],
            hover_data=list(df.columns.values) + [pval["trans_cname"]],
            labels={
                pval["cname"]: pval["label"],
                pval["trans_cname"]: pval["trans_label"],
                effect["cname"]: effect["label"]
            },
            color_discrete_sequence=px.colors.qualitative.__dict__.get(
                self.get(path=["formatting", "cmap"])
            ),
            marginal_x=None if effect['marginal'] == '' else effect['marginal'], # noqa
            marginal_y=None if pval['marginal'] == '' else pval['marginal']
        )

        return plot_data

    def add_filtering(self, plot_data: dict) -> dict:

        # Test each point to see if it passes the filter
        passes_filter = plot_data["data_frame"].apply(
            self.test_passes_filter,
            axis=1
        )

        # If no points pass the filter, take no further action
        if not passes_filter.any():
            return plot_data

        # Add a column indicating which rows pass the filter
        plot_data["data_frame"] = plot_data["data_frame"].assign(
            passes_filter=passes_filter.apply(str)
        )

        # Tell the plot to color by that value
        plot_data["color"] = "passes_filter"

        # Modify the label which is displayed
        plot_data["labels"]["passes_filter"] = self.get(
            path=["formatting", "filter_label"]
        )

        return plot_data

    def test_passes_filter(self, r: pd.Series):
        """Test whether a single column passes the filter."""

        if r[
            self.get(path=["pval", "cname"])
        ] > self.get(path=["pval", "threshold"]):
            return False
        if np.abs(r[
            self.get(path=["effect", "cname"])
        ]) < self.get(path=["effect", "threshold"]):
            return False
        else:
            return True

    def add_styling(self, plot_data: dict) -> dict:

        formatting = self.all_values(path=["formatting"])

        for kw in ["title", "width", "height", "template"]:
            plot_data[kw] = formatting[kw]

        return plot_data

    def threshold_lines(self, fig) -> None:

        # Get the attributes assigned for the pval and effect columns
        pval = self.all_values(path=["pval"])
        effect = self.all_values(path=["effect"])
        threshold_line_opacity = self.get(
            path=["formatting", "threshold_line_opacity"]
        )

        if pval["showthreshold"] and pval["threshold"] != 0:
            fig.add_hline(
                y=self.transform_pval(
                    pval["threshold"],
                    pval["trans"]
                ),
                opacity=threshold_line_opacity
            )

        if effect["showthreshold"]:
            fig.add_vline(
                x=effect["threshold"],
                opacity=threshold_line_opacity
            )
            fig.add_vline(
                x=-effect["threshold"],
                opacity=threshold_line_opacity
            )

    def update_select_menu(self, resource_id, df: pd.DataFrame, criteria=None):

        options = list(df.columns.values)

        # If the currently selected value is not in the list of options
        if self.get(path=resource_id) is None or self.get(path=resource_id) not in options: # noqa

            # Set the options
            self.set(
                path=resource_id,
                attr="options",
                value=options,
                update=False
            )

            # If no criteria was provided
            if not criteria:
                self.set(path=[resource_id], attr="index", value=0)

            # Otherwise
            else:

                # Find the best selection
                selection = self.pick_best_column(df, criteria)

                # And set that option
                self.set(
                    path=resource_id,
                    attr="index",
                    value=list(options).index(selection)
                )

    def pick_best_column(self, df, criteria):
        """Select the top-scoring column from the DataFrame"""

        # Count up the number of rows which meet the criteria, per column
        column_scores = df.apply(
            lambda c: c.apply(criteria).sum()
        )

        for cname, score in column_scores.items():
            if score ==  column_scores.max() and cname not in self.selected_columns: # noqa
                self.selected_columns.append(cname)
                return cname

    def transform_pval(self, v: float, trans: str):
        if trans == "-log10":
            return -np.log10(v)
        elif trans == "":
            return v
        else:
            raise WidgetFunctionException(
                f"Unspecified transformation: {trans}"
            )


if __name__ == "__main__":
    volcano = Volcano()
    volcano.run()
