#!/usr/bin/python3

import sys
import argparse

if sys.version_info[0] > 2:
    import configparser as ConfParser
else:
    import ConfigParser as ConfParser

import uuid
import glob
import os
import shutil
import numpy as np
import nibabel as nib
from subprocess import call
from pathlib import Path

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

parser.add_argument('-i', '--dw-images-prefix', type=str, required=True, help='DW images prefix (folder + basename)')
parser.add_argument('-d', '--dw-dicom-folders-prefix', type=str, default="", help='Dicom folders prefixes (will append _n to them, where n is the image number)')
parser.add_argument('-t', '--t1-images-prefix', type=str, required=True, help='T1 images prefix (folder + basename)')
parser.add_argument('--type', type=str, default="tensor", help="Type of compartment model for fascicles (stick, zeppelin, tensor, noddi, ddi)")

parser.add_argument('--dw-without-reversed-b0', action='store_true', help="No reversed B0 provided with the DWIs")

parser.add_argument('-b', '--bvalue-extract', type=int, default=0, help="Extract only a specific b-value for TractSeg (recommended for CUSP)")

parser.add_argument('--map', action='store_true', help='Add map option in MCM estimation')

parser.add_argument('-K', '--keep-intermediate-folders', action='store_true',
                    help='Keep intermediate folders after script end')

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

animaDTIScalarMaps = os.path.join(animaDir, "animaDTIScalarMaps")
animaPyramidalBMRegistration = os.path.join(animaDir, "animaPyramidalBMRegistration")
animaTransformSerieXmlGenerator = os.path.join(animaDir, "animaTransformSerieXmlGenerator")
animaApplyTransformSerie = os.path.join(animaDir, "animaApplyTransformSerie")
animaImageArithmetic = os.path.join(animaDir, "animaImageArithmetic")
animaThrImage = os.path.join(animaDir, "animaThrImage")

os.makedirs('DTI', exist_ok=True)
os.makedirs('Preprocessed_DWI', exist_ok=True)
os.makedirs('MCM', exist_ok=True)
os.makedirs('Tracts_Masks', exist_ok=True)

# Tracts list imported from tractseg (
tracksLists = ['AF_left', 'AF_right', 'ATR_left', 'ATR_right', 'CA', 'CC_1', 'CC_2', 'CC_3', 'CC_4', 'CC_5', 'CC_6',
               'CC_7', 'CG_left', 'CG_right', 'CST_left', 'CST_right', 'MLF_left', 'MLF_right', 'FPT_left', 'FPT_right',
               'FX_left', 'FX_right', 'ICP_left', 'ICP_right', 'IFO_left', 'IFO_right', 'ILF_left', 'ILF_right', 'MCP',
               'OR_left', 'OR_right', 'POPT_left', 'POPT_right', 'SCP_left', 'SCP_right', 'SLF_I_left', 'SLF_I_right',
               'SLF_II_left', 'SLF_II_right', 'SLF_III_left', 'SLF_III_right', 'STR_left', 'STR_right', 'UF_left',
               'UF_right', 'CC', 'T_PREF_left', 'T_PREF_right', 'T_PREM_left', 'T_PREM_right', 'T_PREC_left',
               'T_PREC_right', 'T_POSTC_left', 'T_POSTC_right', 'T_PAR_left', 'T_PAR_right', 'T_OCC_left',
               'T_OCC_right', 'ST_FO_left', 'ST_FO_right', 'ST_PREF_left', 'ST_PREF_right', 'ST_PREM_left',
               'ST_PREM_right', 'ST_PREC_left', 'ST_PREC_right', 'ST_POSTC_left', 'ST_POSTC_right', 'ST_PAR_left',
               'ST_PAR_right', 'ST_OCC_left', 'ST_OCC_right']

dwiPrefixBase = os.path.dirname(args.dw_images_prefix)
dwiPrefixParent = Path(dwiPrefixBase).parent
dwiPrefix = os.path.basename(args.dw_images_prefix)

tractsegFATemplate = os.path.join(animaDataDir, "mni_template", "MNI_FA_Template.nii.gz")

