#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Tests unitaires pour placement
import placement
import running
import unittest

class TestnumTaskToLetter(unittest.TestCase):
    def test_exc(self):
        self.assertRaises(placement.PlacementException,placement.numTaskToLetter,67)
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

class Testlist2CompactString(unittest.TestCase):
    def test_limits(self):
        self.assertEqual(placement.list2CompactString([]),"")
        self.assertEqual(placement.list2CompactString([2]),"2")
        self.assertEqual(placement.list2CompactString([0,1,2,3]),"0-3")
        self.assertEqual(placement.list2CompactString([1,3,5,7]),"1,3,5,7")

    def test_unsorted(self):
        A=[4,2,0,1,3,5,9]
        self.assertEqual(placement.list2CompactString(A),"0-5,9")
        # A est inchangée (nouveau comportement)
        self.assertEqual(A,[4,2,0,1,3,5,9])

    def test_general(self):
        self.assertEqual(placement.list2CompactString([0,1,2,3,7,10,11,12,13]),"0-3,7,10-13")

class TestcompactString2List(unittest.TestCase):
    def test_limits(self):
        self.assertEqual(placement.compactString2List(""),[])
        self.assertEqual(placement.compactString2List("2"),[2])
        self.assertEqual(placement.compactString2List("3-7"),[3,4,5,6,7])
        self.assertEqual(placement.compactString2List("0,1,2,5"),[0,1,2,5])

    def test_general(self):
        self.assertEqual(placement.compactString2List("0-3,4-8,10-12"),[0,1,2,3,4,5,6,7,8,10,11,12])

class TestdetectOverlap(unittest.TestCase):
    def test_limits(self):
        (overlap,overcores) = running._detectOverlap([[0,1,2,3],[0,1,2,3],[0,1,2,3]])
        self.assertEqual(overlap,[('A','B'),('A','C'),('B','C')])
        self.assertEqual(overcores,[0,1,2,3])

        (overlap,overcores) = running._detectOverlap([[0,1,2,3],[4,5,6,7],[8,9,10,11]])
        self.assertEqual(overlap,[])
        self.assertEqual(overcores,[])

        (overlap,overcores) = running._detectOverlap([[],[],[]])
        self.assertEqual(overlap,[])
        self.assertEqual(overcores,[])

        (overlap,overcores) = running._detectOverlap([])
        self.assertEqual(overlap,[])
        self.assertEqual(overcores,[])
        
        (overlap,overcores) = running._detectOverlap([[4],[5],[6]])
        self.assertEqual(overlap,[])
        self.assertEqual(overcores,[])

        (overlap,overcores) = running._detectOverlap([[1],[1],[2]])
        self.assertEqual(overlap,[('A','B')])
        self.assertEqual(overcores,[1])

    def test_general(self):
        (overlap,overcores) = running._detectOverlap([[0,1,2,3],[0,4,5,6],[10,11,12,13],[20,21,22,4]])
        self.assertEqual(overlap,[('A','B'),('B','D')])
        self.assertEqual(overcores,[0,4])
        
if __name__ == '__main__':
    suite1 = unittest.TestLoader().loadTestsFromTestCase(TestnumTaskToLetter)
    suite2 = unittest.TestLoader().loadTestsFromTestCase(Testlist2CompactString)
    suite3 = unittest.TestLoader().loadTestsFromTestCase(TestcompactString2List)
    suite4 = unittest.TestLoader().loadTestsFromTestCase(TestdetectOverlap)
    alltests = unittest.TestSuite([suite1, suite2, suite3, suite4])
    unittest.TextTestRunner(verbosity=2).run(alltests)

