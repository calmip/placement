#! /usr/bin/env python
# -*- coding: utf-8 -*-

from utilities import *
from hardware import *
from architecture import *
from compact import *
import unittest

class TestCompactExclusive(unittest.TestCase):
    def setUp(self):
        os.environ['PLACEMENT_PARTITION'] = 'exclusive'
        self.hardware = Hardware.factory()
        self.assertEqual(self.hardware.NAME,'Bullx_dlc')

        # Architecture = 4 tâches/4 threads
        self.exclu_ok1        = Exclusive(self.hardware,4,4,False)
        self.compact_phys_ok1 = CompactPhysicalMode(self.exclu_ok1)
        self.compact_ok1      = CompactMode(self.exclu_ok1)
        # Architecture = 4 tâches/8 threads hyperthreading
        self.exclu_ok2        = Exclusive(self.hardware,8,4,True)
        self.compact_phys_ok2 = CompactPhysicalMode(self.exclu_ok2)
        self.compact_ok2      = CompactMode(self.exclu_ok2)
        # Architecture = 20 tâches/1 thread no hyperthreading
        self.exclu_ok3        = Exclusive(self.hardware,1,20,False)
        self.compact_phys_ok3 = CompactPhysicalMode(self.exclu_ok3)
        self.compact_ok3      = CompactMode(self.exclu_ok3)
        # Architecture = 20 tâches/2 threads hyperthreading
        self.exclu_ok4        = Exclusive(self.hardware,2,20,True)
        self.compact_phys_ok4 = CompactPhysicalMode(self.exclu_ok4)
        self.compact_ok4      = CompactMode(self.exclu_ok4)

        # Architecture = 4 tâches/8 threads no hyperthreading
        self.exclu_ok5        = Exclusive(self.hardware,4,8,False)
        self.compact_phys_ok5 = CompactPhysicalMode(self.exclu_ok5)
        self.compact_ok5      = CompactMode(self.exclu_ok5)

        # Architecture = 20 tâches/2 threads no hyperthreading (en fait l'hyper est forcé)
        self.exclu_ok6        = Exclusive(self.hardware,2,20,False)
        self.compact_phys_ok6 = CompactPhysicalMode(self.exclu_ok6)

        # Architecture = 21 tâches/2 threads  hyperthreading
        self.exclu_ko7   = Exclusive(self.hardware,2,21,True)

        # Si pas d'hyperthreading, autant de threads qu'on veut
        self.exclu_ok8   = Exclusive(self.hardware,1,5,False)
        self.compact_phys_ok8 = CompactPhysicalMode(self.exclu_ok8)
        self.compact_ok8      = CompactMode(self.exclu_ok8)

        self.exclu_ok9   = Exclusive(self.hardware,2,5,False)
        self.compact_phys_ok9 = CompactPhysicalMode(self.exclu_ok9)
        self.compact_ok9      = CompactMode(self.exclu_ok9)

        # Si hyperthreading activé, seulement nombre PAIR de threads !
        self.exclu_ko10 = Exclusive(self.hardware,1,5,True)

        self.exclu_ok11 = Exclusive(self.hardware,2,5,True)
        self.compact_phys_ok11 = CompactPhysicalMode(self.exclu_ok11)
        self.compact_ok11      = CompactMode(self.exclu_ok11)

        # Si une seule tache elle peut déborder du socket
        # cf. compact.py L 30-32
        self.exclu_ok12 = Exclusive(self.hardware,12,1,False)
        self.compact_phys_ok12 = CompactPhysicalMode(self.exclu_ok12)
        self.compact_ok12      = CompactMode(self.exclu_ok12)

        # Si plusieurs tâches elles peuvent être à cheval sur deux sockets
        self.exclu_ok15 = Exclusive(self.hardware,4,5,False)
        self.compact_phys_ok15 = CompactPhysicalMode(self.exclu_ok15)
        self.compact_ok15      = CompactMode(self.exclu_ok15)

        # Architecture = 4 tâches/8 threads/hyper
