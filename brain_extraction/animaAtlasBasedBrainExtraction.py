#!/usr/bin/python
# Warning: works only on unix-like systems, not windows where "python animaAtlasBasedBrainExtraction.py ..." has to be run

import sys

if sys.version_info[0] > 2 :
	import configparser as ConfParser
else :
	import ConfigParser as ConfParser
	
import glob
import os
import shutil
from subprocess import call

configFilePath = os.path.expanduser("~") + "/.anima/config.txt"
if not os.path.exists(configFilePath) :
	print('Please create a configuration file for Anima python scripts. Refer to the README')
	quit()

configParser = ConfParser.RawConfigParser()
configParser.read(configFilePath)

animaDir = configParser.get("anima-scripts",'anima')
animaExtraDataDir = configParser.get("anima-scripts",'extra-data-root')

if len(sys.argv) < 2:
	print('Computes the brain mask of images given in input by registering a known atlas on it. Their output is prefix_brainMask.nrrd and prefix_masked.nrrd.')
	quit()

numImages = len(sys.argv) - 1
atlasImage = animaExtraDataDir + "icc_atlas/Reference_T1.nrrd"
iccImage = animaExtraDataDir + "icc_atlas/BrainMask.nrrd"

for brainImage in sys.argv[1:] :
	print("Brain masking image: " + brainImage)

	# Get floating image prefix
	brainImagePrefix = os.path.splitext(brainImage)[0]
	if os.path.splitext(brainImage)[1] == '.gz' :
		brainImagePrefix = os.path.splitext(brainImagePrefix)[0]

	command = [animaDir + "animaPyramidalBMRegistration","-m",atlasImage,"-r",brainImage,"-o",brainImagePrefix + "_rig.nrrd","-O",brainImagePrefix + "_rig_tr.txt","-p","4","-l","1","--sp","3"]
	call(command)

	command = [animaDir + "animaPyramidalBMRegistration","-m",atlasImage,"-r",brainImage,"-o",brainImagePrefix + "_aff.nrrd","-O",brainImagePrefix + "_aff_tr.txt","-i",brainImagePrefix + "_rig_tr.txt","-p","4","-l","1","--sp","3","--ot","2"]
	call(command)

	command = [animaDir + "animaDenseSVFBMRegistration","-r",brainImage,"-m",brainImagePrefix + "_aff.nrrd","-o",brainImagePrefix + "_nl.nrrd","-O",brainImagePrefix + "_nl_tr.nrrd","-p","4","-l","1","--sr","1"]
	call(command)

	command = [animaDir + "animaTransformSerieXmlGenerator","-i",brainImagePrefix + "_aff_tr.txt","-i",brainImagePrefix + "_nl_tr.nrrd","-o",brainImagePrefix + "_nl_tr.xml"]
	call(command)

	command = [animaDir + "animaApplyTransformSerie","-i",iccImage,"-t",brainImagePrefix + "_nl_tr.xml","-g",brainImage,"-o",brainImagePrefix + "_brainMask.nrrd","-n","nearest"]
	call(command)

	command = [animaDir + "animaMaskImage","-i",brainImage,"-m",brainImagePrefix + "_brainMask.nrrd","-o",brainImagePrefix + "_masked.nrrd"]
	call(command)

map(os.remove, glob.glob("*_rig*"))
map(os.remove, glob.glob("*_aff*"))
map(os.remove, glob.glob("*_nl*"))
