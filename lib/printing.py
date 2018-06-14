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
from decimal import Decimal
from running import *
from matrix import *
from utilities import *
from exception import *
import itertools
from socket import gethostname

class PrintingFor(object):
    """ Base class, all PrintingFor classes extend this class

    o = PrintingForxxx(tasks_binding)
    print o
"""
    # This is a STATIC property, use it with PrintingFor.__warn_printed !
    # Avoid printing the warning several times, even if we use several PrintingFor objects !
    __warn_printed = False
    
    def __init__(self,tasks_binding):
        self._tasks_binding = tasks_binding
        
    # If self._tasks_binding is an instance of Running, warn if there is overlap
    def _warnOverlap(self):
        warn = ""
        if PrintingFor.__warn_printed:
            return warn

        if not isinstance(self._tasks_binding,RunningMode):
            return warn

        # If overlap, print a warning !
        try:
            overlap = self._tasks_binding.overlap
            if len(overlap)>0:
                warn += "WARNING - FOLLOWING TASKS ARE OVERLAPPING !\n"
                warn += "===========================================\n"
                warn += str(overlap)
                warn += "\n\n"
            PrintingFor.__warn_printed = True
            
        except AttributeError:
            pass
        
        return warn

    def __str__(self):
        return "INTERNAL ERROR - ABSTRACT CLASS !!!!!"


class PrintingForSrun(PrintingFor):
    """ Printing for srun 

    # placement 4 4 --srun
    --cpu_bind=mask_cpu:0xf,0xf0,0x3c00,0x3c000
    """

    def __str__(self):
        return self.__getCpuBinding(self._tasks_binding.archi,self._tasks_binding.tasks_bound)

    def __getCpuBinding(self,archi,tasks_bound):
        """ Call __GetCpuTaskBinding for each task, concatene and return """

        mask_cpus=[]
        for t in tasks_bound:
            mask_cpus += [self.__getCpuTaskBinding(archi,t)]

        return "--cpu_bind=mask_cpu:" + ",".join(mask_cpus)


    def __getCpuTaskBinding(self,archi,cores):
        """ Return string, representing the core positions in hexa coding for srun

        Arguments:
        archi = An object deriving from Architecture
        cores = A list of integers, representing the cores (physical + logical)
        """

        i = 1
        rvl = 0
        for j in range(archi.cores_per_node*archi.threads_per_core):
            if (j in cores):
                rvl += i
            i = 2 * i
        rvl = str(hex(rvl))
    
        # remove the final 'L', useful when there are many many cores
        return rvl.rstrip('L')



class PrintingForHuman(PrintingFor):
    """ Printing for a human being

    # placement 4 4 --human
    [ 0 1 2 3 ]
    [ 4 5 6 7 ]
    [ 10 11 12 13 ]
    [ 14 15 16 17 ]
    """

    def __str__(self):
        return self.__getCpuBinding(self._tasks_binding.archi,self._tasks_binding.tasks_bound)

    def __getCpuBinding(self,archi,tasks_bound):
        """ Call __GetCpuTaskBinding for each task, concatene and return """

        rvl = ""
        for t in tasks_bound:
            rvl += self.__getCpuTaskBinding(archi,t)
        return rvl

    def __getCpuTaskBinding(self,archi,cores):
        """ Return a list of cores written as a string """

        rvl="[ "
        sorted_cores = cores
        sorted_cores.sort()
        for c in sorted_cores:
            rvl+=str(c)
            rvl += ' '
        rvl+="]\n"
        return rvl



