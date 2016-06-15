#! /usr/bin/env python
# -*- coding: utf-8 -*-

from utilities import *
from hardware import *
from architecture import *
from scatter import *
import unittest

#@unittest.skip("it works, not tested")
class TestScatterExclusive(unittest.TestCase):
    def setUp(self):
        os.environ['PLACEMENT_PARTITION'] = 'exclusive'
        self.hardware = Hardware.factory()
        self.assertEqual(self.hardware.NAME,'Bullx_dlc')

        # Architecture = 4 tâches/4 threads
        self.exclu_ok1   = Exclusive(self.hardware,4,4,False)
        self.scatter_ok1 = ScatterMode(self.exclu_ok1)
        # Architecture = 4 tâches/8 threads hyperthreading
        self.exclu_ok2   = Exclusive(self.hardware,8,4,True)
        self.scatter_ok2 = ScatterMode(self.exclu_ok2)
        # Architecture = 20 tâches/1 thread no hyperthreading
        self.exclu_ok3   = Exclusive(self.hardware,1,20,False)
        self.scatter_ok3 = ScatterMode(self.exclu_ok3)
        # Architecture = 20 tâches/2 threads hyperthreading
        self.exclu_ok4   = Exclusive(self.hardware,2,20,True)
        self.scatter_ok4 = ScatterMode(self.exclu_ok4)

        # Architecture = 4 tâches/8 threads no hyperthreading
        self.exclu_ko5   = Exclusive(self.hardware,8,8,False)

        # Architecture = 20 tâches/2 threads no hyperthreading (en fait l'hyper est forcé)
        self.exclu_ok6   = Exclusive(self.hardware,2,20,False)
        self.scatter_ok6 = ScatterMode(self.exclu_ok6)

        # Architecture = 21 tâches/2 threads  hyperthreading
        self.exclu_ko7   = Exclusive(self.hardware,2,21,True)

        # Si pas d'hyperthreading, autant de threads qu'on veut
        self.exclu_ok8   = Exclusive(self.hardware,1,5,False)
        self.scatter_ok8 = ScatterMode(self.exclu_ok8)

        self.exclu_ok9   = Exclusive(self.hardware,2,5,False)
        self.scatter_ok9 = ScatterMode(self.exclu_ok9)

        # Si hyperthreading activé, seulement nombre PAIR de threads !
        self.exclu_ko10 = Exclusive(self.hardware,1,5,True)

        self.exclu_ok11 = Exclusive(self.hardware,2,5,True)
        self.scatter_ok11 = ScatterMode(self.exclu_ok11)

        # Si une seule tache elle peut déborder du socket
        # cf. scatter.py L 30-32
        self.exclu_ok12 = Exclusive(self.hardware,12,1,False)
        self.scatter_ok12 = ScatterMode(self.exclu_ok12)
        self.exclu_ok13 = Exclusive(self.hardware,24,1,True)
        self.scatter_ok13 = ScatterMode(self.exclu_ok13)

        # Si plusieurs tâches elles ne doivent pas être à cheval sur deux sockets
        self.exclu_ko15 = Exclusive(self.hardware,4,5,False)

    def test_compute_task_template(self):
        self.assertEqual(self.scatter_ok1.test__compute_task_template(),[0,1,2,3])
        self.assertEqual(self.scatter_ok2.test__compute_task_template(),[0,1,2,3,20,21,22,23])
        self.assertEqual(self.scatter_ok3.test__compute_task_template(),[0])
        self.assertEqual(self.scatter_ok4.test__compute_task_template(),[0,20])
        self.assertEqual(self.scatter_ok6.test__compute_task_template(),[0,20])
        self.assertEqual(self.scatter_ok11.test__compute_task_template(),[0,20])
        self.assertEqual(self.scatter_ok12.test__compute_task_template(True),[0,1,2,3,4,5])
        self.assertEqual(self.scatter_ok13.test__compute_task_template(True),[0,1,2,3,4,5,20,21,22,23,24,25])


    def test_exclusive_check(self):
        ok = [self.scatter_ok1,self.scatter_ok2,self.scatter_ok3,self.scatter_ok4,self.scatter_ok6,self.scatter_ok8,self.scatter_ok9,self.scatter_ok11,self.scatter_ok12]
        ko = [self.exclu_ko5,self.exclu_ko7,self.exclu_ko10,self.exclu_ko15]
        i=0
        for s in ok:
            self.assertEqual(s.checkParameters(),None)
            i += 1
            #print i

        i=0
        for s in ko:
            self.assertRaises(PlacementException,ScatterMode,s)
            i += 1
            #print i

    def test_exclusive_distrib(self):
        self.assertEqual(self.scatter_ok1.distribTasks(),[[0,1,2,3],[4,5,6,7],[10,11,12,13],[14,15,16,17]])
        self.assertEqual(self.scatter_ok2.distribTasks(),[[0,1,2,3,20,21,22,23],[4,5,6,7,24,25,26,27],[10,11,12,13,30,31,32,33],[14,15,16,17,34,35,36,37]])
        self.assertEqual(self.scatter_ok3.distribTasks(),[[0],[1],[2],[3],[4],[5],[6],[7],[8],[9],[10],[11],[12],[13],[14],[15],[16],[17],[18],[19]])
        self.assertEqual(self.scatter_ok4.distribTasks(),[[0,20],[1,21],[2,22],[3,23],[4,24],[5,25],[6,26],[7,27],[8,28],[9,29],
                                                          [10,30],[11,31],[12,32],[13,33],[14,34],[15,35],[16,36],[17,37],[18,38],[19,39]])
        self.assertEqual(self.scatter_ok4.distribTasks(),[[0,20],[1,21],[2,22],[3,23],[4,24],[5,25],[6,26],[7,27],[8,28],[9,29],
                                                          [10,30],[11,31],[12,32],[13,33],[14,34],[15,35],[16,36],[17,37],[18,38],[19,39]])
        self.assertEqual(self.scatter_ok8.distribTasks(),[[0],[1],[2],[10],[11]])
        self.assertEqual(self.scatter_ok9.distribTasks(),[[0,1],[2,3],[4,5],[10,11],[12,13]])
        self.assertEqual(self.scatter_ok11.distribTasks(),[[0,20],[1,21],[2,22],[10,30],[11,31]])
        self.assertEqual(self.scatter_ok12.distribTasks(),[[0,1,2,3,4,5,10,11,12,13,14,15]])
        self.assertEqual(self.scatter_ok13.distribTasks(),[[0,1,2,3,4,5,20,21,22,23,24,25,10,11,12,13,14,15,30,31,32,33,34,35]])

