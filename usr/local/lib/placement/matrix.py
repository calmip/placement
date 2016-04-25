#! /usr/bin/env python
# -*- coding: utf-8 -*-

#import os
from exception import *
from utilities import *
#from itertools import chain,product



#
# Réécrit le placement pour des ensembles de threads et de tâches
# Réécriture matricielle, une colonne par cœur et une ligne par thread
#
# Params: archi (l'architecture processeurs)
#         ppsr_min, ppsr_max = Les cœurs limites (physiques)
# Return: la chaine de caracteres pour affichage
#

class Matrix(object):
    def __init__(self,archi,ppsr_min=-1,ppsr_max=-1):
        self.__hard  = archi.hardware
        self.__archi = archi
        if ppsr_min < 0:
            self.__ppsr_min = 0
            self.__ppsr_max = archi.sockets_per_node * archi.cores_per_socket - 1
        else:
            # Partir toujours au premier core d'un socket jusqu'au dernier core
            #            c = self.__hard.getCore2Core(psr_min)
            self.__socket_min = self.__hard.getCore2Socket(ppsr_min)
            self.__socket_max = self.__hard.getCore2Socket(ppsr_max)
            self.__ppsr_min = self.__hard.getSocket2CoreMin(self.__socket_min)
            self.__ppsr_max = self.__hard.getSocket2CoreMax(self.__socket_max)

        self.__last_pid = 0

    def getHeader(self,h_header=15*' '):
        '''Renvoie un header avec le numéro des psr sur trois lignes (<999 !)'''
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

        # Ligne 3 = les unités + %cpu
        rvl += h_header
        for p in range(self.__ppsr_min,self.__ppsr_max+1):
            if self.__hard.getCore2Core(p)==0:
                rvl += ' '
            rvl += str(p%10)
        rvl += '  %CPU %MEM'
        rvl += '\n'
        return rvl

    # imprime une ligne pour l'occupation mémoire des sockets
    def getNumamem(self,sockets_mem,h_header=15*' '):
        space = "."
        sockets_mem_rel = self.getMem2Slice(sockets_mem)
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

    # convertit le tableau d'occupation de la mémoire en "slices", prets pour affichage
    def getMem2Slice(self,sockets_mem):
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
        '''Renvoie une ligne pleine de blancs avec H en colonne 0 et S sur la colonne ppsr, et cpu sur la colonne adhoc'''
        # if ppsr > self.__ppsr_max and self.__archi.threads_per_core == 2:
        #    ppsr -= self.__archi.cores_per_node
        if (ppsr<self.__ppsr_min or ppsr>self.__ppsr_max):
            raise PlacementException("ERREUR INTERNE - psr ("+str(ppsr)+") devrait appartenir à ["+str(self.__ppsr_min)+','+str(self.__ppsr_max)+"]")

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