class PrintingForAsciiArt(PrintingFor):
    """ Printing for an artist, ie a special human being

    # placement 4 4 --ascii-art
    S0-------- S1-------- 
  P AAAABBBB.. CCCCDDDD.. 
    """

    def __str__(self):
        rvl = self._warnOverlap()

        if self._tasks_binding.tasks > 296:
            rvl += "ERROR - AsciiArt representation unsupported if more than 296 tasks !"
        else:
            rvl += self.__getCpuBinding(self._tasks_binding.archi,self._tasks_binding.tasks_bound,self._tasks_binding.over_cores)
        return rvl


    def __getCpuBinding(self,archi,tasks_bound,over_cores=None):
        """ Return a graphics more or less representing the sockets """

        char=ord('A')

        # A list of cores, prefilled with '.'
        cores=[]
        for s in range(archi.sockets_per_node):
            if s in archi.l_sockets:
                to_app = '.'
            else:
                to_app = ' '
            for t in range(archi.threads_per_core):
                for c in range(archi.cores_per_socket):
                    cores.append(to_app)

        # Fill the cores array with a letter, 1 letter / task
        nt=0
        for t in tasks_bound:
            for c in t:
                if over_cores!=None and c in over_cores:
                    cores[c] = '#'
                else:
                    cores[c] = numTaskToLetter(nt)
            nt += 1

        # For an SMP machine full of sockets, like the sgi uv, we display the sockets by groups of 8
        rvl = ""
        for gs in range(0,archi.sockets_per_node,8):
            rvl += "  "
            for s in range(gs,min(gs+8,archi.sockets_per_node)):
                rvl += 'S'
                rvl += str(s)
                cmin = 2
                if s>=10:
                    cmin=3
                for c in range(archi.cores_per_socket):
                    if c<cmin:
                        continue
                    else:
                        rvl += '-'
                rvl += ' '
            rvl += '\n'

            for l in range(archi.threads_per_core):
                if l==0:
                    rvl += "P "
                else:
                    rvl += "L "

                for s in range(gs,min(gs+8,archi.sockets_per_node)):
                    for c in range(archi.cores_per_socket):
                        rvl += cores[l*archi.cores_per_node+s*archi.cores_per_socket+c]
                    rvl += ' '
                rvl += '\n'
    
        return rvl


class PrintingForIntelAff(PrintingFor):
    """ Printing for the intel environment variable KMP_AFFINITY (ONLY if 1 task) 

    # placement 1 6 --intel_affinity
    export KMP_AFFINITY="granularity=fine,explicit,proclist=[0, 1, 2, 10, 11, 12]"

    """

    def __init__(self,tasks_binding,verbose):
        PrintingFor.__init__(self,tasks_binding)
        self.__verbose = verbose

    def __str__(self):
        if len(self._tasks_binding.tasks_bound) > 1:
            return "ERROR - KMP_Affinity representation impossible if more than 1 task !"
        else:
            rvl  = 'export KMP_AFFINITY="granularity=fine,explicit,proclist=';
            rvl += self.__getCpuBinding(self._tasks_binding.tasks_bound);
            if self.__verbose:
                rvl += ',verbose';
            rvl += '"';
            return rvl

    def __getCpuBinding(self,tasks_bound):
        return str(tasks_bound[0])



class PrintingForGnuAff(PrintingFor):
    """ Printing for the GNU environment variable GOMP_AFFINITY (ONLY if 1 task) 

    # placement 1 6 --gnu_affinity
    export GOMP_AFFINITY="0 1 2 10 11 12"

    """

    def __init__(self,tasks_binding,verbose):
        PrintingFor.__init__(self,tasks_binding)
        self.__verbose = verbose

    def __str__(self):
        if len(self._tasks_binding.tasks_bound) > 1:
            return "ERROR - Gnu_Affinity representation impossible if more than 1 task !"
        else:
            rvl  = 'export GOMP_CPU_AFFINITY="';
            rvl += self.__getCpuBinding(self._tasks_binding.tasks_bound);
            rvl += '"';
            return rvl

    def __getCpuBinding(self,tasks_bound):
        return ' '.join(map(str,tasks_bound[0]))