# Preprocess diffusion data
preprocCommand = ["python3", os.path.join(animaScriptsDir,"diffusion","animaDiffusionImagePreprocessing.py"), "-b", os.path.join(dwiPrefixBase, dwiPrefix + ".bval"), "-t", os.path.join(args.t1_images_prefix), "-i", os.path.join(dwiPrefixBase, dwiPrefix + ".nii.gz")]

if not args.dw_without_reversed_b0:
    preprocCommand = preprocCommand + ["-r", os.path.join(dwiPrefixBase, dwiPrefix + "_reversed_b0.nii.gz")]

if args.dw_dicom_folders_prefix == "":
    preprocCommand = preprocCommand + ["-g", os.path.join(dwiPrefixBase, dwiPrefix + ".bvec")]
else:
    dicomGlobFiles = glob.glob(os.path.join(args.dw_dicom_folders_prefix, "*"))
    preprocCommand = preprocCommand + ["-D"] + dicomGlobFiles

call(preprocCommand)

# Move preprocessed results to output folders
shutil.move(os.path.join(dwiPrefixBase, dwiPrefix + "_Tensors.nrrd"), os.path.join("DTI", dwiPrefix + "_DTI.nrrd"))
shutil.move(os.path.join(dwiPrefixBase, dwiPrefix + "_preprocessed.bvec"), os.path.join("Preprocessed_DWI", dwiPrefix +  "_DWI.bvec"))
shutil.copy(os.path.join(dwiPrefixBase, dwiPrefix + ".bval"), os.path.join("Preprocessed_DWI",  dwiPrefix +  "_DWI.bval"))
shutil.move(os.path.join(dwiPrefixBase, dwiPrefix + "_preprocessed.nrrd"), os.path.join("Preprocessed_DWI",  dwiPrefix + "_DWI.nrrd"))
shutil.move(os.path.join(dwiPrefixBase, dwiPrefix + "_brainMask.nrrd"), os.path.join("Preprocessed_DWI",  dwiPrefix +  "_DWI_BrainMask.nrrd"))
os.remove(os.path.join(dwiPrefixBase, dwiPrefix + "_Tensors_B0.nrrd"))
os.remove(os.path.join(dwiPrefixBase, dwiPrefix + "_Tensors_NoiseVariance.nrrd"))

# Now estimate MCMs
os.chdir("Preprocessed_DWI")
mcmCommand = ["python3", os.path.join(animaScriptsDir,"diffusion","myAnimaMultiCompartmentModelEstimation.py"), "-i", dwiPrefix +  "_DWI.nrrd",
                "-g", dwiPrefix +  "_DWI.bvec", "-b", dwiPrefix +  "_DWI.bval", "-n", "3", "-m", dwiPrefix +  "_DWI_BrainMask.nrrd",
                "-t", args.type]
if args.map:
    mcmCommand = mcmCommand + ["--map"]

call(mcmCommand)

# Now move results to MCM folder
os.chdir("..")
shutil.move(os.path.join("Preprocessed_DWI", dwiPrefix +  "_DWI_MCM_avg.mcm"), os.path.join("MCM", dwiPrefix +  "_MCM_avg.mcm"))

if os.path.exists(os.path.join("MCM", dwiPrefix +  "_MCM_avg")):
    shutil.rmtree(os.path.join("MCM", dwiPrefix +  "_MCM_avg", ignore_errors=True))

shutil.move(os.path.join("Preprocessed_DWI", dwiPrefix +  "_DWI_MCM_avg"), os.path.join("MCM", dwiPrefix +  "_MCM_avg"))
shutil.move(os.path.join("Preprocessed_DWI", dwiPrefix +  "_DWI_MCM_B0_avg.nrrd"), os.path.join("MCM", dwiPrefix +  "_MCM_avg_B0.nrrd"))
shutil.move(os.path.join("Preprocessed_DWI", dwiPrefix +  "_DWI_MCM_S2_avg.nrrd"), os.path.join("MCM", dwiPrefix +  "_MCM_avg_S2.nrrd"))
for f in glob.glob(os.path.join("Preprocessed_DWI", dwiPrefix +  "_DWI_MCM*")):
    if os.path.isdir(f):
        shutil.rmtree(f, ignore_errors=True)
    else:
        os.remove(f)

