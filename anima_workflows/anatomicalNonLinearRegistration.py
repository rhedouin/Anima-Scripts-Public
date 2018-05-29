from nipype import Node, Workflow, MapNode
from nipype.interfaces import anima
import nipype.interfaces.utility as niu


def create_anatomical_non_linear_registration_workflow(name='anima_non_linear_registration',
                                                       linear_block_spacing=3,
                                                       linear_pyramid_levels=4,
                                                       linear_last_pyramid_level=1,
                                                       dense_search_radius=1,
                                                       dense_pyramid_levels=3,
                                                       dense_last_pyramid_level=0,
                                                       temp_rigid_img_file='rigid_data.nrrd',
                                                       temp_rigid_trsf='rigid_data_tr.txt',
                                                       temp_affine_img_file='affine_data.nrrd',
                                                       temp_affine_trsf='affine_data_tr.txt',
                                                       temp_dense_img_file='dense_data.nrrd',
                                                       temp_dense_trsf='dense_data_tr.nrrd',
                                                       temp_trsf_xml='dense_tr_series.xml'):
    wf = Workflow(name=name)
    wf.base_output_dir = name

    input_node = Node(niu.IdentityInterface(fields=['reference_file', 'moving_file', 'out_rigid_img_file',
                                                    'out_rigid_trsf', 'out_affine_img_file', 'out_affine_trsf',
                                                    'out_dense_img_file', 'out_dense_trsf', 'out_trsf_xml',
                                                    'out_file', 'out_mask_file']),
                      name='input_node')

    input_node.inputs.out_rigid_img_file = temp_rigid_img_file
    input_node.inputs.out_rigid_trsf = temp_rigid_trsf

    input_node.inputs.out_affine_img_file = temp_affine_img_file
    input_node.inputs.out_affine_trsf = temp_affine_trsf

    input_node.inputs.out_dense_img_file = temp_dense_img_file
    input_node.inputs.out_dense_trsf = temp_dense_trsf

    input_node.inputs.out_trsf_xml = temp_trsf_xml

    output_node = Node(niu.IdentityInterface(fields=['out_file', 'out_trsf_xml', 'out_affine_trsf', 'out_dense_trsf']),
                       name='output_node')

    # Rigid registration process
    rigid_reg = Node(interface=anima.PyramidalBMRegistration(block_spacing=linear_block_spacing,
                                                             pyramid_levels=linear_pyramid_levels,
                                                             last_pyramid_level=linear_last_pyramid_level),
                     name='rigid_reg')

    # Affine registration process
    affine_reg = Node(interface=anima.PyramidalBMRegistration(block_spacing=linear_block_spacing,
                                                              pyramid_levels=linear_pyramid_levels,
                                                              last_pyramid_level=linear_last_pyramid_level,
                                                              out_transform_type=2), name='affine_reg')

    # Dense registration process
    dense_reg = Node(interface=anima.DenseSVFBMRegistration(block_search_radius=dense_search_radius,
                                                            pyramid_levels=dense_pyramid_levels,
                                                            last_pyramid_level=dense_last_pyramid_level),
                     name='dense_reg')

    # Transforms XML generator
    xml_generator = Node(interface=anima.TransformSerieXmlGenerator(), name='xml_generator')

    # Apply transform process
    trsf_applyer = Node(interface=anima.ApplyTransformSerie(interpolation_mode='linear'), name='trsf_applyer')

    wf.connect(input_node, 'reference_file', rigid_reg, 'reference_file')
    wf.connect(input_node, 'moving_file', rigid_reg, 'moving_file')
    wf.connect(input_node, 'out_rigid_img_file', rigid_reg, 'out_file')
    wf.connect(input_node, 'out_rigid_trsf', rigid_reg, 'out_transform_file')

    wf.connect(input_node, 'reference_file', affine_reg, 'reference_file')
    wf.connect(input_node, 'moving_file', affine_reg, 'moving_file')
    wf.connect(input_node, 'out_affine_img_file', affine_reg, 'out_file')
    wf.connect(input_node, 'out_affine_trsf', affine_reg, 'out_transform_file')
    wf.connect(rigid_reg, 'out_transform_file', affine_reg, 'input_transform_file')

    wf.connect(input_node, 'reference_file', dense_reg, 'reference_file')
    wf.connect(affine_reg, 'out_file', dense_reg, 'moving_file')
    wf.connect(input_node, 'out_dense_img_file', dense_reg, 'out_file')
    wf.connect(input_node, 'out_dense_trsf', dense_reg, 'out_transform_file')
    wf.connect(affine_reg, 'out_transform_series', dense_reg, 'input_transform_series')

    wf.connect(dense_reg, 'out_transform_series', xml_generator, 'input_files')
    wf.connect(input_node, 'out_trsf_xml', xml_generator, 'out_file')

    wf.connect(input_node, 'moving_file', trsf_applyer, 'input_file')
    wf.connect(xml_generator, 'out_file', trsf_applyer, 'transform_file')
    wf.connect(input_node, 'reference_file', trsf_applyer, 'geometry_file')
    wf.connect(input_node, 'out_file', trsf_applyer, 'out_file')

    wf.connect(trsf_applyer, 'out_file', output_node, 'out_file')
    wf.connect(xml_generator, 'out_file', output_node, 'out_trsf_xml')
    wf.connect(affine_reg, 'out_transform_file', output_node, 'out_affine_trsf')
    wf.connect(dense_reg, 'out_transform_file', output_node, 'out_dense_trsf')

    return wf
