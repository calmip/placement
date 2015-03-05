#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Tests unitaires pour placement
import placement
import unittest

class TestnumTaskToLetter(unittest.TestCase):
    def test_exc(self):
        self.assertRaises(placement.PlacementException,placement.numTaskToLetter,62)
        self.assertRaises(placement.PlacementException,placement.numTaskToLetter,-1)

    def test_26(self):
        # test for n=0..25
        self.assertEqual(placement.numTaskToLetter(4),'E')
        self.assertEqual(placement.numTaskToLetter(0),'A')
        self.assertEqual(placement.numTaskToLetter(25),'Z')

    def test_52(self):
        # test for n=26..51
        self.assertEqual(placement.numTaskToLetter(31),'f')
        self.assertEqual(placement.numTaskToLetter(26),'a')
        self.assertEqual(placement.numTaskToLetter(51),'z')

    def test_62(self):
        # test for n=52..61
        self.assertEqual(placement.numTaskToLetter(55),'3')
        self.assertEqual(placement.numTaskToLetter(52),'0')
        self.assertEqual(placement.numTaskToLetter(61),'9')

class TestgetCompactString(unittest.TestCase):
    def test_limits(self):
        self.assertEqual(placement.getCompactString([]),"")
        self.assertEqual(placement.getCompactString([2]),"2")
        self.assertEqual(placement.getCompactString([0,1,2,3]),"0-3")
        self.assertEqual(placement.getCompactString([1,3,5,7]),"1,3,5,7")

    def test_unsorted(self):
        A=[4,2,0,1,3,5,9]
        self.assertEqual(placement.getCompactString(A),"0-5,9")
        # A est triée à la fin
        self.assertEqual(A,[0,1,2,3,4,5,9])

    def test_general(self):
        self.assertEqual(placement.getCompactString([0,1,2,3,7,10,11,12,13]),"0-3,7,10-13")

if __name__ == '__main__':
    suite1 = unittest.TestLoader().loadTestsFromTestCase(TestnumTaskToLetter)
    suite2 = unittest.TestLoader().loadTestsFromTestCase(TestgetCompactString)
    alltests = unittest.TestSuite([suite1, suite2])
    unittest.TextTestRunner(verbosity=2).run(alltests)

