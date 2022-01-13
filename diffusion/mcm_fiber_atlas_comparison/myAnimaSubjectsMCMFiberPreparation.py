#!/usr/bin/python3

import sys
import argparse

if sys.version_info[0] > 2:
    import configparser as ConfParser
else:
    import ConfigParser as ConfParser

import tempfile
import glob
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

parser.add_argument('-n', '--num-subjects', type=int, required=True,
                    help="Number of subjects used for computing the atlas")
parser.add_argument('-s', '--start-subject', type=int, default=1, help="Subject to start with")

parser.add_argument('-i', '--dw-images-prefix', type=str, required=True, help='DW images prefix (folder + basename)')
parser.add_argument('-d', '--dw-dicom-folders-prefix', type=str, default="", help='Dicom folders prefixes (will append _n to them, where n is the image number)')
parser.add_argument('-t', '--t1-images-prefix', type=str, required=True, help='T1 images prefix (folder + basename)')

parser.add_argument('--type', type=str, default="tensor", help="Type of compartment model for fascicles (stick, zeppelin, tensor, noddi, ddi)")
parser.add_argument('--hcp', action='store_true',
                    help="Use HCP adapted models (with isotropic restricted and stationary water)")
parser.add_argument('--map', action='store_true',
                    help="Use prior on parameters? (MAP estimation)")

parser.add_argument('--dw-without-reversed-b0', action='store_true', help="No reversed B0 provided with the DWIs")

parser.add_argument('-b', '--bvalue-extract', type=int, default=0, help="Extract only a specific b-value for TractSeg (recommended for CUSP)")

parser.add_argument('--output-prefix', type=str, default="", help='Specify a name prefix')
parser.add_argument('--temp-folder', type=str, default="", help='Specify a temp folder')

args = parser.parse_args()

# The goal here is to prepare, from DWI data, the creation of an atlas with all data necessary for fiber atlas creation
# What's needed: a DWI folder (with bvecs and bvals attached, if unsure of bvecs: with dicoms attached in
# separated folders), a T13D images folder
# Things done:
# - preprocess using diffusion pre-processing script each DWI -> get tensors from that, brain masks and smooth DWIs
# - estimate MCM from smooth DWIs
# - run tractseg (registration to MNI, run tractseg, get begin and end regions, merge them and put them back on patient)
# - put all data in structure for atlas creation and post-processing. Folders will be:
#    - images: tensors for atlas creation
#    - Masks: DWI brain masks
#    - Tracts_Masks: masks for tractography from tractseg
#    - MCM: MCM estimations from DWI
# And that's it we're done, after that the DTI atlas may be created

animaComputeDTIScalarMaps = os.path.join(animaDir, "animaComputeDTIScalarMaps")
animaPyramidalBMRegistration = os.path.join(animaDir, "animaPyramidalBMRegistration")
animaTransformSerieXmlGenerator = os.path.join(animaDir, "animaTransformSerieXmlGenerator")
animaApplyTransformSerie = os.path.join(animaDir, "animaApplyTransformSerie")
animaImageArithmetic = os.path.join(animaDir, "animaImageArithmetic")
animaThrImage = os.path.join(animaDir, "animaThrImage")

os.makedirs('DTI', exist_ok=True)
os.makedirs('Preprocessed_DWI', exist_ok=True)
os.makedirs('MCM', exist_ok=True)

dwiPrefixBase = os.path.dirname(args.dw_images_prefix)
dwiPrefix = os.path.basename(args.dw_images_prefix)
t1PrefixBase = os.path.dirname(args.t1_images_prefix)
t1Prefix = os.path.basename(args.t1_images_prefix)
tractsegFATemplate = os.path.join(animaDataDir, "mni_template", "MNI_FA_template.nii.gz")

outputPrefix = args.output_prefix

for dataNum in range(args.start_subject, args.num_subjects + 1):
    print("Subject", str(dataNum))
#   Preprocess diffusion data
    preprocCommand = ["python3", os.path.join(animaScriptsDir,"diffusion","myAnimaDiffusionImagePreprocessing.py"), "-b", os.path.join(dwiPrefixBase, dwiPrefix + "_" + str(dataNum) + ".bval"),
                      "-t", os.path.join(t1PrefixBase, t1Prefix + "_" + str(dataNum) + ".nii.gz"),
                      "-i", os.path.join(dwiPrefixBase, dwiPrefix + "_" + str(dataNum) + ".nii.gz")]

    if not args.dw_without_reversed_b0:
        preprocCommand = preprocCommand + ["-r", os.path.join(dwiPrefixBase, dwiPrefix + "_" + str(dataNum) + "_reversed_b0.nii.gz")]

    if  args.dw_dicom_folders_prefix == "":
        preprocCommand = preprocCommand + ["-g", os.path.join(dwiPrefixBase, dwiPrefix + "_" + str(dataNum) + ".bvec")]
    else:
        dicomGlobFiles = glob.glob(os.path.join(args.dw_dicom_folders_prefix + "_" + str(dataNum), "*"))
        preprocCommand = preprocCommand + ["-D"] + dicomGlobFiles

    if not args.temp_folder == "":
        preprocCommand = preprocCommand + ["--temp-folder", args.temp_folder]
    preprocCommand = preprocCommand + ["--temp-folder", args.temp_folder]

    call(preprocCommand)

