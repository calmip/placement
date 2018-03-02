#! /usr/bin/env python
# -*- coding: utf-8 -*-

#
# This file is part of PLACEMENT software
# PLACEMENT helps users to bind their processes to one or more cpu-cores
#
# PLACEMENT is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
#  Copyright (C) 2015-2018 Emmanuel Courcelle
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

import os
from exception import *
from utilities import compactString2List
import subprocess

class Architecture(object):
    """ Describing the architecture of the system

    The architecture, is driven by:
    - The guessed hardware
    - The number of sockets/node: on a shared machine we do not necessarily use ALL sockets
    - The number of tasks (processes or threads) who may start hyperthreading use (if allowed by the hardware)

    THIS IS AN ABSTRACT CLASS
    """

    def __init__(self, hardware, cpus_per_task, tasks, hyper, sockets_per_node=-1):
        """ Build an Architecture object

        Arguments:
        hardware     : An object of class Hardware, descriving the hardware limits of the system
        tasks        : The number of tasks (= processes)
        cpus_per_task: The number of cpus dedicated to each process (enerally the number of threads)
        hyper        : If False, do not used hyperthreading, even if allowed by the hardware
        sockets_per_node : Should be < hardware.SOCKETS_PER_NODE - Not used yet

        Attributes:
        l_sockets : A list of sockets which can be used
        m_cores   : A mask describing the usable cores (useful on a shared architecture)
        sockets_reserved : Number of reserved sockets on a shared node
        cores_reserved   : Number of cores reservend on a shared node

        Main attributes are set by the constructor and cannot be changed during the object lifetime.
        """

        if sockets_per_node > hardware.SOCKETS_PER_NODE:
            msg = "ERREUR INTERNE "
            msg += str(sockets_per_node)
            msg += " > " 
            msg += str(hardware.SOCKETS_PER_NODE)
            print msg
            raise PlacementException(msg)
        if sockets_per_node < 0:
            self.sockets_per_node = hardware.SOCKETS_PER_NODE
        else:
            self.sockets_per_node = sockets_per_node
        
        self.hardware         = hardware
        self.sockets_reserved = self.sockets_per_node
        self.l_sockets        = None
        self.cores_per_socket = self.hardware.CORES_PER_SOCKET
        self.cores_per_node   = self.sockets_per_node * self.cores_per_socket
        self.cores_reserved   = self.cores_per_node
        self.m_cores          = None
        self.tasks            = tasks
        self.cpus_per_task    = cpus_per_task
        self.threads_per_core = self.__activateHyper(hyper)
        #print self.sockets_per_node,self.cores_per_socket,self.cores_per_node,self.threads_per_core

    def __setattr__(self,name,value):
        """ Initialize an attribute only if it does not already exist"""

        try:
            getattr(self,name)
            raise PlacementException("ERREUR INTERNE - Pas le droit de changer les attributs")
        except Exception:
            object.__setattr__(self,name,value)

    def __activateHyper(self,hyper):
        """ Start hyperthreading if possible and if necessary, and return the number of threads per physical core (1 or 2 on a Xeon)

        If hyperthreading is disabled in hardware configuration and if hyperthreading is necessary, an exception is raised
        """

        threads_per_core=1
        if hyper==True or (self.cpus_per_task*self.tasks>self.cores_reserved and self.cpus_per_task*self.tasks<=self.hardware.THREADS_PER_CORE*self.cores_reserved):
            if self.hardware.HYPERTHREADING:
                threads_per_core = self.hardware.THREADS_PER_CORE
            else:
                msg = "OUPS - l'hyperthreading n'est pas actif sur cette machine"
                raise PlacementException(msg)
        return threads_per_core

class Exclusive(Architecture):
    """Describe an exclusive node"""

    def __init__(self, hardware, cpus_per_task, tasks, hyper, sockets_per_node=-1):
        """ Build an object, initializing l_sockets, m_cores and other attributes

        Arguments:
        hardware            : The hardware
            tasks           : Number of tasks processes
            cpus_per_task   : Nombre de cpus per process
            hyper           : If False, no hyperthreading !
            sockets_per_node: Number of sockets per node, should be <= hardware.SOCKETS_PER_NODE 
        """

        Architecture.__init__(self, hardware, cpus_per_task, tasks, hyper, sockets_per_node)
        self.l_sockets = range(self.sockets_per_node)
        self.m_cores = None


