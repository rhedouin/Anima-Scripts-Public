#!/bin/bash
# Parse configuration file located in ~/.anima/config.txt

configFile=~/.anima/config.txt

ANIMA_DIR=''
ROOT_DIR=''
ANIMA_EXTRA_DATA_DIR=''
IFS=$(echo -en "\n\b")

for data in `cat $configFile | sed "s/ = /=/g" | grep '='`
do
	key=`echo $data | awk -F\= '{print $1;}'`
	value=`echo $data | awk -F\= '{print $2;}'`

	if [ "$key" == "anima" ]; then
		ANIMA_DIR="$value"
	fi

	if [ "$key" == "anima-scripts-root" ]; then
		ROOT_DIR="$value"
	fi

	if [ "$key" == "extra-data-root" ]; then
		ANIMA_EXTRA_DATA_DIR=$value
	fi
done 

unset IFS
