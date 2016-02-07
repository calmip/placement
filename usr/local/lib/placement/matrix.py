#! /usr/bin/env python
# -*- coding: utf-8 -*-

#import os
from exception import *
#from itertools import chain,product



#
# Réécrit le placement pour des ensembles de threads et de tâches
# Réécriture matricielle, une colonne par cœur et une ligne par thread
#
# Params: archi (l'architecture processeurs)
#         threads_bound (le tableau self.processus de la classe RunningMode, cf running.py)
# Return: la chaine de caracteres pour affichage
#

class Matrix(object):
    def __init__(self,archi,psr_min=-1,psr_max=-1):
        self.__archi = archi
        if psr_min < 0:
            self.__psr_min = 0
            self.__psr_max = archi.sockets_per_node * archi.cores_per_socket - 1
        else:
            # Partir toujours au premier core d'un socket jusqu'au dernier core
            #            c = self.__archi.getCore2Core(psr_min)
            self.__socket_min = self.__archi.getCore2Socket(psr_min)
            self.__socket_max = self.__archi.getCore2Socket(psr_max)
            self.__psr_min = self.__archi.getSocket2CoreMin(self.__socket_min)
            self.__psr_max = self.__archi.getSocket2CoreMax(self.__socket_max)

            # En cas d'hyperthreading, corriger psr_max et psr_min
            if self.__archi.threads_per_core == 2:
                # Si seuls les cœurs logiques sont utilisés...
                if self.__psr_min >= self.__archi.cores_per_node:
                    self.__psr_min -= self.__archi.cores_per_node
                    self.__socket_min -= self.__archi.sockets_per_node
                # @todo - un truc plus subtil
                if self.__psr_max > self.__archi.cores_per_node:
                    self.__psr_max    = self.__archi.cores_per_node - 1
                    self.__socket_max = self.__archi.sockets_per_node - 1

        self.__last_pid = 0

    def getHeader(self,h_header=15*' '):
        '''Renvoie un header avec le numéro des psr sur trois lignes (<999 !)'''
        self.__last_pid = 0
        rvl = ''
        # Ligne 1 = les centaines
        rvl += h_header
        for p in range(self.__psr_min,self.__psr_max+1):
            #rvl += getBlankOrDigit(p/100,p<100)
            if self.__archi.getCore2Core(p)==0:
                rvl += ' '
            rvl += str(p/100)
        rvl += '\n'

        # Ligne 2 = les dizaines
        rvl += h_header
        for p in range(self.__psr_min,self.__psr_max+1):
            #        rvl += getBlankOrDigit((p%100)/10,p<10)
            if self.__archi.getCore2Core(p)==0:
                rvl += ' '
            rvl += str((p%100)/10)
        rvl += '\n'

        # Ligne 3 = les unités + %cpu
        rvl += h_header
        for p in range(self.__psr_min,self.__psr_max+1):
            if self.__archi.getCore2Core(p)==0:
                rvl += ' '
            rvl += str(p%10)
        rvl += '  %CPU %MEM'
        rvl += '\n'
        return rvl

    def getLine(self,pid,tid,psr,S,H,cpu=100,mem='-'):
        '''Renvoie une ligne pleine de blancs avec H en colonne 0 et S sur la colonne psr, et cpu sur la colonne adhoc'''
        if psr > self.__psr_max and self.__archi.threads_per_core == 2:
            psr -= self.__archi.cores_per_node
        if (psr<self.__psr_min or psr>self.__psr_max):
            raise PlacementException("ERREUR INTERNE - psr ("+str(psr)+") devrait appartenir à ["+str(self.__psr_min)+','+str(self.__psr_max)+"]")

        fmt1  = '{:6d}'
        fmt2  = '{:5.1f}'
        pre = H[0] + ' '
        if (pid != self.__last_pid):
            self.__last_pid = pid
            pre += fmt1.format(pid) + ' ' + fmt1.format(tid)
        else:
            pre += 7 * ' ' + fmt1.format(tid)

        socket= self.__archi.getCore2Socket(psr)
        tekcos= self.__socket_max - socket
        socket= socket - self.__socket_min
        debut = (psr-self.__psr_min) * ' ' + socket * ' '
        if mem=='-':
            mem = '    -'
        else:
            mem = fmt2.format(mem)

        fin   = (self.__psr_max-psr) * ' ' + tekcos * ' ' + ' ' + fmt2.format(cpu) + mem
        return pre + ' ' + debut + S[0] + fin + '\n'

#def getBlankOrDigit(d,flg):
#    if d!=0 or flg==False:
#        return str(d)
#    else:
#        return ' '

