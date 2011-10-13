# To change this template, choose Tools | Templates
# and open the template in the editor.

import pypar

import os.path
import sys

from anuga.utilities.system_tools import get_pathname_from_package
from anuga.geometry.polygon_function import Polygon_function

import anuga
from math import pi, pow, sqrt
import numpy as num
from parallel_inlet_operator import Parallel_Inlet_operator
from parallel_structure_operator import Parallel_Structure_operator
from parallel_boyd_box_operator import Parallel_Boyd_box_operator
from anuga_parallel import distribute, myid, numprocs, finalize
from anuga.geometry.polygon import inside_polygon, is_inside_polygon, line_intersect

import anuga.structures.boyd_box_operator
import anuga.structures.inlet_operator

from anuga.utilities.numerical_tools import ensure_numeric
from anuga_parallel.parallel_shallow_water import Parallel_domain

import math



def Inlet_operator(domain, line, Q, master_proc = 0, procs = range(0,pypar.size()), debug = False):

    if isinstance(domain, Parallel_domain) is False:
        if debug: print "Allocating non parallel inlet operator ....."
        return anuga.structures.inlet_operator.Inlet_operator(domain, line, Q)
    

    myid = pypar.rank()

    alloc, inlet_master_proc, inlet_procs, enquiry_proc = allocate_inlet_procs(domain, line,
                                                                               master_proc = master_proc,
                                                                               procs = procs, debug = debug)



    if alloc:
        if debug and myid == inlet_master_proc:
            print "Parallel Inlet Operator ================="
            print "Line = " + str(line)
            print "Master Processor is P%d" %(inlet_master_proc)
            print "Processors are P%s" %(inlet_procs)
            print "========================================="

        return Parallel_Inlet_operator(domain, line, Q, master_proc = inlet_master_proc, procs = inlet_procs)
    else:
        return None


