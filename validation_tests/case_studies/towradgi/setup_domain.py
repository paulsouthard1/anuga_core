""" 
Towradgi Creek 17 August 1998 Storm Event Calibration
By Petar Milevski, some revisions by Gareth Davies
Changed into first partition in sequential mode. Use 
argumet np to specify the distribution

Then use run_parallel_evolve in parallel to do the evolution
"""

#------------------------------------------------------------------------------
# IMPORT NECESSARY MODULES
#------------------------------------------------------------------------------


import anuga
import time
import numpy
import os
import zipfile


from anuga import Polygon_function
from anuga import create_mesh_from_regions
from anuga import Domain


from anuga import sequential_distribute_dump
from anuga_parallel.sequential_distribute import sequential_distribute_load_pickle_file


from project import *



def read_polygon_list(poly_list):
    # Alternative to read_polygon_dir -- allows us to control order of polygons
    from anuga import read_polygon
    
    result = []
    for i in range(len(poly_list)):
        result.append((read_polygon(poly_list[i][0]) , poly_list[i][1]))
    return result



#--------------------------------------------------------------------------
# Setup Domain
#--------------------------------------------------------------------------
def setup_domain(verbose=False):
    
    
    from catchment_info import CatchmentList
    from catchment_info import ManningList
    
    #------------------------------------------------------------------------------
    # CREATING MESH
    #------------------------------------------------------------------------------
    
    bounding_polygon = [[W, S], [E, S], [E, N], [W, N]]
    #interior_regions = read_polygon_dir(CatchmentDictionary, join('Model', 'Bdy'))
    interior_regions = read_polygon_list(CatchmentList)

    # FIXME: Have these in a shapefile / other file and read them in    
    breaklines=[[[306612.336559443,6193708.75358065],
                 [306604.441364239,6193693.17994946]],
                [[306977.886673843,6193753.44134088],
                 [306978.027867398,6193710.94208076]],
                [[306956.001672788,6193750.89985688],
                 [306956.707640564,6193706.14149989]],
                [[306627.303076293,6193697.45809624],
                 [306620.525785644,6193683.62112783]],
                [[307236.83565407,6193741.01630802],
                 [307231.682089306,6193721.03741996]],
                [[307224.975395434,6193742.71063068],
                 [307220.880782334,6193723.36711362]],
                [[307624.764946969,6193615.98941489],
                 [307617.98765632,6193601.44647871]],
                [[307613.328268998,6193623.19028621],
                 [307607.751123568,6193610.97704368]]]

    # Make the mesh
    create_mesh_from_regions(bounding_polygon, 
        boundary_tags={'south': [0], 'east': [1], 'north': [2], 'west': [3]},
        maximum_triangle_area=maximum_triangle_area,
        interior_regions=interior_regions,
        filename=meshname,
        breaklines=breaklines,
        use_cache=False,
        verbose=True)
    
    #------------------------------------------------------------------------------
    # SETUP COMPUTATIONAL DOMAIN
    #------------------------------------------------------------------------------
    
    domain = Domain(meshname, use_cache=False, verbose=True)

    domain.set_flow_algorithm(alg)

    if(not domain.get_using_discontinuous_elevation()):
        raise Exception, 'This model run relies on a discontinuous elevation solver (because of how topography is set up)'

    domain.set_datadir(model_output_dir)
    domain.set_name(outname)
        
    print domain.statistics()
    
    #------------------------------------------------------------------------------
    # APPLY MANNING'S ROUGHNESSES
    #------------------------------------------------------------------------------
    
    if verbose: print 'Calculating complicated polygon friction function'
    friction_list = read_polygon_list(ManningList)
    domain.set_quantity('friction', Polygon_function(friction_list, default=base_friction, geo_reference=domain.geo_reference))
    
    # Set a Initial Water Level over the Domain
    domain.set_quantity('stage', 0)
   
    # Decompress the zip file to make a csv for reading 
    zipfile.ZipFile('DEM_bridges/towradgi_cleaner.zip').extract('towradgi.csv',path='DEM_bridges/')

    if verbose: print 'Setting up elevation interpolation function'
    from anuga.utilities.quantity_setting_functions import make_nearestNeighbour_quantity_function
    elev_xyz=numpy.genfromtxt(fname=basename+'.csv',delimiter=',')

    # Use nearest-neighbour interpolation of elevation 
    elev_fun_wrapper=make_nearestNeighbour_quantity_function(elev_xyz,domain)
    if verbose: print 'Applying elevation interpolation function'    
    domain.set_quantity('elevation', elev_fun_wrapper, location='centroids')

    os.remove('DEM_bridges/towradgi.csv') # Clean up csv file
    
    return domain