class PrintingForNumactl(PrintingFor):
    """ Printing for numactl command:

    # placement 2 6 --numactl
    --physcpubind=0-5,10-15
    """

    def __str__(self):
        return self.__getCpuBinding(self._tasks_binding.archi,self._tasks_binding.tasks_bound)


    def __getCpuBinding(self,archi,tasks_bound):
        """ Call __GetCpuTaskBinding for each task, concatene and return """

        cpus=[]

        sorted_tasks_bound=list(tasks_bound)
        sorted_tasks_bound.sort()

        for t in sorted_tasks_bound:
            cpus += [list2CompactString(t)]

        return "--physcpubind=" + ",".join(cpus)
  
class PrintingForMatrixThreads(PrintingFor):
    """ Printing the (running) threads in a matrix """

    __show_idle              = False
    __sorted_threads_cores   = False
    __sorted_processes_cores = False
    __print_numamem          = False
    def SortedThreadsCores(self):
        self.__sorted_threads_cores = True
    def SortedProcessesCores(self):
        self.__sorted_processes_cores = True
    def ShowIdleThreads(self):
        self.__show_idle = True

    # mem_proc if True, display memory occupation/sockets relative to the process memory
    #          if False, display memory occupation/sockets relative to the socket memory
    def PrintNumamem(self,mem_proc=True):
        self.__print_numamem = True
        self.__mem_proc = mem_proc

    def __str__(self):
        '''Convert to a string (-> print) '''
        
        rvl = self._warnOverlap()
        if self._tasks_binding.tasks > 296:
            rvl += "ERROR - Threads representation is not supported if more than 296 tasks !"
        else:
            rvl += gethostname()
            rvl += '\n'
            # Print cpu binding, memory info and gpu info
            rvl += self.__getCpuBinding(self._tasks_binding)
            
        return rvl

    def __getCpuBinding(self,tasks_binding):
        """ return a string, representing sets of threads and tasks in a matrix representation, used only for running tasks

        1 column/PHYSICAL core, 1 line/process
        Physical and logical cores are on the same column

        Arguments:
        archi         = An object deriving from Architecture
        threads_bound = A dictionary containing a lot of data about each running task, see running.py for details
        """

        archi         = tasks_binding.archi
        threads_bound = tasks_binding.threads_bound
        gpus_info     = tasks_binding.gpus_info
        
        # For each task in threads_bound, compute the ppsr_min and ppsr_max, ie the min and max physical cores
        ppsr_min = 999999
        ppsr_max = 0
        for pid in list(threads_bound.keys()):
            p_ppsr_min = 9999
            threads = threads_bound[pid]['threads']

            for tid in threads:
                ppsr = threads[tid]['ppsr']
                if ppsr_min>ppsr:
                    ppsr_min=ppsr
                if p_ppsr_min>ppsr:
                    p_ppsr_min=ppsr
                if ppsr_max<ppsr:
                    ppsr_max=ppsr
                    
            threads_bound[pid]['ppsr_min'] = p_ppsr_min

        # If memory printing, or gpu_info, consider the whole machine
        if self.__print_numamem or gpus_info != None:
            ppsr_min = 0
            ppsr_max = archi.sockets_per_node * archi.cores_per_node - 1

        # First, create a Matrix and print the header
        m = Matrix(archi,ppsr_min,ppsr_max)
        rvl = ''
        rvl += m.getHeader()

        # Print a second header line
        rvl += m.getHeader1()

        # Printing the body
        # Sort threads_bound, on processes or on threads
        if self.__sorted_processes_cores:
            sorted_processes = sorted(iter(threads_bound.items()),key=lambda k_v1:(k_v1[1]['ppsr_min'],k_v1[0]))
        else:
            sorted_processes = sorted(threads_bound.items())

        # Print one line/thread
        for (pid,thr) in sorted_processes:
            l = threads_bound[pid]['tag']
            threads = threads_bound[pid]['threads']
            if self.__sorted_threads_cores:
                sorted_threads = sorted(iter(threads.items()),key=lambda k_v:(k_v[1]['ppsr'],k_v[0]))
            else:
                sorted_threads = sorted(threads.items())

            for (tid,thr) in sorted_threads:
                if not self.__show_idle and threads[tid]['state'] != 'R':
                    continue
                if thr['state'] == 'R':
                    S = l
                elif thr['state'] == 'S':
                    S = '.'
                else:
                    S = '?'
                if 'mem' in thr:
                    rvl += m.getLine(pid,tid,threads[tid]['ppsr'],S,l,threads[tid]['cpu'],threads[tid]['mem'])
                else:
                    rvl += m.getLine(pid,tid,threads[tid]['ppsr'],S,l,threads[tid]['cpu'])

        # If wanted, print 1 line / process about memory allocation
        if self.__print_numamem:
            sockets_mem = self.__compute_memory_per_socket(archi,threads_bound)
            rvl += "\n"
            rvl += m.getNumamem(sockets_mem)
 
        # If wanted, print info about the gpus
        if self._tasks_binding.gpus_info != None:
            rvl += m.getGpuInfo(self._tasks_binding)
                  
        return rvl


    def __compute_memory_per_socket(self,archi,threads_bound):
        """ return a data structure representing the memory occupation of each task on each socket:
        
        Arguments:
        archi         (contains the information about sockets)
        threads_bound (contains the information about memory occupation)

        Return sockets_mem: A list of dictionaries: 
                            for each socket, a dict
                                key   : process tag ('A','B',...)
                                value : memory used by this task on the socket  
                            
        """

        sockets = list(range(0,archi.hardware.SOCKETS_PER_NODE))
        sockets_mem = []
        for s in sockets:
            sockets_mem.append({})

        for pid in threads_bound:
            tag     = threads_bound[pid]['tag']
            numamem = threads_bound[pid]['numamem']
            for s in sockets:
                sockets_mem[s][tag]=numamem[s]

        return sockets_mem

