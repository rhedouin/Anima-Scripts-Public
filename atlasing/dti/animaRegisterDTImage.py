#!/usr/bin/python
# Warning: works only on unix-like systems, not windows where "python animaAnatomicalRegisterImage.py ..." has to be run

import argparse
import os
import sys
from subprocess import call
import shutil

if sys.version_info[0] > 2:
    import configparser as ConfParser
else:
    import ConfigParser as ConfParser

configFilePath = os.path.expanduser("~") + "/.anima/config.txt"
if not os.path.exists(configFilePath):
    print('Please create a configuration file for Anima python scripts. Refer to the README')
    quit()

configParser = ConfParser.RawConfigParser()
configParser.read(configFilePath)

animaDir = configParser.get("anima-scripts", 'anima')

# Argument parsing
parser = argparse.ArgumentParser(
    description="Runs the registration of an image onto a current reference (to be used from build anatomical atlas).")
parser.add_argument('-d', '--ref-dir', type=str, required=True, help='Reference (working) folder')
parser.add_argument('-r', '--ref-image', type=str, required=True, help='Reference image')
parser.add_argument('-B', '--prefix-base', type=str, required=True, help='Prefix base')
parser.add_argument('-p', '--prefix', type=str, required=True, help='Prefix')
parser.add_argument('-b', '--bch-order', type=int, default=2, help='BCH order when composing transformations in rigid unbiased (default: 2)')
parser.add_argument('-n', '--num-image', type=int, required=True, help='Image number')
parser.add_argument('-c', '--num-cores', type=int, default=40, help='Number of cores to run on')
parser.add_argument('--rigid', action='store_true', help="Unbiased atlas up to a rigid transformation")

args = parser.parse_args()
os.chdir(args.ref_dir)
basePrefBase = os.path.dirname(args.prefix_base)

animaComputeDTIScalarMaps = os.path.join(animaDir,"animaComputeDTIScalarMaps")
animaCreateImage = os.path.join(animaDir,"animaCreateImage")
animaMaskImage = os.path.join(animaDir,"animaMaskImage")
animaThrImage = os.path.join(animaDir,"animaThrImage")
animaPyramidalBMRegistration = os.path.join(animaDir,"animaPyramidalBMRegistration")
animaDenseTensorSVFBMRegistration = os.path.join(animaDir,"animaDenseTensorSVFBMRegistration")
animaTransformSerieXmlGenerator = os.path.join(animaDir,"animaTransformSerieXmlGenerator")
animaLinearTransformArithmetic = os.path.join(animaDir,"animaLinearTransformArithmetic")
animaLinearTransformToSVF = os.path.join(animaDir,"animaLinearTransformToSVF")
animaDenseTransformArithmetic = os.path.join(animaDir,"animaDenseTransformArithmetic")
animaApplyTransformSerie = os.path.join(animaDir,"animaApplyTransformSerie")
animaTensorApplyTransformSerie = os.path.join(animaDir,"animaTensorApplyTransformSerie")

# Extract DTI scalar map
command = [animaComputeDTIScalarMaps,"-i",os.path.join(args.prefix_base,args.prefix + "_" + str(args.num_image) + ".nii.gz"),
           "-a",os.path.join(args.prefix_base,args.prefix + "_" + str(args.num_image) + "_ADC.nii.gz")]
call(command)

