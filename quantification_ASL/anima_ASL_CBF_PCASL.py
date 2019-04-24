#!/usr/bin/python
# Warning: works only on unix-like systems, not windows where "python animaDiffusionImagePreprocessing.py ..." has to be run

import sys
import argparse
import tempfile
import os

if sys.version_info[0] > 2 :
    import configparser as ConfParser
else :
    import ConfigParser as ConfParser

import os
import shutil
import subprocess 
from subprocess import call
import time

configFilePath = os.path.expanduser("~") + "/.anima/config.txt"

if not os.path.exists(configFilePath) :
    print('Please create a configuration file for Anima python scripts. Refer to the README')
    quit()

configParser = ConfParser.RawConfigParser()
configParser.read(configFilePath)
animaDir = configParser.get("anima-scripts",'anima')
animaScriptsDir = configParser.get("anima-scripts",'anima-scripts-root')

# Argument parsing

parser = argparse.ArgumentParser(description="Compute cerebral blood flow (CBF) from ASL, M0 and T1 images")
parser.add_argument('-asl', '--asl', type=str, required=True, help="ASL 4D file")
parser.add_argument('-m0', '--m0', type=str, required=True, help="M0 file")
parser.add_argument('-t1', '--t1', type=str, required=True, help='T13D file')
parser.add_argument('-o', '--o', type=str, required=True, help='output directory')

parser.add_argument('-fASL', '--fASL', type=int, default=0, help='1=functional ASL or 0=ASL')
parser.add_argument('-nbVolRemoved', '--nbVolRemoved', type=int, default=0, help='remove the first nbVolRemoved volumes of the acquisition (must be a even number)')
parser.add_argument('-volRefReg', '--volRefReg', type=int, default=0, help='0=first volume or 1=mean')
parser.add_argument('-firstVolLabel', '--firstVolLabel', type=int, default=1, help='1=label or 0=control')
parser.add_argument('-denoising', '--denoising', type=int, default=0, help='0=no denoising, 1=denoising on substracted labels - controls')
parser.add_argument('-surround', '--surround', type=int, default=1, help='1=surround substraction or 0=classical substraction')
parser.add_argument('-meanQuantile', '--meanQuantile', type=float, default=0.1, help='quantile for robust mean (between 0 and 1), if 0 or 1 -> classic mean')
parser.add_argument('-template', '--template', type=str, default="", help='Template file')
parser.add_argument('-mask', '--mask', type=str, default="", help='Mask file (based on T1 image)')

# Quantif arguments

parser.add_argument('-tau', '--tau', type=float, required=False, help='label duration (ms)')
parser.add_argument('-sDelay', '--sDelay', type=float, required=False, help='slice delay (ms)')
parser.add_argument('-alpha', '--alpha', type=float, required=False, help='labeling efficiency')
parser.add_argument('-lambdaa', '--lambdaa', type=float, required=False, help='blood Partition Coefficient')
parser.add_argument('-PLD', '--PLD', type=float, required=False, help='post labelling delay (ms)')
parser.add_argument('-T1Blood', '--T1Blood', type=float, required=False, help='longitudinal relaxation time of blood (ms)')

tic = time.time()

args = parser.parse_args()

ASLImage = args.asl
ASLImagePrefix = os.path.splitext(ASLImage)[0]
if os.path.splitext(ASLImage)[1] == '.gz' :
    ASLImagePrefix = os.path.splitext(ASLImagePrefix)[0]

M0Image = args.m0
M0ImagePrefix = os.path.splitext(M0Image)[0]
if os.path.splitext(M0Image)[1] == '.gz' :
    M0ImagePrefix = os.path.splitext(M0ImagePrefix)[0]

T1Image = args.t1
T1ImagePrefix = os.path.splitext(T1Image)[0]
if os.path.splitext(T1Image)[1] == '.gz' :
    T1ImagePrefix = os.path.splitext(T1ImagePrefix)[0]

if args.mask == "":
    MaskImage = T1Image
else:
    MaskImage=args.mask
print(MaskImage)      
MaskImagePrefix = os.path.splitext(MaskImage)[0]
if os.path.splitext(MaskImage)[1] == '.gz' :
    MaskImagePrefix = os.path.splitext(MaskImagePrefix)[0]

outDir = args.o
if not os.path.exists(outDir):
    os.makedirs(outDir)
outASLPrefix = os.path.join(outDir, os.path.basename(ASLImagePrefix))
outM0Prefix = os.path.join(outDir, os.path.basename(M0ImagePrefix))
outT1Prefix = os.path.join(outDir, os.path.basename(T1ImagePrefix))

