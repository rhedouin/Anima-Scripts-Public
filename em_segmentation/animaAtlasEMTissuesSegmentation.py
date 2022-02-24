#!/usr/bin/python3
# Warning: works only on unix-like systems, not windows where "python3 animaAtlasEMTissuesSegmentation.py ..." has to be run

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
import uuid

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
animaTissuesEMClassification = os.path.join(animaDir, "animaTissuesEMClassification")
animaConvertImage = os.path.join(animaDir, "animaConvertImage")
animaMaskImage = os.path.join(animaDir, "animaMaskImage")
animaThrImage = os.path.join(animaDir, "animaThrImage")
animaN4BiasCorrection = os.path.join(animaDir, "animaN4BiasCorrection")
animaMorphologicalOperations = os.path.join(animaDir, "animaMorphologicalOperations")

# Argument parsing
parser = argparse.ArgumentParser(
    description="Computes tissue segmentation from a prior atlas, multiple modalities inputs, and "
                "EM tissue classification")

parser.add_argument('-i', '--input', type=str, required=True, action='append',
                    help='Image input: can give multiple modalities')
parser.add_argument('-a', '--atlas', type=str, help='Atlas folder (default: use the one in anima scripts data '
                                                    '- em_prior_atlas folder)')
parser.add_argument('-m', '--mask', type=str, required=True, help='Brain mask of the first input')

parser.add_argument('-o', '--output', type=str, help='Output path of the tissues segmentation '
                                                     '(default is inputName_classification.nrrd)')
parser.add_argument('-O', '--classes-output', type=str, help='Output path of the tissues probabilities')
parser.add_argument('-z', '--zsc', type=str, help='Output path of the zscores of classification')
parser.add_argument('-K', '--keep-intermediate-folder', action='store_true',
                    help='Keep intermediate folder after script end')
parser.add_argument('-P', '--prune-outliers', action='store_true',
                    help='Remove outliers from the segmentation (according to z-score)')
parser.add_argument('-Z', '--zsc-thr', type=int, default=4,
                    help='Outliers threshold if -P is activated (default: 4)')

args = parser.parse_args()

numImages = len(sys.argv) - 1

atlasDir = os.path.join(animaExtraDataDir,"em_prior_atlas")
if args.atlas:
    atlasDir = args.atlas

atlasImage = os.path.join(atlasDir,"T1.nrrd")
tissuesImage = os.path.join(atlasDir,"Tissue_Probabilities.nrrd")

brainImages = args.input

# Get floating image prefix
brainImagePrefix = os.path.splitext(brainImages[0])[0]
if os.path.splitext(brainImages[0])[1] == '.gz':
    brainImagePrefix = os.path.splitext(brainImagePrefix)[0]

tissuesOutputName = args.output if args.output else brainImagePrefix + "_classification.nrrd"
intermediateFolder = os.path.join(os.path.dirname(brainImages[0]), 'em_tissues_' + str(uuid.uuid1()))

if not os.path.isdir(intermediateFolder):
    os.mkdir(intermediateFolder)

brainImagePrefix = os.path.join(intermediateFolder, os.path.basename(brainImagePrefix))

# Decide on whether to use large image setting or small image setting
command = [animaConvertImage, "-i", brainImages[0], "-I"]
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

# First preprocess input images
myfileImages = open(os.path.join(intermediateFolder,"listData.txt"),"w")
for i in range(0,len(brainImages)):
    currentData = brainImages[i]
    if i > 0:
        command = [animaPyramidalBMRegistration, "-m", currentData,
                   "-r", brainImages[0],
                   "-o", brainImagePrefix + "_rig_onRef_" + str(i) + ".nrrd", "--sp", "3"] + pyramidOptions
        call(command)

        currentData = brainImagePrefix + '_rig_onRef_' + str(i) + '.nrrd'

    command = [animaMaskImage, "-i", currentData, "-m", args.mask,
               "-o", brainImagePrefix + '_masked_' + str(i) + '.nrrd']
    call(command)

    command = [animaN4BiasCorrection, "-i", brainImagePrefix + '_masked_' + str(i) + '.nrrd',
               "-o", brainImagePrefix + '_biasCorrected_' + str(i) + '.nrrd']
    call(command)

    myfileImages.write(brainImagePrefix + '_biasCorrected_' + str(i) + '.nrrd\n')

myfileImages.close()

# Now register prior atlas onto first reference image
command = [animaPyramidalBMRegistration, "-m", atlasImage, "-r", brainImages[0], "-o", brainImagePrefix + "_rig.nrrd",
           "-O", brainImagePrefix + "_rig_tr.txt", "--sp", "3"] + pyramidOptions
call(command)

command = [animaPyramidalBMRegistration, "-m", atlasImage, "-r", brainImages[0], "-o", brainImagePrefix + "_aff.nrrd",
           "-O", brainImagePrefix + "_aff_tr.txt", "-i", brainImagePrefix + "_rig_tr.txt", "--sp", "3", "--ot",
           "2"] + pyramidOptions
call(command)

command = [animaDenseSVFBMRegistration, "-r", brainImages[0], "-m", brainImagePrefix + "_aff.nrrd",
           "-o", brainImagePrefix + "_nl.nrrd", "-O", brainImagePrefix + "_nl_tr.nrrd", "--tub", "2"] + pyramidOptions
call(command)

command = [animaTransformSerieXmlGenerator, "-i", brainImagePrefix + "_aff_tr.txt", "-i",
           brainImagePrefix + "_nl_tr.nrrd", "-o", brainImagePrefix + "_nl_tr.xml"]
call(command)

command = [animaApplyTransformSerie, "-i", tissuesImage, "-t", brainImagePrefix + "_nl_tr.xml", "-g", brainImages[0],
           "-o", brainImagePrefix + "_PriorTissues.nrrd"]
call(command)

# Finally, run classification step
command = [animaTissuesEMClassification, "-i", os.path.join(intermediateFolder,"listData.txt"),
           "-m", args.mask, "-t", brainImagePrefix + "_PriorTissues.nrrd", "-o", tissuesOutputName]

if args.classes_output:
    command = command + ["-O", args.classes_output]

zscOut = args.zsc

if not args.zsc and args.prune_outliers is True:
    zscOut = brainImagePrefix + "_zsc.nrrd"

if zscOut:
    command = command + ["-z", zscOut]

call(command)

if args.prune_outliers is True:
    command = [animaThrImage, "-i", zscOut, "-t", str(args.zsc_thr), "-o", brainImagePrefix + "_WrongMask.nrrd", "-I"]
    call(command)

    command = [animaMaskImage, "-i", tissuesOutputName, "-m", brainImagePrefix + "_WrongMask.nrrd",
               "-o", tissuesOutputName]
    call(command)

if not args.keep_intermediate_folder:
    rmtree(intermediateFolder)