# bien qu'on teste ici une architecture Shared, tout se passe comme si elle était exclusive
class TestScatterSharedMesca(unittest.TestCase):
    def setUp(self):
        os.environ['PLACEMENT_PARTITION'] = 'mesca'
        self.hardware = Hardware.factory()
        self.assertEqual(self.hardware.NAME,'Mesca2')

        # Architecture = 8 sockets/4 tâches/4 threads
        self.shared_ok1   = Shared(self.hardware,4,4,False)
        self.scatter_ok1 = ScatterMode(self.shared_ok1)

        # Architecture = 8 sockets/4 tâches/8 threads
        self.shared_ok2   = Shared(self.hardware,8,4,False)
        self.scatter_ok2 = ScatterMode(self.shared_ok2)

        # Architecture = 8 sockets/10 tâches/4 threads
        self.shared_ok3   = Shared(self.hardware,4,10,False)
        self.scatter_ok3 = ScatterMode(self.shared_ok3)

#    @unittest.skip("it works, not tested")
    def test_compute_task_template(self):
        self.assertEqual(self.scatter_ok1.test__compute_task_template(),[0,1,2,3])
        self.assertEqual(self.scatter_ok2.test__compute_task_template(),[0,1,2,3,4,5,6,7])

    def test_shared_distrib(self):
        self.assertEqual(self.scatter_ok1.distribTasks(),[[0,1,2,3],[16,17,18,19],[32,33,34,35],[48,49,50,51]])
        self.assertEqual(self.scatter_ok2.distribTasks(),[[0,1,2,3,4,5,6,7],[16,17,18,19,20,21,22,23],[32,33,34,35,36,37,38,39],[48,49,50,51,52,53,54,55]])
        self.assertEqual(self.scatter_ok3.distribTasks(),[[0,1,2,3],[4,5,6,7],[16,17,18,19],[20,21,22,23],
                                                          [32,33,34,35],
                                                          [48,49,50,51],
                                                          [64,65,66,67],
                                                          [80,81,82,83],
                                                          [96,97,98,99],
                                                          [112,113,114,115]])


