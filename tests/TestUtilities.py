#! /usr/bin/env python
# -*- coding: utf-8 -*-

#
# This file is part of PLACEMENT software
# PLACEMENT helps users to bind their processes to one or more cpu cores
#
# Copyright (C) 2015-2018 Emmanuel Courcelle
# PLACEMENT is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
#  PLACEMENT is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with PLACEMENT.  If not, see <http://www.gnu.org/licenses/>.
#
#  Authors:
#        Emmanuel Courcelle - C.N.R.S. - UMS 3667 - CALMIP
#        Nicolas Renon - Université Paul Sabatier - University of Toulouse)
#

from utilities import *
import unittest
import os

class TestNumTaskToLetter(unittest.TestCase):

#    def setUp(self):
#        self.seq = range(10)

    def test_normal(self):
        self.assertEqual(numTaskToLetter(0),'A')
        self.assertEqual(numTaskToLetter(25),'Z')
        self.assertEqual(numTaskToLetter(26),'a')
        self.assertEqual(numTaskToLetter(51),'z')
        self.assertEqual(numTaskToLetter(52),chr(200))
        self.assertEqual(numTaskToLetter(295),chr(443))

    def test_out_of_limits(self):
        self.assertRaises(PlacementException, numTaskToLetter, -1)
        self.assertRaises(PlacementException, numTaskToLetter, 296)


class TestList2CompactString(unittest.TestCase):
    def setUp(self):
        self.s1 = [0,1,2,5,6,7,9]
        self.s11= [6,5,0,1,9,7,2]
        self.s2 = []
        self.s3 = [0]
        self.s4 = [1,1,9]

    def test_normal(self):
        self.assertEqual(list2CompactString(self.s1),'0-2,5-7,9')
        self.assertEqual(list2CompactString(self.s11),'0-2,5-7,9')

        # s11 a été trié par l'appel précédent
#        self.assertEqual(self.s1,self.s11)

    def test_limits(self):
        self.assertEqual(list2CompactString(self.s2),'')
        self.assertEqual(list2CompactString(self.s3),'0')
        self.assertEqual(list2CompactString(self.s4),'1,9')
        

class TestCompactString2List(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(compactString2List('0-3,5'),[0,1,2,3,5])
        self.assertEqual(compactString2List('5,2,0,1'),[5,2,0,1])
        self.assertEqual(compactString2List('8-12'),[8,9,10,11,12])
        self.assertEqual(compactString2List('8-12,98-102'),[8,9,10,11,12,98,99,100,101,102])

    def test_limits(self):
        self.assertEqual(compactString2List(''),[])
        self.assertEqual(compactString2List('1'),[1])
        self.assertEqual(compactString2List('3-1'),[1,2,3])
        self.assertEqual(compactString2List('12-8'),[8,9,10,11,12])
        self.assertRaises(ValueError,compactString2List,'a-c')

class TestExpandNodeList(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(expandNodeList('eoscomp[1-3]'),['eoscomp1','eoscomp2','eoscomp3'])
        self.assertEqual(expandNodeList('eoscomp[1]'),['eoscomp1'])
        self.assertEqual(expandNodeList('eoscomp[1-2,4]'),['eoscomp1','eoscomp2','eoscomp4'])
        self.assertEqual(expandNodeList('eoscomp[1,2]'),['eoscomp1','eoscomp2'])
        self.assertEqual(expandNodeList('toto[08-10]'),['toto08','toto09','toto10'])

    def test_limits(self):
        self.assertEqual(expandNodeList('eosmesca1'),['eosmesca1'])

class TestConvertMemory(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(convertMemory('200 KiB'),204800)
        self.assertEqual(convertMemory('200 MiB'),209715200)
        self.assertEqual(convertMemory('200 GiB'),214748364800)

    def test_bad(self):
        self.assertRaises(PlacementException, convertMemory, '200 TiB')
        self.assertRaises(PlacementException, convertMemory, '200')
        self.assertRaises(PlacementException, convertMemory, 200)

class TestNum2Slice(unittest.TestCase):
    '''OBSOLETE - NOT USED ANY MORE'''
    def test_normal(self):
        self.assertEqual(mem2Slice(5.0,1.0),5)
        self.assertEqual(mem2Slice(4.9,1.0),5)
        self.assertEqual(mem2Slice(4.5,1.0),5)
        self.assertEqual(mem2Slice(4.499,1.0),4)
        self.assertEqual(mem2Slice(0.9,1.0),1)
        self.assertEqual(mem2Slice(0.45,1.0),0)
        
    def test_limits(self):
        self.assertEqual(mem2Slice(5.0,0),0)

class TestgetGauge(unittest.TestCase):
    def test_gauge(self):
        self.assertEqual(getGauge(-1,10,False,True),'..........')
        self.assertEqual(getGauge(0,10,False),'..........')
        self.assertEqual(getGauge(4,10,False),'..........')
        self.assertEqual(getGauge(5,10,False),'*.........')
        self.assertEqual(getGauge(10,10,False),'*.........')
        self.assertEqual(getGauge(12,10,False),'*.........')
        self.assertEqual(getGauge(15,10,False),'**........')
        self.assertEqual(getGauge(100,10,False),'**********')
        self.assertEqual(getGauge(101,10,False,True),'**********')
        self.assertEqual(getGauge(50,8,False),'****....')
        self.assertEqual(getGauge(50,8,False),'****....')
        self.assertEqual(getGauge(33,8,False),'***.....')
        self.assertEqual(getGauge(66,8,False),'*****...')

    def test_gauge_outofbounds(self):
        self.assertRaises(ValueError,getGauge,-1,8,False)
        self.assertRaises(ValueError,getGauge,101,8,False)

class TestgetHostname(unittest.TestCase):
    def test_normal(self):
         self.assertEqual(getHostname(),runCmd(['hostname','-s']).rstrip())
 
class TestAnsiCodes(unittest.TestCase):
	def test_map(self):
		self.assertNotEqual(AnsiCodes.map(1),AnsiCodes.map(2))
		self.assertNotEqual(AnsiCodes.map(1),AnsiCodes.map(11))
		self.assertNotEqual(AnsiCodes.map(1),AnsiCodes.map(21))
		self.assertNotEqual(AnsiCodes.map(1),AnsiCodes.map(31))
		self.assertEqual(AnsiCodes.map(1),AnsiCodes.map(33))
		         
if __name__ == '__main__':
    unittest.main()
