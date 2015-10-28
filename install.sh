#! /bin/bash

[ "$1" = "" ] && echo "merde" && exit 1

DST=$1
BIN="$DST/bin"
LIB="$DST/lib/placement"

[ ! -d $BIN ] && echo "Pas de répertoire $BIN" && exit 1
[ ! -d $LIB ] && echo "Pas de répertoire $LIB" && exit 1

SRC=usr/local

for f in hardware.py architecture.py exception.py tasksbinding.py scatter.py compact.py running.py utilities.py
do
  cp $SRC/lib/placement/$f $LIB
done

cp $SRC/bin/placement.py $SRC/bin/placement $BIN/
chmod a=r,u+w $LIB/*
chmod a=rx,u+w $BIN/placement.py $BIN/placement

echo "C'est fait, man !"
