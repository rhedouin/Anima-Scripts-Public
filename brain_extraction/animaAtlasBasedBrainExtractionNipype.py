#!/usr/bin/python
# Warning: works only on unix-like systems, not windows where "python scriptName.py..." has to be run

import sys

if sys.version_info[0] > 2:
    import configparser as ConfParser
else:
    import ConfigParser as ConfParser

import glob
import os
import shutil
from subprocess import call, Popen

from nipype.interfaces.io import DataSink
from nipype import Node, Workflow
import animaAtlasBasedBrainExtractionWorkflow as wf_creator


configFilePath = os.path.expanduser("~") + "/.anima/config.txt"
if not os.path.exists(configFilePath):
    print('Please create a configuration file for Anima python scripts. Refer to the README')
    quit()

configParser = ConfParser.RawConfigParser()
configParser.read(configFilePath)

animaDir = configParser.get("anima-scripts", 'anima')
animaExtraDataDir = configParser.get("anima-scripts", 'extra-data-root')
anima_env = os.environ.copy()
anima_env["PATH"] += os.pathsep + animaDir

if len(sys.argv) < 2:
    print('Computes the brain mask of images given in input by registering a known atlas on it. Their output is prefix_brainMask.nrrd and prefix_masked.nrrd.')
    quit()

atlasImage = os.path.join(animaExtraDataDir, "icc_atlas/Reference_T1.nrrd")
iccImage = os.path.join(animaExtraDataDir, "icc_atlas/BrainMask.nrrd")

for brainImage in sys.argv[1:]:
    print("Brain masking image: " + brainImage)

    # Get floating image prefix
    brainImagePrefix = os.path.splitext(os.path.basename(brainImage))[0]
    brainImageDir = os.path.dirname(brainImage)
    if os.path.splitext(brainImage)[1] == '.gz':
        brainImagePrefix = os.path.splitext(brainImagePrefix)[0]

    wf = wf_creator.create_atlas_based_brain_extraction_workflow(name='anima_brain_extraction_' + brainImagePrefix)
    wf.base_dir = brainImageDir

    wf.inputs.input_node.input_file = brainImage
    wf.inputs.input_node.atlas_img_file = atlasImage
    wf.inputs.input_node.atlas_icc_file = iccImage
    wf.inputs.input_node.out_mask_file = brainImagePrefix + "_brainMask.nrrd"
    wf.inputs.input_node.out_masked_file = brainImagePrefix + "_masked.nrrd"

    datasink = Node(DataSink(), name='datasink')
    datasink.inputs.base_directory = brainImageDir

    wf.connect([
        (wf.get_node('output_node'), datasink, [('brain_mask', '@brain_mask')]),
        (wf.get_node('output_node'), datasink, [('masked_image', '@masked_image')])
    ])

    wf.run()

    shutil.rmtree(os.path.join(brainImageDir,'anima_brain_extraction_' + brainImagePrefix))
