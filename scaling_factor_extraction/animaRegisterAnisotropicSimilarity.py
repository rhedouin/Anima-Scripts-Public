#!/usr/bin/python
# Warning: works only on unix-like systems, not windows where "python animaComputeLongitudinalAtlasWeights.py ..." has to be run

import argparse
import os
import sys
from subprocess import call

from read_ITK_transform import readITKtransform

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
animaScriptsDir = configParser.get("anima-scripts", 'anima-scripts-public-root')

# Argument parsing
parser = argparse.ArgumentParser(description="Perform anisotropic similarity registration")

parser.add_argument('-i', '--image-file', required=True, type=str, help='list of images (in txt file)')
parser.add_argument('-I', '--image-number', required=True, type=int, help='image number')
parser.add_argument('-m', '--mask-file', default="", type=str, help='list of masks (in txt file)')
parser.add_argument('-M', '--mask-number', default=1, type=int, help='mask number')
parser.add_argument('-o', '--out-dir', required=True, type=str, help='output directory')
parser.add_argument('-u', '--scalDir-file', type=str, help='directions of scaling (in itk txt affine transform) (real coordinates)')
parser.add_argument('-a', '--reference-image',required=True, type=str, help='reference image')
parser.add_argument('-c', '--num-cores', type=int, default=8, help='number of cores to run on (default: 8)')

args = parser.parse_args()

outDir = args.out_dir

with open(args.image_file) as f:
    images = f.read().splitlines()
image=images[args.image_number-1]

if args.mask_file != "":
    with open(args.mask_file) as f:
        masks = f.read().splitlines()
    mask=masks[args.mask_number-1]

with open(args.scalDir_file) as f:
    us = f.read().splitlines()
if len(us)>1:
    u=us[args.mask_number-1]
else:
    u=us[0];

sub = os.path.splitext(image)[0]
if os.path.splitext(image)[1] == '.gz' :
    sub = os.path.splitext(sub)[0]
sub=os.path.basename(sub)
outSubSim=os.path.join(outDir, "similarity", sub)
outSubAnisotropSim=os.path.join(outDir, "anisotropicSimilarity", "ROI_" + str(args.mask_number), sub)

ref = args.reference_image

animaPyramidalBMRegistration = os.path.join(animaDir,"animaPyramidalBMRegistration")

command = [animaPyramidalBMRegistration,"-r",ref,"-m",image,
           "-o", outSubAnisotropSim + "_anisotropSim.nii.gz", "-O", outSubAnisotropSim + "_anisotropSim_tr.txt",
           "--ot","3","-p","3","-l","0","-T",str(args.num_cores),
           "-i", outSubSim + "_sim_tr.txt", "-U", u]
if args.mask_file != "":
    command += ["-M", mask]
call(command)

os.remove(outSubAnisotropSim + "_anisotropSim.nii.gz")