infoCommand=[animaDir + "animaConvertImage", "-i", ASLImage, "-I"]
info=str(subprocess.check_output(infoCommand))
ASLsize=list(eval(info[info.index("["):info.index("]")+1]))

nbVol=ASLsize[3]


# 4D into 3D ( 1 mxnxpxt image to t mxnxp images )

j=0
for i in range(0,nbVol):
    if i >= args.nbVolRemoved:
        ASL4Dto3DCommand=[animaDir +"animaCropImage", "-i", ASLImage, "-t", str(j), "-T", "1", "-o", outASLPrefix + "_" + str(j) + ".nii.gz"]
        print('cropping',i+1,'/',nbVol)
        call(ASL4Dto3DCommand, stdout=open(os.devnull, "w"))
        j=j+1
nbVol=nbVol-args.nbVolRemoved

# Mask T1 image

MaskT1ImageCommand= [animaDir + "animaMaskImage", "-i", T1Image, "-m", MaskImage, "-o", outT1Prefix + "_masked.nii.gz"]
call(MaskT1ImageCommand, stdout=open(os.devnull, "w"))
T1Image=outT1Prefix + "_masked.nii.gz"

# Coregistration M0 et ASLImage

print("\n COREGISTRATIONS...")
outRegDir=os.path.join(outDir,"regTransfos")
if not os.path.exists(outRegDir):
    os.makedirs(outRegDir)

if args.volRefReg==0:
    ReferenceImage=outASLPrefix + "_" + str(0) + ".nii.gz"

if args.volRefReg==1:
    listImgFile = open(outASLPrefix + "_list.txt", 'w')
    for i in range(0,nbVol):
        print(outASLPrefix + "_" + str(i) + ".nii.gz", file= listImgFile)
    listImgFile.close()
    ASLMeanImageCommand= [animaDir + "animaAverageImages", "-i", outASLPrefix + "_list.txt", "-o", outASLPrefix + "_mean.nii.gz"]
    call(ASLMeanImageCommand, stdout=open(os.devnull, "w"))
    ReferenceImage=outASLPrefix + "_mean.nii.gz"

outRegT1=os.path.join(outRegDir,os.path.basename(T1ImagePrefix))
T1RegistrationCommand = [animaDir + "animaPyramidalBMRegistration", "-m", T1Image,"-r", ReferenceImage,"-o", outT1Prefix + "_reg.nii.gz", "-O", outRegT1 + "_reg.txt","-p","4","-l","1","--sp","2","--ot","0"]
print('registration T1') 
call(T1RegistrationCommand, stdout=open(os.devnull, "w"))

transfoGenCommand=[animaDir + "animaTransformSerieXmlGenerator", "-i", outRegT1 + "_reg.txt", "-o",  outRegT1 + "_reg.xml" ]
call(transfoGenCommand, stdout=open(os.devnull, "w"))
applyTransfoCommand=[animaDir + "animaApplyTransformSerie", "-i", MaskImage, "-g", ReferenceImage, "-t",  outRegT1 + "_reg.xml", "-o", outASLPrefix + "_maskASL.nii.gz", "-n", "nearest" ]
call(applyTransfoCommand, stdout=open(os.devnull, "w"))

outRegM0=os.path.join(outRegDir,os.path.basename(M0ImagePrefix))
M0RegistrationCommand = [animaDir + "animaPyramidalBMRegistration","-m", M0Image,"-r", ReferenceImage,"-o", outM0Prefix + "_reg.nii.gz","-O", outRegM0 + "_reg.txt","-p","4","-l","1","--sp","2","--ot","0"]
print('registration M0')
call(M0RegistrationCommand, stdout=open(os.devnull, "w"))

outReg=os.path.join(outRegDir,os.path.basename(ASLImagePrefix))
for i in range(0,nbVol):
    ASLRegistrationCommand = [animaDir + "animaPyramidalBMRegistration","-m", outASLPrefix + "_" + str(i) + ".nii.gz","-r", ReferenceImage,"-o", outASLPrefix + "_" + str(i) +  ".nii.gz", "-O", outReg + "_" + str(i) + ".txt","-p","4","-l","1","--sp","2","--ot","0"]
    print('registration ASL',i+1,'/',nbVol)
    call(ASLRegistrationCommand, stdout=open(os.devnull, "w"))

# Substract or surround substract

