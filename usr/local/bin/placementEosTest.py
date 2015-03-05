#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# emmanuel.courcelle@inp-toulouse.fr
# http://www.calmip.univ-toulouse.fr
# Mars 2015

# Tests unitaires pour placement.py, version EOS UNIQUEMENT
# Vérifiez la variable ARCHI !
# ARCHI = 'BULLX-DLC'

import placement
import unittest

# scatter, 2 sockets, 4 tasks, 4 threads/task, no hyper required
class Test_scatter_2_4_4_F(unittest.TestCase):
    def setUp(self):
         self.archi         = placement.Architecture(2,4,4,False)
         task_distrib       = placement.ScatterMode(self.archi,4,4)
         self.tasks_bounded = task_distrib.distribProcesses()

    def test_tasks_bounded(self):
        self.assertEqual(self.tasks_bounded,[[0,1,2,3],[10,11,12,13],[4,5,6,7],[14,15,16,17]])

    def test_ascii(self):
        ascii = placement.getCpuBindingAscii(self.archi,self.tasks_bounded)
        should= '''  S0-------- S1-------- 
P AAAACCCC.. BBBBDDDD.. 
'''
        self.assertEqual(ascii,should)

    def test_srun(self):
        srun = placement.getCpuBindingSrun(self.archi,self.tasks_bounded)
        self.assertEqual(srun,'--cpu_bind=mask_cpu:0xf,0x3c00,0xf0,0x3c000')

    def test_numa(self):
        numa = placement.getCpuBindingNumactl(self.archi,self.tasks_bounded)
        self.assertEqual(numa,'--physcpubind=0-3,4-7,10-13,14-17')

# scatter, 2 sockets, 4 tasks, 4 threads/task, hyper required
class Test_scatter_2_4_4_T(unittest.TestCase):
    def setUp(self):
         self.archi         = placement.Architecture(2,4,4,True)
         task_distrib       = placement.ScatterMode(self.archi,4,4)
         self.tasks_bounded = task_distrib.distribProcesses()

    def test_tasks_bounded(self):
        self.assertEqual(self.tasks_bounded,[[0,1,2,3],[10,11,12,13],[20,21,22,23],[30,31,32,33]])

    def test_ascii(self):
        ascii = placement.getCpuBindingAscii(self.archi,self.tasks_bounded)
        should= '''  S0-------- S1-------- 
P AAAA...... BBBB...... 
L CCCC...... DDDD...... 
'''
        self.assertEqual(ascii,should)

    def test_srun(self):
        srun = placement.getCpuBindingSrun(self.archi,self.tasks_bounded)
        self.assertEqual(srun,'--cpu_bind=mask_cpu:0xf,0x3c00,0xf00000,0x3c0000000')

    def test_numa(self):
        numa = placement.getCpuBindingNumactl(self.archi,self.tasks_bounded)
        self.assertEqual(numa,'--physcpubind=0-3,10-13,20-23,30-33')

# scatter, 1 socket, 4 tasks, 4 threads/task, no hyper required
class Test_scatter_1_4_4_F(unittest.TestCase):
    def setUp(self):
         self.archi         = placement.Architecture(1,4,4,False)
         task_distrib       = placement.ScatterMode(self.archi,4,4)
         self.tasks_bounded = task_distrib.distribProcesses()

    def test_tasks_bounded(self):
        self.assertEqual(self.tasks_bounded,[[0,1,2,3],[10,11,12,13],[4,5,6,7],[14,15,16,17]])

    def test_ascii(self):
        ascii = placement.getCpuBindingAscii(self.archi,self.tasks_bounded)
        should= '''  S0-------- 
P AAAACCCC.. 
L BBBBDDDD.. 
'''
        self.assertEqual(ascii,should)

    def test_srun(self):
        srun = placement.getCpuBindingSrun(self.archi,self.tasks_bounded)
        self.assertEqual(srun,'--cpu_bind=mask_cpu:0xf,0x3c00,0xf0,0x3c000')

    def test_numa(self):
        numa = placement.getCpuBindingNumactl(self.archi,self.tasks_bounded)
        self.assertEqual(numa,'--physcpubind=0-3,4-7,10-13,14-17')

# compact, 2 sockets, 4 tasks, 4 threads/task, no hyper required
class Test_compact_2_4_4_F(unittest.TestCase):
    def setUp(self):
         self.archi         = placement.Architecture(2,4,4,False)
         task_distrib       = placement.CompactMode(self.archi,4,4)
         self.tasks_bounded = task_distrib.distribProcesses()

    def test_tasks_bounded(self):
        self.assertEqual(self.tasks_bounded,[[0,1,2,3],[4,5,6,7],[8,9,10,11],[12,13,14,15]])

    def test_ascii(self):
        ascii = placement.getCpuBindingAscii(self.archi,self.tasks_bounded)
        should= '''  S0-------- S1-------- 
P AAAABBBBCC CCDDDD.... 
'''
        self.assertEqual(ascii,should)

    def test_srun(self):
        srun = placement.getCpuBindingSrun(self.archi,self.tasks_bounded)
        self.assertEqual(srun,'--cpu_bind=mask_cpu:0xf,0xf0,0xf00,0xf000')

    def test_numa(self):
        numa = placement.getCpuBindingNumactl(self.archi,self.tasks_bounded)
        self.assertEqual(numa,'--physcpubind=0-3,4-7,8-11,12-15')