def Boyd_box_operator(domain,
                       losses,
                       width,
                       height=None,
                       end_points=None,
                       exchange_lines=None,
                       enquiry_points=None,
                       apron=0.1,
                       manning=0.013,
                       enquiry_gap=0.0,
                       use_momentum_jet=True,
                       use_velocity_head=True,
                       description=None,
                       label=None,
                       structure_type='boyd_box',
                       logging=False,
                       verbose=False,
                       master_proc=0,
                       procs=range(0,pypar.size()),
                       debug = False):

    if isinstance(domain, Parallel_domain) is False:
        if debug: print "Allocating non parallel boyd box operator ....."
        return anuga.structures.boyd_box_operator.Boyd_box_operator(domain,
                                                                    losses,
                                                                    width,
                                                                    height,
                                                                    end_points,
                                                                    exchange_lines,
                                                                    enquiry_points,
                                                                    apron,
                                                                    manning,
                                                                    enquiry_gap,
                                                                    use_momentum_jet,
                                                                    use_velocity_head,
                                                                    description,
                                                                    label,
                                                                    structure_type,
                                                                    logging,
                                                                    verbose)

    myid = pypar.rank()

    end_points = ensure_numeric(end_points)
    exchange_lines = ensure_numeric(exchange_lines)
    enquiry_points = ensure_numeric(enquiry_points)

    if height is None:
        height = width

    if apron is None:
        apron = width

    if myid == master_proc:
        if exchange_lines is not None:
            exchange_lines_tmp = exchange_lines
            enquiry_points_tmp = __process_skew_culvert(exchange_lines, end_points, enquiry_points, apron, enquiry_gap)

            for i in procs:
                if i == master_proc: continue
                pypar.send(enquiry_points_tmp, i)

        elif end_points is not None:
            exchange_lines_tmp, enquiry_points_tmp = __process_non_skew_culvert(end_points, width, 
                                                                                enquiry_points, apron, enquiry_gap)
            for i in procs:
                if i == master_proc: continue
                pypar.send(exchange_lines_tmp, i)
                pypar.send(enquiry_points_tmp, i)
        else:
            raise Exception, 'Define either exchange_lines or end_points'
        
    else:
        if exchange_lines is not None:
            exchange_lines_tmp = exchange_lines
            enquiry_points_tmp = pypar.receive(master_proc)
        elif end_points is not None:
            exchange_lines_tmp = pypar.receive(master_proc)
            enquiry_points_tmp = pypar.receive(master_proc)

    line0 = exchange_lines_tmp[0] #self.inlet0_lines[0]
    enquiry_point0 = enquiry_points_tmp[0]

    alloc0, inlet0_master_proc, inlet0_procs, enquiry0_proc = allocate_inlet_procs(domain, line0, enquiry_point =  enquiry_point0,
                                                                                   master_proc = master_proc,
                                                                                   procs = procs, debug = debug)

    line1 = exchange_lines_tmp[1]
    enquiry_point1 = enquiry_points_tmp[1]

    alloc1, inlet1_master_proc, inlet1_procs, enquiry1_proc = allocate_inlet_procs(domain, line1, enquiry_point =  enquiry_point1,
                                                                                   master_proc = master_proc,
                                                                                   procs = procs, debug = debug)

    structure_procs = list(set(inlet0_procs + inlet1_procs))
    inlet_master_proc = [inlet0_master_proc, inlet1_master_proc]
    inlet_procs = [inlet0_procs, inlet1_procs]
    enquiry_proc = [enquiry0_proc, enquiry1_proc]

    if myid == master_proc and debug:
        print "Parallel Boyd Box Operator ============================="
        print "Structure Master Proc is P" + str(inlet0_master_proc)
        print "Structure Procs are P" + str(structure_procs)
        print "Inlet Master Procs are P" + str(inlet_master_proc)
        print "Inlet Procs are P" + str(inlet_procs[0]) + " and " + str(inlet_procs[1])
        print "Inlet Enquiry Procs are P" + str(enquiry_proc)
        print "Enquiry Points are " + str(enquiry_point0) + " and " + str(enquiry_point1)
        print "Inlet Exchange Lines are " + str(line0) + " and " + str(line1)
        print "========================================================"

    if alloc0 or alloc1:
       return Parallel_Boyd_box_operator(domain,
                                         losses,
                                         width,
                                         height,
                                         end_points,
                                         exchange_lines,
                                         enquiry_points,
                                         apron,
                                         manning,
                                         enquiry_gap,
                                         use_momentum_jet,
                                         use_velocity_head,
                                         description,
                                         label,
                                         structure_type,
                                         logging,
                                         verbose,
                                         master_proc = inlet0_master_proc,
                                         procs = structure_procs,
                                         inlet_master_proc = inlet_master_proc,
                                         inlet_procs = inlet_procs,
                                         enquiry_proc = enquiry_proc)
    else:
        return None


def __process_non_skew_culvert(end_points, width, enquiry_points, apron, enquiry_gap):
    # PETE: This can actually be computed by the master
    """Create lines at the end of a culvert inlet and outlet.
    At either end two lines will be created; one for the actual flow to pass through and one a little further away
    for enquiring the total energy at both ends of the culvert and transferring flow.
    """

    culvert_vector = end_points[1] - end_points[0]
    culvert_length = math.sqrt(num.sum(culvert_vector**2))
    assert culvert_length > 0.0, 'The length of culvert is less than 0'

    culvert_vector /= culvert_length

    culvert_normal = num.array([-culvert_vector[1], culvert_vector[0]])  # Normal vector
    w = 0.5*width*culvert_normal # Perpendicular vector of 1/2 width

    exchange_lines = []

    # Build exchange polyline and enquiry point
    if enquiry_points is None:

        gap = (apron + enquiry_gap)*culvert_vector
        enquiry_points = []

        for i in [0, 1]:
            p0 = end_points[i] + w
            p1 = end_points[i] - w
            exchange_lines.append(num.array([p0, p1]))
            ep = end_points[i] + (2*i - 1)*gap #(2*i - 1) determines the sign of the points
            enquiry_points.append(ep)

    else:
        for i in [0, 1]:
            p0 = end_points[i] + w
            p1 = end_points[i] - w
            exchange_lines.append(num.array([p0, p1]))

    return exchange_lines, enquiry_points

