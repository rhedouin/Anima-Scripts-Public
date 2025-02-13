#!/usr/bin/python3
# Warning: works only on unix-like systems, not windows where "python animaAtlasBasedBrainExtraction.py ..." has to be run

import sys
import argparse

if sys.version_info[0] > 2:
    import configparser as ConfParser
else:
    import ConfigParser as ConfParser

import glob
import os
from shutil import copyfile, rmtree
from subprocess import call, check_output
import tempfile

configFilePath = os.path.join(os.path.expanduser("~"), ".anima",  "config.txt")
if not os.path.exists(configFilePath):
    print('Please create a configuration file for Anima python scripts. Refer to the README')
    quit()

configParser = ConfParser.RawConfigParser()
configParser.read(configFilePath)

animaDir = configParser.get("anima-scripts", 'anima')
animaExtraDataDir = configParser.get("anima-scripts", 'extra-data-root')
animaPyramidalBMRegistration = os.path.join(animaDir, "animaPyramidalBMRegistration")
animaDenseSVFBMRegistration = os.path.join(animaDir, "animaDenseSVFBMRegistration")
animaTransformSerieXmlGenerator = os.path.join(animaDir, "animaTransformSerieXmlGenerator")
animaApplyTransformSerie = os.path.join(animaDir, "animaApplyTransformSerie")
animaConvertImage = os.path.join(animaDir, "animaConvertImage")
animaMaskImage = os.path.join(animaDir, "animaMaskImage")

# Argument parsing
parser = argparse.ArgumentParser(
    description="Computes the brain mask of images given in input by registering a known atlas on it. Their output is prefix_brainMask.nrrd and prefix_masked.nrrd")

parser.add_argument('-S', '--second-step', action='store_true',
                    help="Perform second step of atlas based cropping (might crop part of the external part of the brain)")

parser.add_argument('-i', '--input', type=str, required=True, help='File to process')
parser.add_argument('-m', '--mask', type=str, help='Output path of the brain mask (default is inputName_brainMask.nrrd)')
parser.add_argument('-b', '--brain', type=str, help='Output path of the masked brain (default is inputName_masked.nrrd)')
parser.add_argument('-f', '--intermediate_folder', type=str, help="""Path where intermediate files (transformations, transformed images and rough mask) are stored 
                    (default is an temporary directory created automatically and deleted after the process is finished ;
                    intermediate files are deleted by default and kept if this option is given).
                    """)

args = parser.parse_args()

numImages = len(sys.argv) - 1
atlasImage = animaExtraDataDir + "icc_atlas/Reference_T1.nrrd"
atlasImageMasked = animaExtraDataDir + "icc_atlas/Reference_T1_masked.nrrd"
iccImage = animaExtraDataDir + "icc_atlas/BrainMask.nrrd"

brainImage = args.input

if not os.path.exists(brainImage):
    sys.exit("Error: the image \"" + brainImage + "\" could not be found.")

print("Brain masking image: " + brainImage)

# Get floating image prefix
brainImagePrefix = os.path.splitext(brainImage)[0]
if os.path.splitext(brainImage)[1] == '.gz':
    brainImagePrefix = os.path.splitext(brainImagePrefix)[0]

brainMask = args.mask if args.mask else brainImagePrefix + "_brainMask.nrrd"
maskedBrain = args.brain if args.brain else brainImagePrefix + "_masked.nrrd"
intermediateFolder = args.intermediate_folder if args.intermediate_folder else tempfile.mkdtemp()

if not os.path.isdir(intermediateFolder):
    os.mkdir(intermediateFolder)

brainImagePrefix = os.path.join(intermediateFolder, os.path.basename(brainImagePrefix))

# Decide on whether to use large image setting or small image setting
command = [animaConvertImage, "-i", brainImage, "-I"]
convert_output = check_output(command, universal_newlines=True)
size_info = convert_output.split('\n')[1].split('[')[1].split(']')[0]
large_image = False
for i in range(0, 3):
    size_tmp = int(size_info.split(', ')[i])
    if size_tmp >= 350:
        large_image = True
        break

