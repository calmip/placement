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
import re
import ConfigParser

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
    # @brief Build a Hardware object fom several env variables: SLURM_NODELIST, PLACEMENT_ARCHI, HOSTNAME
    #
    ####################################################################
    @staticmethod
    def factory():
        # Read the configuration file
        conf_file = os.environ['PYTHONETC'] + '/partitions.conf'
        config    = ConfigParser.RawConfigParser()
        config.read(conf_file)        
 
        archi_name = ''

        # Forcing an architecture from its partition name, using a special environment variable
        if 'PLACEMENT_ARCHI' in os.environ:
            placement_archi=os.environ['PLACEMENT_ARCHI'].strip()
            if config.has_section('partitions')==False:
                raise PlacementException("OUPS - PLACEMENT_ARCHI is set but there is no section called partitions in placement.conf")
            if config.has_option('partitions',placement_archi)==None:
                raise PlacementException("OUPS - PLACEMENT_ARCHI="+os.environ['PLACEMENT_ARCHI']+" Unknown partition, can't guess the architecture")
            else:
                archi_name = config.get('partitions',placement_archi)
                
        # Archi not yet guessed !
        if archi_name == '':

            # Using SLURM_NODELIST, if defined (so if we live in a slurm sbatch or salloc), AND if there is only ONE node
            # NOTE - Not sure it is really useful
            node = ''
            if 'SLURM_NNODES' in os.environ and os.environ['SLURM_NNODES']=='1':
                node = os.environ['SLURM_NODELIST']

            # Using the environment variable HOSTNAME to guess the architecture
            if 'HOSTNAME' in os.environ:
                node = os.environ['HOSTNAME']
            else:
                raise(PlacementException("OUPS - Unknown host, thus unknown architecture - Please check $SLURM_NODELIST, $PLACEMENT_ARCHI, $HOSTNAME"))

            archi_name = Hardware.__name2Archi(config, node)
            
            if archi_name == None:
                raise(PlacementException("OUPS - Could not guess the architecture from the hostname (" + node + ") - Please check " + conf_file))
                
            # Create and return the object from its name
            archi = eval(archi_name+'()')
            return archi

    ####################################################################
    #
    # @brief Guess the architecture name from the hostname, using the configuration file
    #        Try a regex match between host and all the options
    #        When a match is found return the corresponding value
    #        If no match, return None
    #
    # @param config A ConfigParser object
    # @param host   A hostname
    #
    ####################################################################
    @staticmethod
    def __name2Archi(config, host):
        options = config.options('hosts')
        for o in options:
            if re.match(o,host) != None:
                return config.get('hosts',o)
        return None

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
class Bullx_dlc_broadwell(Hardware):
    NAME             = 'prolix'
    SOCKETS_PER_NODE = 2
    CORES_PER_SOCKET = 20
    HYPERTHREADING   = True
    THREADS_PER_CORE = 2
    MEM_PER_SOCKET   = 262144
    IS_SHARED        = False
