from typing import Any
import widgets.streamlit as wist
from widgets.streamlit import StResource
from widgets.base.exceptions import WidgetFunctionException
from living_figures.bio.fom.widgets.microbiome.base_widget import BaseMicrobiomeExplorer # noqa


class MicrobiomePlot(wist.StResource):
    """Base class with helper functions used for microbiome plots."""

    def _root(self) -> BaseMicrobiomeExplorer:
        return super()._root()

    def option(self, id) -> StResource:
        for r in self._find_child(id):
            return r
        raise WidgetFunctionException(f"Cannot find option {id}")

    def val(self, id) -> Any:
        return self.option(id).get_value()

    def update_options(self, options, id):
        """Update the set of options for user-provided metadata."""

        # Get the resource by ID
        resource = self.option(id)

        # Remove any values which are not in the new options
        value = resource.get_value()
        if isinstance(value, list):
            value = [i for i in value if i in options]
        else:
            value = value if value in options else None
        if value != resource.get_value():
            resource.set(value=value, update=False)

        # If the options do not already match
        if resource.get_attr("options") != options:

            # Set the options
            resource.set(
                attr="options",
                value=options,
                # Only update the front-end if the element is being shown
                update=self.main_container is not None
            )

        # Regenerate the plot
        if self.main_container is not None:
            self.run_self()

    def _get_child(self, child_id, *cont) -> 'StResource':
        return super()._get_child(child_id, *cont)