pyramidOptions = ["-p", "4", "-l", "1"]
if large_image:
    pyramidOptions = ["-p", "5", "-l", "2"]

# Rough mask with whole brain
command = [animaPyramidalBMRegistration, "-m", atlasImage, "-r", brainImage, "-o", brainImagePrefix + "_rig.nrrd",
           "-O", brainImagePrefix + "_rig_tr.txt", "--sp", "3"] + pyramidOptions
call(command)

command = [animaPyramidalBMRegistration, "-m", atlasImage, "-r", brainImage, "-o", brainImagePrefix + "_aff.nrrd",
           "-O", brainImagePrefix + "_aff_tr.txt", "-i", brainImagePrefix + "_rig_tr.txt", "--sp", "3", "--ot",
           "2"] + pyramidOptions
call(command)

command = [animaDenseSVFBMRegistration, "-r", brainImage, "-m", brainImagePrefix + "_aff.nrrd", "-o",
           brainImagePrefix + "_nl.nrrd", "-O", brainImagePrefix + "_nl_tr.nrrd", "--sr", "1"] + pyramidOptions
call(command)

command = [animaTransformSerieXmlGenerator, "-i", brainImagePrefix + "_aff_tr.txt", "-i",
           brainImagePrefix + "_nl_tr.nrrd", "-o", brainImagePrefix + "_nl_tr.xml"]
call(command)

command = [animaApplyTransformSerie, "-i", iccImage, "-t", brainImagePrefix + "_nl_tr.xml", "-g", brainImage, "-o",
           brainImagePrefix + "_rough_brainMask.nrrd", "-n", "nearest"]
call(command)

command = [animaMaskImage, "-i", brainImage, "-m", brainImagePrefix + "_rough_brainMask.nrrd", "-o",
           brainImagePrefix + "_rough_masked.nrrd"]
call(command)

brainImageRoughMasked = brainImagePrefix + "_rough_masked.nrrd"

if args.second_step is True:
    # Fine mask with masked brain
    command = [animaPyramidalBMRegistration, "-m", atlasImageMasked, "-r", brainImageRoughMasked, "-o",
               brainImagePrefix + "_rig.nrrd", "-O", brainImagePrefix + "_rig_tr.txt", "--sp", "3"] + pyramidOptions
    call(command)

    command = [animaPyramidalBMRegistration, "-m", atlasImageMasked, "-r", brainImageRoughMasked, "-o",
               brainImagePrefix + "_aff.nrrd", "-O", brainImagePrefix + "_aff_tr.txt", "-i",
               brainImagePrefix + "_rig_tr.txt", "--sp", "3", "--ot", "2"] + pyramidOptions
    call(command)

    command = [animaDenseSVFBMRegistration, "-r", brainImageRoughMasked, "-m", brainImagePrefix + "_aff.nrrd", "-o",
               brainImagePrefix + "_nl.nrrd", "-O", brainImagePrefix + "_nl_tr.nrrd", "--sr", "1"] + pyramidOptions
    call(command)

    command = [animaApplyTransformSerie, "-i", iccImage, "-t", brainImagePrefix + "_nl_tr.xml", "-g", brainImage, "-o",
               brainMask, "-n", "nearest"]
    call(command)

    command = [animaMaskImage, "-i", brainImage, "-m", brainMask, "-o", maskedBrain]
    call(command)
else:
    command = [animaConvertImage, "-i", brainImageRoughMasked, "-o", maskedBrain]
    call(command)
    command = [animaConvertImage, "-i", brainImagePrefix + "_rough_brainMask.nrrd", "-o", brainMask]
    call(command)

if args.intermediate_folder is None:
    rmtree(intermediateFolder)