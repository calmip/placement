#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################
#
#  Hardware: Permet de décrire le hardware des machines
#            L'attribut IS_SHARED exprime le fait que la machine est "partagée", ou pas
#            C'est de la configuration, pas vraiment du hardware, mais c'est une donnée qui ne bouge jamais
#            pour une machine particulière, donc elle a bien sa place ici
#
################################################################

import os
from exception import *

class Hardware(object):
    def __init__(self):
        self.CORES_PER_NODE = self.CORES_PER_SOCKET*self.SOCKETS_PER_NODE

    NAME             = ''
    SOCKETS_PER_NODE = ''
    CORES_PER_SOCKET = ''
    HYPERTHREADING   = ''
    THREADS_PER_CORE = ''
    IS_SHARED        = ''

    @staticmethod
    def catalogue():
        return [ 'uvprod','eosmesca1','mesca','exclusive','shared', 'prolix' ]

    ####################################################################
    #
    # @brief Construit un objet à partir des variables d'environnement: SLURM_NODELIST, PLACEMENT_ARCHI, HOSTNAME
    #
    ####################################################################
    @staticmethod
    def factory():
        # Construction de la partition shared
        partition_shared = [ ]
        for i in range(606,612):
            partition_shared.append('eoscomp'+str(i))

        # Permet de forcer une architecture en reprenant les noms des partitions
        if 'PLACEMENT_ARCHI' in os.environ:
            placement_archi=os.environ['PLACEMENT_ARCHI'].strip()
            if placement_archi == 'uvprod':
                return Uvprod()
            elif placement_archi == 'mesca':
                return Mesca2()
            elif placement_archi == 'exclusive':
                return Bullx_dlc()
            elif placement_archi == 'shared':
                return Bullx_dlc_shared()
            else:
                raise PlacementException("OUPS - PLACEMENT_ARCHI="+os.environ['PLACEMENT_ARCHI']+" Architecture hardware inconnue")

        # Si SLURM_NODELIST est défini, on est dans un sbatch ou un salloc
        # On utilise SLURM_NODELIST en priorité seulement s'il y a qu'un seul node !
        if 'SLURM_NNODES' in os.environ and os.environ['SLURM_NNODES']=='1':
            node = os.environ['SLURM_NODELIST']
            if node in partition_shared:
                return Bullx_dlc_shared
            if node == 'eosmesca1':
                return Mesca2()
        if 'HOSTNAME' in os.environ:
            # Machines particulières
            if os.environ['HOSTNAME'] == 'uvprod':
                return Uvprod()
            elif os.environ['HOSTNAME'] == 'eosmesca1':
                return Mesca2()
	    elif os.environ['HOSTNAME'] == 'prolix':
		return Prolix()

            # Nœuds shared d'eos
            elif os.environ['HOSTNAME'] in partition_shared:
                return Bullx_dlc_shared()

            # Nœuds d'eos ordinaires
            else:
                return Bullx_dlc()
        
        # Si aucune de ces variables n'est définie, on fait la même chose avec le hostname !
        #elif 'HOSTNAME' in os.environ and os.environ['HOSTNAME'] == 'uvprod':
        #    return Uvprod()
        #elif 'HOSTNAME' in os.environ and os.environ['HOSTNAME'] == 'eosmesca1':
        #    return Mesca2()
        else:
            raise(PlacementException("OUPS - Architecture indéfinie ! - Vérifiez $SLURM_NODELIST, $PLACEMENT_ARCHI, $HOSTNAME"))

    # Renvoie le numéro de socket à partir du numéro de cœur
    # Utilisé par certains affichages
    def getCore2Socket(self,core):
        if core >= self.CORES_PER_NODE:
            return self.getCore2Socket(core - self.CORES_PER_NODE)
        else:
            return core / self.CORES_PER_SOCKET

    # Renvoie le numéro de cœur sur le socket courant
    # Utilisé par certains affichages
    def getCore2Core(self,core):
        core = core % self.CORES_PER_NODE
        return core % self.CORES_PER_SOCKET

    # Renvoie le numéro de cœur physique correspondant au paramètre
    # ex. sur eos, 25 renvoie 5, 35 renvoie 15
    # Utilisé par certains affichages
    def getCore2PhysCore(self,core):
        return core % self.CORES_PER_NODE

    def getSocket2CoreMax(self,s):
        return (s+1) * self.CORES_PER_SOCKET - 1

    def getSocket2CoreMin(self,s):
        return s * self.CORES_PER_SOCKET


# 1/ BULLx DLC (eos), 2 sockets Intel Ivybridge 10 cœurs, hyperthreading activé
class Bullx_dlc(Hardware):
    NAME             = 'Bullx_dlc'
    SOCKETS_PER_NODE = 2
    CORES_PER_SOCKET = 10
    HYPERTHREADING   = True
    THREADS_PER_CORE = 2
    MEM_PER_SOCKET   = 32768
    IS_SHARED        = False

# 1/ BULLx DLC (eos), 2 sockets Intel Ivybridge 10 cœurs, hyperthreading activé, shared
class Bullx_dlc_shared(Hardware):
    NAME             = 'Bullx_dlc'
    SOCKETS_PER_NODE = 2
    CORES_PER_SOCKET = 10
    HYPERTHREADING   = True
    THREADS_PER_CORE = 2
    IS_SHARED        = True
    MEM_PER_SOCKET   = 32768

# 2 / SGI UV, uvprod, 48 sockets, 8 cœurs par socket, pas d'hyperthreading, SHARED
class Uvprod(Hardware):
    NAME             = 'uvprod'
    SOCKETS_PER_NODE = 48
    CORES_PER_SOCKET = 8
    HYPERTHREADING   = False
    THREADS_PER_CORE = 1
    MEM_PER_SOCKET   = 87381
    IS_SHARED        = True

# 3/ BULL SMP-mesca, 8 sockets, 15 cœurs par socket, pas d'hyperthreading
class Mesca(Hardware):
    NAME             = 'bull_mesca1'
    SOCKETS_PER_NODE = 8
    CORES_PER_SOCKET = 15
    HYPERTHREADING   = False
    THREADS_PER_CORE = 1
    MEM_PER_SOCKET   = 262144
    IS_SHARED        = True

# 4/ BULL SMP-mesca2, 8 sockets, 16 cœurs par socket, pas d'hyperthreading (pour l'instant), machine partagée
class Mesca2(Hardware):
    NAME             = 'bull_mesca2'
    SOCKETS_PER_NODE = 8
    CORES_PER_SOCKET = 16
    HYPERTHREADING   = False
    THREADS_PER_CORE = 1
    MEM_PER_SOCKET   = 262144
    IS_SHARED        = True

# 5/ Nouvelles machines Bull MF
class Prolix(Hardware):
    NAME             = 'prolix'
    SOCKETS_PER_NODE = 2
    CORES_PER_SOCKET = 20
    HYPERTHREADING   = True
    THREADS_PER_CORE = 2
    MEM_PER_SOCKET   = 262144
    IS_SHARED        = False
