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
import os
import unittest

# Testing PLACEMENT_ARCHI
class TestHardwareConf1(unittest.TestCase):
    def setUp(self):
        os.environ['PLACEMENT_CONF'] = 'test1.conf'
        os.environ.pop('HOSTNAME',0)

    def test_archi_ok(self):
        os.environ['PLACEMENT_ARCHI']= 'hard1'
        self.assertEqual(Hardware.factory().NAME,'hard1')
 
    def test_archi_ko(self):
        os.environ['PLACEMENT_ARCHI']= 'toto'
        self.assertRaises(PlacementException,Hardware.factory)

# Testing HOSTNAME
class TestHardwareConf3(unittest.TestCase):
    def setUp(self):
        os.environ['PLACEMENT_CONF'] = 'test3.conf'
        os.environ.pop('PLACEMENT_ARCHI',0)

    def test_archi_ok(self):
        os.environ['HOSTNAME']= 'node45'
        self.assertEqual(Hardware.factory().NAME,'hard3')
 
    def test_archi_ko(self):
        os.environ['HOSTNALE']= 'toto'
        self.assertRaises(PlacementException,Hardware.factory)

# Testing without any configuration
class TestHardwareNoConf(unittest.TestCase):
    def setUp(self):
        os.environ.pop('PLACEMENT_ARCHI',0)
        os.environ['PLACEMENT_CONF'] = 'file_does_not_exist'
        os.environ['SLURM_CONF'] = 'file_does_not_exist'
    
    def test_archi_ko(self):
        self.assertRaises(PlacementException,Hardware.factory)
                           
#@unittest.skip("it works, not tested")
class TestHardwareBullDlc(unittest.TestCase):
    def setUp(self):
        os.environ['PLACEMENT_CONF'] = 'test3.conf'
        os.environ['PLACEMENT_ARCHI'] = 'hard1'
        self.hardware = Hardware.factory()

    def test_getCore2Socket(self):
        self.assertEqual(self.hardware.getCore2Socket(0),0)
        self.assertEqual(self.hardware.getCore2Socket(6),0)
        self.assertEqual(self.hardware.getCore2Socket(9),0)
        self.assertEqual(self.hardware.getCore2Socket(10),1)
        self.assertEqual(self.hardware.getCore2Socket(16),1)
        self.assertEqual(self.hardware.getCore2Socket(19),1)
        self.assertEqual(self.hardware.getCore2Socket(20),0)
        self.assertEqual(self.hardware.getCore2Socket(26),0)
        self.assertEqual(self.hardware.getCore2Socket(29),0)
        self.assertEqual(self.hardware.getCore2Socket(30),1)
        self.assertEqual(self.hardware.getCore2Socket(36),1)
        self.assertEqual(self.hardware.getCore2Socket(39),1)

    def test_getCore2Core(self):
        self.assertEqual(self.hardware.getCore2Core(0),0)
        self.assertEqual(self.hardware.getCore2Core(6),6)
        self.assertEqual(self.hardware.getCore2Core(9),9)
        self.assertEqual(self.hardware.getCore2Core(10),0)
        self.assertEqual(self.hardware.getCore2Core(16),6)
        self.assertEqual(self.hardware.getCore2Core(19),9)
        self.assertEqual(self.hardware.getCore2Core(20),0)
        self.assertEqual(self.hardware.getCore2Core(26),6)
        self.assertEqual(self.hardware.getCore2Core(29),9)
        self.assertEqual(self.hardware.getCore2Core(30),0)
        self.assertEqual(self.hardware.getCore2Core(36),6)
        self.assertEqual(self.hardware.getCore2Core(39),9)

    def test_getCore2PhysCore(self):
        self.assertEqual(self.hardware.getCore2PhysCore(0),0)
        self.assertEqual(self.hardware.getCore2PhysCore(6),6)
        self.assertEqual(self.hardware.getCore2PhysCore(9),9)
        self.assertEqual(self.hardware.getCore2PhysCore(10),10)
        self.assertEqual(self.hardware.getCore2PhysCore(16),16)
        self.assertEqual(self.hardware.getCore2PhysCore(19),19)
        self.assertEqual(self.hardware.getCore2PhysCore(20),0)
        self.assertEqual(self.hardware.getCore2PhysCore(26),6)
        self.assertEqual(self.hardware.getCore2PhysCore(29),9)
        self.assertEqual(self.hardware.getCore2PhysCore(30),10)
        self.assertEqual(self.hardware.getCore2PhysCore(36),16)
        self.assertEqual(self.hardware.getCore2PhysCore(39),19)

    def test_isHyperThreadingUsed(self):
        self.assertEqual(self.hardware.isHyperThreadingUsed([0,1,2,20,21,22]),True)
        self.assertEqual(self.hardware.isHyperThreadingUsed([0,1,2,23,24,25]),False)


# bien qu'on teste ici une architecture Shared, on considère qu'elle est Exclusive
class TestHardwareMesca2(unittest.TestCase):
    def setUp(self):
        os.environ['PLACEMENT_CONF'] = 'test3.conf'
        os.environ['PLACEMENT_ARCHI'] = 'hard4'
        self.hardware = Hardware.factory()

