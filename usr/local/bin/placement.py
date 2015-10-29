#! /usr/bin/env python
# -*- coding: utf-8 -*-

################################################################
# Ce script peut vous aider à placer vos tâches sur les coeurs
#
# CALMIP - 2015
#
# Commencez par: placement --help 
#
# Calcule et renvoie le switch cpu_bin qui doit être inséré dans l'appel srun
#
# Exemple: 4 processus, 8 threads par processus, hyperthreading activé
#
# Switch -H: Renvoie l'affectation des cores aux processes de manière lisible par les humains:
#
# placement -H 4 8 2
# [ 0 1 2 3 20 21 22 23 ]
# [ 10 11 12 13 30 31 32 33 ]
# [ 4 5 6 7 24 25 26 27 ]
# [ 14 15 16 17 34 35 36 37 ]
#
# --cpu_bind=mask_cpu:0xf0000f,0x3c0003c00,0xf0000f0,0x3c0003c000
#
# Switch -A: Renvoie l'affectation des cores aux processes de manière cartographique:
#
# placement.py -A 4 8 2
# /XXXX...... .......... 
# \XXXX...... .......... 
# /.......... XXXX...... 
# \.......... XXXX...... 
# /....XXXX.. .......... 
# \....XXXX.. .......... 
# /.......... ....XXXX.. 
# \.......... ....XXXX.. 
#
# --cpu_bind=mask_cpu:0xf0000f,0x3c0003c00,0xf0000f0,0x3c0003c000
#
# DANS UN SCRIPT SBATCH:
# ======================
#
# Pas la peine de spécifier les paramètres, les variables d'environnement SLURM seront utilisées
# Commandes recommandées:
# 
# placement -A
# if [[ $? != 0 ]]
# then
#  echo "ERREUR DANS LE NOMBRE DE PROCESES OU DE TACHES" 2>&1
#  exit $?
# fi
# ...
# srun $(placement) ./mon_application
#        
# emmanuel.courcelle@inp-toulouse.fr
# http://www.calmip.univ-toulouse.fr
# Mars 2015
################################################################

import os
from optparse import OptionParser
import subprocess
from itertools import chain,product
import hardware
from architecture import *
from exception import *
from tasksbinding import *
from scatter import *
from compact import *
from running import *
from utilities import *

