"""
Rate operators (such as rain)

Constraints: See GPL license in the user guide
Version: 1.0 ($Revision: 7731 $)
"""

__author__="steve"
__date__ ="$09/03/2012 4:46:39 PM$"


from anuga import Domain
from anuga import Quantity
from anuga import indent
import numpy as num
import anuga.utilities.log as log

from anuga.geometry.polygon import inside_polygon

from anuga.operators.base_operator import Operator
from anuga.fit_interpolate.interpolate import Modeltime_too_early, \
                                              Modeltime_too_late


class Rate_operator(Operator):
    """
    Add water at certain rate (ms^{-1} = vol/Area/sec) over a
    triangles specified by

    indices: None == all triangles, Empty list [] no triangles

    rate can be a function of time.

    """

    def __init__(self,
                 domain,
                 rate=0.0,
                 factor=1.0,
                 indices=None,
                 default_rate=None,
                 description = None,
                 label = None,
                 logging = False,
                 verbose = False):


        Operator.__init__(self, domain, description, label, logging, verbose)

        #------------------------------------------
        # Local variables
        #------------------------------------------
        self.rate = rate
        self.indices = indices
        self.factor = factor

        #------------------------------------------
        # Check and store default_rate
        #------------------------------------------
        msg = ('Keyword argument default_rate must be either None '
               'or a function of time.\nI got %s.' % str(default_rate))
        assert (default_rate is None or
                isinstance(default_rate, (int, float)) or
                callable(default_rate)), msg


        #------------------------------------------
        # Allow application longer than data
        #------------------------------------------
        if default_rate is not None:
            # If it is a constant, make it a function
            if not callable(default_rate):
                tmp = default_rate
                default_rate = lambda t: tmp

            # Check that default_rate is a function of one argument
            try:
                default_rate(0.0)
            except:
                raise Exception(msg)

        self.default_rate = default_rate
        self.default_rate_invoked = False    # Flag




    def __call__(self):
        """
        Apply rate to those triangles defined in indices

        indices == [], then don't apply anywhere
        indices == None, then apply everywhere
        otherwise apply for the specific indices
        """

        if self.indices is []:
            return

        t = self.domain.get_time()
        timestep = self.domain.get_timestep()
        factor = self.factor
        indices = self.indices

        rate = self.get_rate(t)

        if self.verbose is True:
            log.critical('Rate of %s at time = %.2f = %f'
                         % (self.quantity_name, domain.get_time(), rate))

        if self.indices is None:
            self.stage_c[:] = self.stage_c[:]  \
                   + factor*rate*timestep
        else:
            self.stage_c[indices] = self.stage_c[indices] \
                   + factor*rate*timestep


    def get_rate(self, t=None):
        """Provide a rate to calculate added volume
        """

        if t is None:
            t = self.get_time()

            
        if callable(self.rate):
            try:
                rate = self.rate(t)
            except Modeltime_too_early, e:
                raise Modeltime_too_early(e)
            except Modeltime_too_late, e:
                if self.default_rate is None:
                    msg = '%s: ANUGA is trying to run longer than specified data.\n' %str(e)
                    msg += 'You can specify keyword argument default_rate in the '
                    msg += 'rate operator to tell it what to do in the absence of time data.'
                    raise Modeltime_too_late(msg)
                else:
                    # Pass control to default rate function
                    rate = self.default_rate(t)

                    if self.default_rate_invoked is False:
                        # Issue warning the first time
                        msg = ('%s\n'
                           'Instead I will use the default rate: %s\n'
                           'Note: Further warnings will be supressed'
                           % (str(e), str(self.default_rate)))
                        warn(msg)

                        # FIXME (Ole): Replace this crude flag with
                        # Python's ability to print warnings only once.
                        # See http://docs.python.org/lib/warning-filter.html
                        self.default_rate_invoked = True
        else:
            rate = self.rate


        if rate is None:
            msg = ('Attribute rate must be specified in '+self.__name__+
                   ' before attempting to call it')
            raise Exception(msg)

        return rate

    def parallel_safe(self):
        """Operator is applied independently on each cell and
        so is parallel safe.
        """
        return True

    def statistics(self):

        message = 'You need to implement operator statistics for your operator'
        return message


    def timestepping_statistics(self):

        message  = indent + self.label + ': Rate = ' + str(self.get_rate())
        return message






#===============================================================================
# Specific Rate Operators for circular region.
#===============================================================================
class Circular_rate_operator(Rate_operator):
    """
    Add water at certain rate (ms^{-1} = vol/Area/sec) over a
    circular region

    rate can be a function of time.

    """

    def __init__(self, domain,
                 rate=0.0,
                 factor=1.0,
                 center=None,
                 radius=None,
                 default_rate=None,
                 verbose=False):

        assert center is not None
        assert radius is not None


        # Determine indices in update region
        N = domain.get_number_of_triangles()
        points = domain.get_centroid_coordinates(absolute=True)


        indices = []

        c = center
        r = radius

        for k in range(N):
            x, y = points[k,:]    # Centroid

            if ((x-c[0])**2+(y-c[1])**2) < r**2:
                indices.append(k)


        # It is possible that circle doesn't intersect with mesh (as can happen
        # for parallel runs


        Rate_operator.__init__(self,
                               domain,
                               rate=rate,
                               factor=factor,
                               indices=indices,
                               default_rate=default_rate,
                               verbose=verbose)


        self.center = center
        self.radius = radius


#===============================================================================
# Specific Rate Operators for polygonal region.
#===============================================================================
class Polygonal_rate_operator(Rate_operator):
    """
    Add water at certain rate (ms^{-1} = vol/Area/sec) over a
    polygonal region

    rate can be a function of time.

    """

    def __init__(self, domain,
                 rate=0.0,
                 factor=1.0,
                 polygon=None,
                 default_rate=None,
                 verbose=False):

        assert polygon is not None


        # Determine indices in update region
        N = domain.get_number_of_triangles()
        points = domain.get_centroid_coordinates(absolute=True)


        indices = inside_polygon(points, polygon)
        self.polygon = polygon


        # It is possible that circle doesn't intersect with mesh (as can happen
        # for parallel runs


        Rate_operator.__init__(self,
                               domain,
                               rate=rate,
                               factor=factor,
                               indices=indices,
                               default_rate=default_rate,
                               verbose=verbose)


                



