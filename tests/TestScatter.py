#! /usr/bin/env python
# -*- coding: utf-8 -*-

from utilities import *
from hardware import *
from architecture import *
from scatter import *
import unittest

class TestScatterExclusive(unittest.TestCase):
    def setUp(self):
        self.hardware = Bullx_dlc()

        # Architecture = 4 tâches/4 threads
        self.exclu_ok1   = Exclusive(self.hardware,2,4,4,False)
        self.scatter_ok1 = ScatterMode(self.exclu_ok1,4,4)
        # Architecture = 4 tâches/8 threads hyperthreading
        self.exclu_ok2   = Exclusive(self.hardware,2,8,4,True)
        self.scatter_ok2 = ScatterMode(self.exclu_ok2,8,4)
        # Architecture = 20 tâches/1 thread no hyperthreading
        self.exclu_ok3   = Exclusive(self.hardware,2,1,20,False)
        self.scatter_ok3 = ScatterMode(self.exclu_ok3,1,20)
        # Architecture = 20 tâches/2 threads hyperthreading
        self.exclu_ok4   = Exclusive(self.hardware,2,2,20,True)
        self.scatter_ok4 = ScatterMode(self.exclu_ok4,2,20)

        # Architecture = 4 tâches/8 threads no hyperthreading
        self.exclu_ko5   = Exclusive(self.hardware,2,8,8,False)
        self.scatter_ko5 = ScatterMode(self.exclu_ko5,8,8)

        # Architecture = 20 tâches/2 threads no hyperthreading (en fait l'hyper est forcé)
        self.exclu_ok6   = Exclusive(self.hardware,2,2,20,False)
        self.scatter_ok6 = ScatterMode(self.exclu_ok6,2,20)

        # Architecture = 21 tâches/2 threads  hyperthreading
        self.exclu_ko7   = Exclusive(self.hardware,2,2,21,True)
        self.scatter_ko7 = ScatterMode(self.exclu_ko7,2,21)

        # Si pas d'hyperthreading, autant de threads qu'on veut
        self.exclu_ok8   = Exclusive(self.hardware,2,1,5,False)
        self.scatter_ok8 = ScatterMode(self.exclu_ok8,1,5)

        self.exclu_ok9   = Exclusive(self.hardware,2,2,5,False)
        self.scatter_ok9 = ScatterMode(self.exclu_ok9,2,5)

        # Si hyperthreading activé, seulement nombre PAIR de threads !
        self.exclu_ko10 = Exclusive(self.hardware,2,1,5,True)
        self.scatter_ko10 = ScatterMode(self.exclu_ko10,1,5)
        self.exclu_ok11 = Exclusive(self.hardware,2,2,5,True)
        self.scatter_ok11 = ScatterMode(self.exclu_ok11,2,5)

        # Si une seule tache elle peut déborder du socket
        # cf. scatter.py L 30-32
        self.exclu_ok12 = Exclusive(self.hardware,2,12,1,False)
        self.scatter_ok12 = ScatterMode(self.exclu_ok12,12,1)
        #self.exclu_ok13 = Exclusive(self.hardware,2,22,1,True)
        #self.scatter_ok13 = ScatterMode(self.exclu_ok13,22,1)
        #self.scatter_ko14 = ScatterMode(self.exclu_ko14,12,2)

        # Si plusieurs tâches non, elles ne peuvent pas
        #self.exclu_ko14 = Exclusive(self.hardware,2,12,2,True)

        # Si plusieurs tâches elles ne doivent pas être à cheval sur deux sockets
        self.exclu_ko15 = Exclusive(self.hardware,2,4,5,False)
        self.scatter_ko15 = ScatterMode(self.exclu_ko15,4,5)

    def test_exclusive_check(self):
        ok = [self.scatter_ok1,self.scatter_ok2,self.scatter_ok3,self.scatter_ok4,self.scatter_ok6,self.scatter_ok8,self.scatter_ok9,self.scatter_ok11,self.scatter_ok12]
        ko = [self.scatter_ko5,self.scatter_ko7,self.scatter_ko10,self.scatter_ko15]
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
        self.assertEqual(self.scatter_ok1.distribTasks(),[[0,1,2,3],[10,11,12,13],[4,5,6,7],[14,15,16,17]])
        self.assertEqual(self.scatter_ok2.distribTasks(),[[0,1,2,3,4,5,6,7],[10,11,12,13,14,15,16,17],[20,21,22,23,24,25,26,27],[30,31,32,33,34,35,36,37]])
        self.assertEqual(self.scatter_ok3.distribTasks(),[[0],[10],[1],[11],[2],[12],[3],[13],[4],[14],[5],[15],[6],[16],[7],[17],[8],[18],[9],[19]])
        self.assertEqual(self.scatter_ok4.distribTasks(),[[0,1],[10,11],[20,21],[30,31],
                                                          [2,3],[12,13],[22,23],[32,33],
                                                          [4,5],[14,15],[24,25],[34,35],
                                                          [6,7],[16,17],[26,27],[36,37],
                                                          [8,9],[18,19],[28,29],[38,39]])
        self.assertEqual(self.scatter_ok6.distribTasks(),[[0,1],[10,11],[20,21],[30,31],
                                                          [2,3],[12,13],[22,23],[32,33],
                                                          [4,5],[14,15],[24,25],[34,35],
                                                          [6,7],[16,17],[26,27],[36,37],
                                                          [8,9],[18,19],[28,29],[38,39]])
        self.assertEqual(self.scatter_ok8.distribTasks(),[[0],[10],[1],[11],[2]])
        self.assertEqual(self.scatter_ok9.distribTasks(),[[0,1],[10,11],[2,3],[12,13],[4,5]])
        self.assertEqual(self.scatter_ok11.distribTasks(),[[0,1],[10,11],[20,21],[30,31],[2,3]])
        self.assertEqual(self.scatter_ok12.distribTasks(),[[0,1,2,3,4,5,10,11,12,13,14,15]])
        

if __name__ == '__main__':
    unittest.main()
