#! /bin/bash

[ "$1" = "" ] && echo "Usage: ./install.sh eoslogin1 /users/sysadmin/$(whoami)" && exit 1

EOS=$1
DST=$2
BIN="$DST/bin"
LIB="$DST/lib/placement"

ssh $EOS "[ ! -d $BIN ] && echo Pas de répertoire $BIN sur $EOS" && exit 1
ssh $EOS "[ ! -d $LIB ] && echo Pas de répertoire $LIB sur $EOS" && exit 1

SRC=usr/local

for f in hardware.py architecture.py exception.py tasksbinding.py scatter.py compact.py running.py utilities.py
do
  scp $SRC/lib/placement/$f "$EOS:$LIB"
done

scp $SRC/bin/placement.py $SRC/bin/placement "$EOS:$BIN"
ssh $EOS "chmod a=r,u+w $LIB/*"
ssh $EOS "chmod a=rx,u+w $BIN/placement.py $BIN/placement"

echo "C'est fait, man !"
