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
import argparse
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
from printing import *

# Si execute via ssh, on ne peut pas utiliser la variable d'environnement
from socket import gethostname

def main():

    # Si la variable PLACEMENT_DEBUG existe, on simule un environnement shared avec des réservations
    # Exemple: export PLACEMENT_DEBUG='9,10,11,12,13' pour simuler un environnement shared, 5 sockets réservées
    # NB - Ne pas oublier non plus de positionner SLURM_NODELIST ! (PAS PLACEMENT_PARTITION ça n'activera pas Shared)
    #if 'PLACEMENT_DEBUG' in os.environ:
    #    import mock
    #    placement_debug=os.environ['PLACEMENT_DEBUG']
    #    rvl=map(int,placement_debug.split(','))
    #    Shared._Shared__detectSockets = mock.Mock(return_value=rvl)

    epilog = newEpilog()
    ver="1.1.1"
    parser = argparse.ArgumentParser(version=ver,description="placement " + ver,epilog=epilog)

    # Les arguments de ce groupe sont reconnus par le wrapper bash SEULEMENT, ils sont là pour la cohérence et pour afficher le help
    group = parser.add_argument_group('checking jobs running on compute nodes (THOSE SWITCHES MUST BE SPECIFIED FIRST)')
    group.add_argument("--checkme",dest='checkme',action="store_true",help="Check my running job")
    group.add_argument("--jobid",dest='jobid',action="store_true",help="Check this running job (must be mine, except for sysadmins)")
    group.add_argument("--host",dest='host',action="store_true",help="Check this host (must execute my jobs, except for sysadmins)")

    group = parser.add_argument_group('Displaying some information')
    group.add_argument("-I","--hardware",dest='show_hard',action="store_true",help="Show the currently selected hardware and leave")
    group.add_argument("-E","--examples",action="store_true",dest="example",help="Print some examples and leave")
    group.add_argument("--environment",action="store_true",dest="show_env",help="Show some useful environment variables and leave")

    
    parser.add_argument('tasks', metavar='tasks',nargs='?',default=-1 ) 
    parser.add_argument('nbthreads', metavar='cpus_per_tasks',nargs='?',default=-1 ) 
    parser.add_argument("-T","--hyper",action="store_true",default=False,dest="hyper",help='Force use of hyperthreading (False)')
    parser.add_argument("-P","--hyper_as_physical",action="store_true",default=False,dest="hyper_phys",help="Used ONLY with mode=compact - Force hyperthreading and consider logical cores as supplementary sockets (False)")
    parser.add_argument("-M","--mode",choices=["compact","scatter","scatter_cyclic","scatter_block"],default="scatter_cyclic",dest="mode",action="store",help="distribution mode: scatter, scatter_cyclic (same as scatter),scatter_block, compact (scatter_cyclic)")
    parser.add_argument("-U","--human",action="store_true",default=False,dest="human",help="Output humanly readable")
    parser.add_argument("-A","--ascii-art",action="store_true",default=False,dest="asciiart",help="Output geographically readable")
    parser.add_argument("-R","--srun",action="store_const",dest="output_mode",const="srun",help="Output for srun (default)")
    parser.add_argument("-N","--numactl",action="store_const",dest="output_mode",const="numactl",help="Output for numactl")
    parser.add_argument("-Z","--intel_affinity",action="store_const",dest="output_mode",const="kmp",help="Output for intel openmp compiler, try also --verbose")

    parser.add_argument("--mpi_aware",action="store_true",default=False,dest="mpiaware",help="For running hybrid codes, forces --numactl. See examples")
    parser.add_argument("--make_mpi_aware",action="store_true",default=False,dest="makempiaware",help="To be used with --mpi_aware in the sbatch script BEFORE mpirun - See examples")
    parser.add_argument("-C","--check",dest="check",action="store",help="Check the cpus binding of a running process (CHECK=command name or user name or ALL)")
    parser.add_argument("-H","--threads",action="store_true",default=False,help="With --check: show threads affinity to the cpus")
    parser.add_argument("-r","--only_running",action="store_true",default=False,help="With --threads: show ONLY running threads")
    parser.add_argument("-t","--sorted_threads_cores",action="store_true",default=False,help="With --threads: sort the threads in core numbers rather than pid")
    parser.add_argument("-p","--sorted_processes_cores",action="store_true",default=False,help="With --threads: sort the processes in core numbers rather than pid")
    parser.add_argument("-Y","--memory",action="store_true",default=False,help="With --threads: show memory occupation relative to the sockets")
    parser.add_argument("-K","--taskset",action="store_true",default=False,help="With --check: compute the binding with taskset rather than ps")
    parser.add_argument("-V","--verbose",action="store_true",default=False,dest="verbose",help="more verbose output can be used with --check and --intel_kmp")
    parser.set_defaults(output_mode="srun")
    options=parser.parse_args()
    args=(options.tasks,options.nbthreads)

    if options.example==True:
        examples()
        exit(0)

    if options.show_env==True:
        show_env()
        exit(0)

    if options.makempiaware==True:
        make_mpi_aware()
        exit(0)

    # En mode mpi_aware, vérifie que toutes les variables d'environnement sont bien là
    if options.mpiaware==True:
        try:
            check_mpi_aware()
        except PlacementException, e:
            print e
            exit(1)

    # Recherche le hardware, actuellement à partir de variables d'environnement
    hard = '';
    try:
        hard = hardware.Hardware.factory()
            
    except PlacementException, e:
        print e
        exit(1)

    try:
        if options.show_hard==True:
            show_hard(hard)
            exit(0)

        # Première étape = Collecte des données résultat dans tasks_binding
        # Option --check -> Collecte à partir des jobs, sinon collecte à partir des paramètres
        if options.check != None:
            #[tasks,tasks_bound,threads_bound,over_cores,archi] = compute_data_from_running(options,args,hard)
            tasks_binding = compute_data_from_running(options,args,hard)
        else:
            #[tasks,tasks_bound,threads_bound,over_cores,archi] = compute_data_from_parameters(options,args,hard)
            tasks_binding = compute_data_from_parameters(options,args,hard)

        # Imprime les infos d'overlap si pertinentes et si elles existent
        try:
            overlap = tasks_binding.overlap
            if len(overlap)>0:
                print "ATTENTION LES TACHES SUIVANTES ONT DES RECOUVREMENTS:"
                print "====================================================="
                print overlap
                print
        except AttributeError:
            pass

        # Seconde étape = Impression des résultats sous plusieurs formats
        outputs = buildOutputs(options,tasks_binding)
        if len(outputs)==0:
            print "OUPS, Aucune sortie demandée !"
        else:
            if options.check != None:
                print gethostname()
        for o in outputs:
            print o
            
    except PlacementException, e:
        print e
        exit(1)


