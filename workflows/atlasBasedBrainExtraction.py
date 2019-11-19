from nipype import Node, Workflow, MapNode
from nipype.interfaces import anima
import nipype.interfaces.utility as niu
from . import anatomicalNonLinearRegistration as wf_creator


def create_atlas_based_brain_extraction_workflow(name='anima_brain_extraction'):
    wf = Workflow(name=name)
    wf.base_output_dir = name

    input_node = Node(niu.IdentityInterface(fields=['input_file', 'atlas_img_file', 'atlas_icc_file']),
                      name='input_node')

    output_node = Node(niu.IdentityInterface(fields=['brain_mask', 'masked_image']), name='output_node')

    # Atlas registration process
    anat_reg = wf_creator.create_anatomical_non_linear_registration_workflow(name='anat_reg', linear_block_spacing=3,
                                                                             linear_pyramid_levels=4,
                                                                             linear_last_pyramid_level=1,
                                                                             dense_search_radius=1,
                                                                             dense_pyramid_levels=4,
                                                                             dense_last_pyramid_level=1)

    # Apply transform process
    trsf_applyer = Node(interface=anima.ApplyTransformSerie(interpolation_mode='nearest'), name='trsf_applyer')

    # Mask process
    img_masker = Node(interface=anima.MaskImage(), name='img_masker')

    wf.connect(input_node, 'input_file', anat_reg, 'input_node.reference_file')
    wf.connect(input_node, 'atlas_img_file', anat_reg, 'input_node.moving_file')

    wf.connect(input_node, 'atlas_icc_file', trsf_applyer, 'input_file')
    wf.connect(anat_reg, 'output_node.out_trsf_xml', trsf_applyer, 'transform_file')
    wf.connect(input_node, 'input_file', trsf_applyer, 'geometry_file')

    wf.connect(input_node, 'input_file', img_masker, 'input_file')
    wf.connect(trsf_applyer, 'out_file', img_masker, 'mask_file')

    wf.connect(trsf_applyer, 'out_file', output_node, 'brain_mask')
    wf.connect(img_masker, 'out_file', output_node, 'masked_image')

    return wf