#@unittest.skip("it works, not tested")
class TestScatterBlockExclusive(unittest.TestCase):
    def setUp(self):
        os.environ['PLACEMENT_PARTITION'] = 'exclusive'
        self.hardware = Hardware.factory()
        self.assertEqual(self.hardware.NAME,'Bullx_dlc')

        # Architecture = 4 tâches/4 threads
        self.exclu_ok1   = Exclusive(self.hardware,4,4,False)
        self.scatter_block_ok1 = ScatterBlockMode(self.exclu_ok1)
        # Architecture = 4 tâches/8 threads hyperthreading
        self.exclu_ok2   = Exclusive(self.hardware,8,4,True)
        self.scatter_block_ok2 = ScatterBlockMode(self.exclu_ok2)
        # Architecture = 20 tâches/1 thread no hyperthreading
        self.exclu_ok3   = Exclusive(self.hardware,1,20,False)
        self.scatter_block_ok3 = ScatterBlockMode(self.exclu_ok3)
        # Architecture = 20 tâches/2 threads hyperthreading
        self.exclu_ok4   = Exclusive(self.hardware,2,20,True)
        self.scatter_block_ok4 = ScatterBlockMode(self.exclu_ok4)

        # Architecture = 4 tâches/8 threads no hyperthreading
        self.exclu_ko5   = Exclusive(self.hardware,8,8,False)

        # Architecture = 20 tâches/2 threads no hyperthreading (en fait l'hyper est forcé)
        self.exclu_ok6   = Exclusive(self.hardware,2,20,False)
        self.scatter_block_ok6 = ScatterBlockMode(self.exclu_ok6)

        # Architecture = 21 tâches/2 threads  hyperthreading
        self.exclu_ko7   = Exclusive(self.hardware,2,21,True)

        # Si pas d'hyperthreading, autant de threads qu'on veut
        self.exclu_ok8   = Exclusive(self.hardware,1,5,False)
        self.scatter_block_ok8 = ScatterBlockMode(self.exclu_ok8)

        self.exclu_ok9   = Exclusive(self.hardware,2,5,False)
        self.scatter_block_ok9 = ScatterBlockMode(self.exclu_ok9)

        # Si hyperthreading activé, seulement nombre PAIR de threads !
        self.exclu_ko10 = Exclusive(self.hardware,1,5,True)

        self.exclu_ok11 = Exclusive(self.hardware,2,5,True)
        self.scatter_block_ok11 = ScatterBlockMode(self.exclu_ok11)

        # Si une seule tache elle peut déborder du socket
        # cf. scatter.py L 30-32
        self.exclu_ok12 = Exclusive(self.hardware,12,1,False)
        self.scatter_block_ok12 = ScatterBlockMode(self.exclu_ok12)
        #self.exclu_ok13 = Exclusive(self.hardware,22,1,True)
        #self.scatter_block_ok13 = ScatterBlockMode(self.exclu_ok13)
        #self.scatter_block_ko14 = ScatterBlockMode(self.exclu_ko14)

        # Si plusieurs tâches non, elles ne peuvent pas
        #self.exclu_ko14 = Exclusive(self.hardware,12,2,True)

        # Si plusieurs tâches elles ne doivent pas être à cheval sur deux sockets
        self.exclu_ko15 = Exclusive(self.hardware,4,5,False)

    def test_exclusive_check(self):
        ok = [self.scatter_block_ok1,self.scatter_block_ok2,self.scatter_block_ok3,self.scatter_block_ok4,self.scatter_block_ok6,self.scatter_block_ok8,self.scatter_block_ok9,self.scatter_block_ok11,self.scatter_block_ok12]
        ko = [self.exclu_ko5,self.exclu_ko7,self.exclu_ko10,self.exclu_ko15]
        i=0
        for s in ok:
            self.assertEqual(s.checkParameters(),None)
            i += 1
            #print i

        i=0
        for s in ko:
            self.assertRaises(PlacementException,ScatterBlockMode,s)
            i += 1
            #print i

    def test_exclusive_distrib(self):
        self.assertEqual(self.scatter_block_ok1.distribTasks(),[[0,1,2,3],[10,11,12,13],[4,5,6,7],[14,15,16,17]])
        self.assertEqual(self.scatter_block_ok2.distribTasks(),[[0,1,2,3,4,5,6,7],[10,11,12,13,14,15,16,17],[20,21,22,23,24,25,26,27],[30,31,32,33,34,35,36,37]])
        self.assertEqual(self.scatter_block_ok3.distribTasks(),[[0],[10],[1],[11],[2],[12],[3],[13],[4],[14],[5],[15],[6],[16],[7],[17],[8],[18],[9],[19]])
        self.assertEqual(self.scatter_block_ok4.distribTasks(),[[0,1],[10,11],[20,21],[30,31],
                                                                [2,3],[12,13],[22,23],[32,33],
                                                                [4,5],[14,15],[24,25],[34,35],
                                                                [6,7],[16,17],[26,27],[36,37],
                                                                [8,9],[18,19],[28,29],[38,39]])
        self.assertEqual(self.scatter_block_ok6.distribTasks(),[[0,1],[10,11],[20,21],[30,31],
                                                                [2,3],[12,13],[22,23],[32,33],
                                                                [4,5],[14,15],[24,25],[34,35],
                                                                [6,7],[16,17],[26,27],[36,37],
                                                                [8,9],[18,19],[28,29],[38,39]])
        self.assertEqual(self.scatter_block_ok8.distribTasks(),[[0],[10],[1],[11],[2]])
        self.assertEqual(self.scatter_block_ok9.distribTasks(),[[0,1],[10,11],[2,3],[12,13],[4,5]])
        self.assertEqual(self.scatter_block_ok11.distribTasks(),[[0,1],[10,11],[20,21],[30,31],[2,3]])
        self.assertEqual(self.scatter_block_ok12.distribTasks(),[[0,1,2,3,4,5,10,11,12,13,14,15]])
        

if __name__ == '__main__':
    unittest.main()