oldNbVol=nbVol
if args.surround == 1:
    print("\n SURROUND SUBSTRACTION...")
    ASLsubstrCommand=[animaDir +"animaImageArithmetic", "-i", outASLPrefix + "_0.nii.gz", "-s", outASLPrefix + "_1.nii.gz", "-o ", outASLPrefix + "_flow_0.nii.gz"]
    call(ASLsubstrCommand)
    ASLsubstrCommand=[animaDir +"animaImageArithmetic", "-i", outASLPrefix + "_" + str(nbVol-2) + ".nii.gz", "-s", outASLPrefix + "_" + str(nbVol-1) + ".nii.gz", "-o ", outASLPrefix + "_flow_" + str(nbVol-1) + ".nii.gz"]
    call(ASLsubstrCommand)
    for i in range(1,nbVol-1):
        ASLaddCommand=[animaDir +"animaImageArithmetic", "-i", outASLPrefix + "_" + str(i-1) + ".nii.gz", "-a", outASLPrefix + "_" + str(i+1) + ".nii.gz", "-o ", outASLPrefix + "_flow_tmp.nii"]
        call(ASLaddCommand)
        ASLdivCommand=[animaDir +"animaImageArithmetic", "-i", outASLPrefix + "_flow_tmp.nii", "-D", "2", "-o ", outASLPrefix + "_flow_tmp.nii"]
        call(ASLdivCommand)
        if i%2==1:
            ASLsubstrCommand=[animaDir +"animaImageArithmetic", "-i", outASLPrefix + "_flow_tmp.nii", "-s", outASLPrefix + "_" + str(i) + ".nii.gz", "-o ", outASLPrefix + "_flow_" + str(i) + ".nii.gz"]
        else:
            ASLsubstrCommand=[animaDir +"animaImageArithmetic", "-s", outASLPrefix + "_flow_tmp.nii", "-i", outASLPrefix + "_" + str(i) + ".nii.gz", "-o ", outASLPrefix + "_flow_" + str(i) + ".nii.gz"]
        call(ASLsubstrCommand)
    os.remove(outASLPrefix + "_flow_tmp.nii")

