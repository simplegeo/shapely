"""
Multiple points.
"""

from ctypes import byref, c_double, c_int, c_void_p, cast, POINTER, pointer

from shapely.geos import lgeos
from shapely.geometry.base import BaseGeometry, GeometrySequence, exceptNull
from shapely.geometry.point import Point, geos_point_from_py
from shapely.geometry.proxy import CachingGeometryProxy


def geos_multipoint_from_py(ob):
    try:
        # From array protocol
        array = ob.__array_interface__
        assert len(array['shape']) == 2
        m = array['shape'][0]
        n = array['shape'][1]
        assert m >= 1
        assert n == 2 or n == 3

        # Make pointer to the coordinate array
        cp = cast(array['data'][0], POINTER(c_double))

        # Array of pointers to sub-geometries
        subs = (c_void_p * m)()

        for i in xrange(m):
            geom, ndims = geos_point_from_py(cp[n*i:n*i+2])
            subs[i] = cast(geom, c_void_p)

    except AttributeError:
        # Fall back on list
        m = len(ob)
        n = len(ob[0])
        assert n == 2 or n == 3

        # Array of pointers to point geometries
        subs = (c_void_p * m)()
        
        # add to coordinate sequence
        for i in xrange(m):
            coords = ob[i]
            geom, ndims = geos_point_from_py(coords)
            subs[i] = cast(geom, c_void_p)
            
    return lgeos.GEOSGeom_createCollection(4, subs, m), n


class MultiPoint(BaseGeometry):

    """A multiple point geometry.
    """

    def __init__(self, coordinates=None):
        """Initialize.

        Parameters
        ----------
        
        coordinates : sequence or array
            This may be an object that satisfies the numpy array protocol,
            providing an M x 2 or M x 3 (with z) array, or it may be a sequence
            of x, y (,z) coordinate sequences.

        Example
        -------

        >>> geom = MultiPoint([[0.0, 0.0], [1.0, 2.0]])
        >>> geom = MultiPoint(array([[0.0, 0.0], [1.0, 2.0]]))
        
        Each result in a line string from (0.0, 0.0) to (1.0, 2.0).
        """
        BaseGeometry.__init__(self)

        if coordinates is None:
            # allow creation of null lines, to support unpickling
            pass
        else:
            self._geom, self._ndim = geos_multipoint_from_py(coordinates)


    @property
    @exceptNull
    def __geo_interface__(self):
        return {
            'type': 'MultiPoint',
            'coordinates': tuple([g.coords[0] for g in self.geoms])
            }

    @property
    @exceptNull
    def ctypes(self):
        if not self._ctypes_data:
            temp = c_double()
            n = self._ndim
            m = len(self.geoms)
            array_type = c_double * (m * n)
            data = array_type()
            for i in xrange(m):
                g = self.geoms[i]._geom    
                cs = lgeos.GEOSGeom_getCoordSeq(g)
                lgeos.GEOSCoordSeq_getX(cs, 0, byref(temp))
                data[n*i] = temp.value
                lgeos.GEOSCoordSeq_getY(cs, 0, byref(temp))
                data[n*i+1] = temp.value
                if n == 3: # TODO: use hasz
                    lgeos.GEOSCoordSeq_getZ(cs, 0, byref(temp))
                    data[n*i+2] = temp.value
            self._ctypes_data = data
        return self._ctypes_data

    @exceptNull
    def array_interface(self):
        """Provide the Numpy array protocol."""
        ai = self.array_interface_base
        ai.update({'shape': (len(self.geoms), self._ndim)})
        return ai
    __array_interface__ = property(array_interface)

    def _get_coords(self):
        raise NotImplementedError, \
        "Component rings have coordinate sequences, but the polygon does not"

    def _set_coords(self, ob):
        raise NotImplementedError, \
        "Component rings have coordinate sequences, but the polygon does not"

    @property
    def coords(self):
        raise NotImplementedError, \
        "Multipart geometries do not themselves provide coordinate sequences"

    @property
    @exceptNull
    def geoms(self):
        return GeometrySequence(self, Point)
        

class MultiPointAdapter(CachingGeometryProxy, MultiPoint):

    """Adapts a Python coordinate pair or a numpy array to the multipoint
    interface.
    """
    
    context = None
    _owned = False

    def __init__(self, context):
        self.context = context
        self.factory = geos_multipoint_from_py

    @property
    def _ndim(self):
        try:
            # From array protocol
            array = self.context.__array_interface__
            n = array['shape'][1]
            assert n == 2 or n == 3
            return n
        except AttributeError:
            # Fall back on list
            return len(self.context[0])

    @property
    def __array_interface__(self):
        """Provide the Numpy array protocol."""
        try:
            return self.context.__array_interface__
        except AttributeError:
            return self.array_interface()


def asMultiPoint(context):
    """Factory for MultiPointAdapter instances."""
    return MultiPointAdapter(context)


# Test runner
def _test():
    import doctest
    doctest.testmod()


if __name__ == "__main__":
    _test()
