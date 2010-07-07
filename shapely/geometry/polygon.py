"""
Polygons and their linear ring components.
"""

from ctypes import byref, c_double, c_int, c_void_p, cast, POINTER, pointer
import weakref
from shapely.geos import lgeos
from shapely.geometry.base import BaseGeometry, exceptNull
from shapely.geometry.linestring import LineString, LineStringAdapter
from shapely.geometry.proxy import PolygonProxy


def geos_linearring_from_py(ob, update_geom=None, update_ndim=0):
    try:
        # From array protocol
        array = ob.__array_interface__
        assert len(array['shape']) == 2
        m = array['shape'][0]
        n = array['shape'][1]
        if m < 3:
            raise ValueError, "A LinearRing must have at least 3 coordinate tuples"
        assert n == 2 or n == 3

        # Make pointer to the coordinate array
        try:
            cp = cast(array['data'][0], POINTER(c_double))
        except ArgumentError:
            cp = array['data']

        # Add closing coordinates to sequence?
        if cp[0] != cp[m*n-n] or cp[1] != cp[m*n-n+1]:
            M = m + 1
        else:
            M = m

        # Create a coordinate sequence
        if update_geom is not None:
            cs = lgeos.GEOSGeom_getCoordSeq(update_geom)
            if n != update_ndim:
                raise ValueError, \
                "Wrong coordinate dimensions; this geometry has dimensions: %d" \
                % update_ndim
        else:
            cs = lgeos.GEOSCoordSeq_create(M, n)

        # add to coordinate sequence
        for i in xrange(m):
            dx = c_double(cp[n*i])
            dy = c_double(cp[n*i+1])
            dz = None
            if n == 3:
                dz = c_double(cp[n*i+2])
        
            # Because of a bug in the GEOS C API, 
            # always set X before Y
            lgeos.GEOSCoordSeq_setX(cs, i, dx)
            lgeos.GEOSCoordSeq_setY(cs, i, dy)
            if n == 3:
                lgeos.GEOSCoordSeq_setZ(cs, i, dz)

        # Add closing coordinates to sequence?
        if M > m:
            dx = c_double(cp[0])
            dy = c_double(cp[1])
            dz = None
            if n == 3:
                dz = c_double(cp[2])
        
            # Because of a bug in the GEOS C API, 
            # always set X before Y
            lgeos.GEOSCoordSeq_setX(cs, M-1, dx)
            lgeos.GEOSCoordSeq_setY(cs, M-1, dy)
            if n == 3:
                lgeos.GEOSCoordSeq_setZ(cs, M-1, dz)
            
    except AttributeError:
        # Fall back on list
        m = len(ob)
        n = len(ob[0])
        if m < 3:
            raise ValueError, "A LinearRing must have at least 3 coordinate tuples"
        assert (n == 2 or n == 3)

        # Add closing coordinates if not provided
        if ob[0][0] != ob[-1][0] or ob[0][1] != ob[-1][1]:
            M = m + 1
        else:
            M = m

        # Create a coordinate sequence
        if update_geom is not None:
            cs = lgeos.GEOSGeom_getCoordSeq(update_geom)
            if n != update_ndim:
                raise ValueError, \
                "Wrong coordinate dimensions; this geometry has dimensions: %d" \
                % update_ndim
        else:
            cs = lgeos.GEOSCoordSeq_create(M, n)
        
        # add to coordinate sequence
        for i in xrange(m):
            coords = ob[i]
            dx = c_double(coords[0])
            dy = c_double(coords[1])
            dz = None
            if n == 3:
                dz = c_double(coords[2])
        
            # Because of a bug in the GEOS C API, 
            # always set X before Y
            lgeos.GEOSCoordSeq_setX(cs, i, dx)
            lgeos.GEOSCoordSeq_setY(cs, i, dy)
            if n == 3:
                lgeos.GEOSCoordSeq_setZ(cs, i, dz)

        # Add closing coordinates to sequence?
        if M > m:
            coords = ob[0]
            dx = c_double(coords[0])
            dy = c_double(coords[1])
            dz = None
            if n == 3:
                dz = c_double(coords[2])
        
            # Because of a bug in the GEOS C API, 
            # always set X before Y
            lgeos.GEOSCoordSeq_setX(cs, M-1, dx)
            lgeos.GEOSCoordSeq_setY(cs, M-1, dy)
            if n == 3:
                lgeos.GEOSCoordSeq_setZ(cs, M-1, dz)

    if update_geom is not None:
        return None
    else:
        return lgeos.GEOSGeom_createLinearRing(cs), n

