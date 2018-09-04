# Anima-Scripts-Public
Open source scripts for medical image processing from the VISAGES team

This repository includes python and Unix shell scripts (for execution on an [OAR](https://oar.imag.fr) cluster). Their goal is to combine several tools from [Anima public](https://github.com/Inria-Visages/Anima-Public/) to accomplish more complex tasks (atlasing, image stitching, full lesion segmentation pipeline,...).

## Installation

Anima-Scripts-Public only requires two packages:
- [Python](https://www.python.org)
- [Anima public](https://github.com/Inria-Visages/Anima-Public/)
- [Anima scripts data](https://team.inria.fr/visages/files/2018/09/Anima_Data.zip): data required for some scripts to work (brain extraction and diffusion scripts)

Installation requires only a few steps:
- Clone the Anima-Scripts-Public repository from Github
- Copy / paste the `example-config.txt` file in .anima/config.txt in your home folder
- Copy / paste the `configParser.sh` file inside the .anima folder in your home folder
- Update the paths in your config file to match where Anima public binaries are and where the data folder are (use full paths, no tilde)