else:
    print("\n CLASSIC SUBSTRACTION...")
    for i in range(0,nbVol,2):
        ASLsubstrCommand=[animaDir +"animaImageArithmetic", "-i", outASLPrefix + "_" + str(i) + ".nii.gz", "-s", outASLPrefix + "_" + str(i+1) + ".nii.gz", "-o ", outASLPrefix + "_flow_" + str(i//2) + ".nii.gz"]
        call(ASLsubstrCommand)
    nbVol//=2

for i in range(0,oldNbVol):
    if outASLPrefix + "_" + str(i) + ".nii.gz" != ReferenceImage:
        os.remove(outASLPrefix + "_" + str(i) + ".nii.gz")

# denoising

if args.denoising==1:

    print("\n DENOISINGS 3D...")
    for i in range(0,nbVol):
        ASLDenoiseCommand = [animaDir + "animaNLMeans","-i", outASLPrefix + "_flow_" + str(i) + ".nii.gz", "-o", outASLPrefix + "_flow_" + str(i) + ".nii.gz"]
        print('denoising',i+1,'/',nbVol)
        call(ASLDenoiseCommand) 

# Could be a good idea to consider denoising with 4D patches.


# averaging

print("\n AVERAGING...")

concatCommand=[animaDir + "animaConcatenateImages", "-o", outASLPrefix + "_flow_4D.nii.gz"]
for i in range(0,nbVol):
    concatCommand.append("-i")
    concatCommand.append(outASLPrefix + "_flow_" + str(i) + ".nii.gz")
call(concatCommand, stdout=open(os.devnull, "w"))

ASLMeanImageCommand= [animaDir + "animaQuantileTemporalImage", "-i", outASLPrefix + "_flow_4D.nii.gz", "-m", outASLPrefix + "_flow_mean.nii.gz", "-q", str(args.meanQuantile)]
call(ASLMeanImageCommand, stdout=open(os.devnull, "w"))

if args.firstVolLabel == 0:
    ASLinvCommand=[animaDir +"animaImageArithmetic", "-i", outASLPrefix + "_flow_mean.nii.gz", "-M", "-1", "-o", outASLPrefix + "_flow_mean.nii.gz"]
    call(ASLinvCommand)


# quantification

print("\n QUANTIFICATION...")
quantifCommand=[animaDir +"animaCBFEstimation_PCASL", "-i", outASLPrefix + "_flow_mean.nii.gz", "--m0", outM0Prefix + "_reg.nii.gz", "-o", outASLPrefix + "_CBF.nii.gz", "-d", str(args.PLD), "-b", str(args.T1Blood), "-a", str(args.alpha), "-l", str(args.lambdaa), "-L", str(args.tau), "-s", str(args.sDelay)]
call(quantifCommand, stdout=open(os.devnull, "w"))

maskCommand=[animaDir + "animaMaskImage", "-i", outASLPrefix + "_CBF.nii.gz", "-m", outASLPrefix + "_maskASL.nii.gz", "-o", outASLPrefix + "_CBF_masked.nii.gz"]
call(maskCommand, stdout=open(os.devnull, "w"))

if args.fASL == 1:
    for i in range(0,nbVol):
        if args.firstVolLabel == 0:
            ASLinvCommand=[animaDir +"animaImageArithmetic", "-i", outASLPrefix + "_flow_" + str(i) + ".nii.gz", "-M", "-1", "-o", outASLPrefix + "_flow_" + str(i) + ".nii.gz"]
            call(ASLinvCommand)
        fQuantifCommand=[animaDir +"animaCBFEstimation", "-i", outASLPrefix + "_flow_" + str(i) + ".nii.gz", "--m0", outM0Prefix + "_reg.nii.gz", "-o", outASLPrefix + "_" + str(i) + "_CBF.nii.gz", "-d", str(args.PLD), "-b", str(args.T1Blood), "-a", str(args.alpha), "-l", str(args.lambdaa), "-L", str(args.tau), "-s", str(args.sDelay)]
        print('quantification',i+1,'/',nbVol)
        call(fQuantifCommand, stdout=open(os.devnull, "w"))
        maskCommand=[animaDir + "animaMaskImage", "-i", outASLPrefix + "_" + str(i) + "_CBF.nii.gz", "-m", outASLPrefix + "_maskASL.nii.gz", "-o", outASLPrefix + "_" + str(i) + "_CBF_masked.nii.gz"]
        call(maskCommand, stdout=open(os.devnull, "w"))

for i in range(0,nbVol):
        os.remove(outASLPrefix + "_flow_" + str(i) + ".nii.gz")


# registration onto a template

if args.template != "":
    print("\n REGISTRATION ONTO A TEMPLATE...")
    print("affine")
    affTemplateCommand=[animaDir + "animaPyramidalBMRegistration", "--ot", str(2), "-p", str(4), "-l", str(0), "-m", T1Image, "-r", args.template, "-o", outT1Prefix + "_regTemplate_aff.nii.gz","-O", outReg + "_regTemplate_aff_tr.txt" ]
    call(affTemplateCommand, stdout=open(os.devnull, "w"))
    print("diffeomorphic")
    diffeoTemplateCommand=[animaDir + "animaDenseSVFBMRegistration", "--sr", str(1), "--es", str(3), "--fs", str(2), "-m", outT1Prefix + "_regTemplate_aff.nii.gz", "-r", args.template, "-o", outT1Prefix + "_regTemplate_diffeo.nii.gz","-O", outReg + "_regTemplate_diffeo_tr.nii.gz" ]
    call(diffeoTemplateCommand, stdout=open(os.devnull, "w"))
    transfoGenCommand=[animaDir + "animaTransformSerieXmlGenerator", "-i", outReg + "_regTemplate_aff_tr.txt", "-i", outReg + "_regTemplate_diffeo_tr.nii.gz", "-o", outReg + "_regTemplate_tr.xml" ]
    call(transfoGenCommand, stdout=open(os.devnull, "w"))
    applyTransfoCommand=[animaDir + "animaApplyTransformSerie", "-i", outASLPrefix + "_CBF.nii.gz", "-g", args.template, "-t", outReg + "_regTemplate_tr.xml", "-o", outASLPrefix + "_CBF_regTemplate.nii.gz" ]
    call(applyTransfoCommand, stdout=open(os.devnull, "w"))

    if args.fASL == 1:
        for i in range(0,nbVol):
            applyTransfoCommand=[animaDir + "animaApplyTransformSerie", "-i", outASLPrefix + "_" + str(i) + "_CBF.nii.gz", "-g", args.template, "-t", outReg + "_regTemplate_tr.xml", "-o", outASLPrefix + "_" + str(i) + "_CBF_regTemplate.nii.gz" ]
            call(applyTransfoCommand, stdout=open(os.devnull, "w"))

toc = time.time()

print("\nprocessing time: ", toc-tic)

# #shutil.rmtree(tmpFolder)


