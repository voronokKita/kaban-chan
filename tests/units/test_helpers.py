import unittest

from kaban import helpers


class TestSum(unittest.TestCase):
    def setUp(self):
        self.sum = helpers.sum  # makeSomethingDB

    def tearDown(self):
        self.sum = None  # deleteSomethingDB

    def test_list_int(self):
        data = [5, 5, 5]
        result = self.sum(data)
        self.assertEqual(result, 15)

    def test_list_float(self):
        data = [5.5, 5.5, 5.5]
        result = self.sum(data)
        self.assertEqual(result, 16.5)


if __name__ == '__main__':
    unittest.main()
