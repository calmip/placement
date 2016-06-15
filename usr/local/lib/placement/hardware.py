#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import ConfigParser
from exception import *

#############################################################################################################
#
#  Hardware: Describing hardware configuration
#            The private membre IS_SHARED describes the fact that he hst is SHARED between users, 
#            or exclusively dedicated to the user
#            It is not strictly hardware consideration, but as it never changes during the node life, 
#            it makes sense considering it as a hardware parameter
#
################################################################
class Hardware(object):
    NAME             = ''
    SOCKETS_PER_NODE = ''
    CORES_PER_SOCKET = ''
    CORES_PER_NODE   = ''
    HYPERTHREADING   = ''
    THREADS_PER_CORE = ''
    IS_SHARED        = ''

    @staticmethod
    def catalog():
        conf_file = os.environ['PLACEMENTETC'] + '/placement.conf'
        config    = ConfigParser.RawConfigParser()
        config.read(conf_file)        
        partitions = config.options('partitions')
        hosts      = config.options('hosts')
        return [hosts,partitions]

    ####################################################################
    #
    # @brief Build a Hardware object from several env variables: SLURM_NODELIST, PLACEMENT_PARTITION, HOSTNAME
    #
    ####################################################################
    @staticmethod
    def factory():
        # 1st stage: Read the configuration file
        conf_file = os.environ['PLACEMENTETC'] + '/placement.conf'
        config    = ConfigParser.RawConfigParser()
        config.read(conf_file)        
 
        # 2nd stage: Guess the architecture name from the env variables
        archi_name = Hardware.__guessArchiName(conf_file,config)

        # 3rd stage: Create and return the object from its name
        archi = SpecificHardware(conf_file,config,archi_name)

        return archi

    ####################################################################
    #
    # @brief Guess the architecture name from the env variables
    #
    # @param conf_file The configuration file name
    # @param config A ConfigParser object
    # @return       An architecture name
    #
    ####################################################################
    @staticmethod
    def __guessArchiName(conf_file,config):
        archi_name = ''

        # Forcing an architecture from its partition name, using a special environment variable
        if 'PLACEMENT_PARTITION' in os.environ:
            placement_archi=os.environ['PLACEMENT_PARTITION'].strip()
            if config.has_section('partitions')==False:
                raise PlacementException("OUPS - PLACEMENT_PARTITION is set but there is no section called partitions in placement.conf")
            if config.has_option('partitions',placement_archi)==None:
                raise PlacementException("OUPS - PLACEMENT_PARTITION="+os.environ['PLACEMENT_PARTITION']+" Unknown partition, can't guess the architecture")
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
            elif 'HOSTNAME' in os.environ:
                node = os.environ['HOSTNAME']
            else:
                raise(PlacementException("OUPS - Unknown host, thus unknown architecture - Please check $SLURM_NODELIST, $PLACEMENT_PARTITION, $HOSTNAME"))

            archi_name = Hardware.__hostname2Archi(config, node)
            
            if archi_name == None:
                raise(PlacementException("OUPS - Could not guess the architecture from the hostname (" + node + ") - Please check " + conf_file))
            
        return archi_name

    ####################################################################
    #
    # @brief Read the architecture name from the hostname, using the configuration file
    #        Try a regex match between host and all the options
    #        When a match is found return the corresponding value
    #        If no match, return None
    #
    # @param config A ConfigParser object
    # @param host   A hostname
    #
    ####################################################################
    @staticmethod
    def __hostname2Archi(config, host):
        options = config.options('hosts')
        for o in options:
            if re.match(o,host) != None:
                return config.get('hosts',o)
        return None

    ####################################################################
    #
    # @brief Return the socket number from the core number
    #        Ex: 2 sockets 10 c/socket, hyper ON
    #            5 => 0, 15 => 1, 25 => 0, 35 => 1
    #
    # @param core
    # @return socket number
    ####################################################################
    def getCore2Socket(self,core):
        if core >= self.CORES_PER_NODE:
            return self.getCore2Socket(core - self.CORES_PER_NODE)
        else:
            return core / self.CORES_PER_SOCKET

    ####################################################################
    #
    # @brief Return the physical socket core number from the node core number
    #        Ex: 2 sockets 10 c/socket, hyper ON
    #            5 => 5, 15 => 5, 25 => 5, 35 => 5
    #
    # @param core
    # @return core
    ####################################################################
    def getCore2Core(self,core):
        core = core % self.CORES_PER_NODE
        return core % self.CORES_PER_SOCKET

    ####################################################################
    #
    # @brief Return the physical node core number from the node core number
    #        Ex: 2 sockets 10 c/socket, hyper ON
    #            5 => 5, 15 => 15, 25 => 5, 35 => 15
    #
    # @param core
    # @return core
    ####################################################################
    def getCore2PhysCore(self,core):
        return core % self.CORES_PER_NODE

    ####################################################################
    #
    # @brief Return the max physical node core number from the socket number
    #        Ex: 2 sockets 10 c/socket, hyper ON
    #            0 => 9, 1 => 19
    #
    # @param socket
    # @return core
    ####################################################################
    def getSocket2CoreMax(self,s):
        return (s+1) * self.CORES_PER_SOCKET - 1

    ####################################################################
    #
    # @brief Return the min physical node core number from the socket number
    #        Ex: 2 sockets 10 c/socket, hyper ON
    #            0 => 0, 1 => 10
    #
    # @param socket
    # @return core
    ####################################################################
    def getSocket2CoreMin(self,s):
        return s * self.CORES_PER_SOCKET


####################################################################
#
# @brief Class derived from Hardware, uses the configuration
#
####################################################################

class SpecificHardware(Hardware):
    def __init__(self,conf_file, config,archi_name):
        # archi_name should be a section in the configuration file
        if config.has_section(archi_name)==False:
            raise(PlacementException("OUPS - The architecture " + archi_name + " is unknown - Please check " + conf_file))

        try:
            self.NAME             = archi_name
            self.SOCKETS_PER_NODE = config.getint(archi_name,'SOCKETS_PER_NODE')
            self.CORES_PER_SOCKET = config.getint(archi_name,'CORES_PER_SOCKET')
            self.HYPERTHREADING   = config.getboolean(archi_name,'HYPERTHREADING')
            self.THREADS_PER_CORE = config.getint(archi_name,'THREADS_PER_CORE')
            self.MEM_PER_SOCKET   = config.getint(archi_name,'MEM_PER_SOCKET')
            self.IS_SHARED        = config.getboolean(archi_name,'IS_SHARED')
            self.CORES_PER_NODE   = self.CORES_PER_SOCKET*self.SOCKETS_PER_NODE

        except Exception, e:
            msg = "OUPS - Something is wrong in the configuration - Please check " + conf_file
            msg += "\n"
            msg += "ERROR WAS = " + str(e)
            raise(PlacementException(msg))