# compact, 2 sockets, 4 tasks, 4 threads/task, hyper required
class Test_compact_2_4_4_T(unittest.TestCase):
    def setUp(self):
         self.archi         = placement.Architecture(2,4,4,True)
         task_distrib       = placement.CompactMode(self.archi,4,4)
         self.tasks_bounded = task_distrib.distribProcesses()

    def test_tasks_bounded(self):
        self.assertEqual(self.tasks_bounded,[[0,1,2,3],[4,5,6,7],[8,9,20,21],[22,23,24,25]])

    def test_ascii(self):
        ascii = placement.getCpuBindingAscii(self.archi,self.tasks_bounded)
        should= '''  S0-------- S1-------- 
P AAAABBBBCC .......... 
L CCDDDD.... .......... 
'''
        self.assertEqual(ascii,should)


    def test_srun(self):
        srun = placement.getCpuBindingSrun(self.archi,self.tasks_bounded)
        self.assertEqual(srun,'--cpu_bind=mask_cpu:0xf,0xf0,0x300300,0x3c00000')

    def test_numa(self):
        numa = placement.getCpuBindingNumactl(self.archi,self.tasks_bounded)
        self.assertEqual(numa,'--physcpubind=0-3,4-7,8-9,20-21,22-25')

# compact, 1 sockets, 4 tasks, 4 threads/task, no hyper required 
class Test_compact_1_4_4_F(unittest.TestCase):
    def setUp(self):
         self.archi         = placement.Architecture(1,4,4,False)
         task_distrib       = placement.CompactMode(self.archi,4,4)
         self.tasks_bounded = task_distrib.distribProcesses()

    def test_tasks_bounded(self):
        self.assertEqual(self.tasks_bounded,[[0,1,2,3],[4,5,6,7],[8,9,10,11],[12,13,14,15]])

    def test_ascii(self):
        ascii = placement.getCpuBindingAscii(self.archi,self.tasks_bounded)
        should= '''  S0-------- 
P AAAABBBBCC 
L CCDDDD.... 
'''
        self.assertEqual(ascii,should)


    def test_srun(self):
        srun = placement.getCpuBindingSrun(self.archi,self.tasks_bounded)
        self.assertEqual(srun,'--cpu_bind=mask_cpu:0xf,0xf0,0xf00,0xf000')

    def test_numa(self):
        numa = placement.getCpuBindingNumactl(self.archi,self.tasks_bounded)
        self.assertEqual(numa,'--physcpubind=0-3,4-7,8-11,12-15')

# scatter, 2 sockets, 1 task, 20 threads/task, no hyper required
class Test_scatter_2_1_20_F(unittest.TestCase):
    def setUp(self):
         self.archi         = placement.Architecture(2,20,1,False)
         task_distrib       = placement.ScatterMode(self.archi,20,1)
         self.tasks_bounded = task_distrib.distribProcesses()

    def test_tasks_bounded(self):
        self.assertEqual(self.tasks_bounded,[[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19]])

    def test_ascii(self):
        ascii = placement.getCpuBindingAscii(self.archi,self.tasks_bounded)
        should= '''  S0-------- S1-------- 
P AAAAAAAAAA AAAAAAAAAA 
'''
        self.assertEqual(ascii,should)

    def test_srun(self):
        srun = placement.getCpuBindingSrun(self.archi,self.tasks_bounded)
        self.assertEqual(srun,'--cpu_bind=mask_cpu:0xfffff')

    def test_numa(self):
        numa = placement.getCpuBindingNumactl(self.archi,self.tasks_bounded)
        self.assertEqual(numa,'--physcpubind=0-19')
# compact, 2 sockets, 1 task, 20 threads/task, no hyper required
class Test_compact_2_1_20_F(unittest.TestCase):
    def setUp(self):
         self.archi         = placement.Architecture(2,20,1,False)
         task_distrib       = placement.CompactMode(self.archi,20,1)
         self.tasks_bounded = task_distrib.distribProcesses()

    def test_tasks_bounded(self):
        self.assertEqual(self.tasks_bounded,[[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19]])

    def test_ascii(self):
        ascii = placement.getCpuBindingAscii(self.archi,self.tasks_bounded)
        should= '''  S0-------- S1-------- 
P AAAAAAAAAA AAAAAAAAAA 
'''
        self.assertEqual(ascii,should)

    def test_srun(self):
        srun = placement.getCpuBindingSrun(self.archi,self.tasks_bounded)
        self.assertEqual(srun,'--cpu_bind=mask_cpu:0xfffff')

    def test_numa(self):
        numa = placement.getCpuBindingNumactl(self.archi,self.tasks_bounded)
        self.assertEqual(numa,'--physcpubind=0-19')
        
if __name__ == '__main__':
    suite1 = unittest.TestLoader().loadTestsFromTestCase(Test_scatter_2_4_4_F)
    suite2 = unittest.TestLoader().loadTestsFromTestCase(Test_scatter_2_4_4_T)
    suite3 = unittest.TestLoader().loadTestsFromTestCase(Test_scatter_1_4_4_F)
    suite4 = unittest.TestLoader().loadTestsFromTestCase(Test_compact_2_4_4_F)
    suite5 = unittest.TestLoader().loadTestsFromTestCase(Test_compact_2_4_4_T)
    suite6 = unittest.TestLoader().loadTestsFromTestCase(Test_compact_1_4_4_F)
    suite7 = unittest.TestLoader().loadTestsFromTestCase(Test_scatter_2_1_20_F)
    suite8 = unittest.TestLoader().loadTestsFromTestCase(Test_compact_2_1_20_F)


    alltests = unittest.TestSuite([suite1,suite2,suite3,suite4,suite5,suite6,suite7,suite8])
    unittest.TextTestRunner(verbosity=2).run(alltests)

