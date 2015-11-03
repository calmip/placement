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
    def catalogue():
        return [ 'uvprod','eosmesca1','mesca','exclusiv','shared' ]

    ####################################################################
    #
    # @brief Construit un objet à partir des variables d'environnement: SLURM_NODELIST, PLACEMENT_ARCHI, HOSTNAME
    #
    ####################################################################
    @staticmethod
    def factory():
        # Construction de la partition shared
        partition_shared = [ ]
        for i in range(604,612):
            partition_shared.append('eoscomp'+str(i))

        # Si SLURM_NODELIST est défini, on est dans un sbatch
        if 'HOSTNAME' in os.environ:
            # Machines particulières
            if os.environ['HOSTNAME'] == 'uvprod':
                return Uvprod()
            elif os.environ['HOSTNAME'] == 'eosmesca1':
                return Mesca2()

            # Nœuds shared d'eos
            elif os.environ['HOSTNAME'] in partition_shared:
                return Bullx_dlc_shared()

            # Nœuds d'eos ordinaires
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
            elif os.environ['PLACEMENT_ARCHI'] == 'shared':
                return Bullx_dlc_shared()
            else:
                raise PlacementException("OUPS - PLACEMENT_ARCHI="+os.environ['PLACEMENT_ARCHI']+" Architecture hardware inconnue")

        # Si aucune de ces variables n'est définie, on fait la même chose avec le hostname !
        #elif 'HOSTNAME' in os.environ and os.environ['HOSTNAME'] == 'uvprod':
        #    return Uvprod()
        #elif 'HOSTNAME' in os.environ and os.environ['HOSTNAME'] == 'eosmesca1':
        #    return Mesca2()
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

# 1/ BULLx DLC (eos), 2 sockets Intel Ivybridge 10 cœurs, hyperthreading activé, shared
class Bullx_dlc_shared(Hardware):
    NAME             = 'Bullx_dlc'
    SOCKETS_PER_NODE = 2
    CORES_PER_SOCKET = 10
    HYPERTHREADING   = True
    THREADS_PER_CORE = 2
    IS_SHARED        = True

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

# 4/ BULL SMP-mesca2, 8 sockets, 16 cœurs par socket, pas d'hyperthreading (pour l'instant), machine partagée
class Mesca2(Hardware):
    NAME             = 'bull_mesca2'
    SOCKETS_PER_NODE = 8
    CORES_PER_SOCKET = 16
    HYPERTHREADING   = False
    THREADS_PER_CORE = 1
    IS_SHARED        = True