#        self.exclu_ok16   = Exclusive(self.hardware,4,4,False)
#        self.compact_ok16 = CompactPhysicalMode(self.exclu_ok1)

    def test_exclusive_check(self):
        ok = [self.compact_phys_ok1,self.compact_phys_ok2,self.compact_phys_ok3,self.compact_phys_ok4,self.compact_phys_ok5,self.compact_phys_ok6,self.compact_phys_ok8,self.compact_phys_ok9,self.compact_phys_ok11,self.compact_phys_ok12,self.compact_phys_ok15]
        ko = [self.exclu_ko7,self.exclu_ko10]
        i=0
        for s in ok:
            self.assertEqual(s.checkParameters(),None)
            i += 1
            #print i

        i=0
        for s in ko:
            self.assertRaises(PlacementException,CompactMode,s)

            i += 1
            #print i

    def test_exclusive_distrib(self):
        self.assertEqual(self.compact_phys_ok1.distribTasks(),[[0,1,2,3],[4,5,6,7],[8,9,10,11],[12,13,14,15]])
        self.assertEqual(self.compact_ok1.distribTasks(),     [[0,1,2,3],[4,5,6,7],[8,9,10,11],[12,13,14,15]])
        self.assertEqual(self.compact_phys_ok2.distribTasks(),[[0,1,2,3,4,5,6,7],[8,9,20,21,22,23,24,25],[26,27,28,29,10,11,12,13],[14,15,16,17,18,19,30,31]])
        self.assertEqual(self.compact_ok2.distribTasks(),     [[0,20,1,21,2,22,3,23],[4,24,5,25,6,26,7,27],[8,28,9,29,10,30,11,31],[12,32,13,33,14,34,15,35]])
        self.assertEqual(self.compact_phys_ok3.distribTasks(),[[0],[1],[2],[3],[4],[5],[6],[7],[8],[9],[10],[11],[12],[13],[14],[15],[16],[17],[18],[19]])
        self.assertEqual(self.compact_ok3.distribTasks(),     [[0],[1],[2],[3],[4],[5],[6],[7],[8],[9],[10],[11],[12],[13],[14],[15],[16],[17],[18],[19]])
        self.assertEqual(self.compact_phys_ok4.distribTasks(),[[0,1],[2,3],[4,5],[6,7],
                                                               [8,9],[20,21],[22,23],[24,25],
                                                               [26,27],[28,29],[10,11],[12,13],
                                                               [14,15],[16,17],[18,19],[30,31],
                                                               [32,33],[34,35],[36,37],[38,39]])
        self.assertEqual(self.compact_ok4.distribTasks(),      [[0,20],[1,21],[2,22],[3,23],
                                                               [4,24],[5,25],[6,26],[7,27],
                                                               [8,28],[9,29],[10,30],[11,31],
                                                               [12,32],[13,33],[14,34],[15,35],
                                                               [16,36],[17,37],[18,38],[19,39]]);
        self.assertEqual(self.compact_phys_ok6.distribTasks(),[[0,1],[2,3],[4,5],[6,7],
                                                               [8,9],[20,21],[22,23],[24,25],
                                                               [26,27],[28,29],[10,11],[12,13],
                                                               [14,15],[16,17],[18,19],[30,31],
                                                               [32,33],[34,35],[36,37],[38,39]])
        self.assertEqual(self.compact_phys_ok8.distribTasks(),[[0],[1],[2],[3],[4]])
        self.assertEqual(self.compact_ok8.distribTasks(),     [[0],[1],[2],[3],[4]])
        self.assertEqual(self.compact_phys_ok9.distribTasks(),[[0,1],[2,3],[4,5],[6,7],[8,9]])
        self.assertEqual(self.compact_ok9.distribTasks(),     [[0,1],[2,3],[4,5],[6,7],[8,9]])
        self.assertEqual(self.compact_phys_ok11.distribTasks(),[[0,1],[2,3],[4,5],[6,7],[8,9]])
        self.assertEqual(self.compact_ok11.distribTasks(),     [[0,20],[1,21],[2,22],[3,23],[4,24]])
        self.assertEqual(self.compact_phys_ok12.distribTasks(),[[0,1,2,3,4,5,6,7,8,9,10,11]])
        self.assertEqual(self.compact_ok12.distribTasks(),     [[0,1,2,3,4,5,6,7,8,9,10,11]])
        self.assertEqual(self.compact_phys_ok15.distribTasks(),[[0,1,2,3],[4,5,6,7],[8,9,10,11],[12,13,14,15],[16,17,18,19]])
        self.assertEqual(self.compact_ok15.distribTasks(),     [[0,1,2,3],[4,5,6,7],[8,9,10,11],[12,13,14,15],[16,17,18,19]])
        

if __name__ == '__main__':
    unittest.main()
