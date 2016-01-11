#! /bin/bash

# bump.sh: définit le numéro de version
#          version => 1.X.Y
#                     X = Incrémenté lors des ajouts de fonctionnalités
#                     Y = Incrémenté lors des hotfixes
#

[ "$1" = "" ] && echo "Usage: ./bump.sh 1.X.Y" && exit 1

sed -r -e "s/version=\"%prog (.*)\"/version=\"%prog $1\"/" usr/local/bin/placement.py >usr/local/bin/placement.py.tmp
mv usr/local/bin/placement.py.tmp usr/local/bin/placement.py

