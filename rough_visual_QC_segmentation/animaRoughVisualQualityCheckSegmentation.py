#!/usr/bin/python3
# Warning: works only on unix-like systems, not windows where "python animaAtlasBasedBrainExtraction.py ..." has to be run

import sys
import argparse
import os
from shutil import copyfile
from subprocess import call, check_output

if sys.version_info[0] > 2:
    import configparser as ConfParser
else:
    import ConfigParser as ConfParser

configFilePath = os.path.join(os.path.expanduser("~"), ".anima",  "config.txt")
if not os.path.exists(configFilePath):
    print('Please create a configuration file for Anima python scripts. Refer to the README')
    quit()

configParser = ConfParser.RawConfigParser()
configParser.read(configFilePath)

animaDir = configParser.get("anima-scripts", 'anima')
animaPyramidalBMRegistration = os.path.join(animaDir, "animaPyramidalBMRegistration")
animaTransformSerieXmlGenerator = os.path.join(animaDir, "animaTransformSerieXmlGenerator")
animaApplyTransformSerie = os.path.join(animaDir, "animaApplyTransformSerie")
animaConcatenateImages = os.path.join(animaDir, "animaConcatenateImages")
animaCropImage = os.path.join(animaDir, "animaCropImage")
animaConvertImage = os.path.join(animaDir, "animaConvertImage")

# Argument parsing
parser = argparse.ArgumentParser(description="Build volumes containing 1 slice per subjects for a rough visual quality check of the segmentations")

parser.add_argument('-i', '--image-file', required=True, type=str, help='list of anatomical images to be segmented (in txt file)')
parser.add_argument('-s', '--seg-file', required=True, type=str, help='list of output label images from segmentation (in txt file)')
parser.add_argument('-x', '--xdim', required=True, type=int, help='blim')
parser.add_argument('-y', '--ydim', required=True, type=int, help='blam')
parser.add_argument('-z', '--zdim', required=True, type=int, help='blom')
parser.add_argument('-r', '--ref-file', default="", type=str, help='reference image for orientation')
parser.add_argument('-o', '--out-dir', required=True, type=str, help='output directory')
parser.add_argument('-c', '--num-cores', type=int, default=8, help='Number of cores to run on (default: 8)')

args = parser.parse_args()

images = [line.rstrip('\n') for line in open(args.image_file)]            
N = len(images)
segs = [line.rstrip('\n') for line in open(args.seg_file)]
if args.ref_file == "":
    ref = images[0]
else:
    ref = args.ref_file

if len(segs) != N:
    print("The number of anatomical images must be equal to the number of label images")
    exit()
    
outDir = args.out_dir
if not os.path.exists(outDir):
    os.makedirs(outDir)
if not os.path.exists(os.path.join(outDir, "err")):
    os.makedirs(os.path.join(outDir, "err"))
if not os.path.exists(os.path.join(outDir, "out")):
    os.makedirs(os.path.join(outDir, "out"))
if not os.path.exists(os.path.join(outDir, "registrations")):
    os.makedirs(os.path.join(outDir, "registrations"))

# Decide on whether to use large image setting or small image setting
command = [animaConvertImage, "-i", ref, "-I"]
convert_output = check_output(command, universal_newlines=True)
size_info = convert_output.split('\n')[1].split('[')[1].split(']')[0]
large_image = False
for i in range(0, 3):
    size_tmp = int(size_info.split(', ')[i])
    if size_tmp >= 350:
        large_image = True
        break

pyramidOptions = ["-p", "4", "-l", "1"]
if large_image:
    pyramidOptions = ["-p", "5", "-l", "2"]

