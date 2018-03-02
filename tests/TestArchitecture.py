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
from hardware import *
from architecture import *
from scatter import *
import unittest

# Testing Mesca2, the cpuset is simulated in PLACEMENT_PHYSCPU
#                 The archi.l_sockets and archi.m_cores arrays should be set accordingly !
# 
#@unittest.skip("it works, not tested")
class TestShared1(unittest.TestCase):
    def setUp(self):
        try:
            del os.environ['PLACEMENT_PARTITION']
        except Exception:
            pass
        os.environ['HOSTNAME']          = 'bigmemory1'
        os.environ['PLACEMENT_NODE']    = '0,1'
        os.environ['PLACEMENT_PHYSCPU'] = '0,1,2,3,4,5,6,7,16,17,18,19,20,21,22,23'
        self.hardware = Hardware.factory()

    def test_shared(self):
        self.maxDiff=None
        sock  = [0,1]
        
        # init cores
        cores = {}
        core0 = {}
        core1 = {}
        for c in range(8):
            core0[c] = True
        for c in range(8,16):
            core0[c] = False
        for c in range(16,24):
            core1[c] = True
        for c in range(24,32):
            core1[c] = False

        cores[0] = core0
        cores[1] = core1

#        cores = {0:{0:True,1:True,2:True,3:True,4:True,5:True,6:True,7:True},
#                 1:{16:True,17:True,18:True,19:True,20:True,21:True,22:True,23:True}}
        archi = Shared(self.hardware,8,4,False,2)

        self.assertEqual(self.hardware.NAME,'Mesca2')
        self.assertEqual(archi.l_sockets,sock)
        self.assertEqual(archi.m_cores[0],cores[0])
        self.assertEqual(archi.m_cores[1],cores[1])

# Testing that an exception is raised if PLACEMENT_NODE is defined and NOT PLACEMENT_PHYSCPU
# 
#@unittest.skip("it works, not tested")
class TestShared2(unittest.TestCase):
    def setUp(self):
        os.environ['HOSTNAME   ']    = 'bigmemory1'
        os.environ['PLACEMENT_NODE'] = '0,1'
        del os.environ['PLACEMENT_PHYSCPU']
        self.hardware = Hardware.factory()

    def test_shared(self):
        #sock  = [0,1]
        #cores = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19]
        #archi = Shared(self.hardware,8,4,False,2)
        self.assertEqual(self.hardware.NAME,'Mesca2')
        self.assertRaises(PlacementException,Shared,self.hardware,8,4,False,2)
        
# Testing Mesca2, the cpuset is simulated in PLACEMENT_PHYSCPU
#                 The archi.l_sockets and archi.m_cores arrays should be set accordingly !
# 
#@unittest.skip("it works, not tested")
class TestShared3(unittest.TestCase):
    def setUp(self):
        os.environ['HOSTNAME']          = 'bigmemory1'
        os.environ['PLACEMENT_NODE']    = '2,3'
        os.environ['PLACEMENT_PHYSCPU'] = '32,33,34,35,36,37,38,39,48,49,50,51,52,53,54,55'
        self.hardware = Hardware.factory()

    def test_shared(self):
        self.maxDiff=None
        sock  = [2,3]
        
        # init cores
        cores = {}
        core0 = {}
        core1 = {}
        for c in range(32,40):
            core0[c] = True
        for c in range(40,48):
            core0[c] = False
        for c in range(48,56):
            core1[c] = True
        for c in range(56,64):
            core1[c] = False

        cores[2] = core0
        cores[3] = core1

        archi = Shared(self.hardware,8,4,False,2)
        self.assertEqual(archi.l_sockets,sock)
        self.assertEqual(archi.m_cores,cores)

if __name__ == '__main__':
    unittest.main()
