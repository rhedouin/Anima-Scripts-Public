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

# Anima config
configFilePath = os.path.join(os.path.expanduser("~"), ".anima",  "config.txt")
if not os.path.exists(configFilePath):
    print('Please create a configuration file for Anima python scripts. Refer to the README')
    quit()

configParser = ConfParser.RawConfigParser()
configParser.read(configFilePath)

animaDir = configParser.get("anima-scripts", 'anima')
animaDataDir = configParser.get("anima-scripts", 'extra-data-root')
animaScriptsDir = configParser.get("anima-scripts", 'anima-scripts-public-root')

# ants config
configFilePath = os.path.join(os.path.expanduser("~"), ".ants",  "config.txt")
if not os.path.exists(configFilePath):
    print('Please create a configuration file for ants binaries.')
    quit()

configParser = ConfParser.RawConfigParser()
configParser.read(configFilePath)

antsDir = configParser.get("ants-bin", 'ants')

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
parser.add_argument('--atlas-name', type=str, default="", help='Atlas suffix output')

args = parser.parse_args()

animaPyramidalBMRegistration = os.path.join(animaDir, "animaPyramidalBMRegistration")
animaTransformSerieXmlGenerator = os.path.join(animaDir, "animaTransformSerieXmlGenerator")
animaApplyTransformSerie = os.path.join(animaDir, "animaApplyTransformSerie")

ANTS = os.path.join(antsDir, "ANTS")
WarpImageMultiTransform = os.path.join(antsDir, "WarpImageMultiTransform")

# Required
atlas = args.atlas
t1 = args.subject_t1
t1PrefixBase = os.path.dirname(args.subject_t1)
t1Prefix = os.path.basename(args.subject_t1).split(".")[0]

mv = args.subject_mv
mvPrefixBase = os.path.dirname(args.subject_mv)
mvPrefix = os.path.basename(args.subject_mv).split(".")[0]

dataNum = args.data_num

# Optionnal
label = args.label
outputFolder = args.output_folder
trsfFolder = args.trsf_folder
atlasName = args.atlas_name
atlasFolder = "Atlas_To_" + atlasName

# Create Trsf directory
os.makedirs(trsfFolder, exist_ok=True)

# Registration T1 subject -> atlas
print("BM")
bmRegistrationCommand = [animaPyramidalBMRegistration, "-r", atlas, "-m", t1,  "-o",  os.path.join(trsfFolder, label + "_T1_rigid2" + atlasName + "_" + dataNum + ".nii.gz"), "-O", os.path.join(trsfFolder, label + "_T1_rigid2" + atlasName + "_" + dataNum + ".txt"), "-p", "3", "-l", "0", "--sp", "2", "--ot", "2"]
call(bmRegistrationCommand)

print("ANTS")
antsRegistrationCommand = [ANTS, "3", "-m", "CC[" + atlas + "," + os.path.join(trsfFolder, label + "_T1_rigid2" + atlasName + "_" + dataNum + ".nii.gz") + ",1,4]", "-o", os.path.join(trsfFolder, label + "_T1_nl_tr_" + atlasName + "_" + dataNum), "-i", "75x75x10", "-r", "Gauss[3,0]", "-t", "SyN[0.25]", "--number-of-affine-iterations", "0"]
call(antsRegistrationCommand)

print("WarpImageMultiTransform")
warpImageCommand = [WarpImageMultiTransform, "3", os.path.join(trsfFolder, label + "_T1_rigid2" + atlasName + "_" + dataNum + ".nii.gz"), os.path.join(trsfFolder, label + "_T1_nl_" + dataNum + "_on" + atlasName + ".nii.gz"), "-R", atlas, os.path.join(trsfFolder, label + "_T1_nl_tr_" + atlasName + "_" + dataNum + "Warp.nii.gz"), os.path.join(trsfFolder, label + "_T1_nl_tr_" + atlasName + "_" + dataNum + "Affine.txt")]
call(warpImageCommand)

# Registration T0 subject -> T1 subject
print("BM")
bmRegistrationCommand = [animaPyramidalBMRegistration, "-r", mv, "-m", t1,  "-o",  os.path.join(trsfFolder, label + "_T1_rigid2T0_" + dataNum + ".nii.gz"), "-O", os.path.join(trsfFolder, label + "_T1_rigid2T0_" + dataNum + ".txt"), "-p", "3", "-l", "0", "--sp", "2", "--ot", "2"]
call(bmRegistrationCommand)

print("trsfGeneratorCommand")
trsfGeneratorCommand = [animaTransformSerieXmlGenerator, "-i", os.path.join(trsfFolder, label + "_T1_rigid2T0_" + dataNum + ".txt"), "-I", "1", "-i", os.path.join(trsfFolder, label + "_T1_rigid2" + atlasName + "_" + dataNum + ".txt"), "-I", "0", "-i", os.path.join(trsfFolder, label + "_T1_nl_tr_" + atlasName + "_" + dataNum + "Warp.nii.gz"), "-D", "-I", "0", "-o", os.path.join(trsfFolder, label + "_T0_transf_" + atlasName + "_" + dataNum + ".xlm")]
call(trsfGeneratorCommand)

os.makedirs(os.path.join(outputFolder, atlasFolder, "Transformed_T0"), exist_ok=True)
print("applyTransformCommand")
applyTransformCommand = [animaApplyTransformSerie, "-i", mv, "-g", atlas, "-t", os.path.join(trsfFolder, label + "_T0_transf_" + atlasName + "_" + dataNum + ".xlm"), "-o", os.path.join(outputFolder, atlasFolder, "Transformed_T0", label + "_DWI_" + dataNum + "T0_on" + atlasName + ".nii.gz")]
call(applyTransformCommand)










