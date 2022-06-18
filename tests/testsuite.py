import pathlib
import signal
import sys
import unittest

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from kaban.helpers import exit_signal
from tests.units import test_helpers, test_bot_processor, test_receiver, test_updater, test_webhook
from tests.integration import integration


def execute():
    # big_suite = unittest.TestLoader().loadTestsFromModule(test_helpers)
    # big_suite = unittest.TestLoader().loadTestsFromModule(test_webhook)
    # big_suite = unittest.TestLoader().loadTestsFromModule(test_updater)
    # big_suite = unittest.TestLoader().loadTestsFromModule(test_receiver)
    # big_suite = unittest.TestLoader().loadTestsFromModule(test_bot_processor)
    # big_suite = unittest.TestLoader().loadTestsFromModule(integration)

    test_modules = [test_helpers, test_bot_processor,
                    test_receiver, test_updater, test_webhook]

    suite_list = []
    loader = unittest.TestLoader()
    for module in test_modules:
        suite = loader.loadTestsFromModule(module)
        suite_list.append(suite)
    else:
        big_suite = unittest.TestSuite(suite_list)

    unittest.TextTestRunner(verbosity=2).run(big_suite)
    unittest.TextTestRunner(verbosity=2).run(
        unittest.TestLoader().loadTestsFromModule(integration)
    )


if __name__ == '__main__':
    signal.signal(signal.SIGINT, exit_signal)
    signal.signal(signal.SIGTSTP, exit_signal)
    execute()
