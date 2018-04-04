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

from exception import *
from utilities import *

#
# Réécrit le placement pour des ensembles de threads et de tâches
# Réécriture matricielle, une colonne par cœur et une ligne par thread
#
# Params: archi (l'architecture processeurs)
#         ppsr_min, ppsr_max = Les cœurs limites (physiques)
# Return: la chaine de caracteres pour affichage
#

class Matrix(object):
    """ Compute the placement in  matrix (1 col/core, 1 line/thread) for sets of running threads 
        This representation is used ONLY with the option --check, to check running jobs
    """

    def __init__(self,archi,ppsr_min=-1,ppsr_max=-1):
        """ Parameters: archi    = The object Architecture found
                        ppsr_min = The min used core number 
                        ppsr_max = The max used core number (useful if not all sockets are used by the job, as we do not draw all sockets)
        """
        self.__hard  = archi.hardware
        self.__archi = archi
        if ppsr_min < 0:
            self.__ppsr_min = 0
            self.__ppsr_max = archi.sockets_per_node * archi.cores_per_socket - 1
        else:
            # We correct ppsr_min and ppsr_max to sockets boundaries
            self.__socket_min = self.__hard.getCore2Socket(ppsr_min)
            self.__socket_max = self.__hard.getCore2Socket(ppsr_max)
            self.__ppsr_min = self.__hard.getSocket2CoreMin(self.__socket_min)
            self.__ppsr_max = self.__hard.getSocket2CoreMax(self.__socket_max)

        self.__last_pid = 0

    def getHeader(self,h_header=15*' '):
        '''Return a header with psr nb displayed on 3 lines (must be < 999 !)'''

        self.__last_pid = 0
        rvl = ''

        # Ligne 1 = les centaines
        rvl += h_header
        for p in range(self.__ppsr_min,self.__ppsr_max+1):
            if self.__hard.getCore2Core(p)==0:
                rvl += ' '
            rvl += str(p/100)
        rvl += '\n'

        # Ligne 2 = les dizaines
        rvl += h_header
        for p in range(self.__ppsr_min,self.__ppsr_max+1):
            if self.__hard.getCore2Core(p)==0:
                rvl += ' '
            rvl += str((p%100)/10)
        rvl += '\n'

        # Ligne 3 = les unités
        rvl += h_header
        for p in range(self.__ppsr_min,self.__ppsr_max+1):
            if self.__hard.getCore2Core(p)==0:
                rvl += ' '
            rvl += str(p%10)
