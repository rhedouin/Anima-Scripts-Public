#!/usr/bin/python
# Warning: works only on unix-like systems, not windows where "python animaDiffusionImagePreprocessing.py ..." has to be run

import sys
import argparse
import tempfile

if sys.version_info[0] > 2 :
	import configparser as ConfParser
else :
	import ConfigParser as ConfParser

import os
import shutil
from subprocess import call

configFilePath = os.path.expanduser("~") + "/.anima/config.txt"
if not os.path.exists(configFilePath) :
	print('Please create a configuration file for Anima python scripts. Refer to the README')
	quit()

configParser = ConfParser.RawConfigParser()
configParser.read(configFilePath)

animaDir = configParser.get("anima-scripts",'anima')
animaScriptsDir = configParser.get("anima-scripts",'anima-scripts-root')

# Argument parsing
parser = argparse.ArgumentParser(description="Prepares DWI for model estimation: denoising, brain masking, distortion correction")
parser.add_argument('-b', '--bval', type=str, default="", help="DWI b-values file")
parser.add_argument('-g', '--grad', type=str, default="", help="DWI gradients file")
parser.add_argument('-r', '--reverse', type=str, default="", help="Reversed PED B0 image")
parser.add_argument('-d', '--direction', type=int, default=1, help="PED direction (0: x, 1: y, 2: z)")
parser.add_argument('--no-disto-correction', action='store_true', help="Do not perform distortion correction")
parser.add_argument('--no-denoising', action='store_true', help="Do not perform NL-Means denoising")
parser.add_argument('-t', '--t1', type=str, default="", help="T1 image for brain masking (B0 used if not provided)")
parser.add_argument('--no-brain-masking', action='store_true', help="Do not perform any brain masking")
parser.add_argument('--no-eddy-correction', action='store_true', help="Do not perform Eddy current distortion correction")
parser.add_argument('-i', '--input', type=str, required=True, help='DWI file to process')

args = parser.parse_args()

tmpFolder=tempfile.mkdtemp()

dwiImage = args.input
dwiImagePrefix = os.path.splitext(dwiImage)[0]
if os.path.splitext(dwiImage)[1] == '.gz' :
	dwiImagePrefix = os.path.splitext(dwiImagePrefix)[0]

tmpDWIImagePrefix = os.path.join(tmpFolder, os.path.basename(dwiImagePrefix))

outputImage = dwiImage
# Distortion correction first
# Eddy current first
if args.no_eddy_correction is False :
	eddyCorrectionCommand = [animaDir + "animaEddyCurrentCorrection","-i",dwiImage,"-o",tmpDWIImagePrefix + "_eddy_corrected.nrrd", \
		"-d",str(args.direction)]
	call(eddyCorrectionCommand)

	outputImage = tmpDWIImagePrefix + "_eddy_corrected.nrrd"

# Extract brain from T1 image if present (used for further processing)
if (args.no_disto_correction is False or args.no_brain_masking is False) and not args.t1 == "" :
	brainExtractionCommand = ["python",animaScriptsDir + "brain_extraction/animaAtlasBasedBrainExtraction.py", args.t1]
	call(brainExtractionCommand)

# Then susceptibility distortion
if args.no_disto_correction is False :
	if not (args.reverse == "") :
		b0ExtractCommand = [animaDir + "animaCropImage","-i",outputImage,"-t","0","-T","0","-o",tmpDWIImagePrefix + "_B0.nrrd"]
		call(b0ExtractCommand)

		initCorrectionCommand = [animaDir + "animaDistortionCorrection","-s","2","-d",str(args.direction), \
			"-f",tmpDWIImagePrefix + "_B0.nrrd","-b",args.reverse,"-o",tmpDWIImagePrefix + "_init_correction_tr.nrrd"]
		call(initCorrectionCommand)
		bmCorrectionCommand = [animaDir + "animaBMDistortionCorrection","-f",tmpDWIImagePrefix + "_B0.nrrd", \
			"-b",args.reverse,"-o",tmpDWIImagePrefix + "_B0_corrected.nrrd","-i",tmpDWIImagePrefix + "_init_correction_tr.nrrd", \
			"--bs","3","-s","10","-d",str(args.direction),"-O",tmpDWIImagePrefix + "_B0_correction_tr.nrrd"]
		call(bmCorrectionCommand)

		applyCorrectionCommand = [animaDir + "animaApplyDistortionCorrection","-f",outputImage,"-t", \
			tmpDWIImagePrefix + "_B0_correction_tr.nrrd","-o",tmpDWIImagePrefix + "_corrected.nrrd"]
		call(applyCorrectionCommand)

		outputImage = tmpDWIImagePrefix + "_corrected.nrrd"
	elif not (args.t1 == "") :
		b0ExtractCommand = [animaDir + "animaCropImage","-i",outputImage,"-t","0","-T","0","-o",tmpDWIImagePrefix + "_B0.nrrd"]
		call(b0ExtractCommand)

		T1Prefix = os.path.splitext(args.t1)[0]
		if os.path.splitext(args.t1)[1] == '.gz' :
			T1Prefix = os.path.splitext(T1Prefix)[0]

		tmpT1Prefix = os.path.join(tmpFolder, os.path.basename(T1Prefix))

		correctionCommand = [animaDir + "animaPyramidalBMRegistration","-r",tmpDWIImagePrefix + "_B0.nrrd", \
			"-m",T1Prefix + "_masked.nrrd","-o",tmpT1Prefix + "_rig.nrrd"]
		call(correctionCommand)

		correctionCommand = [animaDir + "animaDenseSVFBMRegistration","-r",tmpT1Prefix + "_rig.nrrd", \
			"-m",tmpDWIImagePrefix + "_B0.nrrd","-o",tmpDWIImagePrefix + "_B0_corrected.nrrd","-d",str(args.direction), \
			"-O",tmpDWIImagePrefix + "_B0_correction_tr.nrrd","-t","3"]
		call(correctionCommand)

		applyCorrectionCommand = [animaDir + "animaApplyDistortionCorrection","-f",outputImage,"-t", \
			tmpDWIImagePrefix + "_B0_correction_tr.nrrd","-o",tmpDWIImagePrefix + "_corrected.nrrd"]
		call(applyCorrectionCommand)

