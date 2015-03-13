#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# emmanuel.courcelle@inp-toulouse.fr
# http://www.calmip.univ-toulouse.fr
# Mars 2015

# Tests unitaires pour placement.py, version EOS UNIQUEMENT
# Forçage de uvprod !
# On est donc en mode shared, on utilise un mock pour remplacer numactl
import os
os.environ['SLURM_NODELIST'] = 'uvprod'

import placement
import unittest
import mock

# scatter, 2 sockets réservés, 4 tasks, 4 threads/task
# On met un bouchon sur l'appel numactl 
class Test_scatter_24_2_4_4(unittest.TestCase):
    def setUp(self):
        placement.Shared._Shared__detectSockets = mock.Mock(return_value=[9,10])
        self.archi         = placement.Shared(24,4,4,False)
        task_distrib       = placement.ScatterMode(self.archi,4,4)
        self.tasks_bounded = task_distrib.distribProcesses()

    def test_tasks_bounded(self):
        self.assertEqual(self.tasks_bounded,[[72,73,74,75],[80,81,82,83],[76,77,78,79],[84,85,86,87]])

    def test_ascii(self):
        ascii = placement.getCpuBindingAscii(self.archi,self.tasks_bounded)
        should= '''  S0------ S1------ S2------ S3------ S4------ S5------ S6------ S7------ 
P                                                                         
  S8------ S9------ S10----- S11----- S12----- S13----- S14----- S15----- 
P          AAAACCCC BBBBDDDD                                              
  S16----- S17----- S18----- S19----- S20----- S21----- S22----- S23----- 
P                                                                         
'''
        #print
        #print should
        #print 
        #print ascii.replace(' ','#')+'=='
        #print should.replace(' ','#')+'=='
        self.assertEqual(len(ascii),len(should))
        self.assertEqual(ascii,should)

    def test_srun(self):
        srun   = placement.getCpuBindingSrun(self.archi,self.tasks_bounded)
        should = '--cpu_bind=mask_cpu:0xf000000000000000000,0xf00000000000000000000,0xf0000000000000000000,0xf000000000000000000000'
        #print
        #print srun
        #print should
        self.assertEqual(srun,should)

    def test_numa(self):
        numa = placement.getCpuBindingNumactl(self.archi,self.tasks_bounded)
        self.assertEqual(numa,'--physcpubind=72-75,76-79,80-83,84-87')

# scatter, 3 sockets réservés, 3 tasks, 4 threads/task
# On met un bouchon sur l'appel numactl 
class Test_scatter_24_3_3_4(unittest.TestCase):
    def setUp(self):
        placement.Shared._Shared__detectSockets = mock.Mock(return_value=[9,10,12])
        self.archi         = placement.Shared(24,4,3,False)
        task_distrib       = placement.ScatterMode(self.archi,4,3)
        self.tasks_bounded = task_distrib.distribProcesses()

    def test_tasks_bounded(self):
        self.assertEqual(self.tasks_bounded,[[72,73,74,75],[80,81,82,83],[96,97,98,99]])

    def test_ascii(self):
        ascii = placement.getCpuBindingAscii(self.archi,self.tasks_bounded)
        should= '''  S0------ S1------ S2------ S3------ S4------ S5------ S6------ S7------ 
P                                                                         
  S8------ S9------ S10----- S11----- S12----- S13----- S14----- S15----- 
P          AAAA.... BBBB....          CCCC....                            
  S16----- S17----- S18----- S19----- S20----- S21----- S22----- S23----- 
P                                                                         
'''
        #print
        #print should
        #print 
        #print ascii.replace(' ','#')+'=='
        #print should.replace(' ','#')+'=='
        self.assertEqual(len(ascii),len(should))
        self.assertEqual(ascii,should)

    def test_srun(self):
        srun   = placement.getCpuBindingSrun(self.archi,self.tasks_bounded)
        should = '--cpu_bind=mask_cpu:0xf000000000000000000,0xf00000000000000000000,0xf000000000000000000000000'
        #print
        #print srun
        #print should
        self.assertEqual(srun,should)

    def test_numa(self):
        numa = placement.getCpuBindingNumactl(self.archi,self.tasks_bounded)
        self.assertEqual(numa,'--physcpubind=72-75,80-83,96-99')

# scatter, 2 sockets réservés, 3 tasks, 8 threads/task ==> Exception !
# On met un bouchon sur l'appel numactl 
class Test_scatter_24_2_3_8(unittest.TestCase):
    def setUp(self):
        placement.Shared._Shared__detectSockets = mock.Mock(return_value=[9,10])
        self.archi         = placement.Shared(24,8,3,False)
        self.task_distrib  = placement.ScatterMode(self.archi,8,3)

    def test_except(self):
        self.assertRaises(placement.PlacementException,self.task_distrib.distribProcesses)


        
if __name__ == '__main__':
    print placement.ARCHI
    exit

    suite1 = unittest.TestLoader().loadTestsFromTestCase(Test_scatter_24_2_4_4)
    suite2 = unittest.TestLoader().loadTestsFromTestCase(Test_scatter_24_3_3_4)
    suite3 = unittest.TestLoader().loadTestsFromTestCase(Test_scatter_24_2_3_8)

    alltests = unittest.TestSuite([suite1,suite2,suite3])
    unittest.TextTestRunner(verbosity=2).run(alltests)
#    unittest.TextTestRunner(verbosity=2).run(suite1)