def update_linearring_from_py(geom, ob):
    geos_linearring_from_py(ob, geom._geom, geom._ndim)


class LinearRing(LineString):

    """A linear ring.
    """

    _ndim = None
    __geom__ = None
    __p__ = None
    _owned = False

    def __init__(self, coordinates=None):
        """Initialize.

        Parameters
        ----------
        coordinates : sequence or array
            This may be an object that satisfies the numpy array protocol,
            providing an M x 2 or M x 3 (with z) array, or it may be a sequence
            of x, y (,z) coordinate sequences.

        Rings are implicitly closed. There is no need to specific a final
        coordinate pair identical to the first.

        Example
        -------
        >>> ring = LinearRing( ((0.,0.), (0.,1.), (1.,1.), (1.,0.)) )

        Produces a 1x1 square.
        """
        BaseGeometry.__init__(self)
        self._init_geom(coordinates)

    def _init_geom(self, coordinates):
        if coordinates is None:
            # allow creation of null lines, to support unpickling
            pass
        else:
            self._geom, self._ndim = geos_linearring_from_py(coordinates)

    @property
    def __geo_interface__(self):
        return {
            'type': 'LinearRing',
            'coordinates': tuple(self.coords)
            }

    # Coordinate access

    _get_coords = BaseGeometry._get_coords

    def _set_coords(self, coordinates):
        if self._geom is None:
            self._init_geom(coordinates)
        update_linearring_from_py(self, coordinates)

    coords = property(_get_coords, _set_coords)


class LinearRingAdapter(LineStringAdapter):

    context = None
    __geom__ = None
    __p__ = None
    _owned = False

    @property
    def _geom(self):
        """Keeps the GEOS geometry in synch with the context."""
        if self.__geom__ is not None:
            lgeos.GEOSGeom_destroy(self.__geom)
        self.__geom, n = geos_linearring_from_py(self.context)
        return self.__geom

    @property
    def __geo_interface__(self):
        return {
            'type': 'LinearRing',
            'coordinates': tuple(self.coords)
            }

    coords = property(BaseGeometry._get_coords)


def asLinearRing(context):
    return LinearRingAdapter(context)


class InteriorRingSequence(object):

    _factory = None
    _geom = None
    __p__ = None
    _ndim = None
    _index = 0
    _length = 0
    __rings__ = None
    _gtag = None

    def __init__(self, parent):
        self.__p__ = parent
        self._geom = parent._geom
        self._ndim = parent._ndim

    def __iter__(self):
        self._index = 0
        self._length = self.__len__()
        return self

    def next(self):
        if self._index < self._length:
            ring = self._get_ring(self._index)
            self._index += 1
            return ring
        else:
            raise StopIteration 

    def __len__(self):
        return lgeos.GEOSGetNumInteriorRings(self._geom)

    def __getitem__(self, i):
        M = self.__len__()
        if i + M < 0 or i >= M:
            raise IndexError, "index out of range"
        if i < 0:
            ii = M + i
        else:
            ii = i
        return self._get_ring(i)

    @property
    def _longest(self):
        max = 0
        for g in iter(self):
            l = len(g.coords)
            if l > max:
                max = l

    def gtag(self):
        return hash(repr(self.__p__))

    def _get_ring(self, i):
        gtag = self.gtag()
        if gtag != self._gtag:
            self.__rings__ = {}
        if i not in self.__rings__:
            g = lgeos.GEOSGetInteriorRingN(self._geom, i)
            ring = LinearRing()
            ring.__geom__ = g
            ring.__p__ = self
            ring._owned = True
            ring._ndim = self._ndim
            self.__rings__[i] = weakref.ref(ring)
        return self.__rings__[i]()
        

