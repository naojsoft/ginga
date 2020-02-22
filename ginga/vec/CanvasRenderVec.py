#
# CanvasRenderVec.py -- for rendering into a vector of drawing operations
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import math
from itertools import chain
import numpy as np

from .VecHelp import *

from ginga.canvas import render
# force registration of all canvas types
import ginga.canvas.types.all  # noqa
from ginga import trcalc


class RenderContext(render.RenderContextBase):

    def __init__(self, renderer, viewer, surface):
        render.RenderContextBase.__init__(self, renderer, viewer)

        self.pen = None
        self.brush = None
        self.font = None

    def set_line_from_shape(self, shape):
        # TODO: support style
        alpha = getattr(shape, 'alpha', 1.0)
        linewidth = getattr(shape, 'linewidth', 1.0)
        self.pen = Pen(shape.color, linewidth=linewidth, alpha=alpha)

    def set_fill_from_shape(self, shape):
        fill = getattr(shape, 'fill', False)
        if fill:
            if hasattr(shape, 'fillcolor') and shape.fillcolor:
                color = shape.fillcolor
            else:
                color = shape.color
            alpha = getattr(shape, 'alpha', 1.0)
            alpha = getattr(shape, 'fillalpha', alpha)
            self.brush = Brush(color, alpha=alpha)
        else:
            self.brush = None

    def set_font_from_shape(self, shape):
        if hasattr(shape, 'font'):
            if hasattr(shape, 'fontsize') and shape.fontsize is not None:
                fontsize = shape.fontsize
            else:
                fontsize = shape.scale_font(self.viewer)
            fontsize = self.scale_fontsize(fontsize)
            alpha = getattr(shape, 'alpha', 1.0)
            self.font = Font(shape.font, fontsize, shape.color, alpha=alpha)
        else:
            self.font = None

    def initialize_from_shape(self, shape, line=True, fill=True, font=True):
        if line:
            self.set_line_from_shape(shape)
        if fill:
            self.set_fill_from_shape(shape)
        if font:
            self.set_font_from_shape(shape)

    def set_line(self, color, alpha=1.0, linewidth=1, style='solid'):
        # TODO: support line width and style
        self.pen = Pen(color, alpha=alpha)

    def set_fill(self, color, alpha=1.0):
        if color is None:
            self.brush = None
        else:
            self.brush = Brush(color, alpha=alpha)

    def set_font(self, fontname, fontsize, color='black', alpha=1.0):
        fontsize = self.scale_fontsize(fontsize)
        self.font = Font(fontname, fontsize, color, alpha=alpha)

    def text_extents(self, text):
        return self.renderer.text_extents(text, self.font)

    ##### DRAWING OPERATIONS #####

    def draw_image(self, image_id, cpoints, rgb_arr, whence, order='RGB'):
        self.renderer.rl.append((IMAGE, (image_id, cpoints, rgb_arr, whence, order)))

    def draw_text(self, cx, cy, text, rot_deg=0.0):
        self.renderer.rl.append((TEXT, (cx, cy, text, rot_deg),
                                 self.pen, self.brush, self.font))

    def draw_polygon(self, cpoints):
        self.renderer.rl.append((POLYGON, cpoints, self.pen, self.brush))

    def draw_circle(self, cx, cy, cradius):
        self.renderer.rl.append((CIRCLE, (cx, cy, cradius),
                                 self.pen, self.brush))

    ## def draw_bezier_curve(self, cpoints):
    ##     self.renderer.rl.append((BEZIER, cpoints, self.pen, self.brush))

    ## def draw_ellipse_bezier(self, cpoints):
    ##     # draw 4 bezier curves to make the ellipse
    ##     self.renderer.rl.append((ELLIPSE_BEZIER, cpoints, self.pen, self.brush))

    ## def draw_ellipse(self, cx, cy, cxradius, cyradius, rot_deg):
    ##     self.renderer.rl.append((ELLIPSE,
    ##                              (cx, cy, cxradius, cyradius, rot_deg),
    ##                              self.pen, self.brush))

    def draw_line(self, cx1, cy1, cx2, cy2):
        self.renderer.rl.append((LINE, (cx1, cy1, cx2, cy2),
                                 self.pen, self.brush))

    def draw_path(self, cpoints):
        self.renderer.rl.append((PATH, cpoints, self.pen, self.brush))


