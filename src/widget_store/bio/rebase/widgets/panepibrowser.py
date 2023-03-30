#!/usr/bin/env python3

from typing import Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import widgets.streamlit as wist
from widget_store.bio.rebase.utilities.rebase_file import StREBASE
from widget_store.helpers.scaling import convert_text_to_scalar
from widget_store.helpers.sorting import sort_table


class PanEpiGenomeBrowser(wist.StreamlitWidget):
    """
    Visualize the epigenetic information from a collection of
    genomes, with input files provided in REBASE format.
    """

    children = [
        StREBASE(id="rebase"),
        wist.StDataFrame(id="genomes_annot", label="Genome Annotations"),
        wist.StDownloadDataFrame(target="genomes_annot", label="Download Genome Annotations"),
        wist.StDataFrame(id="motifs_annot", label="Motif Annotations"),
        wist.StDownloadDataFrame(target="motifs_annot", label="Download Motif Annotations"),
        wist.StMultiSelect(id='hidden_genomes', label="Hide Genomes"),
        wist.StMultiSelect(id='hidden_motifs', label="Hide Motifs"),
        wist.StSelectString(
            id='genome_axis',
            label="Show Genomes On",
            options=["Rows", "Columns"],
            value="Rows"
        ),
        wist.StSelectString(
            id='sort_genomes_by',
            label="Sort Genomes By",
            options=["Motif Presence/Absence", "Genome Annotations"],
            value="Motif Presence/Absence"
        ),
        wist.StSelectString(
            id='sort_motifs_by',
            label="Sort Motifs By",
            options=["Genome Presence/Absence", "Motif Annotations"],
            value="Genome Presence/Absence"
        ),
        wist.StMultiSelect(
            id="annot_genomes_by",
            label="Annotate Genomes By"
        ),
        wist.StMultiSelect(
            id="annot_motifs_by",
            label="Annotate Motifs By"
        ),
        wist.StSelectString(
            id="heatmap_cpal",
            label="Heatmap Color Palette",
            options=px.colors.named_colorscales(),
            value="blues"
        ),
        wist.StSelectString(
            id="annot_cpal",
            label="Annotation Color Palette",
            options=px.colors.named_colorscales(),
            value="bluered"
        ),
        wist.StInteger(
            label="Figure Width",
            id="figure_width",
            min_value=100,
            max_value=1200,
            step=1,
            value=600
        ),
        wist.StInteger(
            label="Figure Height",
            id="figure_height",
            min_value=100,
            max_value=1200,
            step=1,
            value=600
        ),
        wist.StInteger(
            id="min_fraction",
            label="Minimum Percentage per Motif",
            min_value=0,
            max_value=100,
            value=25,
            step=1,
            help="Only show motifs which are present in a single genome at this minimum threshold"
        ),
        wist.StInteger(
            id="min_prevalence",
            label="Minimum Number of Genomes per Motif",
            min_value=1,
            value=1,
            step=1,
            help="Only show motifs which are present in at least this many genomes"
        )
    ]

    def get_df_vals(self, df_name, cname):
        df = self.get([df_name])
        if df.shape[0] > 0:
            return df[
                cname
            ].dropna(
            ).drop_duplicates(
            ).tolist()
        else:
            return []

    def update_selector_options(self, df_name, cname, selector):
        """Keep the Hide Genomes selector in sync."""

        # Get the list of genomes from the specified table
        all_options = self.get_df_vals(df_name, cname)

        # Get the list of options in the specified input
        avail_options = self.get([selector], attr="options")

        # If they are not the same
        if set(avail_options) != set(all_options):

            # Update the menu item
            self.set([selector], attr="options", value=all_options)

    def update_table(self, table, rebase_cname):
        """
        Update the specified table, making sure that it contains
        a row with an 'id' value for each of the unique values
        in the specifed column in the REBASE table.
        """

        # Get the list of values from the specified column in the REBASE table
        all_options = self.get_df_vals("rebase", rebase_cname)

        # If there are no options, stop
        if len(all_options) == 0:
            return

        # Get the target table which may be updated
        df = self.get([table])

        # If the table is empty
        if df.shape[0] == 0:

            # Set up a new table
            df = pd.DataFrame(dict(id=all_options))

        # Otherwise
        else:

            # See if any of the options are missing
            missing_options = [
                option
                for option in df.reindex(
                    columns=['id']
                ).dropna(
                )['id'].drop_duplicates().tolist()
                if option not in all_options
            ]

            # If no options are missing, we're done
            if len(missing_options) == 0:
                return

            # Otherwise, add in new rows
            df = pd.concat([
                df,
                pd.DataFrame(dict(id=missing_options))
            ])

        # Update the modified table
        self.set(path=[table], value=df)

        # Also update the download button
        self._get_child(f"download_{table}").run_self()

    def run_self(self):

        # Update the metadata tables, if needed
        self.update_table("genomes_annot", "genome")
        self.update_table("motifs_annot", "enz_name")

        # Update the hidden_genomes selector
        self.update_selector_options("rebase", "genome", "hidden_genomes")
        self.update_selector_options("rebase", "enz_name", "hidden_motifs")

        # Update the annotation selectors
        self.update_annotation_selectors()

        # Make the plot
        self.plot_heatmap()

        # Give the user the option to clone this widget
        self.clone_button()

    def update_annotation_selectors(self):

        genomes_annot = self.get(["genomes_annot"])
        if genomes_annot.shape[0] == 0:
            genomes_annot = pd.DataFrame(dict(id=[]))
        else:
            msg = "Must provide 'id' column in genome annotations"
            assert 'id' in genomes_annot.columns.values, msg

            genomes_annot = genomes_annot.set_index('id')

        for df, input_elem in [
            (self.join_motif_annots(), "annot_motifs_by"),
            (genomes_annot, "annot_genomes_by")
        ]:
            self.set(
                path=[input_elem],
                attr="options",
                value=df.columns.values
            )

    def plot_heatmap(self):

        # Get the wide-form tables for plotting
        value_df, text_df = self.prep_heatmap_data()

        if value_df is None:
            return

        # Add the motif annotations from the REBASE files
        # to the user-provided motif annotations
        motif_annot = self.join_motif_annots()

        # Get the genome annotations
        genomes_annot = self.get(["genomes_annot"]).set_index('id')

        # If the user wants to sort the enzymes by an annotation
        if self.get(["sort_motifs_by"]) == "Motif Annotations":

            assert len(self.get(["annot_motifs_by"])) > 0, "Must specify motif annotations for sorting"

            # Sort the annotation table
            enzyme_annot_df = motif_annot.reindex(
                columns=self.get(["annot_motifs_by"])
            ).sort_values(
                by=self.get(["annot_motifs_by"])
            )

            # Only keep the motifs which are detected in >=1 genome
            enzyme_annot_df = enzyme_annot_df.reindex(
                index=[
                    i for i in enzyme_annot_df.index.values
                    if i in value_df.columns.values
                ]
            )

            # Reorder the display data to match
            value_df = value_df.reindex(
                columns=enzyme_annot_df.index.values
            )
            text_df = text_df.reindex(
                columns=enzyme_annot_df.index.values
            )

        # Otherwise, the annotations should be made to match the order of the genomes
        else:
            enzyme_annot_df = motif_annot.reindex(
                columns=self.get(["annot_motifs_by"]) if len(self.get(["annot_motifs_by"])) > 0 else ['none'],
                index=value_df.columns.values
            )

        # If the user wants to sort the genomes by an annotation
        if self.get(["sort_genomes_by"]) == "Genome Annotations":

            assert len(self.get(["annot_genomes_by"])) > 0, "Must specify genome annotations for sorting"

            # Sort the genome annotation table
            genomes_annot_df = genomes_annot.reindex(
                columns=self.get(["annot_genomes_by"])
            ).sort_values(
                by=self.get(["annot_genomes_by"])
            )

            # Only keep the genomes which have >=1 motif detected
            genomes_annot_df = genomes_annot_df.reindex(
                index=[
                    i for i in genomes_annot_df.index.values
                    if i in value_df.index.values
                ]
            )

            # Reorder the display data to match
            value_df = value_df.reindex(
                index=genomes_annot_df.index.values
            )
            text_df = text_df.reindex(
                index=genomes_annot_df.index.values
            )

        # Otherwise, the annotations should be made to match the order of the genomes
        else:
            genomes_annot_df = genomes_annot.reindex(
                columns=self.get(["annot_genomes_by"]) if len(self.get(["annot_genomes_by"])) > 0 else ['none'],
                index=value_df.index.values
            )

        # For the colors, convert all values to numeric and scale to 0-1
        enzyme_marginal_z = enzyme_annot_df.apply(
            convert_text_to_scalar
        )
        genome_marginal_z = genomes_annot_df.apply(
            convert_text_to_scalar
        )

        # Set the fraction of the plot used for the marginal annotation
        # depending on the number of those annotations
        enzyme_annot_frac = min(0.5, 0.02 + (0.05 * float(len(self.get(["annot_motifs_by"])))))
        genomes_annot_frac = min(0.5, 0.02 + (0.05 * float(len(self.get(["annot_genomes_by"])))))

        # If the genomes are being displayed on the horizontal axis
        if self.get(['genome_axis']) == "Columns":

            # Transpose the DataFrames with genome/motif values
            value_df = value_df.T
            text_df = text_df.T

            # The enzyme marginal annotation will be on the rows
            row_marginal_x = self.get(["annot_motifs_by"])
            row_marginal_y = value_df.index.values
            row_marginal_z = enzyme_marginal_z.values
            row_marginal_text = enzyme_annot_df.values

            # The genome marginal annotation will be on the columns
            col_marginal_y = self.get(["annot_genomes_by"])
            col_marginal_x = value_df.columns.values
            col_marginal_z = genome_marginal_z.T.values
            col_marginal_text = genomes_annot_df.T.values

            # Compute the data for the genome-marginal barplot
            genome_bar_x = value_df.columns.values
            genome_bar_y = (value_df > 0).sum(axis=0)
            genome_bar_text = list(map(lambda i: f"{i[0]:,} motifs detected in {i[1]}", zip(genome_bar_y, genome_bar_x)))
            genome_bar_orientation = "v"

            # Place the genome-marginal barplot in the layout
            genome_bar_nrows = 3
            genome_bar_ncols = 2

            # Compute the data for the motif-marginal barplot
            motif_bar_x = (value_df > 0).sum(axis=1)
            motif_bar_y = value_df.index.values
            motif_bar_text = list(map(lambda i: f"Motif {i[0]} detected in {i[1]:,} genomes", zip(motif_bar_y, motif_bar_x)))
            motif_bar_orientation = "h"

            # Place the motif-marginal barplot in the layout
            motif_bar_nrows = 2
            motif_bar_ncols = 3

        # Otherwise
        else:

            # The genomes must be displayed on the vertical axis
            assert self.get(['genome_axis']) == "Rows"

            # The genome/motif data does not need to be transposed

            # The enzyme marginal annotation will be on the columns
            col_marginal_x = value_df.columns.values
            col_marginal_y = self.get(["annot_motifs_by"])
            col_marginal_z = enzyme_marginal_z.T.values
            col_marginal_text = enzyme_annot_df.T.values

            # The genome marginal annotation will be on the rows
            row_marginal_x = self.get(["annot_genomes_by"])
            row_marginal_y = value_df.index.values
            row_marginal_z = genome_marginal_z.values
            row_marginal_text = genomes_annot_df.values

            # Compute the data for the marginal barplot
            genome_bar_x = (value_df > 0).sum(axis=1)
            genome_bar_y = value_df.index.values
            genome_bar_text = list(map(lambda i: f"{i[0]:,} motifs detected in {i[1]}", zip(genome_bar_x, genome_bar_y)))
            genome_bar_orientation = "h"

            # Place the genome-marginal barplot in the layout
            genome_bar_nrows = 2
            genome_bar_ncols = 3

            # Compute the data for the motif-marginal barplot
            motif_bar_x = value_df.columns.values
            motif_bar_y = (value_df > 0).sum(axis=0)
            motif_bar_text = list(map(lambda i: f"Motif {i[0]} detected in {i[1]:,} genomes", zip(motif_bar_x, motif_bar_y)))
            motif_bar_orientation = "v"

            # Place the motif-marginal barplot in the layout
            motif_bar_nrows = 3
            motif_bar_ncols = 2

        # The size of the marginal plots is driven by the number of annotations
        row_heights = [enzyme_annot_frac, 1 - enzyme_annot_frac, 0.1]
        column_widths = [genomes_annot_frac, 1 - genomes_annot_frac, 0.1]

        # Set up the figure
        fig = make_subplots(
            rows=3,
            cols=3,
            vertical_spacing=0.01,
            horizontal_spacing=0.01,
            start_cell="bottom-left",
            column_widths=column_widths,
            row_heights=row_heights,
            shared_xaxes=True,
            shared_yaxes=True,
        )

        # Add the heatmap to the plot
        fig.append_trace(
            go.Heatmap(
                x=value_df.columns.values,
                y=value_df.index.values,
                z=value_df.values,
                colorscale=self.get(["heatmap_cpal"]),
                text=text_df.values,
                hoverinfo="text",
                colorbar_title="Percent<br>Detection<br>of Motif"
            ),
            row=2,
            col=2
        )

        # Add the marginal annotation on the rows
        fig.append_trace(
            go.Heatmap(
                x=row_marginal_x,
                y=row_marginal_y,
                z=row_marginal_z,
                colorscale=self.get(["annot_cpal"]),
                text=row_marginal_text,
                hoverinfo="text",
                showscale=False,
            ),
            row=2,
            col=1
        )

        # Add the marginal annotation on the columns
        fig.append_trace(
            go.Heatmap(
                x=col_marginal_x,
                y=col_marginal_y,
                z=col_marginal_z,
                colorscale=self.get(["annot_cpal"]),
                text=col_marginal_text,
                hoverinfo="text",
                showscale=False
            ),
            row=1,
            col=2
        )

        # Add the barplot with the number of motifs per genome
        fig.append_trace(
            go.Bar(
                x=genome_bar_x,
                y=genome_bar_y,
                hovertext=genome_bar_text,
                orientation=genome_bar_orientation,
                marker_color="blue",
                showlegend=False,
            ),
            row=genome_bar_nrows,
            col=genome_bar_ncols
        )

        # Add the barplot with the number of genomes per motif
        fig.append_trace(
            go.Bar(
                x=motif_bar_x,
                y=motif_bar_y,
                hovertext=motif_bar_text,
                orientation=motif_bar_orientation,
                marker_color="blue",
                showlegend=False,
            ),
            row=motif_bar_nrows,
            col=motif_bar_ncols
        )

        # Set up the size of the figure
        fig.update_layout(
            height=self.get(['figure_height']),
            width=self.get(['figure_width']),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )

        # Return the figure
        self.main_container.plotly_chart(fig)

    def join_motif_annots(self) -> pd.DataFrame:
        """
        Join the user-provided motif annotations to the set
        of automatically generated annotations.
        """

        user_annots = self.get(["motifs_annot"])
        if user_annots.shape[0] == 0:
            user_annots = pd.DataFrame(dict(id=[]))
        else:
            msg = "Must provide 'id' column in motif annotations"
            assert 'id' in user_annots.columns.values, msg
            user_annots = user_annots.set_index('id')

        return pd.merge(
            user_annots,
            self.get_motif_annots(),
            how='outer',
            left_index=True,
            right_index=True
        )

    def get_motif_annots(self) -> pd.DataFrame:
        """Get the motif annotations from the REBASE files."""

        rebase = self.get(["rebase"])

        df = pd.DataFrame({
            cname: rebase.groupby(
                'enz_name'
            ).head(
                1
            ).set_index(
                'enz_name'
            )[cname]
            for cname in [
                "enz_type",
                "sub_type",
                "meth_base",
                "meth_type",
                "comp_meth_base",
                "rec_seq",
                "type_label"
            ]
            if cname in rebase.columns.values
        })

        if 'rec_seq' in df.columns.values:
            df = df.assign(
                motif_length=lambda d: d.rec_seq.apply(len)
            )

        return df

    def prep_heatmap_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:

        user_inputs = self.all_values(flatten=True)

        if user_inputs["rebase"].shape[0] == 0:
            self.main_container.info(
                "Please add REBASE information to get started"
            )
            return None, None

        # MAKE A WIDE TABLE
        value_df = user_inputs["rebase"].pivot_table(
            index="genome",
            columns="enz_name",
            values="percent_detected"
        ).fillna(0)

        text_df = user_inputs["rebase"].pivot(
            index="genome",
            columns="enz_name",
            values="text"
        ).fillna("")

        # MASK ANY SELECTED ROWS/COLUMNS
        if len(user_inputs['hidden_motifs']) > 0:
            value_df = value_df.drop(
                columns=user_inputs['hidden_motifs']
            )
        if len(user_inputs['hidden_genomes']) > 0:
            value_df = value_df.drop(
                index=user_inputs['hidden_genomes']
            )

        # MASK ANY MOTIFS WHICH DO NOT REACH THE MINIMUM THRESHOLD
        value_df = value_df.loc[
            :,
            value_df.max() >= user_inputs['min_fraction']
        ]

        # MASK ANY MOTIFS WHICH ARE NOT FOUND IN THE SPECIFIED NUMBER OF GENOMES
        if user_inputs['min_prevalence'] > 1:

            # Remove the motifs which do not meet the threshold
            value_df = value_df.reindex(
                columns=value_df.columns.values[
                    (value_df > 0).sum() >= user_inputs['min_prevalence']
                ]
            )

            # Remove the genomes which do not contain any motifs
            value_df = value_df.reindex(
                index=value_df.index.values[
                    (value_df > 0).sum(axis=1) > 0
                ]
            )

            # If no motifs are left
            if value_df.shape[0] == 0:
                self.main_container.warning(
                    f"No motifs are found in >= {user_inputs['min_prevalence']} genomes"
                )
                return None, None

        # SORT THE ROWS/COLUMNS
        value_df = sort_table(value_df)

        # REALIGN TEXT TABLE TO MATCH VALUES
        text_df = text_df.reindex(
            index=value_df.index.values,
            columns=value_df.columns.values
        )

        return value_df, text_df


if __name__ == "__main__":
    w = PanEpiGenomeBrowser()
    w.run()
