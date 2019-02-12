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
parser.add_argument('-r', '--ref-image', type=str, required=True, help='Reference image')
parser.add_argument('-B', '--prefix-base', type=str, required=True, help='Prefix base')
parser.add_argument('-p', '--prefix', type=str, required=True, help='Prefix')
parser.add_argument('-w', '--weights', type=str, default="", help='Weights text file')
parser.add_argument('-b', '--bch-order', type=int, default=2, help='BCH order when composing transformations in rigid unbiased (default: 2)')
parser.add_argument('-n', '--num-images', type=int, required=True, help='Number of images')
parser.add_argument('-i', '--num-iter', type=int, required=True, help='Iteration number of atlas creation')
parser.add_argument('-c', '--num-cores', type=int, default=40, help='Number of cores to run on')

args = parser.parse_args()
os.chdir(args.ref_dir)

animaCreateImage = os.path.join(animaDir,"animaCreateImage")
animaAverageImages = os.path.join(animaDir,"animaAverageImages")
animaImageArithmetic = os.path.join(animaDir,"animaImageArithmetic")
animaTransformSerieXmlGenerator = os.path.join(animaDir,"animaTransformSerieXmlGenerator")
animaApplyTransformSerie = os.path.join(animaDir,"animaApplyTransformSerie")

# test if all images are here
nimTest = args.num_images
if args.num_iter == 1:
    nimTest -= 1

numData = len(glob.glob(os.path.join("residualDir",args.prefix + "_*_flag")))
while numData < nimTest:
    print("Missing data " + str(numData) + " " + str(nimTest))
    call(["sleep","600"])
    numData = len(glob.glob(os.path.join("residualDir", args.prefix + "_*_flag")))

# if ok proceed
if args.num_iter == 1:
    command = [animaCreateImage,"-o",os.path.join("tempDir",args.prefix + "_1_nonlinear_tr.nii.gz"),
               "-b","0","-g",os.path.join(args.prefix_base,args.prefix + "_1.nii.gz"),"-v","3"]
    call(command)

os.remove("refIms.txt")
os.remove("masksIms.txt")
os.remove("sumNonlinear.txt")

myfile = open("sumNonlinear.txt","w")
for a in range(1,args.num_images + 1):
    myfile.write(os.path.join(tempDir,args.prefix + "_" + str(a) + "_nonlinear_tr.nii.gz") + "\n")

myfile.close()

command = [animaAverageImages, "-i", "sumNonlinear.txt","-o",os.path.join("tempDir","sumNonlinear_tr.nii.gz")]
if not args.weights == "":
    command += ["-w",args.weights]

call(command)

command = [animaImageArithmetic,"-i",os.path.join("tempDir","sumNonlinear_tr.nii.gz"),"-M","-1",
           "-o",os.path.join("tempDir", "sumNonlinear_inv_tr.nii.gz")]
call(command)

myfileImages = open("refIms.txt","w")
myfileMasks = open("masksIms.txt","w")
for a in range(1,args.num_images+1):
    if a == 1 and args.num_iter == 1:
        command = [animaTransformSerieXmlGenerator,"-i",os.path.join("tempDir", "sumNonlinear_inv_tr.nii.gz"),
                   "-o",os.path.join("tempDir", "trsf_" + str(a) + ".xml")]
        call(command)
    else:
        command = [animaTransformSerieXmlGenerator,"-i",os.path.join("tempDir", args.prefix + "_" + str(a) + "_linear_tr.txt"),
                   "-i", os.path.join("tempDir",args.prefix + "_" + str(a) + "_nonlinear_tr.nii.gz"),
                   "-i",os.path.join("tempDir","sumNonlinear_inv_tr.nii.gz"),
                   "-o",os.path.join("tempDir","trsf_" + str(a) + ".xml")]
        call(command)

    command = [animaApplyTransformSerie,"-i",os.path.join(args.prefix_base,args.prefix + "_" + str(a) + ".nii.gz"),
               "-t",os.path.join("tempDir","trsf_" + str(a) + ".xml"),"-g",args.ref_image + ".nii.gz",
               "-o",os.path.join("tempDir",args.prefix + "_" + str(a) + "_at.nii.gz"),"-p",str(args.num_cores)]
    call(command)
    myfileImages.write(os.path.join("tempDir", args.prefix + "_" + str(a) + "_at.nii.gz"))

    if os.path.exists(os.path.join("Masks", "Mask_" + str(a) + ".nii.gz")):
        command = [animaApplyTransformSerie, "-i",os.path.join(args.prefix_base, "Mask_" + str(a) + ".nii.gz"),
                   "-t", os.path.join("tempDir","trsf_" + str(a) + ".xml"), "-g", args.ref_image + ".nii.gz",
                   "-o", os.path.join("tempDir","Mask_" + str(a) + "_at.nii.gz"),
                   "-n","nearest","-p", str(args.num_cores)]
        call(command)
        myfileMasks.write(os.path.join("tempDir","Mask_" + str(a) + "_at.nii.gz"))

myfileImages.close()
myfileMasks.close()

command = [animaAverageImages,"-i","refIms.txt","-o","averageForm" + str(args.num_iter) + ".nii.gz"]
if not args.weights == "":
    command += ["-w",args.weights]

if os.path.exists(os.path.join("Masks","Mask_1.nii.gz")):
    command += ["-m","masksIms.txt"]

call(command)

if os.path.exists("averageForm" + str(args.num_iter) + ".nii.gz"):
    open("it_" + str(args.num_iter) + "_done")
    t = args.num_iter + 1
    if os.path.exists("iterRun_" + str(t)):
        shutil.rmtree("residualDir")
        shutil.rmtree("tempDir")
        os.makedirs('tempDir')
        os.makedirs('residualDir')
        os.remove("iterRun_" + str(args.num_iter))
