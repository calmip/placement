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
#  Copyright (C) 2015-2018 Emmanuel Courcelle
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
import configparser
from exception import *
from utilities import  expandNodeList, getHostnameRem, flatten, runCmd

class Hardware(object):
    """ Describing hardware configuration 
    
    This file uses placement.conf to guess the correct hardware configuration, using some environment variables
    The private member IS_SHARED describes the fact that the HOST is SHARED between users (if True) or exclusively dedicated (if False) to the job
    It is not strictly hardware consideration, but as it never changes during the node lifetime, it makes sense considering it as a hardware parameter
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
    ADDRESSING       = None
    REVADDRESSING    = None

    @staticmethod
    def catalog():
        """ Return the available hostnames (as regex), architectures as lists of lists """
        conf_file = Hardware.__getConfFile()

        config    = configparser.RawConfigParser()
        config.read(conf_file)        
        hosts      = config.options('hosts')
        archis     = config.sections();
        archis.remove('hosts')
        return [hosts,archis]

    @staticmethod
    def factory():
        """ Build a Hardware object from several env variables: PLACEMENT_ARCHI, HOSTNAME"""

        # 1st stage: Read the configuration file, if possible
        conf_file = Hardware.__getConfFile()
        config    = configparser.RawConfigParser()
        if os.path.exists(conf_file):
            config.read(conf_file)        

        # 2nd stage: Guess the architecture name from the env variables
        archi_name = Hardware.__guessArchiName(conf_file,config)

        # 3rd stage: Create and return the object from its name
        archi = SpecificHardware(conf_file,config,archi_name)

        return archi

    @staticmethod
    def __getConfFile():
        # Useful for testing !
        if 'PLACEMENT_CONF' in os.environ:
            return os.environ['PLACEMENT_CONF']
        else:                
            return os.environ['PLACEMENT_ROOT'] + '/etc/placement.conf'
        
    @staticmethod
    def __guessArchiName(conf_path,config):
        """  Guess the architecture name from the environment variables:

        Arguments:
        conf_file: The config path, used only for error messages
        config:    A ConfigParser object, already created

        return the architecture name, raise an exception if impossible to guess
        """

        archi_name = None

        # Forcing an architecture from its name, using $PLACEMENT_ARCHI
        # Use it only for debug
        if 'PLACEMENT_ARCHI' in os.environ:
            placement_archi=os.environ['PLACEMENT_ARCHI'].strip()
            if config.has_section(placement_archi)==True:
                archi_name = placement_archi

        # Archi not yet guessed, trying to guess from the hostname
        node = getHostnameRem()
        if archi_name == None:
            archi_name = Hardware.__hostname2Archi(config, node)
            
        if archi_name == None:
            msg = "ERROR - Could not guess the architecture from the hostname (" + node + ") - ";
            if conf_path==None or not os.path.exists(conf_path):
                msg += "May be you should write a placement.conf file ";
            else:
                msg += "Please check " + conf_path
            raise PlacementException(msg)
            
        return archi_name

    @staticmethod
    def __hostname2Archi(config, host):
        """ return the architecture name from the hostname, using the configuration
        Each option is a list of hosts: try to find a list of hosts we could be a part of
        When found return the corresponding value
        If nothing found, return None

        Arguments:
        config A ConfigParser object
        host   A hostname
        """
        if config.has_section('hosts')==True:
            options = config.options('hosts')
            for o in options:
                if host in expandNodeList(o):
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
            return core // self.CORES_PER_SOCKET

    def getCore2Addr(self,core):
        """ Return the address of the (logical) core number from the internal representation """

        if self.ADDRESSING==None:
            return core
        else:
            return self.ADDRESSING[core]
            
    def getAddr2Core(self,addr):
        """ Return the core number in the internal representation from the address number"""
        
        if self.REVADDRESSING==None:
            return addr
        else:
            return self.REVADDRESSING[addr]
        
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
        
    def isHyperThreadingUsed(self,l):
        """ Given a list of cores (l) used by some threads, is hypertheading used ? """
        
        pcores =[]
        for c in l:
            pcores.append(self.getCore2PhysCore(c))

        return len(pcores) > len(set(pcores))
        

class SpecificHardware(Hardware):
    """ Class deriving from Hardware, uses the configuration """

    def __init__(self,conf_file, config,archi_name):
        # archi_name should be a section in the configuration file
        if config.has_section(archi_name)==False:
            raise PlacementException("ERROR - The architecture " + archi_name + " is unknown - Please check " + conf_file)

        try:
            self.NAME             = archi_name
            self.SOCKETS_PER_NODE = config.getint(archi_name,'SOCKETS_PER_NODE')
            self.CORES_PER_SOCKET = config.getint(archi_name,'CORES_PER_SOCKET')
            self.HYPERTHREADING   = config.getboolean(archi_name,'HYPERTHREADING')
            self.THREADS_PER_CORE = config.getint(archi_name,'THREADS_PER_CORE')
            self.MEM_PER_SOCKET   = config.getint(archi_name,'MEM_PER_SOCKET')
            self.IS_SHARED        = config.getboolean(archi_name,'IS_SHARED')
            self.CORES_PER_NODE   = self.CORES_PER_SOCKET*self.SOCKETS_PER_NODE
            if 'ADDRESSING' in config[archi_name]:
                self.__initAddressing(config[archi_name]['ADDRESSING'])
            try:
                self.GPUS         = config.get(archi_name,'GPUS')
            except Exception as e:
                pass

        except Exception as e:
            msg = "ERROR - Something is wrong in the configuration - Please check " + conf_file
            msg += "\n"
            msg += "ERROR WAS = " + str(e)
            raise PlacementException(msg)

    #
    # The Cores addressing:
    #
    #     placement uses internally a representation depicted under and supported
    #     by most hardware configurations:
    #
    #     For a machine with 2 sockets, 4 cores/socket, 2 threads by core:
    #
    #     SOCKET 0     SOCKET 1
    #     0  1  2  3    4  5  6  7
    #     8  9 10 11   12 13 14 15 
    #
    #     The numactl --hardware output of such a configuration is:
    #
    #     available: 2 nodes (0-1)
    #     node 0 cpus: 0 1 2 3 8 9 10 11 
    #     ...
    #     node 1 cpus: 4 5 6 7 12 13 14 15
    #
    #     HOWEVER, with the same processors, several machines adopt another addressing, 
    #     shown by the following numactl--hardware output:
    #
    #     available: 2 nodes (0-1)
    #     node 0 cpus: 0 2 4 6 8 10 12 14
    #     ...
    #     node 1 cpus: 1 3 5 7 9 11 13 15
    #
    #     If your machine adopts the FIRST convention, you may REMOVE the parameter
    #     Addressing in placement.conf. 
    #     BUT if your machine adopts the SECOND convention (or still another one), 
    #     you must SET this parameter to Numactl (only value supported),
    #     so that placement will issue a numactl --hardware to fix the addressing.
    #
    #     If you do not know, please set the parameter to Numactl, as it should always work
    #     
    
    def __initAddressing(self,addressing):
        """Initalize core addressing tables"""
        
        if addressing != 'Numactl':
            raise PlacementException("ERROR - The only value accepted for ADDRESSING is Numactl")
        
        tmp = self.__callNumactl()
        
        # Init self.ADDRESSING: for converting FROM internal representation
        self.ADDRESSING = [ -1 for i in range(self.SOCKETS_PER_NODE * self.CORES_PER_SOCKET * self.THREADS_PER_CORE)]
        i   = 0
        for s in range(self.SOCKETS_PER_NODE):
            for t in range(self.THREADS_PER_CORE):
                for c in range(self.CORES_PER_SOCKET):
                    self.ADDRESSING[t * self.SOCKETS_PER_NODE * self.CORES_PER_SOCKET + s * self.CORES_PER_SOCKET + c] = tmp[i]
                    i += 1

        # Init self.REVADDRESSING: for conversion TO internal representation        
        self.REVADDRESSING = [ -1 for i in range(self.SOCKETS_PER_NODE * self.CORES_PER_SOCKET * self.THREADS_PER_CORE)]
        for i in range(self.SOCKETS_PER_NODE * self.CORES_PER_SOCKET * self.THREADS_PER_CORE):
            self.REVADDRESSING[self.ADDRESSING[i]] = i

        # Check: is self.REVADDRESSING or self.ADDRESSING correctly initialized ?
        for i in range(self.SOCKETS_PER_NODE * self.CORES_PER_SOCKET * self.THREADS_PER_CORE):
            if self.ADDRESSING[i] == -1:
                raise PlacementException("INTERNAL ERROR - self.ADDRESSING[" + str(i) + "] not initialized. pb with numactl output")
            if self.REVADDRESSING[i] == -1:
                raise PlacementException("INTERNAL ERROR - self.REVADDRESSING[" + str(i) + "] not initialized. pb with numactl output")

        #print(str(self.ADDRESSING))
        #print(str(self.REVADDRESSING))

    def __callNumactl(self): 
        """Call numactl, detecting sockets and core addressing
           return An array of int (concatenation of node X cpus: outputs of numactl --hardware)
        """

        rvl = []
        cmd = "numactl --hardware"
        output = runCmd(cmd).split('\n')

        # Looking for lines (in this order !)
        # node 0 cpus: 0 2 4 6 8 10 12 14 16 18 20 22 24 26 28 30
        # node 1 cpus: 1 3 5 7 9 11 13 15 17 19 21 23 25 27 29 31
        sock_cnt=0
        for l in output:
            if l.startswith('node '+str(sock_cnt)+ ' cpus:'):
                cores = l.partition(':')[2]
                rvl.append(list(map(int,cores.strip().split(' '))))
                sock_cnt += 1
        
        return flatten(rvl)