command = [animaComputeDTIScalarMaps,"-i",args.ref_image,
           "-a",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_ref_ADC.nii.gz")]
call(command)

# Rigid / affine registration
command = [animaPyramidalBMRegistration,"-r",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_ref_ADC.nii.gz"),
           "-m",os.path.join(args.prefix_base,args.prefix + "_" + str(args.num_image) + "_ADC.nii.gz"),
           "-o",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_aff_ADC.nii.gz"),
           "-O",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_aff_tr.txt"),
           "--out-rigid",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_aff_nr_tr.txt"),
           "--ot","2","-p","3","-l","0","-I","2","-T",str(args.num_cores),"--sym-reg","2","-s","0"]
call(command)

# Apply to DTI and prepare data crop for better registration

command = [animaTransformSerieXmlGenerator,"-i",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_aff_tr.txt"),
           "-o",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_aff_tr.xml")]
call(command)

command = [animaCreateImage,"-b","1","-v","1","-g",os.path.join(args.prefix_base,args.prefix + "_" + str(args.num_image) + ".nii.gz"),
           "-o",os.path.join(basePrefBase,"tempDir","tmpFullMask_" + str(args.num_image) + ".nii.gz")]
call(command)

command = [animaApplyTransformSerie,"-g",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_ref_ADC.nii.gz"),
           "-i",os.path.join(basePrefBase,"tempDir","tmpFullMask_" + str(args.num_image) + ".nii.gz"),
           "-t",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_aff_tr.xml"),
           "-o",os.path.join(basePrefBase,"tempDir","tmpMask_" + str(args.num_image) + ".nii.gz"),
           "-n","nearest","-p",str(args.num_cores)]
call(command)

command = [animaMaskImage,"-i",args.ref_image,"-m",os.path.join(basePrefBase,"tempDir","tmpMask_" + str(args.num_image) + ".nii.gz"),
           "-o",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_ref_c.nii.gz")]
call(command)

command = [animaTensorApplyTransformSerie,"-i",os.path.join(args.prefix_base,args.prefix + "_" + str(args.num_image) + ".nii.gz"),
           "-g",args.ref_image,"-t",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_aff_tr.xml"),
           "-o",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_aff.nii.gz"),"-p",args.num_cores]
call(command)

# Non-Rigid registration

# For basic atlases
command = [animaDenseTensorSVFBMRegistration,"-r",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_ref_c.nii.gz"),
           "-m",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_aff.nii.gz"),
           "-o",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_bal.nii.gz"),
           "-O",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_bal_tr.nii.gz"),
           "--sr","1","--es","3","--fs","2","-T",str(args.num_cores),"--sym-reg","2","--metric","3","-s","0.001"]
call(command)

os.remove(os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_ref_c.nii.gz"))

if args.rigid is True:
    shutil.move(os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_aff_nr_tr.txt"),
                os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_linear_tr.txt"))

    command = [animaLinearTransformArithmetic,"-i",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_linear_tr.txt"),
               "-M","-1","-c",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_aff_tr.txt"),
               "-o",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_linearaddon_tr.txt")]
    call(command)

    command = [animaLinearTransformToSVF,"-i",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_linearaddon_tr.txt"),
               "-o",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_linearaddon_tr.nii.gz"),
               "-g",args.ref_image]
    call(command)

    command = [animaDenseTransformArithmetic,"-i",os.path.join(basePrefBase, "tempDir", args.prefix + "_" + str(args.num_image) + "_linearaddon_tr.nii.gz"),
               "-c",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_bal_tr.nii.gz"),
               "-b",str(args.bch_order),
               "-o",os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_nonlinear_tr.nii.gz")]
    call(command)
else:
    shutil.move(os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_aff_tr.txt"),
                os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_linear_tr.txt"))
    shutil.move(os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_bal_tr.nii.gz"),
                os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_nonlinear_tr.nii.gz"))

if os.path.exists(os.path.join(os.getcwd(), "residualDir", args.prefix + "_" + str(args.num_image) + "_nonlinear_tr.nii.gz")):
    os.remove(os.path.join(os.getcwd(), "residualDir", args.prefix + "_" + str(args.num_image) + "_nonlinear_tr.nii.gz"))

os.symlink(os.path.join(os.getcwd(),"tempDir",args.prefix + "_" + str(args.num_image) + "_nonlinear_tr.nii.gz"),
           os.path.join(os.getcwd(), "residualDir", args.prefix + "_" + str(args.num_image) + "_nonlinear_tr.nii.gz"))

if os.path.exists(os.path.join(os.getcwd(),"tempDir",args.prefix + "_" + str(args.num_image) + "_nonlinear_tr.nii.gz")):
    open(os.path.join(basePrefBase,"residualDir",args.prefix + "_" + str(args.num_image) + "_flag"), 'a').close()

if os.path.exists(os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_bal_tr.nii.gz")):
    os.remove(os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_bal_tr.nii.gz"))

if os.path.exists(os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_linearaddon_tr.nii.gz")):
    os.remove(os.path.join(basePrefBase,"tempDir",args.prefix + "_" + str(args.num_image) + "_linearaddon_tr.nii.gz"))