for i in range(0, N):
    print("----------------------" + str(i) + "----------------------")
    image=images[i]  
    seg=segs[i]
    
    # Registrations
  
    command = [animaPyramidalBMRegistration, "-m", image, "-r", ref, "-O", os.path.join(outDir, "registrations", str(i)) + "_aff.txt",
            "-o", os.path.join(outDir, "registrations", str(i)) + "_anat_aff.nii.gz", "--sp", "3", "--ot", "2", "--out-rigid", os.path.join(outDir, "registrations", str(i)) + "_rig.txt" ] + pyramidOptions
    call(command)
    
    command = [animaTransformSerieXmlGenerator, "-i", os.path.join(outDir, "registrations", str(i)) + "_rig.txt", "-o", os.path.join(outDir, "registrations", str(i)) + "_rig.xml"]
    call(command)
    command = [animaTransformSerieXmlGenerator, "-i", os.path.join(outDir, "registrations", str(i)) + "_aff.txt", "-o", os.path.join(outDir, "registrations", str(i)) + "_aff.xml"]
    call(command)

    command = [animaApplyTransformSerie, "-i", image, "-t", os.path.join(outDir, "registrations", str(i)) + "_rig.xml", "-g", ref, "-o",
            os.path.join(outDir, "registrations", str(i)) + "_anat_rig.nii.gz"]
    call(command)
    command = [animaApplyTransformSerie, "-i", seg, "-t", os.path.join(outDir, "registrations", str(i)) + "_rig.xml", "-g", ref, "-o",
            os.path.join(outDir, "registrations", str(i)) + "_seg_rig.nii.gz", "-n", "nearest"]
    call(command)
    command = [animaApplyTransformSerie, "-i", seg, "-t", os.path.join(outDir, "registrations", str(i)) + "_aff.xml", "-g", ref, "-o",
            os.path.join(outDir, "registrations", str(i)) + "_seg_aff.nii.gz", "-n", "nearest"]
    call(command)


    # Croppings and concatenatings
          
    for img in ["anat", "seg"]:
        for transfo in ["rig", "aff"]:
            command = [animaCropImage, "-i", os.path.join(outDir, "registrations", str(i)) + "_" + img + "_" + transfo + ".nii.gz", "-x", str(args.xdim), "-X", "1", "-o", 
                        os.path.join(outDir, "registrations", str(i)) + "_" + img + "_" + transfo + "_x.nii.gz"]
            call(command)
            command = [animaCropImage, "-i", os.path.join(outDir, "registrations", str(i)) + "_" + img + "_" + transfo + ".nii.gz", "-y", str(args.ydim), "-Y", "1", "-o", 
                        os.path.join(outDir, "registrations", str(i)) + "_" + img + "_" + transfo + "_y.nii.gz"]
            call(command)
            command = [animaCropImage, "-i", os.path.join(outDir, "registrations", str(i)) + "_" + img + "_" + transfo + ".nii.gz", "-z", str(args.zdim), "-Z", "1", "-o", 
                        os.path.join(outDir, "registrations", str(i)) + "_" + img + "_" + transfo + "_z.nii.gz"]
            call(command)
            

orient=["SAGITTAL","CORONAL","AXIAL"]
dim=["x","y","z"]
for img in ["anat", "seg"]:
    for transfo in ["rig", "aff"]:
        for j in range(0, 3):           
            copyfile(os.path.join(outDir, "registrations", "0") + "_" + img + "_" + transfo + "_" + dim[j] + ".nii.gz", os.path.join(outDir, "QC_" + img + "_" + transfo + "_" + dim[j] + ".nii.gz"))
            command = [animaConcatenateImages, "-o", os.path.join(outDir, "QC_" + img + "_" + transfo + "_" + dim[j] + ".nii.gz"), "-b", os.path.join(outDir, "registrations", "0_") + img + "_" + transfo + "_" + dim[j] + ".nii.gz"]
            for i in range(1, N):
                command = command + ["-i", os.path.join(outDir, "registrations", str(i)) + "_" + img + "_" + transfo + "_" + dim[j] + ".nii.gz"]
            
            call(command)
            command = [animaConvertImage, "-i", os.path.join(outDir, "QC_" + img + "_" + transfo + "_" + dim[j] + ".nii.gz"), "-R", orient[j], "-o", os.path.join(outDir, "QC_" + img + "_" + transfo + "_" + dim[j] + ".nii.gz")]
            call(command)
            command = [animaCropImage, "-i", os.path.join(outDir, "QC_" + img + "_" + transfo + "_" + dim[j] + ".nii.gz"), "-" + "Z", "0", "-o", os.path.join(outDir, "QC_" + img + "_" + transfo + "_" + dim[j] + ".nii.gz")]
            call(command)
                
            
            
            
            
            
    
