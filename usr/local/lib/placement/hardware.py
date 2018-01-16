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
from utilities import  expandNodeList, getHostname

class Hardware(object):
    """ Describing hardware configuration 
    
    This file uses slurm.conf if possible, or placement.conf, to guess the correct hardware configuration, using some environment variables
    The private member IS_SHARED describes the fact that the HOST is SHARED between users (if True) or exclusively dedicated (if False) to the job
    It is not strictly hardware consideration, but as it never changes during the node life, it makes sense considering it as a hardware parameter
    WARNING FOR SLURM ADMINS - IS_SHARED means here "The NODE is shared", NOT the Resource. 
                               So you may have Shared=No in slurm.conf and IS_SHARED set to False !
                               IS_SHARED is set to False ONLY if you have Shared=EXCLUSIVE in slurm.conf
    """
    NAME             = ''
    SOCKETS_PER_NODE = ''
    CORES_PER_SOCKET = ''
    CORES_PER_NODE   = ''
    HYPERTHREADING   = ''
    THREADS_PER_CORE = ''
    IS_SHARED        = ''
    GPUS             = ''

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
        """ Build a Hardware object from several env variables: PLACEMENT_ARCHI, PLACEMENT_PARTITION, HOSTNAME"""

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
                
        # Archi not yet guessed, trying to guess from the hostname
        if archi_name == '':
            node = getHostname()
            archi_name = Hardware.__hostname2Archi(config, node)
            
            if archi_name == None:
                archi_name = Hardware.__hostname2ArchiFromSlurmConf(config,node)

            if archi_name == None:
                raise(PlacementException("OUPS - Could not guess the architecture from the hostname (" + node + ") - Please check " + conf_path))
            
        return archi_name

    @staticmethod
    def __hostname2Archi(config, host):
        """ return the architecture name from the hostname, using the configuration
        Each option is a list of hosts: try to find a list of hosts we could be a part of
        When found return the corresponding value
        If no match, return None

        Arguments:
        config A ConfigParser object
        host   A hostname
        """

        options = config.options('hosts')
        for o in options:
            if host in expandNodeList(o):
                return config.get('hosts',o)
        return None

    @staticmethod
    def __hostname2ArchiFromSlurmConf(config, host):
        """ return the architecture name from the hostname, using slurm.conf
        Try a regex match between host and the Nodename= hosts
        If a match is found try a regex match between host and the Nodes= hosts
        Compare the architecture found with the known architectures, creating a new archi if necessary
        At last, return the architecture name
        If no match, return None

        Arguments:
        config A ConfigParser object
        host   A hostname
        """

        try:
            if 'SLURM_CONF' in os.environ:
                slurm_conf = os.environ['SLURM_CONF']
            else:
                slurm_conf = '/etc/slurm/slurm.conf'

            fh_slurm_conf = open(slurm_conf,'r')
            slurm_lines   = fh_slurm_conf.readlines()
            fh_slurm_conf.close()

        except IOError:
            return

        # Analyze the file, looking for NodeName=
        for l in slurm_lines:
            if l[0] == '#':
                continue

            # Search a matching Nodename= and add an auto section to config
            fields = l.split(' ')
            for f in fields:
                p = f.partition('=')
                if p[0].upper()=='NODENAME':
                    nodename = p[2]
                    if host in expandNodeList(nodename):
                        Hardware.__addSlurmSection(config,nodename,fields)
                        break

            # If a slurm section was created, it's OK (NodeName found)
            if config.has_section('Slurm'):
                break

        # If a Slurm section was created, we analyze again the file, looking for PartitionName= and Nodes=
        # The goal is to read the Shared parameter
        if config.has_section('Slurm'):
            for l in slurm_lines:
                if l[0] == '#':
                    continue

                fields = l.split(' ')
                partitionname=''
                nodes=''
                shared=''
                for f in fields:
                    p = f.partition('=')
                    k = p[0].upper()
                    v = p[2]
                    if k=='PARTITIONNAME':
                        partitionname=v
                    elif k=='NODES':
                        nodes=v
                    elif k=='SHARED':
                        shared=v

                # Was it a line to descript the partitions ?
                if partitionname=='':
                    continue

                # Is the current host part of this partition ?
                if host in expandNodeList(nodes):
                    if shared.upper().startswith('EXCLUSIVE'):
                        config.set('Slurm','IS_SHARED','False')
                    else:
                        config.set('Slurm','IS_SHARED','True')

                    # The architecture is definitvely 'Slurm'
                    return 'Slurm'

        # Configuration not found in slum.conf, or incomplete
        return None

    @staticmethod
    def __addSlurmSection(config,nodename,fields):
        """Parse l and add to config a section called "Slurm" to the config object
        Add an option called nodename to the section hosts"""

        cores   = 1
        sockets = 1
        corespersocket = 1
        threadspercore = 1
        realmemory = 0
        for f in fields:
            p = f.partition('=')
            n = p[0].upper()
            if n == 'SOCKETS':
                sockets = int(p[2])
            elif n == 'CORESPERSOCKET':
                corespersocket = int(p[2])
            elif n == 'THREADSPERCORE':
                threadspercore = int(p[2])
            elif n == 'REALMEMORY':
                realmemory = int(p[2])

        config.add_section('Slurm')
        config.set('Slurm','SOCKETS_PER_NODE',sockets)
        config.set('Slurm','CORES_PER_SOCKET',corespersocket)
        config.set('Slurm','THREADS_PER_CORE',threadspercore)
        if threadspercore>1:
            config.set('Slurm','HYPERTHREADING','1')
        else:
            config.set('Slurm','HYPERTHREADING','0')
        config.set('Slurm','MEM_PER_SOCKET',realmemory / sockets)


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
            try:
                self.GPUS         = config.get(archi_name,'GPUS')
            except Exception, e:
                pass

        except Exception, e:
            msg = "OUPS - Something is wrong in the configuration - Please check " + conf_file
            msg += "\n"
            msg += "ERROR WAS = " + str(e)
            raise(PlacementException(msg))
