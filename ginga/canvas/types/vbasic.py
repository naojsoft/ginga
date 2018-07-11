#
# vbasic.py -- classes for vector drawing of basic shapes
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga.canvas.CanvasObject import (CanvasObjectBase, _bool, _color,
                                       Point as XPoint, MovePoint, ScalePoint,
                                       EditPoint,
                                       register_canvas_types,
                                       colors_plus_none, coord_names)
from ginga import trcalc
from ginga.misc.ParamSet import Param
from ginga.util import bezier

from .mixins import (OnePointMixin, TwoPointMixin, OnePointOneRadiusMixin,
                     OnePointTwoRadiusMixin, PolygonMixin)


#
#   ==== BASIC CLASSES FOR GRAPHICS OBJECTS ====
#

class Circles(OnePointOneRadiusMixin, CanvasObjectBase):
    """Draws a circle on a DrawingCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    radius: radius based on the number of pixels in data space
    Optional parameters for linesize, color, etc.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='coord', type=str, default='data',
                  valid=coord_names,
                  description="Set type of coordinates"),
            Param(name='x', type=float, default=0.0, argpos=0,
                  description="X coordinate of center of object"),
            Param(name='y', type=float, default=0.0, argpos=1,
                  description="Y coordinate of center of object"),
            Param(name='radius', type=float, default=1.0, argpos=2,
                  min=0.0,
                  description="Radius of object"),
            Param(name='linewidth', type=int, default=1,
                  min=1, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default solid)"),
            Param(name='color',
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='fill', type=_bool,
                  default=False, valid=[False, True],
                  description="Fill the interior"),
            Param(name='fillcolor', default=None,
                  valid=colors_plus_none, type=_color,
                  description="Color of fill"),
            Param(name='fillalpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
            Param(name='showcap', type=_bool,
                  default=False, valid=[False, True],
                  description="Show caps for this object"),
        ]

    def __init__(self, x, y, radius, color='yellow',
                 linewidth=1, linestyle='solid', showcap=False,
                 fill=False, fillcolor=None, alpha=1.0, fillalpha=1.0,
                 **kwdargs):
        points = np.asarray([(x, y)], dtype=np.float)
        CanvasObjectBase.__init__(self, points=points, color=color,
                                  linewidth=linewidth, showcap=showcap,
                                  linestyle=linestyle,
                                  fill=fill, fillcolor=fillcolor,
                                  alpha=alpha, fillalpha=fillalpha,
                                  radius=radius, **kwdargs)
        OnePointOneRadiusMixin.__init__(self)
        self.kind = 'circles'

    def contains_pt(self, pt):
        x, y = pt
        x_arr, y_arr = np.asarray((self.x, self.y))
        x_arr, y_arr = (x_arr.astype(np.float, copy=False),
                        y_arr.astype(np.float, copy=False))

        xd, yd = self.crdmap.to_data((self.x, self.y))

        # need to recalculate radius in case of wcs coords
        points = self.get_data_points(points=(
            self.crdmap.offset_pt((self.x, self.y), (self.radius, 0)),
            self.crdmap.offset_pt((self.x, self.y), (0, self.radius)),
        ))
        (x2, y2), (x3, y3) = points
        xradius = max(x2, xd) - min(x2, xd)
        yradius = max(y3, yd) - min(y3, yd)

        # See http://math.stackexchange.com/questions/76457/check-if-a-point-is-within-an-ellipse
        res = (((x_arr - xd) ** 2) / xradius ** 2 +
               ((y_arr - yd) ** 2) / yradius ** 2)
        contains = (res <= 1.0)
        return contains

    ## def get_edit_points(self, viewer):
    ##     points = self.get_data_points(points=(
    ##         (self.x, self.y),
    ##         self.crdmap.offset_pt((self.x, self.y), (self.radius, 0)),
    ##     ))
    ##     return [MovePoint(*points[0]),
    ##             ScalePoint(*points[1]),
    ##             ]

    ## def get_llur(self):
    ##     points = self.get_data_points(points=(
    ##         self.crdmap.offset_pt((self.x, self.y),
    ##                               (-self.radius, -self.radius)),
    ##         self.crdmap.offset_pt((self.x, self.y),
    ##                               (self.radius, self.radius)),
    ##     ))
    ##     (x1, y1), (x2, y2) = points
    ##     return self.swapxy(x1, y1, x2, y2)

    def draw(self, viewer):
        i_pts = np.array((self.x, self.y))

        zeds = np.zeros(self.x.size)
        if np.isscalar(self.radius):
            rads = np.full(self.x.size, self.radius)
        else:
            rads = self.radius

        o_pts = self.crdmap.offset_pt((self.x, self.y), (zeds, rads))

        crdmap = viewer.get_coordmap('native')
        ci_pts = crdmap.data_to(i_pts.T)
        co_pts = crdmap.data_to(o_pts.T)
        cx, cy, cradius = self.calc_radius(viewer, ci_pts.T, co_pts.T)

        cr = viewer.renderer.setup_cr(self)
        cr.draw_circles(cx, cy, cradius)

        ## if self.showcap:
        ##     self.draw_caps(cr, self.cap, ((cx, cy), ))


register_canvas_types(
    dict(circles=Circles))

#END
