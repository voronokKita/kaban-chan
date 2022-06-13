import sys
import pathlib
import unittest

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
if BASE_DIR not in sys.path:
    sys.path.append(str(BASE_DIR))

from tests.units import test_helpers, test_webhook, test_updater


def execute():
    # suite = unittest.TestLoader().loadTestsFromModule(test_helpers)
    # suite = unittest.TestLoader().loadTestsFromModule(test_webhook)
    suite = unittest.TestLoader().loadTestsFromModule(test_updater)
    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__':
    execute()
