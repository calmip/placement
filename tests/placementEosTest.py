#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# emmanuel.courcelle@inp-toulouse.fr
# http://www.calmip.univ-toulouse.fr
# Mars 2015

# Tests unitaires pour placement.py, version EOS UNIQUEMENT
# Vérifiez la variable ARCHI !
# ARCHI = 'BULLX-DLC'

import os
os.environ['PLACEMENT_ARCHI'] = 'eos'
import placement
import hardware
import printing
import unittest
import scatter
import compact

# scatter, 2 sockets, 4 tasks, 4 threads/task, no hyper required
class Test_scatter_2_4_4_F(unittest.TestCase):
    def setUp(self):
         self.archi         = placement.Exclusive(hardware.Bullx_dlc(),2,4,4,False)
         self.task_distrib  = scatter.ScatterMode(self.archi,4,4)

    def test_tasks_bounded(self):
        self.assertEqual(self.task_distrib.tasks_bound,[[0,1,2,3],[10,11,12,13],[4,5,6,7],[14,15,16,17]])

    def test_ascii(self):
        ascii = printing.PrintingForAsciiArt(self.task_distrib)
        should= '''  S0-------- S1-------- 
P AAAACCCC.. BBBBDDDD.. 
'''
        self.assertEqual(ascii.__str__(),should)

    def test_srun(self):
        srun = printing.PrintingForSrun(self.task_distrib)
        self.assertEqual(srun.__str__(),'--cpu_bind=mask_cpu:0xf,0x3c00,0xf0,0x3c000')

    def test_numa(self):
        numa = printing.PrintingForNumactl(self.task_distrib)
        self.assertEqual(numa.__str__(),'--physcpubind=0-3,4-7,10-13,14-17')

# scatter, 2 sockets, 4 tasks, 4 threads/task, hyper required
class Test_scatter_2_4_4_T(unittest.TestCase):
    def setUp(self):
         self.archi        = placement.Exclusive(hardware.Bullx_dlc(),2,4,4,True)
         self.task_distrib = scatter.ScatterMode(self.archi,4,4)

    def test_tasks_bounded(self):
        self.assertEqual(self.task_distrib.tasks_bound,[[0,1,2,3],[10,11,12,13],[20,21,22,23],[30,31,32,33]])

    def test_ascii(self):
        ascii = printing.PrintingForAsciiArt(self.task_distrib)
        should= '''  S0-------- S1-------- 
P AAAA...... BBBB...... 
L CCCC...... DDDD...... 
'''
        self.assertEqual(ascii.__str__(),should)

    def test_srun(self):
        srun = printing.PrintingForSrun(self.task_distrib)
        self.assertEqual(srun.__str__(),'--cpu_bind=mask_cpu:0xf,0x3c00,0xf00000,0x3c0000000')

    def test_numa(self):
        numa = placement.PrintingForNumactl(self.task_distrib)
        self.assertEqual(numa.__str__(),'--physcpubind=0-3,10-13,20-23,30-33')

# scatter, 1 socket, 4 tasks, 4 threads/task, no hyper required
class Test_scatter_1_4_4_F(unittest.TestCase):
    def setUp(self):
         self.archi         = placement.Exclusive(hardware.Bullx_dlc(),1,4,4,False)
         self.task_distrib  = scatter.ScatterMode(self.archi,4,4)

    def test_tasks_bounded(self):
        self.assertEqual(self.task_distrib.tasks_bound,[[0,1,2,3],[10,11,12,13],[4,5,6,7],[14,15,16,17]])

    def test_ascii(self):
        ascii = printing.PrintingForAsciiArt(self.task_distrib)
        should= '''  S0-------- 
P AAAACCCC.. 
L BBBBDDDD.. 
'''
        self.assertEqual(ascii.__str__(),should)

    def test_srun(self):
        srun = printing.PrintingForSrun(self.task_distrib)
        self.assertEqual(srun.__str__(),'--cpu_bind=mask_cpu:0xf,0x3c00,0xf0,0x3c000')

    def test_numa(self):
        numa = placement.PrintingForNumactl(self.task_distrib)
        self.assertEqual(numa.__str__(),'--physcpubind=0-3,4-7,10-13,14-17')