# Then re-orient image to be axial first
dwiReorientCommand = [animaDir + "animaConvertImage","-i",outputImage,"-o",tmpDWIImagePrefix + "_or.nrrd","-R","AXIAL"]
if not (args.grad == "") :
	dwiReorientCommand.extend(["-g",args.grad])
call(dwiReorientCommand)
outputImage = tmpDWIImagePrefix + "_or.nrrd"

# Then perform denoising
if args.no_denoising is False :
	denoisingCommand = [animaDir + "animaNLMeansTemporal","-i",outputImage,"-b","0.5","-o",tmpDWIImagePrefix + "_nlm.nrrd"]
	call(denoisingCommand)
	outputImage = tmpDWIImagePrefix + "_nlm.nrrd"

# Finally, brain mask image
if args.no_brain_masking is False :
	brainImage = args.t1

	b0ExtractCommand = [animaDir + "animaCropImage","-i",outputImage,"-t","0","-T","0","-o",tmpDWIImagePrefix + "_forBrainExtract.nrrd"]
	call(b0ExtractCommand)

	if brainImage == "" :
		brainImage = tmpDWIImagePrefix + "_forBrainExtract.nrrd"
		brainExtractionCommand = ["python",animaScriptsDir + "brain_extraction/animaAtlasBasedBrainExtraction.py", brainImage]
		call(brainExtractionCommand)

	if args.t1 == "" :
		shutil.move(tmpDWIImagePrefix + "_forBrainExtract_brainMask.nrrd",dwiImagePrefix + "_brainMask.nrrd")
	else :
		T1Prefix = os.path.splitext(args.t1)[0]
		if os.path.splitext(args.t1)[1] == '.gz' :
			T1Prefix = os.path.splitext(T1Prefix)[0]

		tmpT1Prefix = os.path.join(tmpFolder, os.path.basename(T1Prefix))

		t1RegistrationCommand = [animaDir + "animaPyramidalBMRegistration","-r",tmpDWIImagePrefix + "_forBrainExtract.nrrd","-m",args.t1,"-o",tmpT1Prefix + "_rig.nrrd","-O",tmpT1Prefix + "_rig_tr.txt","-p","4","-l","1","--sp","2","-I"]
		call(t1RegistrationCommand)

		command = [animaDir + "animaTransformSerieXmlGenerator","-i",tmpT1Prefix + "_rig_tr.txt","-o",tmpT1Prefix + "_rig_tr.xml"]
		call(command)

		command = [animaDir + "animaApplyTransformSerie","-i",T1Prefix + "_brainMask.nrrd","-t",tmpT1Prefix + "_rig_tr.xml","-o",dwiImagePrefix + "_brainMask.nrrd","-g",tmpDWIImagePrefix + "_forBrainExtract.nrrd","-n","nearest"]
		call(command)		

	brainExtractionCommand = [animaDir + "animaMaskImage","-i",outputImage,"-m",dwiImagePrefix + "_brainMask.nrrd", \
		"-o",tmpDWIImagePrefix + "_masked.nrrd"]
	call(brainExtractionCommand)

	outputImage = tmpDWIImagePrefix + "_masked.nrrd"

shutil.copy(outputImage,dwiImagePrefix + "_preprocessed.nrrd")
if not (args.grad == "") :
	shutil.copy(tmpDWIImagePrefix + "_or.bvec",dwiImagePrefix + "_preprocessed.bvec")

# Estimate tensors if files were provided
if (not (args.grad == "")) and (not (args.bval == "")) :
	dtiEstimationCommand = [animaDir + "animaDTIEstimator", "-i", outputImage, "-o", dwiImagePrefix + "_Tensors.nrrd", \
		"-O", dwiImagePrefix + "_Tensors_B0.nrrd", "-N", dwiImagePrefix + "_Tensors_NoiseVariance.nrrd", \
		"-g", tmpDWIImagePrefix + "_or.bvec", "-b", args.bval]
	if args.no_brain_masking is False :
		dtiEstimationCommand += ["-m", dwiImagePrefix + "_brainMask.nrrd"]
	call(dtiEstimationCommand)

shutil.rmtree(tmpFolder)