######################################################
#
# construit un tableau de sorties avec différents formats d'impression, en fonction des options
#
######################################################
def buildOutputs(options,tasks_binding):

    outputs = []

    # Imprime en mode verbose (si on n'est pas en kmp)
    if options.verbose and options.output_mode != 'kmp':
        outputs.append(PrintingForVerbose(tasks_binding))

    # Si on est en mpi_aware on imprime SEULEMENT en numactl !
    # @todo Pas très bon, il vaudrait mieux valider les options pour forcer le mode numactl dans options
    #if options.mpiaware==True:
    #    outputs.append(PrintingForNumactl(tasks_binding))
    #    return outputs

    # Imprime le binding de manière compréhensible pour srun ou numactl puis sort
    # (PAS si --check, --ascii ou --human)
    if options.check==None and options.asciiart==False and options.human==False:
        if options.output_mode=="srun":
            outputs.append(PrintingForSrun(tasks_binding))
            return outputs
        if options.output_mode=="numactl":
            outputs.append(PrintingForNumactl(tasks_binding))
            return outputs

    # Imprime le binding pour KMP_AFFINITY puis sort
    # (PAS si --check, --ascii ou --human)
    if options.check==None and options.asciiart==False and options.human==False:
        if options.output_mode=="kmp":
            outputs.append(PrintingForIntelAff(tasks_binding,options.verbose))
            return outputs

    # Imprime le binding de manière compréhensible pour les humains
    if options.human==True:
        outputs.append(PrintingForHuman(tasks_binding))
    
    # Imprime le binding en ascii art
    if options.asciiart==True:
        outputs.append(PrintingForAsciiArt(tasks_binding))

    # Imprime l'affinite des threads et des cpus
    if options.check!=None and options.threads==True:
        o = PrintingForMatrixThreads(tasks_binding)
        if options.only_running == True:
            o.PrintOnlyRunningThreads()
        if options.memory == True:
            o.PrintNumamem()
        if options.sorted_threads_cores == True:
            o.SortedThreadsCores()
        if options.sorted_processes_cores == True:
            o.SortedProcessesCores()
        outputs.append(o)

    return outputs
        

