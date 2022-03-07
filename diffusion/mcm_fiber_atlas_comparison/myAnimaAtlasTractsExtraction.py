#!/usr/bin/python3

import sys
import argparse
import tempfile
import shutil
import tempfile
import glob
import os
import numpy as np
import nibabel as nib
from subprocess import call

if sys.version_info[0] > 2:
    import configparser as ConfParser
else:
    import ConfigParser as ConfParser

import os
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
    description="Given an atlas built using the atlasing scripts of Anima, plus tracts start and end regions provided"
                "by tractseg, and MCM, computes fiber tracts on the DTI atlas and MCM atlas")

parser.add_argument('-s', '--start-subject', type=int, default=1, help="Subject to start with")
parser.add_argument('-n', '--num-subjects', type=int, required=True,
                    help="Number of subjects used for computing the atlas")

parser.add_argument('-a', '--dti-atlas-image', type=str, required=True, help='DTI atlas image')
parser.add_argument('-i', '--tensor-images-prefix', type=str, required=True, help='Tensor images prefix')
parser.add_argument('-m', '--mcm-images-prefix', type=str, required=True, help='MCM images prefix')
parser.add_argument('-t', '--tracts-folder', type=str, default='Tracts_Masks', help='Tract filter masks folder')
parser.add_argument('--output-prefix', type=str, default="", help='Specify a name prefix')
parser.add_argument('-b', '--bvalue-extract', type=int, default=0, help="Extract only a specific b-value for TractSeg (recommended for CUSP)")

parser.add_argument('--temp-folder', type=str, default="", help='Specify a temp folder')

args = parser.parse_args()

outputPrefix = args.output_prefix
tensorsPrefixBase = os.path.dirname(args.tensor_images_prefix)
tensorsPrefix = os.path.basename(args.tensor_images_prefix)
mcmPrefixBase = os.path.dirname(args.mcm_images_prefix)
mcmPrefix = os.path.basename(args.mcm_images_prefix)
tractsegFATemplate = os.path.join(animaDataDir, "mni_template", "MNI_FA_template.nii.gz")

# The goal here is to create, from an atlas and attached data coming from the atlasing script and MCM fiber preparation,
# the atlas of fibers itself. What is done here is:
# - Apply transforms to MCM, tracts masks
# - perform majority voting on each tract mask
# - Computes full brain tractography
# - Filters it to get atlas fiber tracts

animaDTIScalarMaps = os.path.join(animaDir, "animaDTIScalarMaps")
animaThrImage = os.path.join(animaDir, "animaThrImage")
animaPyramidalBMRegistration = os.path.join(animaDir, "animaPyramidalBMRegistration")
animaTransformSerieXmlGenerator = os.path.join(animaDir, "animaTransformSerieXmlGenerator")
animaApplyTransformSerie = os.path.join(animaDir, "animaApplyTransformSerie")
animaMCMAverageImages = os.path.join(animaDir, "animaMCMAverageImages")
animaAverageImages = os.path.join(animaDir, "animaAverageImages")
animaDTITractography = os.path.join(animaDir, "animaDTITractography")
animaMajorityLabelVoting = os.path.join(animaDir, "animaMajorityLabelVoting")
animaFibersFilterer = os.path.join(animaDir, "animaFibersFilterer")
animaTracksMCMPropertiesExtraction = os.path.join(animaDir, "animaTracksMCMPropertiesExtraction")
animaImageArithmetic = os.path.join(animaDir, "animaImageArithmetic")

os.makedirs('Transformed_Tracts_Masks', exist_ok=True)
os.makedirs('Atlas_Tracts', exist_ok=True)
os.makedirs('Augmented_Atlas_Tracts', exist_ok=True)

# Tracts list imported from tractseg
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

if args.temp_folder == '':
    tmpFolder = tempfile.mkdtemp()
else:
    tmpFolder = args.temp_folder
    os.makedirs(tmpFolder, exist_ok=True)
    
