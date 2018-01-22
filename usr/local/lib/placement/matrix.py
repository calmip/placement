#! /usr/bin/env python
# -*- coding: utf-8 -*-

from exception import *
from utilities import *

#
# This file is part of PLACEMENT software
# PLACEMENT helps users to bind their processes to one or more cpu-cores
#
# PLACEMENT is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
#  Copyright (C) 2015,2016 Emmanuel Courcelle
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




#
# Réécrit le placement pour des ensembles de threads et de tâches
# Réécriture matricielle, une colonne par cœur et une ligne par thread
#
# Params: archi (l'architecture processeurs)
#         ppsr_min, ppsr_max = Les cœurs limites (physiques)
# Return: la chaine de caracteres pour affichage
#

class Matrix(object):
    """ Compute the placement in  matrix (1 col/core, 1 line/thread) for sets of running threads """

    def __init__(self,archi,ppsr_min=-1,ppsr_max=-1):
        self.__hard  = archi.hardware
        self.__archi = archi
        if ppsr_min < 0:
            self.__ppsr_min = 0
            self.__ppsr_max = archi.sockets_per_node * archi.cores_per_socket - 1
        else:
            # Partir toujours au premier core d'un socket jusqu'au dernier core
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

    def getNumamem(self,sockets_mem,mem_proc):
        """ Return a line describing memory occupation of the sockets, sockets_mem describes the memory used per task and per socket 
            if mem_dist==False we show the memory occupation relative to each memory socket
            if mem_dist==True  we show the %age memory occupation on each socket, related to the process memory
            This difference may be important is the memory footprint is low
        """
        
        mem_pid_socket = self.__getMemPidSocket(sockets_mem,mem_proc)
        space = "."

        h_header='  SOCKET MEMORY '
        if mem_proc:
            h_header += "relative to the process memory"
        else:
            h_header += "relative to the socket memory"
        
        rvl =  h_header
        rvl += "\n"
        #rvl += str(sockets_mem)
        #rvl += "\n"
        #rvl += str(mem_pid_socket)
        #return rvl
        
        
        
        
        #sockets_mem_rel = self.__getMem2Slice(sockets_mem,mem_proc)
        #rvl = h_header
        #rvl += "\n"
        #rvl += len(h_header)*' '+' '
        #rvl += str(sockets_mem)
        #rvl += "===================\n"
        #rvl += len(h_header)*' '+' '
        #rvl += str(sockets_mem_rel)
        #return rvl
        for tag,val in mem_pid_socket.iteritems():
            rvl += tag
            rvl += ' ' * 14;
            for m in val:
                rvl += ' '
                p = self.__hard.CORES_PER_SOCKET - m

                # Write m times the tag (ex: AAAA) in magenta
                if m>0:
                    rvl += mag_foreground()
                    rvl += '*'*m
                    rvl += normal()

                # Write p time a space in normal
                if p>0:
                    rvl += space*p
            rvl += "\n"

        return rvl


    def __getMem2Slice_OLD(self,sockets_mem,hide_small_memory):
        """ Compute slices for the memory consumption, they are ready to be displayed. 
            Return the same structure as sockets_mem, except that memory is counted in slices  """

        # mem_slice is the memory per core
        mem_slice = self.__hard.MEM_PER_SOCKET / self.__hard.CORES_PER_SOCKET
        sockets_mem_rel = []

        # for each socket
        for s in sockets_mem:
            s_r = {}

            # for each task
            for t in s.keys():
                m = int(s[t])
                q = m / mem_slice
                r = m % mem_slice
                if r <= mem_slice / 2:
                    s_r[t] = q
                else:
                    s_r[t] = q + 1
                if hide_small_memory==False and s_r[t] == 0:
                    s_r[t] = 1
            sockets_mem_rel.append(s_r)

        return sockets_mem_rel

    def __getMemPidSocket(self,sockets_mem,mem_proc):
        """ Compute a NEW dict of arrays: 
                 - Key is a process tag
                 - Value is an array: 
                         if mem_proc==False: the quantity of memory used per socket, counted in slices. 0 if permission problem
                         if mem_proc==True:  the distribution of memory among sockets, counted in slices. 0 if permission problem """
                                       

        # Create and fill the processes dictionary        
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
                
        # Replace absolute values with "slices"
        # mem_slice is the quantity of mem in a slice: 
        # calculated from the mem by core, ...
        if mem_proc == False:
            mem_slice = self.__hard.MEM_PER_SOCKET // self.__hard.CORES_PER_SOCKET
            mem_slice2= mem_slice // 2

        # ... or from the mem_by_proc (thus deferred)
        else:
            mem_slice  = 0
            mem_slice2 = 0

        for tag,val in processes.iteritems():
            slice_val = []
            if mem_proc:
                mem_slice = int(mem_p_proc[tag]) // self.__hard.CORES_PER_SOCKET
                mem_slice2= int(mem_p_proc[tag]) // 2
            for mem in val:
                s = int(mem) // mem_slice
                s1= int(mem) % mem_slice
                if s1>= mem_slice2:
                    s += 1
                slice_val.append(s)
            processes[tag] = slice_val

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