# compact, 2 sockets, 4 tasks, 4 threads/task, no hyper required
class Test_compact_2_4_4_F(unittest.TestCase):
    def setUp(self):
         self.archi         = placement.Exclusive(hardware.Bullx_dlc(),2,4,4,False)
         self.task_distrib  = compact.CompactMode(self.archi)

    def test_tasks_bounded(self):
        self.assertEqual(self.task_distrib.tasks_bound,[[0,1,2,3],[4,5,6,7],[8,9,10,11],[12,13,14,15]])

    def test_ascii(self):
        ascii = printing.PrintingForAsciiArt(self.task_distrib)
        should= '''  S0-------- S1-------- 
P AAAABBBBCC CCDDDD.... 
'''
        self.assertEqual(ascii.__str__(),should)

    def test_srun(self):
        srun = printing.PrintingForSrun(self.task_distrib)
        self.assertEqual(srun.__str__(),'--cpu_bind=mask_cpu:0xf,0xf0,0xf00,0xf000')

    def test_numa(self):
        numa = placement.PrintingForNumactl(self.task_distrib)
        self.assertEqual(numa.__str__(),'--physcpubind=0-3,4-7,8-11,12-15')

# compact, 2 sockets, 4 tasks, 4 threads/task, hyper required
class Test_compact_2_4_4_T(unittest.TestCase):
    def setUp(self):
         self.archi        = placement.Exclusive(hardware.Bullx_dlc(),2,4,4,True)
         self.task_distrib = placement.CompactMode(self.archi)

    def test_tasks_bounded(self):
        self.assertEqual(self.task_distrib.tasks_bound,[[0,1,2,3],[4,5,6,7],[8,9,20,21],[22,23,24,25]])

    def test_ascii(self):
        ascii = printing.PrintingForAsciiArt(self.task_distrib)
        should= '''  S0-------- S1-------- 
P AAAABBBBCC .......... 
L CCDDDD.... .......... 
'''
        self.assertEqual(ascii.__str__(),should)


    def test_srun(self):
        srun = printing.PrintingForSrun(self.task_distrib)
        self.assertEqual(srun.__str__(),'--cpu_bind=mask_cpu:0xf,0xf0,0x300300,0x3c00000')

    def test_numa(self):
        numa = placement.PrintingForNumactl(self.task_distrib)
        self.assertEqual(numa.__str__(),'--physcpubind=0-3,4-7,8-9,20-21,22-25')

# compact, 1 sockets, 4 tasks, 4 threads/task, no hyper required 
class Test_compact_1_4_4_F(unittest.TestCase):
    def setUp(self):
         self.archi         = placement.Exclusive(hardware.Bullx_dlc(),1,4,4,False)
         self.task_distrib  = placement.CompactMode(self.archi)

    def test_tasks_bounded(self):
        self.assertEqual(self.task_distrib.tasks_bound,[[0,1,2,3],[4,5,6,7],[8,9,10,11],[12,13,14,15]])

    def test_ascii(self):
        ascii = printing.PrintingForAsciiArt(self.task_distrib)
        should= '''  S0-------- 
P AAAABBBBCC 
L CCDDDD.... 
'''
        self.assertEqual(ascii.__str__(),should)

    def test_srun(self):
        srun = printing.PrintingForSrun(self.task_distrib)
        self.assertEqual(srun.__str__(),'--cpu_bind=mask_cpu:0xf,0xf0,0xf00,0xf000')

    def test_numa(self):
        numa = printing.PrintingForNumactl(self.task_distrib)
        self.assertEqual(numa.__str__(),'--physcpubind=0-3,4-7,8-11,12-15')

# scatter, 2 sockets, 1 task, 20 threads/task, no hyper required
class Test_scatter_2_1_20_F(unittest.TestCase):
    def setUp(self):
         self.archi         = placement.Exclusive(hardware.Bullx_dlc(),2,20,1,False)
         self.task_distrib  = placement.ScatterMode(self.archi,20,1)

    def test_tasks_bounded(self):
        self.assertEqual(self.task_distrib.tasks_bound,[[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19]])

    def test_ascii(self):
        ascii = printing.PrintingForAsciiArt(self.task_distrib)
        should= '''  S0-------- S1-------- 
P AAAAAAAAAA AAAAAAAAAA 
'''
        self.assertEqual(ascii.__str__(),should)

    def test_srun(self):
        srun = printing.PrintingForSrun(self.task_distrib)
        self.assertEqual(srun.__str__(),'--cpu_bind=mask_cpu:0xfffff')

    def test_numa(self):
        numa = printing.PrintingForNumactl(self.task_distrib)
        self.assertEqual(numa.__str__(),'--physcpubind=0-19')

