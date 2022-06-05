import unittest
#! TODO import
from tests.units import test_helpers


def execute():
    suite = unittest.TestLoader().loadTestsFromModule(test_helpers)
    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__':
    execute()
