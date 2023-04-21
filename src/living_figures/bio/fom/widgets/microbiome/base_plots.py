from typing import Any
import widgets.streamlit as wist
from widgets.streamlit import StResource
from widgets.base.exceptions import WidgetFunctionException
import streamlit as st


class MicrobiomePlot(wist.StResource):
    """Base class with helper functions used for microbiome plots."""

    def option(self, id) -> StResource:
        for r in self._find_child(id):
            return r
        raise WidgetFunctionException(f"Cannot find option {id}")

    def val(self, id) -> Any:
        return self.val(id)

    def update_options(self, options, id):
        """Update the set of options for user-provided metadata."""

        # Get the resource by ID
        resource = self.option(id)

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

    def setup_cache(self) -> None:
        if st.session_state.get(f"{self.id}_cache") is None:
            st.session_state[f"{self.id}_cache"] = {}

    def set_cache(self, cache_key, value) -> None:
        self.setup_cache()
        st.session_state[f"{self.id}_cache"][cache_key] = value

    def get_cache(self, cache_key):
        self.setup_cache()
        return st.session_state[f"{self.id}_cache"].get(cache_key)

    def _get_child(self, child_id, *cont) -> 'StResource':
        return super()._get_child(child_id, *cont)