# Now transform subject FA to MNI reference FA template in tractseg
tmpFolder = "subject_mcm_preparation"
if not os.path.isdir(tmpFolder):
    os.mkdir(tmpFolder)

extractFACommand = [animaDTIScalarMaps, "-i", os.path.join("DTI", dwiPrefix +  "_DTI.nrrd"), "-f", os.path.join(tmpFolder,  dwiPrefix + "_Subject_FA.nrrd")]
call(extractFACommand)

regFACommand = [animaPyramidalBMRegistration, "-r", tractsegFATemplate, "-m", os.path.join(tmpFolder, dwiPrefix +  "_Subject_FA.nrrd"), "-o", os.path.join(tmpFolder, dwiPrefix +  "_Subject_FA_OnMNI.nrrd"), "-O", os.path.join(tmpFolder, dwiPrefix +  "_Subject_FA_OnMNI_tr.txt"), "-s", "0"]
call(regFACommand)

trsfSerieGenCommand = [animaTransformSerieXmlGenerator, "-i", os.path.join(tmpFolder, dwiPrefix +  "_Subject_FA_OnMNI_tr.txt"), "-o", os.path.join(tmpFolder, dwiPrefix +  "_Subject_FA_OnMNI_tr.xml")]
call(trsfSerieGenCommand)

applyTrsfCommand = [animaApplyTransformSerie, "-i", os.path.join("Preprocessed_DWI", dwiPrefix +  "_DWI.nrrd"), "-t", os.path.join(tmpFolder, dwiPrefix +  "_Subject_FA_OnMNI_tr.xml"), "-g", tractsegFATemplate, "-o", os.path.join(tmpFolder,  dwiPrefix +  "_DWI_MNI.nii.gz"), "--grad", os.path.join("Preprocessed_DWI", dwiPrefix +  "_DWI.bvec"),
                    "-O", os.path.join(tmpFolder,  dwiPrefix +  "_DWI_MNI.bvec")]
call(applyTrsfCommand)

shutil.copy(os.path.join("Preprocessed_DWI", dwiPrefix +  "_DWI.bval"), os.path.join(tmpFolder,  dwiPrefix +  "_DWI_MNI.bval"))
# Trick to get back temporary file to mrtrix ok format (switch y axis)
tmpData = np.loadtxt(os.path.join(tmpFolder,  dwiPrefix +  "_DWI_MNI.bvec"))
tmpData[1] *= -1
np.savetxt(os.path.join(tmpFolder,  dwiPrefix +  "_DWI_MNI.bvec"), tmpData)

applyTrsfCommand = [animaApplyTransformSerie, "-i", os.path.join("Preprocessed_DWI",  dwiPrefix +  "_DWI_BrainMask.nrrd"), "-t", os.path.join(tmpFolder,  dwiPrefix +  "_Subject_FA_OnMNI_tr.xml"), "-g", tractsegFATemplate,
                    "-o", os.path.join(tmpFolder,  dwiPrefix +  "_DWI_MNI_brainMask.nii.gz"), "-n", "nearest"]
call(applyTrsfCommand)

# If asked for, extract specific b-value shell for compatibility between CUSP and TractSeg
bvalTS = os.path.join(tmpFolder,  dwiPrefix +  "_DWI_MNI.bval")
bvecTS = os.path.join(tmpFolder,  dwiPrefix +  "_DWI_MNI.bvec")
dwiTS = os.path.join(tmpFolder,  dwiPrefix +  "_DWI_MNI.nii.gz")
if args.bvalue_extract > 0:
    img = nib.load(dwiTS)
    bvals = np.loadtxt(bvalTS)
    bvecs = np.loadtxt(bvecTS)
    div5ShellValue = int(args.bvalue_extract/5)
    lowerShellValue = div5ShellValue * 5
    upperShellValue = lowerShellValue
    if not div5ShellValue == args.bvalue_extract/5:
        upperShellValue = lowerShellValue + 5

    indexesValues = np.where((bvals <= upperShellValue) * (bvals >= lowerShellValue) | (bvals == 0))[0]
    bvals = bvals[indexesValues]
    bvecs = bvecs[:, indexesValues]
    data_crop = img.get_data()[:, :, :, indexesValues]
    img_crop = nib.Nifti1Image(data_crop, img.affine, img.header)
    np.savetxt(os.path.join(tmpFolder,  dwiPrefix +  "_DWI_MNI_crop.bval"), bvals)
    np.savetxt(os.path.join(tmpFolder,  dwiPrefix +  "_DWI_MNI_crop.bvec"), bvecs)
    nib.save(img_crop, os.path.join(tmpFolder,  dwiPrefix +  "_DWI_MNI_crop.nii.gz"))

    bvalTS = os.path.join(tmpFolder,  dwiPrefix +  "_DWI_MNI_crop.bval")
    bvecTS = os.path.join(tmpFolder,  dwiPrefix +  "_DWI_MNI_crop.bvec")
    dwiTS = os.path.join(tmpFolder,  dwiPrefix +  "_DWI_MNI_crop.nii.gz")

