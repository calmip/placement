#! /usr/bin/env python
# -*- coding: utf-8 -*-

################################################################
# Ce script peut vous aider à placer vos tâches sur les coeurs
#
# CALMIP - 2015
#
# Commencez par: placement --help 
#
# Exemple: 4 processus, 8 threads par processus, hyperthreading activé
#
# Switch -H: Renvoie l'affectation des cores aux processes de manière lisible par les humains:
#
# placement.py -H 4 8 2
# [ 0 20 1 21 2 22 3 23 ]
# [ 10 30 11 31 12 32 13 33 ]
# [ 4 24 5 25 6 26 7 27 ]
# [ 14 34 15 35 16 36 17 37 ]
#
# Switch -A: Renvoie l'affectation des cores aux processes de manière cartographique::
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
# Switch -R: Renvoie le switch prêt à insérer dans votre commande srun:
#
# ./placement.py -R 4 8 2
#--cpu_bind=mask_cpu:0xf0000f,0x3c0003c00,0xf0000f0,0x3c0003c000 
#
# Dans les scripts on peut donc mettre:
#
# srun $(placement.py -R 4 8 2)
#        
# emmanuel.courcelle@inp-toulouse.fr
# http://www.calmip.univ-toulouse.fr
################################################################

from optparse import OptionParser

# Variables liées à notre architecture: BULLx DLC, 
# soit 612 nœuds, chacun 2 procs Intel Ivybridge 10 cœurs
sockets=2
cores_per_socket=10

def examples():
    print "not yet written"

#
# Réécrit le placement pour une tâche (appelé par getCpuBindingSrun)
# Réécriture sous forme hexadécimale pour srun
#
# Params: threads_per_core (1/2, HTOFF/ON)
#         cores (un tableau d'entiers représentant les cœurs)
# Return: Le tableau de tableaux réécrit en hexa
#
def getCpuTaskMachineBinding(threads_per_core,cores):
    i = 1
    rvl = 0
    for j in range(sockets*cores_per_socket*threads_per_core):
        if (j in cores):
            rvl += i
        i = 2 * i
    return hex(rvl)

#
# Réécrit le placement pour une tâche (appelé par getCpuBinding)
# Réécriture de manière "humainement lisible"
#
# Params: threads_per_core (1/2, HTOFF/ON)
#         cores (un tableau d'entiers représentant les cœurs)
# Return: Le tableau de tableaux réécrit en chaine de caractères
#
def getCpuTaskHumanBinding(threads_per_core,cores):
    rvl="# [ "
    sorted_cores = cores
    sorted_cores.sort()
    for c in sorted_cores:
        rvl+=str(c)
        rvl += ' '
    rvl+="]\n"
    return rvl

#
# Réécrit le placement pour une tâche (appelé par getCpuBinding)
# Réécriture en "art ascii" représentant l'architecture processeur
#
# Params: threads_per_core (1/2, HTOFF/ON)
#         cores (un tableau d'entiers représentant les cœurs)
# Return: Une ou deux lignes, deux fois 10 colonnes séparées par un espace (pour 2 sockets de 10 cœurs)
#
def getCpuTaskAsciiBinding(threads_per_core,cores):
    rvl = ""
    for l in range(threads_per_core):
        if (threads_per_core>1):
            if l==0:
                rvl += '# /'
            else:
                rvl += '# \\'

        for j in range(sockets):
            for k in range(cores_per_socket):
                if (l*cores_per_socket*sockets+j*cores_per_socket+k in cores):
                    rvl += 'X'
                else:
                    rvl += '.'
            rvl += " "
        rvl += "\n"
    return rvl

#
# Appel de fct pour chaque élément de tasks_binding
# concatène et renvoie les retours de fct
#
def getCpuBinding(threads_per_core,tasks_binding,fct):
    rvl = ""
    for t in tasks_binding:
        rvl += fct(threads_per_core,t)
    return rvl

#
# Réécriture de tasks_binding sous forme de paramètres hexadécimaux pour srun
#
# Params = threads_per_core (passé à getCpuTasksMachineBinding), tasks_binding
# Return = La chaine de caractères à afficher
#    
def getCpuBindingSrun( threads_per_core,tasks_binding):
    mask_cpus=[]
    for t in tasks_binding:
        mask_cpus += [getCpuTaskMachineBinding(threads_per_core,t)]

    return "--cpu_bind=mask_cpu:" + ",".join(mask_cpus)

