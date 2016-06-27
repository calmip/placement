#! /usr/bin/env python
# -*- coding: utf-8 -*-

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

import os
import re
import ConfigParser
from exception import *

class Hardware(object):
    """ Describing hardware configuration 
    
    This file uses placement.conf to guess the correct hardware configuration, using some environment variables
    The private member IS_SHARED describes the fact that he host is SHARED between users or exclusively dedicated to the user
    It is not strictly hardware consideration, but as it never changes during the node life, it makes sense considering it as a hardware parameter
    """
    NAME             = ''
    SOCKETS_PER_NODE = ''
    CORES_PER_SOCKET = ''
    CORES_PER_NODE   = ''
    HYPERTHREADING   = ''
    THREADS_PER_CORE = ''
    IS_SHARED        = ''

    @staticmethod
    def catalog():
        """ Return the available hostsnames (as regex), partitions, architectures as lists of lists """

        conf_file = os.environ['PLACEMENTETC'] + '/placement.conf'
        config    = ConfigParser.RawConfigParser()
        config.read(conf_file)        
        partitions = config.options('partitions')
        hosts      = config.options('hosts')
        archis     = config.sections();
        archis.remove('hosts')
        archis.remove('partitions')
        return [hosts,partitions,archis]

    @staticmethod
    def factory():
        """ Build a Hardware object from several env variables: SLURM_NODELIST, PLACEMENT_PARTITION, HOSTNAME"""

        # 1st stage: Read the configuration file
        conf_file = os.environ['PLACEMENTETC'] + '/placement.conf'
        config    = ConfigParser.RawConfigParser()
        config.read(conf_file)        
 
        # 2nd stage: Guess the architecture name from the env variables
        archi_name = Hardware.__guessArchiName(conf_file,config)

        # 3rd stage: Create and return the object from its name
        archi = SpecificHardware(conf_file,config,archi_name)

        return archi

    @staticmethod
    def __guessArchiName(conf_path,config):
        """  Guess the architecture name from the environment variables:

        Arguments:
        conf_file: The config path, used only for display
        config:    A ConfigParser object, already created

        return the architecture name, of rais an exception if impossible to check
        """

        archi_name = ''

        # Forcing an architecture from its name, using $PLACEMENT_ARCHI
        if 'PLACEMENT_ARCHI' in os.environ:
            placement_archi=os.environ['PLACEMENT_ARCHI'].strip()
            if config.has_section(placement_archi)==False:
                raise PlacementException("OUPS - PLACEMENT_ARCHI="+os.environ['PLACEMENT_ARCHI']+" Unknown architecture, check placement.conf")
            else:
                archi_name = placement_archi

        # Forcing an architecture from its partition name, using $PLACEMENT_PARTITION
        elif 'PLACEMENT_PARTITION' in os.environ:
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
                raise(PlacementException("OUPS - Could not guess the architecture from the hostname (" + node + ") - Please check " + conf_path))
            
        return archi_name

    @staticmethod
    def __hostname2Archi(config, host):
        """ return the architecture name from the hostname, using the configuration
        Try a regex match between host and all the options
        When a match is found return the corresponding value
        If no match, return None

        Arguments:
        config A ConfigParser object
        host   A hostname
        """

        options = config.options('hosts')
        for o in options:
            if re.match(o,host) != None:
                return config.get('hosts',o)
        return None

    def getCore2Socket(self,core):
        """ Return the socket number from the core number

        Ex: for 2 sockets, 10 c/socket, hyper ON
            5 => 0, 15 => 1, 25 => 0, 35 => 1
     
        Arguments:
        core The core number
        """

        if core >= self.CORES_PER_NODE:
            return self.getCore2Socket(core - self.CORES_PER_NODE)
        else:
            return core / self.CORES_PER_SOCKET

    def getCore2Core(self,core):
        """ Return the physical socket core number from the node core number

        Ex: for 2 sockets, 10c/socket, hyper ON
            5 => 5, 15 => 5, 25 => 5, 35 => 5

        Arguments:
        core
        """

        core = core % self.CORES_PER_NODE
        return core % self.CORES_PER_SOCKET

    def getCore2PhysCore(self,core):
        """ Return the physical node core number from the node core number

        Ex: for 2 sockets, 10c/socket, hyper ON
            5 => 5, 15 => 15, 25 => 5, 35 => 15

        Arguments:
        core
        """

        return core % self.CORES_PER_NODE

    def getSocket2CoreMax(self,s):
        """ Return the max physical node core number from the socket number

        Ex: 2 sockets, 10c/socket, hyper ON
            0 => 9, 1 => 19

        Arguments:
        socket
        """

        return (s+1) * self.CORES_PER_SOCKET - 1

    def getSocket2CoreMin(self,s):
        """  Return the min physical node core number from the socket number

        Ex: 2 sockets, 10 c/socket, hyper ON
            0 => 0, 1 => 10

        Arguments:
        socket
        """

        return s * self.CORES_PER_SOCKET

class SpecificHardware(Hardware):
    """ Class deriving from Hardware, uses the configuration """

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
