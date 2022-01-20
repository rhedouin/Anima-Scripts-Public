#!/usr/bin/python3

import argparse
import sys

if sys.version_info[0] > 2:
    import configparser as ConfParser
else:
    import ConfigParser as ConfParser

import os
import shutil
import uuid
from subprocess import call, check_output

configFilePath = os.path.join(os.path.expanduser("~"), ".anima",  "config.txt")
if not os.path.exists(configFilePath):
    print('Please create a configuration file for Anima python scripts. Refer to the README')
    quit()

configParser = ConfParser.RawConfigParser()
configParser.read(configFilePath)

animaDir = configParser.get("anima-scripts", 'anima')

parser = argparse.ArgumentParser(
    prog='animaMSExamPreparationMSSEG2016',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description="Registers and pre-processes input images of an MS patient sequence onto a common reference.")

parser.add_argument('-m', '--mask', required=True,
                    help='Path to the T1 derived intracranial mask (obtained from volBrain')
parser.add_argument('-f', '--flair', required=True, help='Path to the MS patient FLAIR image to register')
parser.add_argument('-t', '--t1', required=True, help='Path to the MS patient T1 image to register')
parser.add_argument('-g', '--t1-gd', required=True, help='Path to the MS patient T1-Gd image to register')
parser.add_argument('-T', '--t2', required=True, help='Path to the MS patient T2 image to register')
parser.add_argument('-p', '--pd', required=True, help='Path to the MS patient PD image to register')

parser.add_argument('-K', '--keep-intermediate-folder', action='store_true',
                    help='Keep intermediate folder after script end')

args = parser.parse_args()

tmpFolder = os.path.join(os.path.dirname(args.reference), 'ms_prepare_2016_' + str(uuid.uuid1()))

if not os.path.isdir(tmpFolder):
    os.mkdir(tmpFolder)

# Anima commands
animaPyramidalBMRegistration = os.path.join(animaDir, "animaPyramidalBMRegistration")
animaTransformSerieXmlGenerator = os.path.join(animaDir, "animaTransformSerieXmlGenerator")
animaApplyTransformSerie = os.path.join(animaDir, "animaApplyTransformSerie")
animaMaskImage = os.path.join(animaDir, "animaMaskImage")
animaNLMeans = os.path.join(animaDir, "animaNLMeans")
animaN4BiasCorrection = os.path.join(animaDir, "animaN4BiasCorrection")
animaConvertImage = os.path.join(animaDir, "animaConvertImage")

refImage = args.flair
listImages = [args.flair, args.t1, args.t1_gd, args.t2, args.pd]

# Decide on whether to use large image setting or small image setting
command = [animaConvertImage, "-i", refImage, "-I"]
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

refImagePrefix = os.path.splitext(refImage)[0]
if os.path.splitext(refImage)[1] == '.gz':
    refImagePrefix = os.path.splitext(refImagePrefix)[0]

# Register brain mask on reference
rigidRegistrationCommand = [animaPyramidalBMRegistration, "-r", refImage, "-m", args.t1, "-o",
                            os.path.join(tmpFolder, "t1Reg.nrrd"), "-O", os.path.join(tmpFolder, "t1Reg_tr.txt")] + pyramidOptions
call(rigidRegistrationCommand)

trsfGenCommand = [animaTransformSerieXmlGenerator, "-i", os.path.join(tmpFolder, "t1Reg_tr.txt"),
                  "-o", os.path.join(tmpFolder, "t1Reg_tr.xml")]
call(trsfGenCommand)

brainMask = refImagePrefix + "_brainMask.nii.gz"
maskTrsfCommand = [animaApplyTransformSerie, "-i", args.mask, "-t", os.path.join(tmpFolder, "t1Reg_tr.xml"),
                   "-g", refImage, "-o", brainMask, "-n", "nearest"]
call(maskTrsfCommand)

# Main loop
for i in range(0, len(listImages)):
    inputPrefix = os.path.splitext(listImages[i])[0]
    if os.path.splitext(listImages[i])[1] == '.gz':
        inputPrefix = os.path.splitext(inputPrefix)[0]

    nlmSecondImage = os.path.join(tmpFolder, "SecondImage_" + str(i) + "_nlm.nrrd")
    nlmCommand = [animaNLMeans, "-i", listImages[i], "-o", nlmSecondImage, "-n", "3"]
    call(nlmCommand)

    registeredDataFile = nlmSecondImage
    if not listImages[i] == args.flair:
        registeredDataFile = os.path.join(tmpFolder, "SecondImage_registered_" + str(i) + ".nrrd")
        registeredDataTrsf = os.path.join(tmpFolder, "SecondImage_registered_" + str(i) + "_tr.txt")
        registeredDataTrsfXml = os.path.join(tmpFolder, "SecondImage_registered_" + str(i) + "_tr.xml")
        rigidRegistrationCommand = [animaPyramidalBMRegistration, "-r", refImage, "-m", nlmSecondImage, "-o",
                                    registeredDataFile, "-O", registeredDataTrsf] + pyramidOptions
        call(rigidRegistrationCommand)

        trsfGenCommand = [animaTransformSerieXmlGenerator, "-i", registeredDataTrsf, "-o", registeredDataTrsfXml]
        call(trsfGenCommand)

        imTrsfCommand = [animaApplyTransformSerie, "-i", nlmSecondImage, "-t", registeredDataTrsfXml,
                           "-g", refImage, "-o", registeredDataFile, "-n", "sinc"]
        call(imTrsfCommand)

    maskedSecondImage = os.path.join(tmpFolder, "SecondImage_" + str(i) + "_masked.nrrd")
    secondMaskCommand = [animaMaskImage, "-i", registeredDataFile, "-m", brainMask, "-o", maskedSecondImage]
    call(secondMaskCommand)

    outputPreprocessedFile = inputPrefix + "_preprocessed.nii.gz"
    biasCorrectionCommand = [animaN4BiasCorrection, "-i", maskedSecondImage, "-o", outputPreprocessedFile]
    call(biasCorrectionCommand)

if not args.keep_intermediate_folder:
    shutil.rmtree(tmpFolder)