def geos_polygon_from_py(shell, holes=None):
    if shell is not None:
        geos_shell, ndim = geos_linearring_from_py(shell)
        if holes:
            ob = holes
            L = len(ob)
            N = len(ob[0][0])
            assert L >= 1
            assert N == 2 or N == 3

            # Array of pointers to ring geometries
            geos_holes = (c_void_p * L)()
    
            # add to coordinate sequence
            for l in xrange(L):
                geom, ndim = geos_linearring_from_py(ob[l])
                geos_holes[l] = cast(geom, c_void_p)

        else:
            geos_holes = POINTER(c_void_p)()
            L = 0

        return (
            lgeos.GEOSGeom_createPolygon(
                        c_void_p(geos_shell),
                        geos_holes,
                        L
                        ),
            ndim
            )

class Polygon(BaseGeometry):

    """A line string, also known as a polyline.
    """

    _exterior = None
    _interiors = []
    _ndim = 2
    __geom__ = None
    _owned = False

    def __init__(self, shell=None, holes=None):
        """Initialize.

        Parameters
        ----------
        exterior : sequence or array
            This may be an object that satisfies the numpy array protocol,
            providing an M x 2 or M x 3 (with z) array, or it may be a sequence
            of x, y (,z) coordinate sequences.

        Example
        -------
        >>> coords = ((0., 0.), (0., 1.), (1., 1.), (1., 0.), (0., 0.))
        >>> polygon = Polygon(coords)
        """
        BaseGeometry.__init__(self)

        if shell is not None:
            self._geom, self._ndim = geos_polygon_from_py(shell, holes)

    @property
    @exceptNull
    def exterior(self):
        if self._exterior is None or self._exterior() is None:
            g = lgeos.GEOSGetExteriorRing(self._geom)
            ring = LinearRing()
            ring.__geom__ = g
            ring.__p__ = self
            ring._owned = True
            ring._ndim = self._ndim
            self._exterior = weakref.ref(ring)
        return self._exterior()

    @property
    @exceptNull
    def interiors(self):
        return InteriorRingSequence(self)

    @property
    def ctypes(self):
        if not self._ctypes_data:
            self._ctypes_data = self.exterior.ctypes
        return self._ctypes_data

    @property
    def __array_interface__(self):
        raise NotImplementedError, \
        "A polygon does not itself provide the array interface. Its rings do."

    def _get_coords(self):
        raise NotImplementedError, \
        "Component rings have coordinate sequences, but the polygon does not"

    def _set_coords(self, ob):
        raise NotImplementedError, \
        "Component rings have coordinate sequences, but the polygon does not"

    @property
    def coords(self):
        raise NotImplementedError, \
        "Component rings have coordinate sequences, but the polygon does not"

    @property
    def __geo_interface__(self):
        coords = [tuple(self.exterior.coords)]
        for hole in self.interiors:
            coords.append(tuple(hole.coords))
        return {
            'type': 'Polygon',
            'coordinates': tuple(coords)
            }


class PolygonAdapter(PolygonProxy, Polygon):

    """Adapts sequences of sequences or numpy arrays to the polygon
    interface.
    """
    
    context = None
    __geom__ = None
    _owned = False

    def __init__(self, shell, holes=None):
        self.shell = shell
        self.holes = holes
        self.context = (shell, holes)
        self.factory = geos_polygon_from_py

    @property
    def _ndim(self):
        try:
            # From array protocol
            array = self.shell.__array_interface__
            n = array['shape'][1]
            assert n == 2 or n == 3
            return n
        except AttributeError:
            # Fall back on list
            return len(self.shell[0])


def asPolygon(shell, holes=None):
    """Factory for PolygonAdapter instances."""
    return PolygonAdapter(shell, holes)


# Test runner
def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()