class CanvasRenderer(render.StandardPixelRenderer):

    def __init__(self, viewer):
        super(CanvasRenderer, self).__init__(viewer)

        self.kind = 'vec'
        self.rgb_order = 'RGBA'
        self.surface = None
        self.dims = (0, 0)

        # the render list
        self.rl = []

    def initialize(self):
        wd, ht = self.dims
        cpoints = ((0, 0), (wd, 0), (wd, ht), (ht, 0))
        bg = self.viewer.get_bg()
        pen = Pen(color=bg)
        brush = Brush(color=bg, fill=True)
        self.rl = [(POLYGON, cpoints, pen, brush)]

    def render_image(self, rgbobj, dst_x, dst_y):
        """Render the image represented by (rgbobj) at dst_x, dst_y
        in the pixel space.
        *** internal method-- do not use ***
        """
        self.logger.debug("redraw surface")
        data = rgbobj.get_array(self.rgb_order, dtype=np.uint8)

        cr = RenderContext(self, self.viewer, self.surface)
        cr.draw_image(dst_x, dst_y, data)

    def get_surface_as_array(self, order=None):
        ## print('---------------')
        ## print('RENDER LIST', len(self.rl), self.rl)
        ## print('---------------')
        if self.surface is None:
            raise render.RenderError("No VEC surface defined")

        # TODO: could these have changed between the time that self.surface
        # was last updated?
        wd, ht = self.dims

        # Get surface as a numpy array
        arr8 = np.fromstring(self.surface.tobytes(), dtype=np.uint8)
        arr8 = arr8.reshape((ht, wd, len(self.rgb_order)))

        # adjust according to viewer's needed order
        return self.reorder(order, arr8)

    def draw_vector(self, cr):
        for tup in self.rl:
            dtyp, font = None, None
            try:
                dtyp = tup[0]
                if dtyp == IMAGE:
                    (image_id, cpoints, rgb_arr, whence, order) = tup[1]
                    cr.draw_image(image_id, cpoints, rgb_arr, whence,
                                  #order=order,
                                  order=self.rgb_order)

                elif dtyp == LINE:
                    (cx1, cy1, cx2, cy2) = tup[1]
                    cr.setup_pen_brush(*tup[2:4])
                    cr.draw_line(cx1, cy1, cx2, cy2)

                elif dtyp == CIRCLE:
                    (cx, cy, cradius) = tup[1]
                    cr.setup_pen_brush(*tup[2:4])
                    cr.draw_circle(cx, cy, cradius)

                elif dtyp == BEZIER:
                    cpoints = tup[1]
                    cr.setup_pen_brush(*tup[2:4])
                    cr.draw_bezier_curve(cpoints)

                elif dtyp == ELLIPSE_BEZIER:
                    cpoints = tup[1]
                    cr.setup_pen_brush(*tup[2:4])
                    cr.draw_ellipse_bezier(cpoints)

                elif dtyp == POLYGON:
                    cpoints = tup[1]
                    cr.setup_pen_brush(*tup[2:4])
                    cr.draw_polygon(cpoints)

                elif dtyp == PATH:
                    cpoints = tup[1]
                    cr.setup_pen_brush(*tup[2:4])
                    cr.draw_path(cpoints)

                elif dtyp == TEXT:
                    (cx, cy, text, rot_deg) = tup[1]
                    cr.setup_pen_brush(*tup[2:4])
                    font = tup[4]
                    cr.set_font(font.fontname, font.fontsize,
                                color=font.color, alpha=font.alpha)
                    cr.draw_text(cx, cy, text, rot_deg=rot_deg)

            except Exception as e:
                self.logger.error("Error drawing '{}': {}".format(dtyp, e),
                                  exc_info=True )

    def setup_cr(self, shape):
        cr = RenderContext(self, self.viewer, self.surface)
        cr.initialize_from_shape(shape, font=False)
        return cr

    def get_dimensions(self, shape):
        cr = self.setup_cr(shape)
        cr.set_font_from_shape(shape)
        return cr.text_extents(shape.text)

#END