# Finally call tractseg on adapted data
TractSegFolder = "TractSeg_output"

if os.path.exists(TractSegFolder):
    shutil.rmtree(TractSegFolder)

tractsegCommand = ["TractSeg", "-i", dwiTS, "-o", TractSegFolder, "--bvals", bvalTS, "--bvecs", bvecTS, "--raw_diffusion_input", "--brain_mask",  os.path.join(tmpFolder,  dwiPrefix +  "_DWI_MNI_brainMask.nii.gz"), "--output_type", "endings_segmentation"]
call(tractsegCommand)

for track in tracksLists:
    # Merge begin and end into a single label image
    shutil.move(os.path.join(TractSegFolder, "endings_segmentations", track + "_e.nii.gz",), os.path.join(TractSegFolder, "endings_segmentations", dwiPrefix + "_" + track + "_e.nii.gz"))
    shutil.move(os.path.join(TractSegFolder, "endings_segmentations", track + "_b.nii.gz",), os.path.join(TractSegFolder, "endings_segmentations", dwiPrefix + "_" + track + "_b.nii.gz"))

    labelsMergeCommand = [animaImageArithmetic, "-i", os.path.join(TractSegFolder, "endings_segmentations", dwiPrefix + "_" +  track + "_e.nii.gz"), "-M", "2",
                            "-a", os.path.join(TractSegFolder, "endings_segmentations", dwiPrefix + "_" +  track + "_b.nii.gz"), "-o", os.path.join(TractSegFolder, "endings_segmentations", dwiPrefix + "_" +  track + ".nrrd")]
    call(labelsMergeCommand)

    labelsThrCommand = [animaThrImage, "-i", os.path.join(TractSegFolder, "endings_segmentations", dwiPrefix + "_" +  track + ".nrrd"), "-t", "2.1", "-o", os.path.join(TractSegFolder, dwiPrefix + "_" +  "tmp.nrrd")]
    call(labelsThrCommand)

    labelFinalizeCommand = [animaImageArithmetic, "-i", os.path.join(TractSegFolder, "endings_segmentations", dwiPrefix + "_" +  track + ".nrrd"), "-s", os.path.join(TractSegFolder, dwiPrefix + "_" +  "tmp.nrrd"),
                            "-o", os.path.join(TractSegFolder, "endings_segmentations", dwiPrefix + "_" +  track + ".nrrd")]
    call(labelFinalizeCommand)

    # # Now move back to native space
    # applyTrsfCommand = [animaApplyTransformSerie, "-i", os.path.join(tmpFolder, "endings_segmentations", dwiPrefix + "_" +  track + ".nrrd"), "-t",
    #                     os.path.join(tmpFolder, dwiPrefix + "_Subject_FA_OnMNI_tr.xml"), "-g", os.path.join("Preprocessed_DWI", dwiPrefix + "_DWI.nrrd"),
    #                     "-o", os.path.join("Tracts_Masks",  dwiPrefix + "_" + track + ".nrrd"), "-I", "-n", "nearest"]
    # call(applyTrsfCommand)

    shutil.move(TractSegFolder, dwiPrefixParent)
    shutil.move("DTI", dwiPrefixParent)
    shutil.move("MCM", dwiPrefixParent)
    shutil.move("Tracts_Masks", dwiPrefixParent)
    shutil.move("Preprocessed_DWI", dwiPrefixParent)

if not args.keep_intermediate_folders:
    shutil.rmtree(tmpFolder)