#   Move preprocessed results to output folders
    shutil.move(os.path.join(dwiPrefixBase, dwiPrefix + "_" + str(dataNum) + "_Tensors.nrrd"), os.path.join("DTI", outputPrefix + "_DTI_" + str(dataNum) + ".nrrd"))
    shutil.move(os.path.join(dwiPrefixBase, dwiPrefix + "_" + str(dataNum) + "_preprocessed.bvec"), os.path.join("Preprocessed_DWI", outputPrefix + "_DWI_" + str(dataNum) + ".bvec"))
    shutil.copy(os.path.join(dwiPrefixBase, dwiPrefix + "_" + str(dataNum) + ".bval"), os.path.join("Preprocessed_DWI", outputPrefix + "_DWI_" + str(dataNum) + ".bval"))
    shutil.move(os.path.join(dwiPrefixBase, dwiPrefix + "_" + str(dataNum) + "_preprocessed.nrrd"), os.path.join("Preprocessed_DWI", outputPrefix + "_DWI_" + str(dataNum) + ".nrrd"))
    shutil.move(os.path.join(dwiPrefixBase, dwiPrefix + "_" + str(dataNum) + "_brainMask.nrrd"), os.path.join("Preprocessed_DWI", outputPrefix + "_DWI_BrainMask_" + str(dataNum) + ".nrrd"))
    os.remove(os.path.join(dwiPrefixBase, dwiPrefix + "_" + str(dataNum) + "_Tensors_B0.nrrd"))
    os.remove(os.path.join(dwiPrefixBase, dwiPrefix + "_" + str(dataNum) + "_Tensors_NoiseVariance.nrrd"))

#   Now estimate MCMs
    os.chdir("Preprocessed_DWI")
    mcmCommand = ["python3", os.path.join(animaScriptsDir,"diffusion","myAnimaMultiCompartmentModelEstimation.py"), "-i", outputPrefix + "_DWI_" + str(dataNum) + ".nrrd",
                  "-g", outputPrefix + "_DWI_" + str(dataNum) + ".bvec", "-b", outputPrefix + "_DWI_" + str(dataNum) + ".bval", "-n", "3", "-m", outputPrefix + "_DWI_BrainMask_" + str(dataNum) + ".nrrd",
                  "-t", args.type]

    if args.hcp is True:
        mcmCommand += ["--hcp"]

    if args.map is True:
        mcmCommand += ["--map"]

    call(mcmCommand)
    os.chdir("..")

    # Now move results to MCM folder
    shutil.move(os.path.join("Preprocessed_DWI", outputPrefix + "_DWI_" + str(dataNum) + "_MCM_avg.mcm"), os.path.join("MCM", outputPrefix + "_MCM_avg_" + str(dataNum) + ".mcm"))

    if os.path.exists(os.path.join("MCM", outputPrefix + "_MCM_avg_" + str(dataNum))):
        shutil.rmtree(os.path.join("MCM", outputPrefix + "_MCM_avg_" + str(dataNum)), ignore_errors=True)

    shutil.move(os.path.join("Preprocessed_DWI", outputPrefix + "_DWI_" + str(dataNum) + "_MCM_avg"), os.path.join("MCM", outputPrefix + "_MCM_avg_" + str(dataNum)))
    shutil.move(os.path.join("Preprocessed_DWI", outputPrefix + "_DWI_" + str(dataNum) + "_MCM_B0_avg.nrrd"), os.path.join("MCM", outputPrefix + "_MCM_avg_B0_" + str(dataNum) + ".nrrd"))
    shutil.move(os.path.join("Preprocessed_DWI", outputPrefix + "_DWI_" + str(dataNum) + "_MCM_S2_avg.nrrd"), os.path.join("MCM", outputPrefix + "_MCM_avg_S2_" + str(dataNum) + ".nrrd"))
    for f in glob.glob(os.path.join("Preprocessed_DWI", outputPrefix + "_DWI_" + str(dataNum) + "_MCM*")):
        if os.path.isdir(f):
            shutil.rmtree(f, ignore_errors=True)
        else:
            os.remove(f)




