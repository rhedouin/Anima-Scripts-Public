#!/usr/bin/python
# Warning: works only on unix-like systems, not windows where "python animaComputeLongitudinalAtlasWeights.py ..." has to be run

import argparse
import os
import sys
import subprocess

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
parser = argparse.ArgumentParser(description="Compute scaling factors through anisotropic similarity registration")

parser.add_argument('-i', '--image-file', required=True, type=str, help='list of images (in txt file)')
parser.add_argument('-o', '--out-dir', required=True, type=str, help='output directory')
parser.add_argument('-u', '--scalDir-file', type=str, help='list of directions of scaling (in txt file, direction files are itk txt transform) - 1 for each ROI or 1 in total')
parser.add_argument('-a', '--reference-image', required=True, type=str, help='reference image onto which images will be registered using anisotropic similarity transformation')
parser.add_argument('-c', '--num-cores', type=int, default=8, help='number of cores to run on (default: 8)')

parser.add_argument('-m', '--mask-file', type=str, default="", help='list of masks of ROIs (in txt file) associated to the reference image')
parser.add_argument('-r', '--root-image-file', type=str, default="", help='list of images (in txt file) for renormalization - relative scaling factors will be divided by the average of the scaling factors of those root images')

args = parser.parse_args()

ref = args.reference_image
if args.mask_file != "":
    with open(args.mask_file) as f:
        masks = f.read().splitlines()

if not os.path.exists(args.out_dir):
    os.makedirs(args.out_dir)
        
for k in [1,2]:
    
    # creating folder tree
    
    if args.root_image_file == "":
        continue
    if k==1:
        outDir=os.path.join(args.out_dir, "root")
        with open(args.root_image_file) as f:
            images = f.read().splitlines()
        jobName="regRoot"
    else:
        outDir=args.out_dir
        with open(args.image_file) as f:
            images = f.read().splitlines()
        jobName="reg"
    if not os.path.exists(outDir):
        os.makedirs(outDir)
    if not os.path.exists(os.path.join(outDir, "similarity")):
        os.makedirs(os.path.join(outDir, "similarity"))        
    if not os.path.exists(os.path.join(outDir, "anisotropicSimilarity")):
        os.makedirs(os.path.join(outDir, "anisotropicSimilarity")) 
        
    if args.mask_file != "":    
        for i in range(1, len(masks)+1):
            if not os.path.exists(os.path.join(outDir, "anisotropicSimilarity", "ROI_"+str(i))):
                os.makedirs(os.path.join(outDir, "anisotropicSimilarity", "ROI_"+str(i)))
    else:
        if not os.path.exists(os.path.join(outDir, "anisotropicSimilarity", "ROI_1")):
            os.makedirs(os.path.join(outDir, "anisotropicSimilarity", "ROI_1"))

    numJobs = len(images)
    nCoresPhysical = int(args.num_cores / 2)


    # similarity registration
    
    fileName = os.path.join(outDir, "simReg")
    myfile = open(fileName,"w")
    myfile.write("#!/bin/bash\n")
    if args.num_cores<=16:
        myfile.write("#OAR -l {hyperthreading=\'NO\'}/nodes=1/core=" + str(args.num_cores) + ",walltime=00:59:00\n")
    myfile.write("#OAR -l {hyperthreading=\'YES\'}/nodes=1/core=" + str(nCoresPhysical) + ",walltime=00:59:00\n")
    myfile.write("#OAR --array " + str(numJobs) + "\n")
    myfile.write("#OAR -O " + os.path.join(outDir, "similarity", "%jobid%.output\n"))
    myfile.write("#OAR -E " + os.path.join(outDir, "similarity", "%jobid%.error\n"))

    myfile.write("python " + os.path.join(animaScriptsDir,"scaling_factor_extraction","animaRegisterSimilarity.py") +
                     " -i " + args.image_file + " -o " + outDir + " -a " + ref +
                     " -I $OAR_ARRAY_INDEX -c " + str(args.num_cores))
    myfile.write("\n")
    myfile.close()
    os.chmod(fileName, 0755)

    oarRunCommand = ["oarsub","-n", jobName + "Sim","-S", fileName]
    if k==2 and args.root_image_file != "":
        for jobId in jobsIds:
            oarRunCommand += ["-a",jobId]
        
    jobsIds = []
    procStat = subprocess.Popen(oarRunCommand, stdout=subprocess.PIPE)
    for statsLine in procStat.stdout:
        if "OAR_JOB_ID" in statsLine:
            jobsIds += [statsLine.split("=")[1]]
            
            
    # anisotropic similarity registration
    
    fileName2 = os.path.join(outDir, "anisotropSimReg")
    myfile = open(fileName2,"w")
    myfile.write("#!/bin/bash\n")
    if args.num_cores<=16:
        myfile.write("#OAR -l {hyperthreading=\'NO\'}/nodes=1/core=" + str(args.num_cores) + ",walltime=01:59:00\n")
    myfile.write("#OAR -l {hyperthreading=\'YES\'}/nodes=1/core=" + str(nCoresPhysical) + ",walltime=01:59:00\n")
    myfile.write("#OAR --array " + str(numJobs) + "\n")
    myfile.write("#OAR -O " + os.path.join(outDir, "anisotropicSimilarity", "%jobid%.output\n"))
    myfile.write("#OAR -E " + os.path.join(outDir, "anisotropicSimilarity", "%jobid%.error\n"))
    if args.mask_file != "":
        for i in range(0, len(masks)):
            myfile.write("python " + os.path.join(animaScriptsDir,"scaling_factor_extraction","animaRegisterAnisotropicSimilarity.py") +
                         " -i " + args.image_file + " -o " + outDir + " -a " + ref +
                         " -m " + args.mask_file + " -M " + str(i+1) + " -u " + args.scalDir_file + 
                         " -I $OAR_ARRAY_INDEX -c " + str(args.num_cores))
            myfile.write("\n")
    else:
        myfile.write("python " + os.path.join(animaScriptsDir,"scaling_factor_extraction","animaRegisterAnisotropicSimilarity.py") +
                     " -i " + args.image_file + " -o " + outDir + " -a " + ref +
                     " -u " + args.scalDir_file + 
                     " -I $OAR_ARRAY_INDEX -c " + str(args.num_cores))
        myfile.write("\n")
    myfile.close()
    os.chmod(fileName2, 0755)
    
    oarRunCommand = ["oarsub","-n", jobName + "AnisotropSim","-S", fileName2]
    for jobId in jobsIds:
        oarRunCommand += ["-a",jobId]
        
    procStat = subprocess.Popen(oarRunCommand, stdout=subprocess.PIPE)
    for statsLine in procStat.stdout:
        if "OAR_JOB_ID" in statsLine:
            jobsIds += [statsLine.split("=")[1]]    