# compact, 2 sockets, 1 task, 20 threads/task, no hyper required
class Test_compact_2_1_20_F(unittest.TestCase):
    def setUp(self):
         self.archi         = placement.Exclusive(hardware.Bullx_dlc(),2,20,1,False)
         self.task_distrib  = placement.CompactMode(self.archi)

    def test_tasks_bounded(self):
        self.assertEqual(self.task_distrib.tasks_bound,[[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19]])

    def test_ascii(self):
        ascii = printing.PrintingForAsciiArt(self.task_distrib)
        should= '''  S0-------- S1-------- 
P AAAAAAAAAA AAAAAAAAAA 
'''
        self.assertEqual(ascii.__str__(),should)

    def test_srun(self):
        srun = printing.PrintingForSrun(self.task_distrib)
        self.assertEqual(srun.__str__(),'--cpu_bind=mask_cpu:0xfffff')

    def test_numa(self):
        numa = printing.PrintingForNumactl(self.task_distrib)
        self.assertEqual(numa.__str__(),'--physcpubind=0-19')

# scatter, 2 sockets, 2 tasks, 16 threads/task, no hyper required
class Test_scatter_2_2_16_F(unittest.TestCase):
    def setUp(self):
         self.archi         = placement.Exclusive(hardware.Bullx_dlc(),2,16,2,False)
         self.task_distrib  = placement.ScatterMode(self.archi,16,2)
         self.task_distrib.threadsSort()

    def test_tasks_bounded(self):
        self.assertEqual(self.task_distrib.tasks_bound,[[0,1,2,3,4,5,6,7,10,11,12,13,14,15,16,17],[20,21,22,23,24,25,26,27,30,31,32,33,34,35,36,37]])

    def test_ascii(self):
        ascii = printing.PrintingForAsciiArt(self.task_distrib)
        should= '''  S0-------- S1-------- 
P AAAAAAAA.. AAAAAAAA.. 
L BBBBBBBB.. BBBBBBBB.. 
'''
        self.assertEqual(ascii.__str__(),should)

    def test_srun(self):
        srun = printing.PrintingForSrun(self.task_distrib)
        self.assertEqual(srun.__str__(),'--cpu_bind=mask_cpu:0x3fcff,0x3fcff00000')

    def test_numa(self):
        numa = printing.PrintingForNumactl(self.task_distrib)
        self.assertEqual(numa.__str__(),'--physcpubind=0-7,10-17,20-27,30-37')

# compact, 2 sockets, 2 tasks, 16 threads/task, no hyper required
class Test_compact_2_2_16_F(unittest.TestCase):
    def setUp(self):
         self.archi         = placement.Exclusive(hardware.Bullx_dlc(),2,16,2,False)
         self.task_distrib  = compact.CompactMode(self.archi)
         self.task_distrib.threadsSort()

    def test_tasks_bounded(self):
        self.assertEqual(self.task_distrib.tasks_bound,[[0,1,2,3,4,5,6,7,8,9,20,21,22,23,24,25],[10,11,12,13,14,15,16,17,18,19,26,27,28,29,30,31]])

    def test_ascii(self):
        ascii = printing.PrintingForAsciiArt(self.task_distrib)
        should= '''  S0-------- S1-------- 
P AAAAAAAAAA BBBBBBBBBB 
L AAAAAABBBB BB........ 
'''
        self.assertEqual(ascii.__str__(),should)

    def test_srun(self):
        srun = printing.PrintingForSrun(self.task_distrib)
        self.assertEqual(srun.__str__(),'--cpu_bind=mask_cpu:0x3f003ff,0xfc0ffc00')

    def test_numa(self):
        numa = printing.PrintingForNumactl(self.task_distrib)
        self.assertEqual(numa.__str__(),'--physcpubind=0-9,20-25,10-19,26-31')
        
if __name__ == '__main__':
    suite1 = unittest.TestLoader().loadTestsFromTestCase(Test_scatter_2_4_4_F)
    suite2 = unittest.TestLoader().loadTestsFromTestCase(Test_scatter_2_4_4_T)
    suite3 = unittest.TestLoader().loadTestsFromTestCase(Test_scatter_1_4_4_F)
    suite4 = unittest.TestLoader().loadTestsFromTestCase(Test_compact_2_4_4_F)
    suite5 = unittest.TestLoader().loadTestsFromTestCase(Test_compact_2_4_4_T)
    suite6 = unittest.TestLoader().loadTestsFromTestCase(Test_compact_1_4_4_F)
    suite7 = unittest.TestLoader().loadTestsFromTestCase(Test_scatter_2_1_20_F)
    suite8 = unittest.TestLoader().loadTestsFromTestCase(Test_compact_2_1_20_F)
    suite9 = unittest.TestLoader().loadTestsFromTestCase(Test_scatter_2_2_16_F)
    suite10 = unittest.TestLoader().loadTestsFromTestCase(Test_compact_2_2_16_F)


    alltests = unittest.TestSuite([suite1,suite2,suite3,suite4,suite5,suite6,suite7,suite8,suite9,suite10])
    unittest.TextTestRunner(verbosity=2).run(alltests)
