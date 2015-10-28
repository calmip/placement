#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################
#
#  Hardware: Permet de décrire le hardware des machines
#
################################################################

import os
from exception import *

class Hardware(object):
    NAME             = ''
    SOCKETS_PER_NODE = ''
    CORES_PER_SOCKET = ''
    HYPERTHREADING   = ''
    THREADS_PER_CORE = ''
    IS_SHARED        = ''

    @staticmethod
    def factory():
        # Si ne contient qu'un seule nœud, c'est peut-être uvprod ou eosmesca1
        if 'SLURM_NODELIST' in os.environ:
            if os.environ['SLURM_NODELIST'] == 'uvprod':
                return Uvprod()
            elif os.environ['SLURM_NODELIST'] == 'eosmesca1':
                return Mesca2()

            # Par défaut un nœud d'eos ordinaire
            else:
                return Bullx_dlc()
        
        # Permet de forcer une architecture en reprenant les noms des partitions
        elif 'PLACEMENT_ARCHI' in os.environ:
            if os.environ['PLACEMENT_ARCHI'] == 'uvprod':
                return Uvprod()
            elif os.environ['PLACEMENT_ARCHI'] == 'mesca':
                return Mesca2()
            elif os.environ['PLACEMENT_ARCHI'] == 'exclusiv':
                return Bullx_dlc()
            elif os.environ['PLACEMENT_ARCHI'] == 'eos':
                return Bullx_dlc()
            else:
                raise PlacementException("OUPS - PLACEMENT_ARCHI="+os.environ['PLACEMENT_ARCHI']+" Architecture hardware inconnue")

        # Si aucune de ces variables n'est définie, on fait la même chose avec le hostname !
        elif 'HOSTNAME' in os.environ and os.environ['HOSTNAME'] == 'uvprod':
            return Uvprod()
        else:
            raise(PlacementException("OUPS - Architecture indéfinie ! - Vérifiez $SLURM_NODELIST, $PLACEMENT_ARCHI, $HOSTNAME"))


# 1/ BULLx DLC (eos), 2 sockets Intel Ivybridge 10 cœurs, hyperthreading activé
class Bullx_dlc(Hardware):
    NAME             = 'Bullx_dlc'
    SOCKETS_PER_NODE = 2
    CORES_PER_SOCKET = 10
    HYPERTHREADING   = True
    THREADS_PER_CORE = 2
    IS_SHARED        = False

# 2 / SGI UV, uvprod, 48 sockets, 8 cœurs par socket, pas d'hyperthreading, SHARED
class Uvprod(Hardware):
    NAME             = 'uvprod'
    SOCKETS_PER_NODE = 48
    CORES_PER_SOCKET = 8
    HYPERTHREADING   = False
    THREADS_PER_CORE = 1
    IS_SHARED        = True

# 3/ BULL SMP-mesca, 8 sockets, 15 cœurs par socket, pas d'hyperthreading
class Mesca(Hardware):
    NAME             = 'bull_mesca1'
    SOCKETS_PER_NODE = 8
    CORES_PER_SOCKET = 15
    HYPERTHREADING   = False
    THREADS_PER_CORE = 1
    IS_SHARED        = False

# 4/ BULL SMP-mesca2, 8 sockets, 16 cœurs par socket, pas d'hyperthreading (pour l'instant)
class Mesca2(Hardware):
    NAME             = 'bull_mesca2'
    SOCKETS_PER_NODE = 8
    CORES_PER_SOCKET = 16
    HYPERTHREADING   = False
    THREADS_PER_CORE = 1
    IS_SHARED        = True