class Shared(Architecture):
    def __init__(self, hardware, cpus_per_task, tasks, hyper, sockets_per_node=-1 ):
        """ Describe a node shared between users

        Arguments:
        hardware            : The hardware
            tasks           : Number of tasks processes
            cpus_per_task   : Nombre de cpus per process
            hyper           : If False, no hyperthreading !
            sockets_per_node: Number of sockets per node, should be <= hardware.SOCKETS_PER_NODE 

        Builds the l_sockets list from __detectSockets,which calls numactl --show
        """
        if sockets_per_node < 0:
            sockets_per_node = hardware.SOCKETS_PER_NODE
        Architecture.__init__(self, hardware, cpus_per_task, tasks, hyper, sockets_per_node )

        (self.l_sockets,self.m_cores) = self.__detectSockets()

        self.sockets_reserved = len(self.l_sockets)
        if self.m_cores != None:
            self.cores_reserved = 0
            for s in self.m_cores:
                for c in self.m_cores[s]:
                    if self.m_cores[s][c]:
                        self.cores_reserved += 1
        else:
            self.cores_reserved   = self.cores_per_socket * self.sockets_reserved


    def __detectSockets(self):
        """ Detect and return as a list of available sockets and cores 

        l_sockets is a list of integers
        m_cores is a dictionary: key is the core number, value is a boolean

        """

        l_sockets = []
        m_cores   = {}

        # mpi_aware context: numactl was already called, the result is stored to PLACEMENT_PHYSCPU
        if 'PLACEMENT_NODE' in os.environ:
            l_sockets = map(int,os.environ['PLACEMENT_NODE'].split(','))
            if 'PLACEMENT_PHYSCPU' not in os.environ:
                msg = "OUPS "
                msg += "Erreur - PLACEMENT_NODE est défini mais PAS PLACEMENT_PHYSCPU - Avez-vous appelé auparavant placement --make_mpi_aware ?"
                raise PlacementException(msg)
            physcpubind = map(int,os.environ['PLACEMENT_PHYSCPU'].split(','))

        # debug mode: do not call numactl, read pseudo-reserved sockets and cores from an environment variable
        elif 'PLACEMENT_DEBUG' in os.environ:
            [l_sockets,physcpubind] = self.__callDebug()

        # Not in an mpi_aware context, no debug: we call numactl --show 
        else:
            [l_sockets,physcpubind] = self.__callNumactl()

        # generating m_cores from l_sockets and physcpubind
        for s in l_sockets:
            cores={}
            for c in range(self.cores_per_socket):
                c1 = c + s*self.cores_per_socket
                cores[c1] = c1 in physcpubind
            m_cores[s] = cores

        # Checking there is not incoherency
        if len(l_sockets) > self.sockets_per_node:
            msg  = "OUPS - sockets_per_node=" + str(self.sockets_per_node)
            msg += " should be at least " +  str(len(l_sockets))
            msg += " Please check switch -S"
            raise PlacementException(msg)

        for s in l_sockets:
            if len(m_cores[s]) != self.cores_per_socket:
                msg  = "OUPS - cores_per_socket=" + str(self.cores_per_socket)
                msg += " should be equal to " +  str(m_cores[s])
                msg += " Check the switch -S"
                raise PlacementException(msg)

        return [l_sockets,m_cores]


    def __callNumactl(self): 
        """Call numactl, detecting reserved sockets and physical cores
           return the list of reserved sockets, and the list of physical cores  """

        cmd = "numactl --show"
        p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        p.wait()
        # Si returncode non nul, on a probablement demandé une tâche qui ne tourne pas
        if p.returncode !=0:
            msg = "OUPS "
            msg += "Erreur numactl - peut-être n'êtes-vous pas sur la bonne machine ?"
            raise PlacementException(msg)
        else:
            output = p.communicate()[0].split('\n')

            # l_sockets is generated from line nodebind of numactl
            # nodebind: 4 5 6 => [4,5,6]
            for l in output:
                if l.startswith('nodebind:'):
                    l_sockets = map(int,l.rpartition(':')[2].strip().split(' '))
                elif l.startswith('physcpubind:'):
                    physcpubind = map(int,l.rpartition(':')[2].strip().split(' '))
                
            return [l_sockets,physcpubind]


    def __callDebug(self):
        """ Read the env variable PLACEMENT_DEBUG and return the list of reserved sockets, and the list of physical cores
            Possible values for PLACEMENT_DEBUG: 
              '[0-3]' Sockets 0 to 3, all cores
              '[0,1]:[0-5,20,21]  Sockets 0,1, physical cores 0,1,2,3,4,5,20,21 """

        placement_debug = os.environ['PLACEMENT_DEBUG']
        part = placement_debug.partition(':')
        l_sockets   = map(int,compactString2List(part[0]))
        physcpubind = []
        if part[2] == '':
            for s in l_sockets:
                min_c = self.hardware.getSocket2CoreMin(s)
                for c in range(self.cores_per_socket):
                    physcpubind.append(min_c+c)
        else:
            physcpubind = map(int,compactString2List(part[2]))
        
        return [l_sockets,physcpubind]