def __process_skew_culvert(exchange_lines, end_points, enquiry_points, apron, enquiry_gap):

    """Compute skew culvert.
    If exchange lines are given, the enquiry points are determined. This is for enquiring
    the total energy at both ends of the culvert and transferring flow.
    """

    centre_point0 = 0.5*(exchange_lines[0][0] + exchange_lines[0][1])
    centre_point1 = 0.5*(exchange_lines[1][0] + exchange_lines[1][1])

    if end_points is None:
        culvert_vector = centre_point1 - centre_point0
    else:
        culvert_vector = end_points[1] - end_points[0]

    culvert_length = math.sqrt(num.sum(culvert_vector**2))
    assert culvert_length > 0.0, 'The length of culvert is less than 0'

    if enquiry_points is None:

        culvert_vector /= culvert_length
        gap = (apron + enquiry_gap)*culvert_vector

        enquiry_points = []

        enquiry_points.append(centre_point0 - gap)
        enquiry_points.append(centre_point1 + gap)

    return enquiry_points
        

def allocate_inlet_procs(domain, line, enquiry_point = None, master_proc = 0, procs = range(0, pypar.size()), debug = False):

    myid = pypar.rank()
    vertex_coordinates = domain.get_full_vertex_coordinates(absolute=True)
    size = 0
    has_enq_point = False
    numprocs = pypar.size()

    line_procs = []
    max_size = -1
    line_master_proc = -1
    line_enq_proc = -1

    # Calculate the number of points of the line inside full polygon


    tri_id = line_intersect(vertex_coordinates, line)

    if debug:
        print "P%d has %d triangles on line %s" %(myid, len(tri_id), line)

    size = len(tri_id)

    if enquiry_point is not None:
        try:
            k = domain.get_triangle_containing_point(enquiry_point)

            if domain.tri_full_flag[k] == 1:
                size = size + 1
                has_enq_point = True
                if debug: print "P%d has enq point %s" %(myid, enquiry_point)
            else:
                if debug: print "P%d contains ghost copy of enq point %s" %(myid, enquiry_point)
                has_enq_point = False
        except:
            if debug: print "P%d does not contain enq point %s" %(myid, enquiry_point)
            has_enq_point = False

    if myid == master_proc:
        # Recieve size of overlap from each processor

        # Initialize line_master_proc and inlet_procs
        if size > 0:
            line_procs = [master_proc]
            max_size = size
            line_master_proc = master_proc
            if has_enq_point:
                line_enq_proc = master_proc

        # Recieve size of overlap
        for i in procs:
            if i == master_proc: continue
            x = pypar.receive(i)
            y = pypar.receive(i)

            if x > 0:
                line_procs.append(i)
                # Choose line_master_proc as the one with the most overlap
                if x > max_size:
                    max_size = x
                    line_master_proc = i

                if y is True:
                    assert line_enq_proc == -1, "Enquiry point correspond to more than one proc"
                    line_enq_proc = i

        assert len(line_procs) > 0, "Line does not intersect any domain"
        assert line_master_proc >= 0, "No master processor assigned"
        if enquiry_point is not None: assert line_enq_proc >= 0, "No enquiry point processor assigned"

        # Send line_master_proc and line_procs to all processors in line_procs
        for i in procs:
            if i != master_proc:
                pypar.send(line_master_proc, i)
                pypar.send(line_procs, i)
                pypar.send(line_enq_proc, i)

    else:
        pypar.send(size, master_proc)
        pypar.send(has_enq_point, master_proc)

        line_master_proc = pypar.receive(master_proc)
        line_procs = pypar.receive(master_proc)
        line_enq_proc = pypar.receive(master_proc)
        if has_enq_point: assert line_enq_proc == myid, "Enquiry found in proc, but not declared globally"

    if size > 0:
        return True, line_master_proc, line_procs, line_enq_proc
    else:
        return False, line_master_proc, line_procs, line_enq_proc


__author__="pete"
__date__ ="$06/09/2011 1:17:57 PM$"

if __name__ == "__main__":
    print "Hello World"