#        rvl += '  %CPU %MEM'
        rvl += '\n'
        return rvl


    def getHeader1(self,h_header=15*' '):
        '''Return a header with left and right column labels'''

        self.__last_pid = 0
        rvl = '     PID    TID'

        # Skip columns
        n_cores   =  self.__ppsr_max-self.__ppsr_min+1
        n_sockets =  self.__socket_max-self.__socket_min+1
        n_blanks  =  n_cores + n_sockets
        rvl       += n_blanks*' '

        # Right column label
        rvl += '  %CPU %MEM'
        rvl += '\n'
        return rvl

    def getNumamem(self,sockets_mem,mem_proc=True):
        """ Return a line describing memory occupation of the sockets, sockets_mem describes the memory used per task and per socket 
            if mem_dist==False we show the memory occupation relative to each memory socket
            if mem_dist==True  we show the %age memory occupation on each socket, related to the process memory
            This difference may be important is the memory footprint is low
        """
        
        mem_pid_socket = self.__getMemPidSocket(sockets_mem,mem_proc)

        h_header='   DISTRIBUTION of the MEMORY among the sockets '
        
        rvl =  h_header
        rvl += "\n"
        #rvl += "                ";
        #rvl += self.__hard.SOCKETS_PER_NODE*(self.__hard.CORES_PER_SOCKET+1)*' '
        #rvl += "  DISTRIBUTION\n"
        
        tags = mem_pid_socket.keys()
        tags.sort()
        for tag in tags:
            val = mem_pid_socket[tag]
            rvl += tag
            rvl += ' ' * 15;
            for v in val:
                rvl += getGauge(v,self.__hard.CORES_PER_SOCKET)
                rvl += ' '
            rvl += '  '
            for v in val:
                rvl += str(v)
                rvl += '%  '
            
            rvl += "\n"

        rvl += "\n"

        return rvl

    def getGpuInfo(self,tasks_binding):
        """ return a string, representing the status of the gpus connected to the sockets"""

        rvl = ""
        gpus_info = tasks_binding.gpus_info
        #print (gpus_info)
        
        col_skipped = ''
        for s in gpus_info:
            for g in s:
                rvl += '  '
                rvl += 'GPU ' + str(g['id']) + "\n"
                rvl += 'USE             ' + col_skipped + getGauge(g['U'],self.__hard.CORES_PER_SOCKET) + ' ' + str(g['U']) + "%\n"
                rvl += 'MEMORY          ' + col_skipped + getGauge(g['M'],self.__hard.CORES_PER_SOCKET) + ' ' + str(g['M']) + "%\n"
                rvl += 'POWER           ' + col_skipped + getGauge(g['P'],self.__hard.CORES_PER_SOCKET) + ' ' + str(g['P']) + "%\n"
                rvl += "\n"
            col_skipped += ' '*(self.__hard.CORES_PER_SOCKET+1)
                
        return rvl
        
        
    def __getGpuInfo_S(self,tasks_binding):
        """ return a string, representing the status of the gpus connected to the sockets"""
        
        gpus_info = tasks_binding.gpus_info
        rvl    = "\nGPUS INFO:"
        i = 0
        j = tasks_binding.archi.cores_per_socket + 1
        k = 0
        for s in gpus_info:
            for g in s:
                if k==0:
                    rvl += 6*' ' + j*i*' '
                    k+=1
                else:
                    rvl += 16*' ' + j*i*' '
                rvl += str(g['id'])+'-'+'U'+str(g['U'])+'%-M'+str(g['M'])+'%-C'+str(g['P'])+'%'+"\n"
            i += 1
        return rvl

    def __getMemPidSocket(self,sockets_mem,mem_proc):
        """ Compute a NEW dict of arrays: 
                 - Key is a process tag
                 - Value is an array: 
                         if mem_proc==False: the quantity of memory used per socket, in %/memory atached to the socket. 
                                            0 if permission problem
                         if mem_proc==True:  the distribution of memory among sockets, in %. 
                                            0 if permission problem """

        # Create and fill the processes dictionary with absolute values        
        processes = {}
        mem_p_proc= {} # key = tag, val = the total mem used by this process
        for sm in sockets_mem:
            for tag,val in sm.iteritems():
                if not tag in processes:
                    processes[tag] = []
                if not tag in mem_p_proc:
                    mem_p_proc[tag] = 0
                processes[tag].append(val)
                mem_p_proc[tag] += val
         
        for tag,val in processes.iteritems():
            if mem_proc:
                processes[tag] = map(lambda x: int(100.0*x/mem_p_proc[tag]),val)
            else:
                processes[tag] = map(lambda x: int(100.0*x/self.__hard.MEM_PER_SOCKET),val)
                    
        return processes

    def getLine(self,pid,tid,ppsr,S,H,cpu=100,mem='-'):
        """ Return a line full of '.' and a letter on the psr coloumn, plus cpu occupation at end of line"""

        if (ppsr<self.__ppsr_min or ppsr>self.__ppsr_max):
            raise PlacementException("INTERNAL ERROR - psr ("+str(ppsr)+") should belong to ["+str(self.__ppsr_min)+','+str(self.__ppsr_max)+"]")

        space = "."
        fmt1  = '{:6d}'
        fmt2  = '{:5.1f}'
        pre = H[0] + ' '
        if (pid != self.__last_pid):
            self.__last_pid = pid
            pre += fmt1.format(pid) + ' ' + fmt1.format(tid)
        else:
            pre += 7 * ' ' + fmt1.format(tid)

        socket= self.__hard.getCore2Socket(ppsr)
        core  = self.__hard.getCore2Core(ppsr)

        # Les colonnes vides avant le coeur concerne
        debut = self.__blankBeforeCore(socket,core)
        
        # Les colonnes vides après le coeur concerne
        fin   = self.__blankAfterCore(socket,core)

        # Les infos de %cpu et %mem
        cpumem = fmt2.format(cpu)
        if mem=='-':
            cpumem += '    -'
        else:
            cpumem += fmt2.format(mem)

        return pre + ' ' + debut + red_foreground() + S[0] + normal() + fin + cpumem + '\n'

    def __blankBeforeCore(self,socket,core):
        space = '.'
        bgn = ''
        for s in range(self.__socket_min,socket):
            bgn += self.__hard.CORES_PER_SOCKET * space
            bgn += ' '
        for c in range(0,core):
            bgn += space
        return bgn
        
    def __blankAfterCore(self,socket,core):
        space = '.'
        end   = ''
        for c in range(core+1,self.__hard.CORES_PER_SOCKET):
            end += space
        end += ' '
        for s in range(socket+1,self.__socket_max+1):
            end += self.__hard.CORES_PER_SOCKET * space
            end += ' '
        return end
