#! /usr/bin/env python
# -*- coding: utf-8 -*-

#import os
#from exception import *
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
    def __init__(self,psr_min,psr_max):
        self.__psr_min = psr_min
        self.__psr_max = psr_max
        self.__last_pid = 0

    def getHeader(self,h_header=16*' '):
        '''Renvoie un header avec le numéro des psr sur trois lignes (<999 !)'''
        self.__last_pid = 0
        rvl = ''
        # Ligne 1 = les centaines
        rvl += h_header
        for p in range(self.__psr_min,self.__psr_max+1):
            #rvl += getBlankOrDigit(p/100,p<100)
            rvl += str(p/100)
        rvl += '\n'

        # Ligne 2 = les dizaines
        rvl += h_header
        for p in range(self.__psr_min,self.__psr_max+1):
            #        rvl += getBlankOrDigit((p%100)/10,p<10)
            rvl += str((p%100)/10)
        rvl += '\n'

        # Ligne 3 = les unités + %cpu
        rvl += h_header
        for p in range(self.__psr_min,self.__psr_max+1):
            rvl += str(p%10)
        rvl += '  %CPU'
        rvl += '\n'
        return rvl

    def getLine(self,pid,tid,psr,S,H,cpu=100):
        '''Renvoie une ligne pleine de blancs avec H en colonne 0 et S sur la colonne psr, et cpu sur la colonne adhoc'''
        if (psr<self.__psr_min or psr>self.__psr_max):
            raise PlacementException("ERREUR INTERNE - psr devrait appartenir à ["+str(self.__psr_min)+','+str(self.__psr_max)+"]")

        fmt1  = '{:6d}'
        fmt2  = '{:5.1f}'
        pre = H[0] + ' '
        if (pid != self.__last_pid):
            self.__last_pid = pid
            pre += fmt1.format(pid) + ' ' + fmt1.format(tid)
        else:
            pre += 7 * ' ' + fmt1.format(tid)

        debut = (psr-self.__psr_min) * ' '
        fin   = (self.__psr_max-psr) * ' ' + ' ' + fmt2.format(cpu)
        return pre + ' ' + debut + S[0] + fin + '\n'

#def getBlankOrDigit(d,flg):
#    if d!=0 or flg==False:
#        return str(d)
#    else:
#        return ' '