fileName3 = os.path.join(outDir, "extractScal")
myfile = open(fileName3,"w")
myfile.write("#!/bin/bash\n")
if args.num_cores<=16:
    myfile.write("#OAR -l {hyperthreading=\'NO\'}/nodes=1/core=" + str(args.num_cores) + ",walltime=01:59:00\n")
myfile.write("#OAR -l {hyperthreading=\'YES\'}/nodes=1/core=" + str(nCoresPhysical) + ",walltime=01:59:00\n")
myfile.write("#OAR --array 1 \n")
myfile.write("#OAR -O " + os.path.join(outDir, "extractScal.%jobid%.output\n"))
myfile.write("#OAR -E " + os.path.join(outDir, "extractScal.%jobid%.error\n"))
myfile.write("python " + os.path.join(animaScriptsDir,"scaling_factor_extraction","animaExtractScalingFactors.py") +
         " -i " + args.image_file + " -o " + outDir + 
         " -u " + args.scalDir_file + " -c " + str(args.num_cores))
if args.mask_file != "":
    myfile.write(" -m " + args.mask_file)
if args.root_image_file != "":
    myfile.write(" -r " + args.root_image_file)
myfile.write("\n")
myfile.close()
os.chmod(fileName3, 0755)

oarRunCommand = ["oarsub","-n", "extractScal","-S", fileName3]
for jobId in jobsIds:
    oarRunCommand += ["-a",jobId]
    
procStat = subprocess.Popen(oarRunCommand, stdout=subprocess.PIPE)



#rm -rf out; python animaComputeScalingFactors.py -i data/images.txt -o out -u data/list_u.txt -a data/atlas.nii.gz -m data/masks.txt -r data/rootImages.txt

