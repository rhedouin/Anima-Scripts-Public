#!/usr/bin/python
# Warning: works only on unix-like systems, not windows where "python animaComputeLongitudinalAtlasWeights.py ..." has to be run

import argparse
import os
import sys
from subprocess import call

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
parser = argparse.ArgumentParser(description="Perform similarity registration")

parser.add_argument('-i', '--image-file', required=True, type=str, help='list of images (in txt file)')
parser.add_argument('-I', '--image-number', required=True, type=int, help='image number')
parser.add_argument('-o', '--out-dir', required=True, type=str, help='output directory')
parser.add_argument('-a', '--reference-image',required=True, type=str, help='reference image')
parser.add_argument('-c', '--num-cores', type=int, default=8, help='number of cores to run on (default: 8)')

args = parser.parse_args()

outDir = args.out_dir

with open(args.image_file) as f:
    images = f.read().splitlines()
    
image=images[args.image_number-1]
sub = os.path.splitext(image)[0]
if os.path.splitext(image)[1] == '.gz' :
    sub = os.path.splitext(sub)[0]
sub=os.path.basename(sub)
outSub=os.path.join(outDir, "similarity", sub)

ref = args.reference_image

animaPyramidalBMRegistration = os.path.join(animaDir,"animaPyramidalBMRegistration")

command = [animaPyramidalBMRegistration,"-r",ref,"-m",image,
           "-o", outSub + "_sim.nii.gz", "--out-sim", outSub + "_sim_tr.txt",
           "--ot","2","-p","3","-l","0","-I","2","-T",str(args.num_cores)]
call(command)

os.remove(outSub + "_sim.nii.gz")

