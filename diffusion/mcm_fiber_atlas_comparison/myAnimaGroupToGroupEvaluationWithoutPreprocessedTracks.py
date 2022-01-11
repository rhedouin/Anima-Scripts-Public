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

parser.add_argument('-f', '--mcm-first-list', type=str, required=True, help='MCM first group list')
parser.add_argument('-s', '--mcm-second-list', type=str, required=True, help='MCM second group list')

parser.add_argument('-r', '--raw-tracts-folder', type=str, default='Atlas_Tracts', help='Raw atlas tracts folder')

parser.add_argument('--temp-folder', type=str, default="", help='Specify a temp folder')
parser.add_argument('--output-name', type=str, default="", help='Specify a output folder / output prefix')

args = parser.parse_args()

# The goal here is to create, from a group of controls and a group of patient's data, stats along tracts of differences. The script should preferably be run in the atlas folder.

animaTracksMCMPropertiesExtraction = os.path.join(animaDir, "animaTracksMCMPropertiesExtraction")
animaGroupToGroupComparisonOnTracks =  os.path.join(animaDir, "animaGroupToGroupComparisonOnTracks")
animaFibersFDRCorrectPValues = os.path.join(animaDir, "animaFibersFDRCorrectPValues")
animaFibersDiseaseScores = os.path.join(animaDir, "animaFibersDiseaseScores")

os.makedirs('Stat_on_tracks', exist_ok=True)

# Tracts list imported from tractseg
tracksLists = ['AF_left', 'AF_right', 'ATR_left', 'ATR_right', 'CA', 'CC_1', 'CC_2', 'CC_4', 'CC_5', 'CC_6',
               'CC_7', 'CG_left', 'CG_right', 'CST_left', 'CST_right', 'MLF_left', 'MLF_right', 'FPT_left', 'FPT_right',
               'FX_left', 'FX_right', 'ICP_left', 'ICP_right', 'IFO_left', 'IFO_right', 'ILF_left', 'ILF_right', 'MCP',
               'OR_left', 'OR_right', 'POPT_left', 'POPT_right', 'SCP_left', 'SCP_right', 'SLF_I_left', 'SLF_I_right',
               'SLF_II_left', 'SLF_II_right', 'SLF_III_left', 'SLF_III_right', 'STR_left', 'STR_right', 'UF_left',
               'UF_right', 'T_PREF_left', 'T_PREF_right', 'T_PREM_left', 'T_PREM_right', 'T_PREC_left',
               'T_PREC_right', 'T_POSTC_left', 'T_POSTC_right', 'T_PAR_left', 'T_PAR_right', 'T_OCC_left',
               'T_OCC_right', 'ST_FO_left', 'ST_FO_right', 'ST_PREF_left', 'ST_PREF_right', 'ST_PREM_left',
               'ST_PREM_right', 'ST_PREC_left', 'ST_PREC_right', 'ST_POSTC_left', 'ST_POSTC_right', 'ST_PAR_left',
               'ST_PAR_right', 'ST_OCC_left', 'ST_OCC_right']

outputFolder = os.path.dirname(args.output_name)
outputPrefix = os.path.basename(args.output_name)

print("Read mcm first group text file")
first_file = open(args.mcm_first_list)
mcm_first_list = first_file.read().splitlines()

print("Read mcm second group text file")
second_file = open(args.mcm_second_list)
mcm_second_list = second_file.read().splitlines()

# Process tracks: augmenting with patient and perform comparison
for track in tracksLists:
    print("track : ", track)
    if args.temp_folder == '':
       tmpFolder = tempfile.mkdtemp()
    else:
       tmpFolder = args.temp_folder
       shutil.rmtree(tmpFolder)
       os.makedirs(tmpFolder, exist_ok=True)

    firstListFile = open(os.path.join(tmpFolder, "first_listTrack_" + track + ".txt"), "w")
    it=0
    print("First group tracks extraction")
    print(os.path.join(args.raw_tracts_folder, track + '.fds'))

    for current_mcm in mcm_first_list:
        it = it+1
        # Remove \n at the end of the line
        print(current_mcm)
        # augment tracks of the atlas with MCM patient data
        propsExtractionCommand = [animaTracksMCMPropertiesExtraction, "-i", os.path.join(args.raw_tracts_folder, track + '.fds'),
                              "-m", current_mcm, "-o", os.path.join(tmpFolder, "first_" + track + '_MCM_augmented_onAtlas_' + str(it) + '.fds')]

        call(propsExtractionCommand)

        firstListFile.write(os.path.join(tmpFolder, "first_" + track + '_MCM_augmented_onAtlas_' + str(it) + '.fds') + "\n")

    firstListFile.close()

    secondListFile = open(os.path.join(tmpFolder, "second_listTrack_" + track + ".txt"), "w")
    it=0
    print("Second group tracks extraction")
    for current_mcm in mcm_second_list:
        it = it+1
        # Remove \n at the end of the line
        print(current_mcm)

        # augment tracks of the atlas with MCM patient data
        propsExtractionCommand = [animaTracksMCMPropertiesExtraction, "-i", os.path.join(args.raw_tracts_folder, track + '.fds'),
                              "-m", current_mcm, "-o", os.path.join(tmpFolder, "second_" + track + '_MCM_augmented_onAtlas_' + str(it) + '.fds')]

        call(propsExtractionCommand)

        secondListFile.write(os.path.join(tmpFolder, "second_" + track + '_MCM_augmented_onAtlas_' + str(it) + '.fds') + "\n")

    secondListFile.close()

#    # Compare to controls list of augmented tracts
    print("Perform group comparison")
    groupComparisonCommand = [animaGroupToGroupComparisonOnTracks, "-c", os.path.join(tmpFolder, "first_listTrack_" + track + ".txt"), "-p", os.path.join(tmpFolder, "second_listTrack_" + track + ".txt"), "-o", os.path.join(outputFolder, outputPrefix + '_' + track + '_average_controls.fds'), "-O", os.path.join(outputFolder, outputPrefix + '_' + track + '_average_patients.fds'), "-d", os.path.join(tmpFolder, track + '_diff_controls_patients.fds'), "-t", os.path.join(outputFolder, track + '_student_t_test.fds'), "-P", os.path.join(outputFolder, outputPrefix + '_' + track + '_student_t_test_PV.fds')]
    call(groupComparisonCommand)

    fdrCorrectionCommand = [animaFibersFDRCorrectPValues, "-i", os.path.join(outputFolder, outputPrefix + '_' + track + '_student_t_test_PV.fds'), "-o", os.path.join(outputFolder, outputPrefix + '_' + track + '_student_t_test_PV_FDR_010.fds'), "-q", "0.10"]
    call(fdrCorrectionCommand)

    # Compute final scores CSV
    command = [animaFibersDiseaseScores, "-i", os.path.join(outputFolder, outputPrefix + '_' + track + '_student_t_test_PV_FDR_010.fds'),
               "-o", os.path.join(outputFolder, outputPrefix + '_' + track + '_student_t_test_PV_FDR_010.csv'), "-p", "6"]
    call(command)

    shutil.rmtree(tmpFolder)