for dataNum in range(args.start_subject, args.num_subjects + 1):

    # Now transform subject FA to MNI reference FA template in tractseg
    extractFACommand = [animaDTIScalarMaps, "-i", os.path.join("DTI", outputPrefix + "_DTI_" + str(dataNum) + ".nrrd"), "-f", os.path.join(tmpFolder, outputPrefix + "_Subject_FA.nrrd")]
    call(extractFACommand)

    regFACommand = [animaPyramidalBMRegistration, "-r", tractsegFATemplate, "-m", os.path.join(tmpFolder, outputPrefix + "_Subject_FA.nrrd"), "-o", os.path.join(tmpFolder, outputPrefix + "_Subject_FA_OnMNI.nrrd"),
                    "-O", os.path.join(tmpFolder, outputPrefix + "_Subject_FA_OnMNI_tr.txt"), "-s", "0"]
    call(regFACommand)

    trsfSerieGenCommand = [animaTransformSerieXmlGenerator, "-i", os.path.join(tmpFolder, outputPrefix + "_Subject_FA_OnMNI_tr.txt"), "-o", os.path.join(tmpFolder, outputPrefix + "_Subject_FA_OnMNI_tr.xml")]
    call(trsfSerieGenCommand)

    applyTrsfCommand = [animaApplyTransformSerie, "-i", os.path.join("Preprocessed_DWI", outputPrefix + "_DWI_" + str(dataNum) + ".nrrd"), "-t", os.path.join(tmpFolder, outputPrefix + "_Subject_FA_OnMNI_tr.xml"),
                        "-g", tractsegFATemplate, "-o", os.path.join(tmpFolder, outputPrefix + "_DWI_MNI.nii.gz"), "--grad", os.path.join("Preprocessed_DWI", outputPrefix + "_DWI_" + str(dataNum) + ".bvec"),
                        "-O", os.path.join(tmpFolder, outputPrefix + "_DWI_MNI.bvec")]
    call(applyTrsfCommand)

    shutil.copy(os.path.join("Preprocessed_DWI", outputPrefix + "_DWI_" + str(dataNum) + ".bval"), os.path.join(tmpFolder, outputPrefix + "_DWI_MNI.bval"))
    # Trick to get back temporary file to mrtrix ok format (switch y axis)
    tmpData = np.loadtxt(os.path.join(tmpFolder, outputPrefix + "_DWI_MNI.bvec"))
    tmpData[1] *= -1
    np.savetxt(os.path.join(tmpFolder, outputPrefix + "_DWI_MNI.bvec"), tmpData)

    applyTrsfCommand = [animaApplyTransformSerie, "-i", os.path.join("Preprocessed_DWI", outputPrefix + "_DWI_BrainMask_" + str(dataNum) + ".nrrd"),
                        "-t", os.path.join(tmpFolder, outputPrefix + "_Subject_FA_OnMNI_tr.xml"), "-g", tractsegFATemplate,
                        "-o", os.path.join(tmpFolder, outputPrefix + "_DWI_MNI_brainMask.nii.gz"), "-n", "nearest"]
    call(applyTrsfCommand)

    # If asked for, extract specific b-value shell for compatibility between CUSP and TractSeg
    bvalTS = os.path.join(tmpFolder, outputPrefix + "_DWI_MNI.bval")
    bvecTS = os.path.join(tmpFolder, outputPrefix + "_DWI_MNI.bvec")
    dwiTS = os.path.join(tmpFolder, outputPrefix + "_DWI_MNI.nii.gz")
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
        np.savetxt(os.path.join(tmpFolder, outputPrefix + "_DWI_MNI_crop.bval"), bvals)
        np.savetxt(os.path.join(tmpFolder, outputPrefix + "_DWI_MNI_crop.bvec"), bvecs)
        nib.save(img_crop, os.path.join(tmpFolder, outputPrefix + "_DWI_MNI_crop.nii.gz"))

        bvalTS = os.path.join(tmpFolder, outputPrefix + "_DWI_MNI_crop.bval")
        bvecTS = os.path.join(tmpFolder, outputPrefix + "_DWI_MNI_crop.bvec")
        dwiTS = os.path.join(tmpFolder, outputPrefix + "_DWI_MNI_crop.nii.gz")

    tractsegCommand = ["TractSeg", "-i", dwiTS, "-o", tmpFolder, "--bvals", bvalTS, "--bvecs", bvecTS, "--raw_diffusion_input", "--brain_mask",  os.path.join(tmpFolder, "DWI_MNI_brainMask.nii.gz"),
                       "--output_type", "endings_segmentation"]
    call(tractsegCommand)   

    for track in tracksLists:
        # Merge begin and end into a single label image
        labelsMergeCommand = [animaImageArithmetic, "-i", os.path.join(tmpFolder, "endings_segmentations", track + "_e.nii.gz"), "-M", "2",
                              "-a", os.path.join(tmpFolder, "endings_segmentations", track + "_b.nii.gz"), "-o", os.path.join(tmpFolder, "endings_segmentations", track + ".nrrd")]
        call(labelsMergeCommand)

        labelsThrCommand = [animaThrImage, "-i", os.path.join(tmpFolder, "endings_segmentations", track + ".nrrd"), "-t", "2.1", "-o", os.path.join(tmpFolder, "tmp.nrrd")]
        call(labelsThrCommand)

        labelFinalizeCommand = [animaImageArithmetic, "-i", os.path.join(tmpFolder, "endings_segmentations", track + ".nrrd"), "-s", os.path.join(tmpFolder, "tmp.nrrd"),
                               "-o", os.path.join(tmpFolder, "endings_segmentations", track + ".nrrd")]
        call(labelFinalizeCommand)

        # Now move back to native space
        applyTrsfCommand = [animaApplyTransformSerie, "-i", os.path.join(tmpFolder, "endings_segmentations", track + ".nrrd"), "-t",
                            os.path.join(tmpFolder, "Subject_FA_OnMNI_tr.xml"), "-g", os.path.join("Preprocessed_DWI","DWI_" + str(dataNum) + ".nrrd"),
                            "-o", os.path.join("Tracts_Masks", track + "_" + str(dataNum) + ".nrrd"), "-I", "-n", "nearest"]
        call(applyTrsfCommand)

    shutil.rmtree(tmpFolder)