################################################
#
# affiche quelques exemples d'utilisation
#
################################################
def examples():
    ex = """===================================
USING placement IN AN SBATCH SCRIPT
===================================

1/ Insert the following lines in your script:

placement --ascii
if [[ $? != 0 ]]
then
 echo "ERREUR DANS LE NOMBRE DE PROCESSES OU DE TACHES" 2>&1
 exit $?
fi

2/ Modify your srun call as follows:

srun $(placement) ./my_application

===================================================================
USING placement WITH hybrid codes (mpi/openMP) IN AN SBATCH SCRIPT:
===================================================================

Put the following inside your slurm script:

# Creating environment variables usefull for placement
eval $(~/bin/placement --make_mpi_aware)

# Calling my application with mpirun
mpirun -binding "pin=no" -n ${SLURM_TASKS_PER_NODE} /bin/bash -c 'numactl $(~/bin/placement Tasks Threads --mpi_aware) my_application'
$(placement --mpi_aware) mpirun -np $SLURM_TASKS_PER_NODE ./my_application

=======================================
USING placement TO CHECK A RUNNING JOB:
=======================================
From the frontale execute:

placement --checkme

===========================================================
For a sysadmin: USING placement TO CHECK USER RUNNING JOBS:
===========================================================
From the frontale execute:

placement --host eoscomp666 --check=ALL --threads
"""
    print ex

###########################################################
# @brief imprime export=PLACEMENT_PHYSCPU=0,1,2
#
###########################################################
def make_mpi_aware():
    numa_res = subprocess.check_output(["numactl", "--show"]).split("\n")

    # Chercher la ligne physcpubind: 0 1 ...
    cores=''
    sockets=''
    for l in numa_res:
        (h,s,t) = l.partition(':')
        if h=='physcpubind':
            cores=t
        if h=='nodebind':
            sockets=t
    
    cores=cores.strip().replace(' ',',')
    sockets=sockets.strip().replace(' ',',')

    # Recopier les variables d'environnement SLURM_TASKS_PER_NODE et SLURM_CPUS_PER_TASK
    msg  = 'export PLACEMENT_PHYSCPU="'+cores+'"; '
    msg += 'export PLACEMENT_NODE="'+sockets+'"; ';
    msg += 'export PLACEMENT_SLURM_TASKS_PER_NODE="'+os.environ['SLURM_TASKS_PER_NODE']+'"; '
    msg += 'export PLACEMENT_SLURM_CPUS_PER_TASK="'+os.environ['SLURM_CPUS_PER_TASK']+'"; '

    print msg
    
    return

