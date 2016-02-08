#! /usr/bin/env python
# -*- coding: utf-8 -*-

from utilities import *
from hardware import *
from architecture import *
from compact import *
import unittest

class TestCompactExclusive(unittest.TestCase):
    def setUp(self):
        self.hardware = Bullx_dlc()

        # Architecture = 4 tâches/4 threads
        self.exclu_ok1   = Exclusive(self.hardware,2,4,4,False)
        self.compact_ok1 = CompactMode(self.exclu_ok1,4,4)
        # Architecture = 4 tâches/8 threads hyperthreading
        self.exclu_ok2   = Exclusive(self.hardware,2,8,4,True)
        self.compact_ok2 = CompactMode(self.exclu_ok2,8,4)
        # Architecture = 20 tâches/1 thread no hyperthreading
        self.exclu_ok3   = Exclusive(self.hardware,2,1,20,False)
        self.compact_ok3 = CompactMode(self.exclu_ok3,1,20)
        # Architecture = 20 tâches/2 threads hyperthreading
        self.exclu_ok4   = Exclusive(self.hardware,2,2,20,True)
        self.compact_ok4 = CompactMode(self.exclu_ok4,2,20)

        # Architecture = 4 tâches/8 threads no hyperthreading
        self.exclu_ok5   = Exclusive(self.hardware,2,4,8,False)
        self.compact_ok5 = CompactMode(self.exclu_ok5,4,8)

        # Architecture = 20 tâches/2 threads no hyperthreading (en fait l'hyper est forcé)
        self.exclu_ok6   = Exclusive(self.hardware,2,2,20,False)
        self.compact_ok6 = CompactMode(self.exclu_ok6,2,20)

        # Architecture = 21 tâches/2 threads  hyperthreading
        self.exclu_ko7   = Exclusive(self.hardware,2,2,21,True)
        self.compact_ko7 = CompactMode(self.exclu_ko7,2,21)

        # Si pas d'hyperthreading, autant de threads qu'on veut
        self.exclu_ok8   = Exclusive(self.hardware,2,1,5,False)
        self.compact_ok8 = CompactMode(self.exclu_ok8,1,5)

        self.exclu_ok9   = Exclusive(self.hardware,2,2,5,False)
        self.compact_ok9 = CompactMode(self.exclu_ok9,2,5)

        # Si hyperthreading activé, seulement nombre PAIR de threads !
        self.exclu_ko10 = Exclusive(self.hardware,2,1,5,True)
        self.compact_ko10 = CompactMode(self.exclu_ko10,1,5)
        self.exclu_ok11 = Exclusive(self.hardware,2,2,5,True)
        self.compact_ok11 = CompactMode(self.exclu_ok11,2,5)

        # Si une seule tache elle peut déborder du socket
        # cf. compact.py L 30-32
        self.exclu_ok12 = Exclusive(self.hardware,2,12,1,False)
        self.compact_ok12 = CompactMode(self.exclu_ok12,12,1)
        #self.exclu_ok13 = Exclusive(self.hardware,2,22,1,True)
        #self.compact_ok13 = CompactMode(self.exclu_ok13,22,1)
        #self.compact_ko14 = CompactMode(self.exclu_ko14,12,2)

        # Si plusieurs tâches non, elles ne peuvent pas
        #self.exclu_ko14 = Exclusive(self.hardware,2,12,2,True)

        # Si plusieurs tâches elles ne doivent pas être à cheval sur deux sockets
        self.exclu_ok15 = Exclusive(self.hardware,2,4,5,False)
        self.compact_ok15 = CompactMode(self.exclu_ok15,4,5)

    def test_exclusive_check(self):
        ok = [self.compact_ok1,self.compact_ok2,self.compact_ok3,self.compact_ok4,self.compact_ok5,self.compact_ok6,self.compact_ok8,self.compact_ok9,self.compact_ok11,self.compact_ok12,self.compact_ok15]
        ko = [self.compact_ko7,self.compact_ko10]
        i=0
        for s in ok:
            self.assertEqual(s.checkParameters(),None)
            i += 1
            #print i

        i=0
        for s in ko:
            self.assertRaises(PlacementException,s.checkParameters)
            i += 1
            #print i

    def test_exclusive_distrib(self):
        self.assertEqual(self.compact_ok1.distribTasks(),[[0,1,2,3],[4,5,6,7],[8,9,10,11],[12,13,14,15]])
        self.assertEqual(self.compact_ok2.distribTasks(),[[0,1,2,3,4,5,6,7],[8,9,20,21,22,23,24,25],[26,27,28,29,10,11,12,13],[14,15,16,17,18,19,30,31]])
        self.assertEqual(self.compact_ok3.distribTasks(),[[0],[1],[2],[3],[4],[5],[6],[7],[8],[9],[10],[11],[12],[13],[14],[15],[16],[17],[18],[19]])
        self.assertEqual(self.compact_ok4.distribTasks(),[[0,1],[2,3],[4,5],[6,7],
                                                          [8,9],[20,21],[22,23],[24,25],
                                                          [26,27],[28,29],[10,11],[12,13],
                                                          [14,15],[16,17],[18,19],[30,31],
                                                          [32,33],[34,35],[36,37],[38,39]])
        self.assertEqual(self.compact_ok6.distribTasks(),[[0,1],[2,3],[4,5],[6,7],
                                                          [8,9],[20,21],[22,23],[24,25],
                                                          [26,27],[28,29],[10,11],[12,13],
                                                          [14,15],[16,17],[18,19],[30,31],
                                                          [32,33],[34,35],[36,37],[38,39]])
        self.assertEqual(self.compact_ok8.distribTasks(),[[0],[1],[2],[3],[4]])
        self.assertEqual(self.compact_ok9.distribTasks(),[[0,1],[2,3],[4,5],[6,7],[8,9]])
        self.assertEqual(self.compact_ok11.distribTasks(),[[0,1],[2,3],[4,5],[6,7],[8,9]])
        self.assertEqual(self.compact_ok12.distribTasks(),[[0,1,2,3,4,5,6,7,8,9,10,11]])
        self.assertEqual(self.compact_ok15.distribTasks(),[[0,1,2,3],[4,5,6,7],[8,9,10,11],[12,13,14,15],[16,17,18,19]])
        

if __name__ == '__main__':
    unittest.main()
