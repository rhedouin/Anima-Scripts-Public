#!/usr/bin/python3


# Registration T1 subject -> atlas
# Ici je recalle la T1 (deja masqué) d'un sujet vers un atlas donc tu as besoin des deux images suivantes

# sujet = Actidep_patients_Tours_T13D_1_masked.nii.gz
# atlas = MIITRA_t1_masked_B0_resolution.nii.gz

# D'abord un recallage rigid entre le sujet et l'atlas en utilisant anima
print("BM")
animaPyramidalBMRegistration -r   MIITRA_t1_masked_B0_resolution.nii.gz  -m  Actidep_patients_Tours_T13D_1_masked.nii.gz  -o Actidep_patients_Tours_T13D_1_masked_rigid2atlas.nii.gz -O Actidep_patients_Tours_T13D_1_masked_rigid2atlas.txt -p 3 -l 0 --sp 2 --ot 2

# Puis un recallage non lineaire sur l'atlas
print("ANTS")
/home/rhedouin/Software/ants/bin/ANTS-build/Examples/ANTS 3 -m CC[ MIITRA_t1_masked_B0_resolution.nii.gz, Actidep_patients_Tours_T13D_1_masked_rigid2atlas.nii.gz, 1.5,4]  -o transfRigid2Atlas -i 75x75x10 -r Gauss[3,0] -t SyN[0.25] --number-of-affine-iterations 0

# Enfin je combine les 2 transformations (c'est mieux de les combiner pour les appliquer en meme temps, si on applique trop de  transformations successivement on obtient une image flou á cause de l'interpolation)
animaTransformSerieXmlGenerator -i Actidep_patients_Tours_T13D_1_masked_rigid2atlas.txt -i transfRigid2AtlasWarp.nii.gz -D -o transfFinalAtlas.xml

# Et j'applique le tout à l'image original
animaApplyTransformSerie -i Actidep_patients_Tours_T13D_1_masked.nii.gz -t transfFinalAtlas.xml -g MIITRA_t1_masked_B0_resolution.nii.gz -o Actidep_patients_Tours_T13D_1_masked_2atlas.nii.gz

# Petite précision, si tu veux appliquer ca à du fMRI (ou à tout autre chose que la T1), ca suppose qu'il n'y a pas eu de mouvement entre les acquisitions (ce qui est une supposition résonnable). Moi au cas où je vais des étapes supplémentaires pour recaler la diffusion sur la T1.