#
# Valide les paramètres d'entrée, lève une exception avec un message clair si pas corrects
#
# On vérifie que les paramètres ne sont pas trop grands ou trop petits
# En particulier, si le nombre tasks*threads_per_task est < 10, on n'est pas sur la partition exclusive
#
# On refuse les tâches à cheval sur deux sockets, sauf s'il n'y a qu'une tâche 
# (tâche unique avec 20 threads: OK, 5 tâches de 4 threads, HTOFF: NON)
#
def checkBuildParameters(threads_per_core,threads_per_task,tasks):
    if (threads_per_core<0 or threads_per_task<0 or tasks<0 ):
        raise Exception("OUPS - Tous les paramètres doivent être entiers positifs")

    if threads_per_core > 2:
        raise Exception("OUPS - threads_per_core doit être <= 2 (pas " + str(threads_per_core) + ")")

    if threads_per_task%threads_per_core!=0:
        raise Exception("OUPS - threads_per_task => doit être multiple de threads_per_core")

    if threads_per_task*tasks<=10:
        raise Exception("OUPS - moins de 10 cœurs utilisés: partition shared, placement non supporté")

    if tasks>1 and threads_per_task>threads_per_core*cores_per_socket:
        raise Exception("OUPS - Votre task déborde du socket, threads_per_task doit être <= "+str(threads_per_core*cores_per_socket))
    if threads_per_task*tasks>threads_per_core*cores_per_socket*sockets:
        raise Exception("OUPS - Pas assez de cores ! Diminuez threads_per_task ou tasks")

    # max_tasks calculé ainsi permet d'être sûr de ne pas avoir une tâche entre deux sockets, 
    max_tasks = sockets * (cores_per_socket*threads_per_core/threads_per_task)
    if threads_per_task>1:
        if tasks>max_tasks and max_tasks>0:
            raise Exception("OUPS - Une task est à cheval sur deux sockets ! Diminuez tasks, le maximum est " + str(max_tasks))

#
# Construit le tableau de tableaux tasks_binding à partir des paramètres
# Params: threads_per_core (HT ON/OFF, soit 2/1), threads_per_task et tasks        
# Return: tasks_binding, un tableau de tableaux:
#         Le tableau des proceses, chaque process est représenté par un tableau de cœurs.
#
def buildTasksBinding(threads_per_core,threads_per_task,tasks):
    checkBuildParameters(threads_per_core,threads_per_task,tasks)

    # c_step est l'épaisseur des "tranches de coeurs", c_max le nombre de tranches par socket
    # Pour 10 coeurs/socket, 4 threads/task, ht OFF -> c_step = 4, 2 itérations
    # Pour 10 coeurs/socket, 4 threads/task, ht ON  -> c_step = 2, 5 itérations
    c_step = threads_per_task / threads_per_core
    tasks_binding=[]
    t = 0
    for c in range(0,cores_per_socket,c_step):
        for s in range(sockets):
            t_binding=[]
            for h in range(threads_per_task/threads_per_core):
                for y in range(threads_per_core):
                    t_binding += [y*cores_per_socket*sockets + s*cores_per_socket + c + h]
            tasks_binding += [t_binding]
            t += 1
            if (t==tasks):
                return tasks_binding

    # normalement on ne passe pas par là on a déjà retourné
    return tasks_binding

    
def main():

    parser = OptionParser(version="%prog 1.0",usage="%prog [options] tasks threads_per_task threads_per_core")
    parser.add_option("-E","--examples",action="store_true",dest="example",help="Print some examples")
    parser.add_option("-H","--human",action="store_true",default=False,dest="human",help="Output humanly readable (%default)")
    parser.add_option("-A","--ascii-art",action="store_true",default=False,dest="asciiart",help="Output geographically readable (%default)")
    parser.add_option("-R","--srun",action="store_true",default=False,dest="srun",help="Output srunnally readable (%default)")
    (options, args) = parser.parse_args()

    # Valeurs par défaut
    threads_per_core = 1
    threads_per_task = 4
    tasks            = 4
    
    if len(args) >= 3:
        threads_per_core = int(args[2])
    if len(args) >= 2:
        threads_per_task = int(args[1])
    if len(args) >= 1:
        tasks            = int(args[0])

    try:
        tasks_binding = buildTasksBinding(threads_per_core, threads_per_task, tasks)
    except Exception, e:
        print e
        exit(1)

    if options.example==True:
        examples()
        exit(0)

# Imprime le binding de manière compréhensible pour les humains
    if options.human==True:
        print getCpuBinding(threads_per_core,tasks_binding,getCpuTaskHumanBinding)
    
# Imprime le binding en ascii art
    if options.asciiart==True:
        print getCpuBinding(threads_per_core,tasks_binding,getCpuTaskAsciiBinding)
    
# Imprime le binding de manière compréhensible pour srun
    if options.srun==True:
        print getCpuBindingSrun(threads_per_core,tasks_binding)

if __name__ == "__main__":
    main()