###########################################################
# @brief Vérifie que les quatre variables d'environnement réglementaires sont bien activées
#
###########################################################
def check_mpi_aware():
    if os.environ.has_key('PLACEMENT_PHYSCPU') and os.environ.has_key('PLACEMENT_NODE') and os.environ.has_key('PLACEMENT_SLURM_TASKS_PER_NODE') and os.environ.has_key('PLACEMENT_SLURM_CPUS_PER_TASK'):
        return

    msg =  'OUPS - Je ne suis pas vraiment mpi_aware, il me manque quelques variables d\'environnement\n'
    msg += '       Avez-vous mis la commande $(placement --make_mpi_aware) AVANT l\'appel mpi ?'
    raise PlacementException(msg)

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

###########################################################
# @brief imprime les variables d'nevironnement utiles
#
###########################################################
def show_env():
    msg = "Current important environment variables...\n\n"
    for v in ['PLACEMENT_PARTITION','HOSTNAME','SLURM_NNODES','SLURM_NODELIST','SLURM_TASKS_PER_NODE','SLURM_CPUS_PER_TASK',
              'PLACEMENT_NODE','PLACEMENT_PHYSCPU','PLACEMENT_SLURM_TASKS_PER_NODE','PLACEMENT_SLURM_CPUS_PER_TASK']:
        try:
            msg += v
            msg += ' = '
            msg += bold() + os.environ[v] + normal()
            msg += '\n'
        except KeyError:
            msg += '<not specified>\n'
    
    print msg

##########################################################
# @brief Calcule les structures de données en vérifiant le taskset ou le ps sur un programme en exécution
#
# @param options Les switches de la ligne de commande
# @param args (non utilisé)
# @param Le hardware
#
# @return Un tableau de tableaux: les taches, les coeurs utilisés, les coeurs en conflit, l'architecture
#
##########################################################
def compute_data_from_running(options,args,hard):
    path = options.check

    # Vérifie qu'au moins une sortie est programmée, sinon force le mode --ascii
    #if options.asciiart==False and options.verbose==False:
    #    options.asciiart = True

    if options.taskset == True:
        buildTasksBound = BuildTasksBoundFromTaskSet()
    else:
        buildTasksBound = BuildTasksBoundFromPs()

    task_distrib = RunningMode(path,hard,buildTasksBound,options.memory)

    return task_distrib


##########################################################
# @brief Calcule les structures de données à partir des paramètres de la ligne de commande
#
# @param options Les switches de la ligne de commande
# @param args (non utilisé)
# @param Le hardware
#
# @return Un tableau de tableaux: les taches, les coeurs utilisés, les coeurs en conflit, l'architecture
#
##########################################################
def compute_data_from_parameters(options,args,hard):
    over_cores = None
    [cpus_per_task,tasks] = computeCpusTasksFromEnv(options,args)
    hyper = options.hyper or options.hyper_phys
    if hard.IS_SHARED:
        archi = Shared(hard, cpus_per_task, tasks, hyper)
    else:
        archi = Exclusive(hard, cpus_per_task, tasks, hyper)
            
    task_distrib = ""
    if options.mode == "scatter":
        task_distrib = ScatterMode(archi)
    elif options.mode == "scatter_cyclic":
        task_distrib = ScatterMode(archi)
    elif options.mode == "scatter_block":
        task_distrib = ScatterBlockMode(archi)
    else:
        if options.hyper_phys == True:
            task_distrib = CompactPhysicalMode(archi)
        else:
            task_distrib = CompactMode(archi)
            
    #tasks_bound = task_distrib.distribTasks()

    # Trie les threads et renvoie task_distrib
    task_distrib.threadsSort()

    # En mpi_aware, on ne garde que la tache correspondant au rang mpi
    if options.mpiaware == True:
        task_distrib.keepOnlyMpiRank()

    return task_distrib

def newEpilog():
    cat     = hardware.Hardware.catalog()
    epilog  = 'Environment:'
    epilog += "PLACEMENT_PARTITION " + str(cat[1]) + " "
    epilog += "SLURM_NODELIST or HOSTNAME should match with one of " +str(cat[0])
    epilog += " Consider also SLURM_TASKS_PER_NODE, SLURM_CPUS_PER_TASK"
    return epilog

if __name__ == "__main__":
    main()
