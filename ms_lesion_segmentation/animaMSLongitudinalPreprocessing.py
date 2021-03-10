import sys
import os
import configparser as ConfParser
import argparse
import subprocess
import shutil

# Data preprocessing for the Longitudinal Multipel Sclerosis Lesion Segmentation Challenge of MICCAI 2021.

# The preprocessing consists in three or four steps:
#  - brain extraction
#  - bias correction
#  - (optional) normalization on the given template
#  - mask flair images with the union of the masks of both time points

# Argument parsing
parser = argparse.ArgumentParser(
    description="""Preprocess data for the Longitudinal MS Lesion Segmentation Challenge of MICCAI 2021 with the anima library. 
                    The preprocessing consists in a brain extraction followed by a bias field correction.""", formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('-i', '--input', type=str, required=True, help="""Input folder containing the patients to preprocess (for example segmentation_challenge_miccai21/training/).
The folder must follow this structure:

/input/folder/
├── 013
│   ├── flair_time01_on_middle_space.nii.gz
│   ├── flair_time02_on_middle_space.nii.gz
│   ├── ground_truth_expert1.nii.gz
│   ├── ground_truth_expert2.nii.gz
│   ├── ground_truth_expert3.nii.gz
│   ├── ground_truth_expert4.nii.gz
│   └── ground_truth.nii.gz
├── 015
│   ├── flair_time01_on_middle_space.nii.gz
│   ├── flair_time02_on_middle_space.nii.gz
│   ├── ground_truth_expert1.nii.gz
│   ├── ground_truth_expert2.nii.gz
│   ├── ground_truth_expert3.nii.gz
│   ├── ground_truth_expert4.nii.gz
│   └── ground_truth.nii.gz
...
""")
parser.add_argument('-o', '--output', type=str, required=True, help='Output folder where the processed data will be saved (it will follow the same file structure as the input folder).')
parser.add_argument('-t', '--template', type=str, help='Path to the template image used to normalize intensities (optional, skip normalization if not given).')

args = parser.parse_args()

patients = args.input
templateFlair = args.template if args.template else None
output = args.output

# The configuration file for anima is ~/.anima/config.txt (can be overridden with -a and -s arguments)
configFilePath = os.path.join(os.path.expanduser("~"),'.anima', 'config.txt')

# Open the configuration parser and exit if anima configuration cannot be loaded
configParser = ConfParser.RawConfigParser()

if os.path.exists(configFilePath):
    configParser.read(configFilePath)
else:
    sys.exit('Please create a configuration file (~/.anima/config.txt) for Anima python scripts.')

# Initialize anima directories
animaDir = configParser.get("anima-scripts", 'anima')
animaScriptsPublicDir = configParser.get("anima-scripts", 'anima-scripts-public-root')

# Anima commands
animaBrainExtraction = os.path.join(animaScriptsPublicDir, "brain_extraction", "animaAtlasBasedBrainExtraction.py")
animaN4BiasCorrection = os.path.join(animaDir, "animaN4BiasCorrection")
animaNyulStandardization = os.path.join(animaDir, "animaNyulStandardization")
animaThrImage = os.path.join(animaDir, "animaThrImage")
animaMaskImage = os.path.join(animaDir, "animaMaskImage")
animaImageArithmetic = os.path.join(animaDir, "animaImageArithmetic")

# Calls a command, if there are errors: outputs them and exit
def call(command):
    command = [str(arg) for arg in command]
    status = subprocess.call(command)
    if status != 0:
        print(' '.join(command) + '\n')
        sys.exit('Command exited with status: ' + str(status))
    return status

# Preprocess all patients: 
#  - brain extraction
#  - bias correction
#  - normalize (optional)
#  - crop
for patientName in os.listdir(patients):

    patient = os.path.join(patients, patientName)

    if not os.path.isdir(patient): continue

    print("Preprocessing patient " + patientName + "...")

    # Create the output directory which will contain the preprocessed files
    patientOutput = os.path.join(output, patientName)
    
    os.makedirs(patientOutput, exist_ok=True)
    
    masks = []

    # For both time points: extract brain and remove bias
    for flairName in ['flair_time01_on_middle_space.nii.gz', 'flair_time02_on_middle_space.nii.gz']:
        
        flair = os.path.join(patient, flairName)
        brain = os.path.join(patientOutput, flairName)
        mask = os.path.join(patientOutput, flairName.replace('.nii.gz', '_mask.nii.gz'))

        # Extract brain
        call(["python", animaBrainExtraction, "-i", flair, "--mask", mask, "--brain", brain])

        # Remove bias
        call([animaN4BiasCorrection, "-i", brain, "-o", brain, "-B", "0.3"])
        
        if templateFlair and os.path.exists(templateFlair):
            # Normalize intensities with the given template
            call([animaNyulStandardization, "-m", flair, "-r", templateFlair, "-o", flair])
        elif not os.path.exists(templateFlair):
            print('Template file ' + templateFlair + ' not found, skipping normalization.')
        
        masks.append(mask)
    
    maskUnion = os.path.join(patientOutput, 'brain_mask.nii.gz')

    # Compute the union of the masks of both time points
    call([animaImageArithmetic, "-i", masks[0], "-a", masks[1], "-o", maskUnion])    # add the two masks
    call([animaThrImage, "-i", maskUnion, "-t", "0.5", "-o", maskUnion])                  # threshold to get a binary mask

    # Remove intermediate masks
    for mask in masks:
        os.remove(mask)
    
    # Copy the ground truths to the output directory
    for imageName in ['ground_truth_expert1.nii.gz', 'ground_truth_expert2.nii.gz', 'ground_truth_expert3.nii.gz', 'ground_truth_expert4.nii.gz', 'ground_truth.nii.gz']:
        shutil.copyfile(os.path.join(patient, imageName), os.path.join(patientOutput, imageName))

    # Mask original FLAIR images with the union mask
    for flairName in ['flair_time01_on_middle_space.nii.gz', 'flair_time02_on_middle_space.nii.gz']:
        
        flair = os.path.join(patient, flairName)
        brain = os.path.join(patientOutput, flairName)

        call([animaMaskImage, "-i", flair, "-m", maskUnion, "-o", brain])