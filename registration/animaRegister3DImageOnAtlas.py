#!/usr/bin/python3

import sys
import argparse

if sys.version_info[0] > 2:
    import configparser as ConfParser
else:
    import ConfigParser as ConfParser

import tempfile
import os
import shutil
import numpy as np
import nibabel as nib
from subprocess import call

configFilePath = os.path.join(os.path.expanduser("~"), ".anima",  "config.txt")
if not os.path.exists(configFilePath):
    print('Please create a configuration file for Anima python scripts. Refer to the README')
    quit()

configParser = ConfParser.RawConfigParser()
configParser.read(configFilePath)

animaDir = configParser.get("anima-scripts", 'anima')
animaDataDir = configParser.get("anima-scripts", 'extra-data-root')
animaScriptsDir = configParser.get("anima-scripts", 'anima-scripts-public-root')

# Argument parsing
parser = argparse.ArgumentParser(
    description="Given a set of DW images, arranges them for atlas construction: preprocessing, DTI and MCM "
                "computation, tracts start and end regions from tractseg")
parser.add_argument('-a', '--atlas', type=str, required=True, help='atlas t1')
parser.add_argument('-t', '--subject-t1', type=str, required=True, help='subject t1')
parser.add_argument('-m', '--subject-mv', type=str, required=True, help='subject moving image')
parser.add_argument('-l', '--label', type=str, required=False, default="",  help='suffix')
parser.add_argument('--data-num', type=str, required=True, default="",  help='subject data number')
parser.add_argument('--output-folder', type=str, default="", help='Specify a output folder')
parser.add_argument('--trsf-folder', type=str, default="Trsf", help='Specify a trsf folder name')

args = parser.parse_args()

animaPyramidalBMRegistration = os.path.join(animaDir, "animaPyramidalBMRegistration")
animaDenseSVFBMRegistration = os.path.join(animaDir, "animaDenseSVFBMRegistration")
animaTransformSerieXmlGenerator = os.path.join(animaDir, "animaTransformSerieXmlGenerator")
animaCropImage = os.path.join(animaDir, "animaCropImage")
animaMaskImage = os.path.join(animaDir, "animaMaskImage")
animaApplyTransformSerie = os.path.join(animaDir, "animaApplyTransformSerie")

# Required
atlas = args.atlas
t1 = args.subject_t1

t1Prefix = os.path.basename(args.subject_t1).split(".")[0]

mv = args.subject_mv
mvPrefixBase = os.path.dirname(args.subject_mv)
mvPrefix = os.path.basename(args.subject_mv).split(".")[0]

dataNum = args.data_num

# Optionnal
label = args.label
outputFolder = args.output_folder
trsfFolder = args.trsf_folder

# Create Trsf directory
os.makedirs(trsfFolder, exist_ok=True)

# Registration T1 subject -> atlas
bmRegistrationCommand = [animaPyramidalBMRegistration, "-r", atlas, "-m", t1,  "-o",  os.path.join(trsfFolder, label + "_T1_aff_MNI_" + dataNum + ".nii.gz"), "-O",  os.path.join(trsfFolder, label + "_T1_aff_MNI_" + dataNum + ".txt"), "-p", "3", "-l", "0", "--sp", "2", "--ot", "2"]
call(bmRegistrationCommand)

bmRegistrationCommand = [animaDenseSVFBMRegistration, "-r", atlas, "-m", os.path.join(trsfFolder, label + "_T1_aff_MNI_" + dataNum
 + ".nii.gz"),  "-o",  os.path.join(trsfFolder, label + "_T1_nl_MNI_" + dataNum + ".nii.gz"), "-O",  os.path.join(trsfFolder, label + "_T1_nl_tr_MNI_" + dataNum + ".nii.gz"), "--sr","1","--es","3","--fs","2","--sym-reg","2","--metric","1"]
call(bmRegistrationCommand)

trsfGeneratorCommand = [animaTransformSerieXmlGenerator, "-i", os.path.join(trsfFolder, label + "_T1_aff_MNI_" + dataNum + ".txt"), "-i", os.path.join(trsfFolder, label + "_T1_nl_tr_MNI_" + dataNum + ".nii.gz"), "-o", os.path.join(trsfFolder, label + "_T1_transf_MNI_" + dataNum + ".xlm")]
call(trsfGeneratorCommand)


# Registration T0 image -> T1 subject
bmRegistrationCommand = [animaPyramidalBMRegistration, "-r", mv, "-m", t1,  "-o",  os.path.join(trsfFolder, label + "_T1_rigid2T0_" + dataNum + ".nii.gz"), "-O", os.path.join(trsfFolder, label + "_T1_rigid2T0_" + dataNum + ".txt"), "-p", "3", "-l", "0", "--sp", "2", "--ot", "2"]
call(bmRegistrationCommand)

trsfGeneratorCommand = [animaTransformSerieXmlGenerator, "-i", os.path.join(trsfFolder, label + "_T1_rigid2T0_" + dataNum + ".txt"), "-I", "1", "-i", os.path.join(trsfFolder, label + "_T1_aff_MNI_" + dataNum + ".txt"), "-I", "0", "-i", os.path.join(trsfFolder, label + "_T1_nl_tr_MNI_" + dataNum + ".nii.gz"), "-I", "0", "-o", os.path.join(trsfFolder, label + "_T0_transf_MNI_" + dataNum + ".xlm")]
call(trsfGeneratorCommand)

# Now apply the transformation to T0
os.makedirs(os.path.join(outputFolder, 'Atlas_To_MNI'), exist_ok=True)
os.makedirs(os.path.join(outputFolder, 'Atlas_To_MNI', 'Transformed_T0'), exist_ok=True)

trsfT0Command = [animaApplyTransformSerie, "-i", mv, "-t", os.path.join(trsfFolder, label + "_T0_transf_MNI_" + dataNum + ".xlm"), "-g", atlas, "-o",  os.path.join(outputFolder, 'Atlas_To_MNI', 'Transformed_T0', mvPrefix + "_onMNI.nii.gz")]
call(trsfT0Command)









