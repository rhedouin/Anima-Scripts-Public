#!/usr/bin/python3

import sys
import argparse

if sys.version_info[0] > 2:
    import configparser as ConfParser
else:
    import ConfigParser as ConfParser

import tempfile
import os
import glob
from subprocess import call
import shutil

configFilePath = os.path.join(os.path.expanduser("~"), ".anima",  "config.txt")
if not os.path.exists(configFilePath):
    print('Please create a configuration file for Anima python scripts. Refer to the README')
    quit()

configParser = ConfParser.RawConfigParser()
configParser.read(configFilePath)

animaDir = configParser.get("anima-scripts", 'anima')
animaScriptsDir = configParser.get("anima-scripts", 'anima-scripts-public-root')

# Argument parsing
parser = argparse.ArgumentParser(description="Given a fiber atlas constructed from controls data, and a patient image, performs patient to atlas comparison")

parser.add_argument('-m', '--mcm-patient-list', type=str, required=True, help='MCM patient list')

parser.add_argument('-r', '--raw-tracts-folder', type=str, default='Atlas_Tracts', help='Raw atlas tracts folder')
parser.add_argument('--tracts-folder', type=str, default='Augmented_Atlas_Tracts', help='Atlas tracts augmented with controls data')
parser.add_argument('--temp-folder', type=str, default="", help='Specify a temp folder')
parser.add_argument('--output-prefix', type=str, default="", help='Specify a temp folder')

args = parser.parse_args()

# The goal here is to create, from a group of controls and a group of patient's data, stats along tracts of differences. The script should preferably be run in the atlas folder.

animaTracksMCMPropertiesExtraction = os.path.join(animaDir, "animaTracksMCMPropertiesExtraction")
animaGroupToGroupComparisonOnTracks =  os.path.join(animaDir, "animaGroupToGroupComparisonOnTracks")
animaFibersFDRCorrectPValues = os.path.join(animaDir, "animaFibersFDRCorrectPValues")
animaFibersDiseaseScores = os.path.join(animaDir, "animaFibersDiseaseScores")

os.makedirs('Stat_on_tracks', exist_ok=True)

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

outputPrefix = args.output_prefix

print("Read mcm text file")
file = open(args.mcm_patient_list)
mcm_list = file.read().splitlines()

outputFolder = os.path.join('Stat_on_tracks', outputPrefix)
os.makedirs(outputFolder,  exist_ok=True)

# Process tracks: augmenting with patient and perform comparison
for track in tracksLists:
    print("track : ", track)
    if args.temp_folder == '':
       tmpFolder = tempfile.mkdtemp()
    else:
       tmpFolder = args.temp_folder
       os.makedirs(tmpFolder, exist_ok=True)

    tractListFile = open(os.path.join(tmpFolder, 'listTrack_' + track + '.txt'), "w")

    it=0
    for current_mcm in mcm_list:
        it = it+1
        # Remove \n at the end of the line
        print(current_mcm)

        # augment tracks of the atlas with MCM patient data
        propsExtractionCommand = [animaTracksMCMPropertiesExtraction, "-i", os.path.join(args.raw_tracts_folder, track + '.fds'),
                              "-m", current_mcm, "-o", os.path.join(tmpFolder, track + '_MCM_augmented_onAtlas_' + str(it) + '.fds')]

        call(propsExtractionCommand)

        tractListFile.write(os.path.join(tmpFolder, track + '_MCM_augmented_onAtlas_' + str(it) + '.fds') + "\n")

    tractListFile.close()

#    # Compare to controls list of augmented tracts
    groupComparisonCommand = [animaGroupToGroupComparisonOnTracks, "-c", os.path.join(args.tracts_folder, "listData_" + track + ".txt"), "-p", os.path.join(tmpFolder, 'listTrack_' + track + '.txt'), "-o", os.path.join(outputFolder, outputPrefix + '_' + track + '_average_controls.fds'), "-O", os.path.join(outputFolder, outputPrefix + '_' + track + '_average_patients.fds'), "-d", os.path.join(tmpFolder, track + '_diff_controls_patients.fds'), "-t", os.path.join(tmpFolder, track + '_student_t_test.fds'), "-P", os.path.join(outputFolder, outputPrefix + '_' + track + '_student_t_test_PV.fds')]
    call(groupComparisonCommand)

    fdrCorrectionCommand = [animaFibersFDRCorrectPValues, "-i", os.path.join(outputFolder, outputPrefix + '_' + track + '_student_t_test_PV.fds'), "-o", os.path.join(outputFolder, outputPrefix + '_' + track + '_student_t_test_PV_FDR_010.fds'), "-q", "0.1"]
    call(fdrCorrectionCommand)

    # Compute final scores CSV
    command = [animaFibersDiseaseScores, "-i", os.path.join(outputFolder, outputPrefix + '_' + track + '_student_t_test_PV_FDR_010.fds'),
               "-o", os.path.join(outputFolder, outputPrefix + '_' + track + '_student_t_test_PV_FDR_010.csv'), "-p", "6"]
    call(command)

    shutil.rmtree(tmpFolder)