def main():

    # Recherche le hardware, actuellement à partir de variables d'environnement ou à partir du nom de la machine
    hard = '';
    try:
        hard = hardware.Hardware.factory()
            
    except PlacementException, e:
        print e
        exit(1)

    # Si la variable PLACEMENT_DEBUG existe, on simule un environnement shared avec des réservations
    # Exemple: export PLACEMENT_DEBUG='9,10,11,12,13' pour simuler un environnement shared, 5 sockets réservées
    # NB - Ne pas oublier non plus de positionner SLURM_NODELIST ! (PAS PLACEMENT_ARCHI ça n'activera pas Shared)
    if 'PLACEMENT_DEBUG' in os.environ:
        import mock
        placement_debug=os.environ['PLACEMENT_DEBUG']
        rvl=map(int,placement_debug.split(','))
        Shared._Shared__detectSockets = mock.Mock(return_value=rvl)

    epilog = 'Environment:\n PLACEMENT_ARCHI (nom de partition: mesca, exclusiv etc), SLURM_NODELIST (noms de nodes), SLURM_TASKS_PER_NODE, SLURM_CPUS_PER_TASK'
    parser = OptionParser(version="%prog 1.0",usage="%prog [options] tasks cpus_per_task",epilog=epilog)
    parser.add_option("-I","--hardware",dest='show_hard',action="store_true",help="Show the currently selected hardware")
    parser.add_option("-E","--examples",action="store_true",dest="example",help="Print some examples")
    parser.add_option("-S","--sockets_per_node",type="choice",choices=map(str,range(1,hard.SOCKETS_PER_NODE+1)),default=hard.SOCKETS_PER_NODE,dest="sockets",action="store",help="Nb of available sockets(1-%default, default %default)")
    parser.add_option("-T","--hyper",action="store_true",default=False,dest="hyper",help="Force use of hard.HYPERTHREADING (%default)")
    parser.add_option("-M","--mode",type="choice",choices=["compact","scatter"],default="scatter",dest="mode",action="store",help="distribution mode: scatter, compact (%default)")
    parser.add_option("-H","--human",action="store_true",default=False,dest="human",help="Output humanly readable (%default)")
    parser.add_option("-A","--ascii-art",action="store_true",default=False,dest="asciiart",help="Output geographically readable (%default)")

    parser.add_option("-R","--srun",action="store_const",dest="output_mode",const="srun",help="Output for srun (default)")
    parser.add_option("-N","--numactl",action="store_const",dest="output_mode",const="numactl",help="Output for numactl")
    parser.add_option("-C","--check",dest="check",action="store",help="Check the cpus binding of a running process")
    parser.set_defaults(output_mode="srun")
    (options, args) = parser.parse_args()

    try:

        if options.example==True:
            examples()
            exit(0)
        if options.show_hard==True:
            show_hard(hard)
            exit(0)
        # Option --check
        if options.check != None:
            check_running(options.check,hard)
            exit(0)
        else:
            over_cores = None
            [cpus_per_task,tasks] = computeCpusTasksFromEnv(options,args)
            if hard.IS_SHARED:
                archi = Shared(hard,int(options.sockets), cpus_per_task, tasks, options.hyper)
            else:
                archi = Exclusive(hard,int(options.sockets), cpus_per_task, tasks, options.hyper)
            
            task_distrib = ""
            if options.mode == "scatter":
                task_distrib = ScatterMode(archi,cpus_per_task,tasks)
            else:
                task_distrib = CompactMode(archi,cpus_per_task,tasks)
            
            tasks_bound = task_distrib.distribTasks()

        task_distrib.threadsSort(tasks_bound)


        # Imprime le binding de manière compréhensible pour les humains
        if options.human==True:
            print getCpuBinding(archi,tasks_bound,getCpuTaskHumanBinding)
    
        # Imprime le binding en ascii art
        if options.asciiart==True:
            if tasks<=62:
                print getCpuBindingAscii(archi,tasks_bound,over_cores)
            else:
                # print getCpuBinding(archi,tasks_bound,getCpuTaskAsciiBinding)
                raise PlacementException("OUPS - switch --ascii interdit pour plus de 62 tâches !")
    
        # Imprime le binding de manière compréhensible pour srun ou numactl
        # (PAS si --check)
        if options.check == None:
            if options.output_mode=="srun":
                print getCpuBindingSrun(archi,tasks_bound)
            if options.output_mode=="numactl":
                print getCpuBindingNumactl(archi,tasks_bound)

    except PlacementException, e:
        print e
        exit(1)

####################
#
# affiche quelques exemple d'utilisation
#
####################
def examples():
    ex = """USING placement IN AN SBATCH SCRIPT
===================================

1/ Insert the following lines in your script:

placement -A
if [[ $? != 0 ]]
then
 echo "ERREUR DANS LE NOMBRE DE PROCESSES OU DE TACHES" 2>&1
 exit $?
fi

2/ Modify your srun call as followes:

srun $(placement) ./my_application
"""
    print ex

###########################################################
# @brief imprime quelques informations sur le hardware
#
# @param hard Un objet de type Hardware
#
###########################################################
def show_hard(hard):
    msg = "Current architecture = " + hard.NAME + " "
    if hard.NAME != 'unknown':
        msg += '(' + str(hard.SOCKETS_PER_NODE) + ' sockets/node, '
        msg += str(hard.CORES_PER_SOCKET) + ' cores/socket, '
        if hard.HYPERTHREADING:
            msg += 'Hyperthreading ON, ' + str(hard.THREADS_PER_CORE) + ' threads/core, '
        if hard.IS_SHARED:
            msg += 'SHARED'
        else:
            msg += 'EXCLUSIVE'
        msg += ')'
        print(msg)

##########################################################
# @brief vérifie le taskset sur un programme en exécution
#
# @param Le nom du code exécutable (pour sélectionner les processus)
# @param Le hardware
##########################################################
def check_running(path,hard):
    task_distrib = RunningMode(path,hard)
    tasks_bound= task_distrib.distribTasks()
    #print tasks_bound
    #print task_distrib.pid
    archi = task_distrib.archi
    cpus_per_task = task_distrib.cpus_per_task
    tasks         = task_distrib.tasks

    print task_distrib.getTask2Pid()
    print

    (overlap,over_cores) = detectOverlap(tasks_bound)
    if len(overlap)>0:
        print "ATTENTION LES TACHES SUIVANTES ONT DES RECOUVREMENTS:"
        print "====================================================="
        print overlap
        print

if __name__ == "__main__":
    main()
