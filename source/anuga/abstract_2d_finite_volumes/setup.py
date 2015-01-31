from __future__ import division, print_function

import os
import sys

from os.path import join

def local_fun():
    pass


def configuration(parent_package='',top_path=None):
    
    from numpy.distutils.misc_util import Configuration
    from numpy.distutils.system_info import get_info
    
    config = Configuration('abstract_2d_finite_volumes', parent_package, top_path)

    config.add_data_dir('tests')

    util_dir = os.path.abspath(join(os.path.dirname(__file__),'..','utilities'))    
    
    config.add_extension('neighbour_mesh_ext',
                         sources=['neighbour_mesh_ext.c'],
                         include_dirs=[util_dir])
    
    config.add_extension('mesh_factory_ext',
                         sources=['mesh_factory_ext.c'],
                         include_dirs=[util_dir])

    config.add_extension('neighbour_table_ext',
                         sources=['neighbour_table_ext.c'],
                         include_dirs=[util_dir])

    config.add_extension('pmesh2domain_ext',
                         sources=['pmesh2domain_ext.c'],
                         include_dirs=[util_dir])

    config.add_extension('quantity_ext',
                         sources=['quantity_ext.c'],
                         include_dirs=[util_dir])        
    

    return config
    
if __name__ == '__main__':
    from numpy.distutils.core import setup
    setup(configuration=configuration)