class PrintingForSummary(PrintingFor):

    __show_depop = False
    __cpu_thr    = 50      # cpu use default threshold
    __mem_thr    = 80      # mem threshold     
    __verbose    = False
    
    def ShowDepopulated(self):
        self.__show_depop = True
    def SetCpuThreshold(self,thr):
        self.__cpu_thr = thr
    def SetMemThreshold(self,thr):
        self.__mem_thr = thr
    def setVerbose(self):
        self.__verbose = True
    def __isOverlap(self):
        '''return True if two threads are overlapping (same logical core)'''
        return len(self._tasks_binding.overlap) > 0
        
    def _isHyperUsed(self):
        '''return true if this job uses hyperthreading'''
        flat_cores = list(itertools.chain.from_iterable(self._tasks_binding.tasks_bound))
        
        return self._tasks_binding.hardware.isHyperThreadingUsed(flat_cores)

    def _getUse(self,hyper):
        '''return sum(cpu-usages) / nb_of_cores
           nb_of_cores depends of hyper status'''
        #processes = self._tasks_binding.pid
        threads   = self._tasks_binding.threads_bound
        
        cpu      = 0.0
        running  = 0
        total    = 0
        mem=0.0
        
        for pid,p in threads.items():
            mem += float(p['mem'])
            if p['R']:    # If the process is running
                for tid,t in p['threads'].items():
                    cpu += float(t['cpu'])
                    if t['state'] == 'R':
                        running += 1
                    total += 1
                            
        if hyper:
            nb_of_cores = self._tasks_binding.hardware.CORES_PER_NODE * self._tasks_binding.hardware.THREADS_PER_CORE
        else:
            nb_of_cores = self._tasks_binding.hardware.CORES_PER_NODE

        cpu = int(cpu // nb_of_cores)
        run = int( (100 * running) / total )
        return [ cpu, run, mem ]
        
    def __str__(self):
        if not isinstance(self._tasks_binding,RunningMode):
            return "ERROR - The switch --summary can be used ONLY with --check"
        
        summary = ""
        if self.__verbose:
            summary += "Pathological status of the job:\n"
            summary += "0.1:N:N:80:50:90 \n"
            summary += "  | | |  |  |  \_ Memory allocated by the tasks (max = 100%)\n"
            summary += "  | | |  |  \____ Part of the threads in state Running at poll time % (max = 100%)\n"
            summary += "  | | |  \_______ Total cpu used by the threads since start of job (max = 100%)\n"
            summary += "  | | \__________ Hyper threading used ? N = no, H = yes\n"
            summary += "  | \____________ Overlap status N = normal, O = Overlap\n"
            summary += "  \______________ Time to poll the node (s)\n\n"

        summary += gethostname()
        summary += ' '

        overlap = self.__isOverlap()
        hyper   = self._isHyperUsed()
        use     = self._getUse(hyper)

        #warning = overlap or use[0] < 50 or use[1] < 20 or use[2] > 80.0 or self._tasks_binding.duration > 10.0
        warning = overlap or self._tasks_binding.duration > 10.0

        if self.__show_depop:
            warning = warning or use[0]<self.__cpu_thr or use[2]>self.__mem_thr
        
        # Hide jobs for which we have LOW cpu use but HIGH memory allocation: this is not a pathological case, this is just a depopulated job
        else:
            warning = warning or ((use[0]<self.__cpu_thr) ^ (use[2]>self.__mem_thr))  # If cpu use low AND memory high, it is NOT pathological, no warning

        if warning:
            summary += AnsiCodes.red_foreground()

        summary += str(round(Decimal(str(self._tasks_binding.duration)),1))
        summary += ':'
        
        if overlap:
            summary += 'O'
        else:
            summary += 'N'
        summary += ':'
        
        if hyper:
            summary += 'H'
        else:
            summary += 'N'
        summary += ':'

        summary += str(use[0])
        summary += ':'
        summary += str(use[1])
        summary += ':'
        summary += str(int(round(Decimal(str(use[2])),0)))

        gpus_info = self._tasks_binding.gpus_info
        if gpus_info != None:
            for s in gpus_info:
                for g in s:
                    summary += ':'
                    summary += str(g['U']) + ':'
                    summary += str(g['M']) + ':'
                    summary += str(g['P'])

        if warning:
            summary += ' W'
            summary += AnsiCodes.normal()
        
        return summary

class PrintingForCsv(PrintingFor):
    def __getUse(self,hyper=True):
        '''return cpu use for each physical core - Return an array, sorted in core number'''

        threads   = self._tasks_binding.threads_bound

        cores={}
        mem=0.0
        for pid,p in threads.items():
            mem += float(p['mem'])
            if p['R']:    # If the process is running
                for tid,t in p['threads'].items():
                    use  = float(t['cpu'])
                    core = int(t['ppsr'])              # Using physical psr, ie cumulating core threads (hyperthreading)
                    if t['state'] == 'R':
                        cpu  = float(t['cpu'])
                    else:
                        cpu = 0.0
                    if core in cores:
                        cores[core] += cpu
                    else:
                        cores[core] = cpu
        
        core_use=[]
        nb_of_cores = self._tasks_binding.hardware.CORES_PER_NODE
        for c in range(nb_of_cores):
            if c in cores:
                core_use.append(cores[c])
            else:
                core_use.append(0)
        core_use.append(mem)
        
        return core_use

    def __str__(self):
        if not isinstance(self._tasks_binding,RunningMode):
            return "ERROR - The switch --csv can be used ONLY with --check"

        core_use = self.__getUse()

        csv = ','.join(map(str,core_use))
        csv += ','

        gpus_info = self._tasks_binding.gpus_info
        if gpus_info != None:
            for s in gpus_info:
                for g in s:
                    csv += str(g['U']) + ','
                    csv += str(g['M']) + ','
                    csv += str(g['P']) + ','

        return csv
        
class PrintingForVerbose(PrintingFor):
    """ Printing more information ! """

    def __str__(self):
        if not isinstance(self._tasks_binding,RunningMode):
            return "ERROR - The switch --verbose can be used ONLY with --check"
        else:
            return self._tasks_binding.PrintingForVerbose()
