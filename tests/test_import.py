from widget_store.bio.volcano.app import Volcano # noqa
import unittest


class TestInit(unittest.TestCase):

    def test_init_volcano(self):

        try:
            Volcano()
        except Exception as e:
            self.fail(f"Could not initialize Volcano ({str(e)})")