#    @unittest.skip("it works, not tested")
    def test_getCore2Socket(self):
        self.assertEqual(self.hardware.getCore2Socket(0),0)
        self.assertEqual(self.hardware.getCore2Socket(5),0)
        self.assertEqual(self.hardware.getCore2Socket(15),0)
        self.assertEqual(self.hardware.getCore2Socket(16),1)
        self.assertEqual(self.hardware.getCore2Socket(20),1)
        self.assertEqual(self.hardware.getCore2Socket(31),1)
        self.assertEqual(self.hardware.getCore2Socket(32),2)
        self.assertEqual(self.hardware.getCore2Socket(34),2)
        self.assertEqual(self.hardware.getCore2Socket(47),2)
        self.assertEqual(self.hardware.getCore2Socket(48),3)
        self.assertEqual(self.hardware.getCore2Socket(52),3)
        self.assertEqual(self.hardware.getCore2Socket(63),3)
        self.assertEqual(self.hardware.getCore2Socket(64),4)
        self.assertEqual(self.hardware.getCore2Socket(66),4)
        self.assertEqual(self.hardware.getCore2Socket(79),4)
        self.assertEqual(self.hardware.getCore2Socket(80),5)
        self.assertEqual(self.hardware.getCore2Socket(86),5)
        self.assertEqual(self.hardware.getCore2Socket(95),5)
        self.assertEqual(self.hardware.getCore2Socket(96),6)
        self.assertEqual(self.hardware.getCore2Socket(100),6)
        self.assertEqual(self.hardware.getCore2Socket(111),6)
        self.assertEqual(self.hardware.getCore2Socket(112),7)
        self.assertEqual(self.hardware.getCore2Socket(118),7)
        self.assertEqual(self.hardware.getCore2Socket(127),7)

#    @unittest.skip("it works, not tested")
    def test_getCore2Core(self):
        self.assertEqual(self.hardware.getCore2Core(0),0)
        self.assertEqual(self.hardware.getCore2Core(5),5)
        self.assertEqual(self.hardware.getCore2Core(15),15)
        self.assertEqual(self.hardware.getCore2Core(16),0)
        self.assertEqual(self.hardware.getCore2Core(20),4)
        self.assertEqual(self.hardware.getCore2Core(31),15)
        self.assertEqual(self.hardware.getCore2Core(32),0)
        self.assertEqual(self.hardware.getCore2Core(34),2)
        self.assertEqual(self.hardware.getCore2Core(47),15)
        self.assertEqual(self.hardware.getCore2Core(48),0)
        self.assertEqual(self.hardware.getCore2Core(52),4)
        self.assertEqual(self.hardware.getCore2Core(63),15)
        self.assertEqual(self.hardware.getCore2Core(64),0)
        self.assertEqual(self.hardware.getCore2Core(66),2)
        self.assertEqual(self.hardware.getCore2Core(79),15)
        self.assertEqual(self.hardware.getCore2Core(80),0)
        self.assertEqual(self.hardware.getCore2Core(86),6)
        self.assertEqual(self.hardware.getCore2Core(95),15)
        self.assertEqual(self.hardware.getCore2Core(96),0)
        self.assertEqual(self.hardware.getCore2Core(100),4)
        self.assertEqual(self.hardware.getCore2Core(111),15)
        self.assertEqual(self.hardware.getCore2Core(112),0)
        self.assertEqual(self.hardware.getCore2Core(118),6)
        self.assertEqual(self.hardware.getCore2Core(127),15)

#    @unittest.skip("it works, not tested")
    def test_getCore2PhysCore(self):
        self.assertEqual(self.hardware.getCore2PhysCore(0),0)
        self.assertEqual(self.hardware.getCore2PhysCore(5),5)
        self.assertEqual(self.hardware.getCore2PhysCore(15),15)
        self.assertEqual(self.hardware.getCore2PhysCore(16),16)
        self.assertEqual(self.hardware.getCore2PhysCore(20),20)
        self.assertEqual(self.hardware.getCore2PhysCore(31),31)
        self.assertEqual(self.hardware.getCore2PhysCore(32),32)
        self.assertEqual(self.hardware.getCore2PhysCore(34),34)
        self.assertEqual(self.hardware.getCore2PhysCore(47),47)
        self.assertEqual(self.hardware.getCore2PhysCore(48),48)
        self.assertEqual(self.hardware.getCore2PhysCore(52),52)
        self.assertEqual(self.hardware.getCore2PhysCore(63),63)
        self.assertEqual(self.hardware.getCore2PhysCore(64),64)
        self.assertEqual(self.hardware.getCore2PhysCore(66),66)
        self.assertEqual(self.hardware.getCore2PhysCore(79),79)
        self.assertEqual(self.hardware.getCore2PhysCore(80),80)
        self.assertEqual(self.hardware.getCore2PhysCore(86),86)
        self.assertEqual(self.hardware.getCore2PhysCore(95),95)
        self.assertEqual(self.hardware.getCore2PhysCore(96),96)
        self.assertEqual(self.hardware.getCore2PhysCore(100),100)
        self.assertEqual(self.hardware.getCore2PhysCore(111),111)
        self.assertEqual(self.hardware.getCore2PhysCore(112),112)
        self.assertEqual(self.hardware.getCore2PhysCore(118),118)
        self.assertEqual(self.hardware.getCore2PhysCore(127),127)
        
if __name__ == '__main__':
    unittest.main()