sys.exit()

for dataNum in range(1, args.num_subjects + 1):
    # Now apply the transform to all tractseg regions
    for track in tracksLists:
        # Apply transform to fused begin and end mask
        applyCommand = [animaApplyTransformSerie,
                        "-i", os.path.join(args.tracts_folder, track + "_" + str(dataNum) + ".nrrd"),
                        "-o", os.path.join('Transformed_Tracts_Masks', track + "_" + str(dataNum) + ".nrrd"),
                        "-t", os.path.join("residualDir", "trsf_" + str(dataNum) + ".xml"),
                        "-g", args.dti_atlas_image, "-n", "nearest"]
        call(applyCommand)

# Perform tractography on average MCM model
adcCommand = [animaDTIScalarMaps, "-i", args.dti_atlas_image, "-a", "averageADC.nrrd"]
call(adcCommand)

thrCommand = [animaThrImage, "-t", "0", "-i", "averageADC.nrrd", "-o",
              "averageMask.nrrd"]
call(thrCommand)

trackingCommand = [animaDTITractography, "-i", args.dti_atlas_image, "-s", "averageMask.nrrd", "--nb-fibers", "2", "-a", "90", "-p", "0",
                   "-o", os.path.join('Atlas_Tracts', 'WholeBrain_Tractography.fds')]
call(trackingCommand)

# Majority vote for tracts masks and filter main tractography
for track in tracksLists:
    trackMasksListFile = open(os.path.join('Transformed_Tracts_Masks', 'listMasks.txt'), "w")
    for dataNum in range(1, args.num_subjects + 1):
        trackMasksListFile.write(os.path.join(os.getcwd(), 'Transformed_Tracts_Masks', track + "_" + str(dataNum) + ".nrrd") + "\n")

    trackMasksListFile.close()

    majorityVoteCommand = [animaMajorityLabelVoting, "-i", os.path.join('Transformed_Tracts_Masks', 'listMasks.txt'),
                           "-o", os.path.join('Transformed_Tracts_Masks', track + '_FilterMask.nrrd')]
    call(majorityVoteCommand)

    fiberFilterCommand = [animaFibersFilterer, "-i", os.path.join('Atlas_Tracts', 'WholeBrain_Tractography.fds'),
                          "-o", os.path.join('Atlas_Tracts', track + '.fds'),
                          "-r", os.path.join('Transformed_Tracts_Masks', track + '_FilterMask.nrrd'),
                          "-e", "1", "-e", "2"]
    call(fiberFilterCommand)

    # trackListFile = open(os.path.join('Augmented_Atlas_Tracts', 'listData_' + track + '.txt'), "w")
    # for dataNum in range(1, args.num_subjects + 1):
    #     propsExtractionCommand = [animaTracksMCMPropertiesExtraction, "-i", os.path.join('Atlas_Tracts', track + '.fds'),
    #                               "-m", os.path.join('Transformed_MCM', mcmPrefix + "_" + str(dataNum) + ".mcm"),
    #                               "-o", os.path.join('Augmented_Atlas_Tracts', track + '_MCM_augmented_' + str(dataNum) + '.fds')]
    #     call(propsExtractionCommand)

    #     trackListFile.write(os.path.join(os.getcwd(), 'Augmented_Atlas_Tracts', track + '_MCM_augmented_' + str(dataNum) + '.fds') + "\n")

    # trackListFile.close()

