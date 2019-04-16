#!/usr/bin/python
# Warning: works only on unix-like systems, not windows where "python animaBuildAnatomicalAtlas.py ..." has to be run

import argparse
import os
import glob
import sys
import subprocess
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
animaScriptsDir = configParser.get("anima-scripts", 'anima-scripts-public-root')

# Argument parsing
parser = argparse.ArgumentParser(
    description="Builds and runs a series of scripts on an OAR cluster to construct an anatomical atlas (unbiased up to an affine or rigid transform, with different or equal weights).")
parser.add_argument('-p', '--data-prefix', type=str, required=True, help='Data prefix (including folder)')
parser.add_argument('-i', '--num-iterations', type=int, default=8, help='Number of iterations (default: 8)')
parser.add_argument('-n', '--num-images', type=int, required=True, help='Number of images in the atlas')
parser.add_argument('-c', '--num-cores', type=int, default=8, help='Number of cores to run on (default: 8)')
parser.add_argument('-b', '--bch-order', type=int, default=2, help='BCH order when composing transformations in rigid unbiased (default: 2)')
parser.add_argument('-w', '--weights-file', type=str, default="", help='Link to weights file if needed, otherwise using equal weights (default: none)')
parser.add_argument('--rigid', action='store_true', help="Unbiased atlas up to a rigid transformation")

args = parser.parse_args()

if not os.path.exists('tempDir'):
    os.makedirs('tempDir')

if os.path.exists('residualDir'):
    shutil.rmtree("residualDir")

os.makedirs('residualDir')

ref = args.data_prefix + '_1'
prefixBase = os.path.dirname(args.data_prefix)
prefix = os.path.basename(args.data_prefix)

# In the first iteration we take the first image as reference, then it is used in the dataset
firstImage = 2
previousMergeId = 0

for k in range(1,args.num_iterations + 1):
    if os.path.exists('it_' + str(k) + '_done'):
        ref = "averageForm" + str(k)
        firstImage = 1
        continue

    print("*************Iteration " + str(k) + ", processing reference: " + ref)

    map(os.remove, glob.glob("residualDir/" + prefix + '_*_nl_tr.nii.gz'))
    map(os.remove, glob.glob("residualDir/" + prefix + '_*_flag'))

    numJobs = args.num_images - firstImage + 1
    nCoresPhysical = int(args.num_cores / 2)

    fileName = 'iterRun_' + str(k)
    myfile = open(fileName,"w")
    myfile.write("#!/bin/bash\n")
    if args.num_cores<=16:
        myfile.write("#OAR -l {hyperthreading=\'NO\'}/nodes=1/core=" + str(args.num_cores) + ",walltime=01:59:00\n")
    myfile.write("#OAR -l {hyperthreading=\'YES\'}/nodes=1/core=" + str(nCoresPhysical) + ",walltime=01:59:00\n")
    myfile.write("#OAR --array " + str(numJobs) + "\n")
    myfile.write("#OAR -O " + os.getcwd() + "/reg-" + str(k) + ".%jobid%.output\n")
    myfile.write("#OAR -E " + os.getcwd() + "/reg-" + str(k) + ".%jobid%.error\n")

    myfile.write("cd " + os.getcwd() + "\n")

    if k == 1:
        myfile.write("let index=${OAR_ARRAY_INDEX}+1\n")
        myfile.write(os.path.join(animaScriptsDir,"atlasing/anatomical/animaAnatomicalRegisterImage.py") +
                     " -d " + os.getcwd() + " -r " + ref + ".nii.gz -B " + prefixBase + " -p " + prefix +
                     " -n $index -b " + str(args.bch_order) + " -c " + str(args.num_cores))
    else:
        myfile.write(os.path.join(animaScriptsDir,"atlasing/anatomical/animaAnatomicalRegisterImage.py") +
                     " -d " + os.getcwd() + " -r " + ref + ".nii.gz -B " + prefixBase + " -p " + prefix +
                     " -n $OAR_ARRAY_INDEX -b " + str(args.bch_order) + " -c " + str(args.num_cores))

    if args.rigid is True:
        myfile.write(" --rigid\n")
    else:
        myfile.write("\n")

    myfile.close()
    os.chmod(fileName, 0755)

    oarRunCommand = ["oarsub"]
    if previousMergeId == 0:
        oarRunCommand += ["-n","reg-" + str(k),"-S", os.getcwd() + "/iterRun_" + str(k)]
    else:
        oarRunCommand += ["-n","reg-" + str(k),"-a",str(previousMergeId),"-S", os.getcwd() + "/iterRun_" + str(k)]

    jobsIds = []
    procStat = subprocess.Popen(oarRunCommand, stdout=subprocess.PIPE)
    for statsLine in procStat.stdout:
        if "OAR_JOB_ID" in statsLine:
            jobsIds += [statsLine.split("=")[1]]

    fileName = 'mergeRun_' + str(k)
    myfile = open(fileName,"w")
    myfile.write("#!/bin/bash\n")
    if args.num_cores<=16:
        myfile.write("#OAR -l {hyperthreading=\'NO\'}/nodes=1/core=" + str(args.num_cores) + ",walltime=01:59:00\n")
    myfile.write("#OAR -l {hyperthreading=\'YES\'}/nodes=1/core=" + str(nCoresPhysical) + ",walltime=01:59:00\n")
    myfile.write("#OAR -O " + os.getcwd() + "/merge-" + str(k) + ".%jobid%.output\n")
    myfile.write("#OAR -E " + os.getcwd() + "/merge-" + str(k) + ".%jobid%.error\n")

    myfile.write("cd " + os.getcwd() + "\n")
    myfile.write(os.path.join(animaScriptsDir,"atlasing/anatomical/animaAnatomicalMergeImages.py") +
                 " -d " + os.getcwd() + " -B " + prefixBase + " -p " + prefix + " -i " + str(k) +
                 " -n " + str(args.num_images) + " -r " + ref + " -c " + str(args.num_cores))

    if not args.weights_file == "":
        myfile.write(" -w " + args.weights_file + "\n")
    else:
        myfile.write("\n")

    myfile.close()
    os.chmod(fileName, 0755)

    oarRunCommand = ["oarsub","-n","merge-" + str(k),"-S",os.getcwd() + "/mergeRun_" + str(k)]

    for jobId in jobsIds:
        oarRunCommand += ["-a",jobId]

    procStat = subprocess.Popen(oarRunCommand, stdout=subprocess.PIPE)
    for statsLine in procStat.stdout:
        if "OAR_JOB_ID" in statsLine:
            previousMergeId = statsLine.split("=")[1]
            break

    ref = "averageForm" + str(k)
    firstImage = 1
