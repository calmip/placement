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


    def getNumamem(self,sockets_mem,h_header='  SOCKET MEMORY'):
        """ Return a line describing memory occupation of the sockets """
        space = "."
        sockets_mem_rel = self.__getMem2Slice(sockets_mem)
        rvl = h_header
        for s in range(self.__socket_min,self.__socket_max+1):
            rvl += ' '
            i=0
            s_m = sockets_mem_rel[s]
            for t in s_m.keys():
                rvl += mag_foreground()
                for l in range(s_m[t]):
                    rvl += t
                    i += 1
                rvl += normal()
            for l in range(i,self.__hard.CORES_PER_SOCKET):
                rvl += space
        rvl += '\n'
        return rvl
        #return str(sockets_mem_rel)+'\n'


    def __getMem2Slice(self,sockets_mem):
        """ Compute slices for the memory consumption, they are ready to be displayed """

        mem_slice = self.__hard.MEM_PER_SOCKET / self.__hard.CORES_PER_SOCKET
        sockets_mem_rel = []

        for s in sockets_mem:
            s_r = {}
            for t in s.keys():
                m = int(s[t])
                q = m / mem_slice
                r = m % mem_slice
                if r <= mem_slice / 2:
                    s_r[t] = q
                else:
                    s_r[t] = q + 1
            sockets_mem_rel.append(s_r)

        return sockets_mem_rel

    def getLine(self,pid,tid,ppsr,S,H,cpu=100,mem='-'):
        """ Return a line fulll of '.' and a letter on the psr coloumn, plus cpu occupation at end of line"""

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

        # Les colonnes vides avant le cœur concerné
        debut = self.__blankBeforeCore(socket,core)
        
        # Les colonnes vides après le cœur concerné
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
