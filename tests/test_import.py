from living_figures.bio.volcano.app import Volcano # noqa
from living_figures.bio.epigenome.widgets import PanEpiGenomeBrowser # noqa
import unittest


class TestInit(unittest.TestCase):

    def test_init_volcano(self):

        try:
            Volcano()
        except Exception as e:
            self.fail(f"Could not initialize Volcano ({str(e)})")

    def test_init_panepi(self):

        try:
            PanEpiGenomeBrowser()
        except Exception as e:
            self.fail(f"Could not initialize PanEpiGenomeBrowser({str(e)})")
