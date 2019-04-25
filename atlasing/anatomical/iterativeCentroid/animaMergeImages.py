#!/usr/bin/python
# Warning: works only on unix-like systems, not windows where "python animaAnatomicalMergeImages.py ..." has to be run

import argparse
import os
import sys
import glob
from subprocess import call
import shutil

if sys.version_info[0] > 2:
    import configparser as ConfParser
else:
    import ConfigParser as ConfParser

configFilePath = os.path.expanduser("~") + "/.anima/config.txt"
if not os.path.exists(configFilePath):
    print('Please create a configuration file for Anima python scripts. Refer to the README')
    quit()

configParser = ConfParser.RawConfigParser()
configParser.read(configFilePath)

animaDir = configParser.get("anima-scripts", 'anima')

# Argument parsing
parser = argparse.ArgumentParser(
    description="Builds a new average anatomical form from previously registered images.")
parser.add_argument('-d', '--ref-dir', type=str, required=True, help='Reference (working) folder')
parser.add_argument('-B', '--prefix-base', type=str, required=True, help='Prefix base')
parser.add_argument('-p', '--prefix', type=str, required=True, help='Prefix')
parser.add_argument('-i', '--num-iter', type=int, required=True, help='Iteration number of atlas creation')
parser.add_argument('-c', '--num-cores', type=int, default=40, help='Number of cores to run on')

args = parser.parse_args()
os.chdir(args.ref_dir)

animaAverageImages = os.path.join(animaDir,"animaAverageImages")

myfile = open("avgImg.txt","w")
for a in range(1,args.num_iter + 1):
    myfile.write(os.path.join("tempDir",args.prefix + "_" + str(a) + "_at.nii.gz") + "\n")

myfile.close()

command = [animaAverageImages, "-i", "avgImg.txt","-o","averageForm" + str(args.num_iter) +".nii.gz"]

call(command)


# if os.path.exists("averageForm" + str(args.num_iter) + ".nii.gz"):
#     open("it_" + str(args.num_iter) + "_done","w").close()
#     t = args.num_iter + 1
#     if os.path.exists("iterRun_" + str(t)):
#         shutil.rmtree("residualDir")
#         shutil.rmtree("tempDir")
#         os.makedirs('tempDir')
#         os.makedirs('residualDir')
#         os.remove("iterRun_" + str(args.num_iter))
   