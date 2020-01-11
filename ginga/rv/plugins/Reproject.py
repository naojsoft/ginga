# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
``Reproject`` is a simple plugin to reproject an image from one WCS to
another.

**Plugin Type: Local**

``Reproject`` is a local plugin, which means it is associated with a channel.
An instance can be opened for each channel.  You need to have the Astropy
'reproject' module installed to use this plugin.

**Usage**

Start the plugin on a channel.  Load the image which has the WCS that you
want to use for the reprojection into the channel.

**Reprojection**

Click "Set WCS" to save the WCS; you will see the image copied into the
plugin viewer and the message "WCS set" will briefly appear there.

Now load any image that you want to reproject into the channel.  Click
"Reproject" to reproject the image using the saved image and it's header/WCS
to do so.  The reprojected image will appear in the channel as a separate
image.  You can keep loading images and reprojecting them.  If you want to
do a different reprojection, simply repeat the "Set WCS", "Reproject"
sequence at any time.

The parameters for the reprojection can be set in the GUI controls.

**Undistort**

Clicking the "Undistort" button will attempt to "undistort" the image by
doing a reprojection based on the current image's WCS with SIP distortion
information removed.

In this case there is no need to click "Set WCS".  The WCS from the channel
image will be used to create the reprojection WCS.  To use this feature the
WCS must contain SIP distortion information.
"""
import os.path
import copy
import numpy as np
#np.set_printoptions(threshold=np.inf)
from astropy.io import fits

have_reproject = False
try:
    import reproject
    have_reproject = True
except ImportError:
    pass

from ginga import GingaPlugin, AstroImage
from ginga.misc import Future
from ginga.gw import Widgets, Viewers
from ginga.util import wcs

__all__ = ['Reproject']

if have_reproject:
    _choose = {'adaptive': dict(order=['nearest-neighbor', 'bilinear'],
                                method=reproject.reproject_adaptive),
               'interp': dict(order=['nearest-neighbor', 'bilinear',
                                     'biquadratic', 'bicubic'],
                              method=reproject.reproject_interp),
               'exact': dict(order=['n/a'],
                             method=reproject.reproject_exact),
               }
else:
    _choose = {}


class Reproject(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Reproject, self).__init__(fv, fitsimage)

        self._wd = 400
        self._ht = 300
        _sz = max(self._wd, self._ht)
        # hack to set a reasonable starting position for the splitter
        self._split_sizes = [_sz, _sz]

        self.count = 1
        self.cache_dir = "/tmp"
        self.img_out = None
        self._proj_types = list(_choose.keys())
        self._proj_types.sort()
        self._proj_type = 'interp'

    def build_gui(self, container):
        if not have_reproject:
            raise Exception("Please install the 'reproject' module to use "
                            "this plugin")
        vtop = Widgets.VBox()
        vtop.set_border_width(4)

        box, sw, orientation = Widgets.get_oriented_box(container)
        zi = Viewers.CanvasView(logger=self.logger)
        zi.set_desired_size(self._wd, self._ht)
        zi.enable_autozoom('override')
        zi.enable_autocuts('override')
        zi.set_bg(0.4, 0.4, 0.4)
        zi.show_pan_mark(True)
        # for debugging
        zi.set_name('reproject-image')
        self.rpt_image = zi

        bd = zi.get_bindings()
        bd.enable_all(True)

        iw = Viewers.GingaViewerWidget(zi)
        iw.resize(self._wd, self._ht)
        paned = Widgets.Splitter(orientation=orientation)
        paned.add_widget(iw)
        self.w.splitter = paned

        vbox2 = Widgets.VBox()
        captions = (("Reproject", 'button', "Set WCS", 'button'),
                    ("Undistort", 'button'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)
        vbox2.add_widget(w, stretch=0)

        b.reproject.add_callback('activated', self.reproject_cb, False)
        b.reproject.set_tooltip("Click to save channel image as reprojection WCS")
        b.reproject.set_enabled(False)
        b.set_wcs.add_callback('activated', self.set_wcs_cb)
        b.set_wcs.set_tooltip("Click to reproject channel image using saved WCS")
        b.undistort.add_callback('activated', self.reproject_cb, True)
        b.undistort.set_tooltip("Click to correct SIP distortion")
        #b.undistort.set_enabled(False)

        captions = (("Reproject type", 'combobox'),
                    ("Order", 'combobox'),
                    ("status", 'llabel'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)
        vbox2.add_widget(w, stretch=0)

        b.status.set_text("")

        cb = b.reproject_type
        for name in self._proj_types:
            cb.insert_alpha(name)
        cb.set_tooltip("Set type of reprojection")
        cb.add_callback('activated', self.set_reprojection_cb)
        idx = self._proj_types.index(self._proj_type)
        cb.set_index(idx)

        self._adjust_orders()

        # stretch
        spacer = Widgets.Label('')
        vbox2.add_widget(spacer, stretch=1)

        box.add_widget(vbox2, stretch=1)

        paned.add_widget(sw)
        paned.set_sizes(self._split_sizes)

        vtop.add_widget(paned, stretch=5)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        vtop.add_widget(btns, stretch=0)

        container.add_widget(vtop, stretch=5)
        self.gui_up = True

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def start(self):
        self.redo()

    def stop(self):
        self.img_out = None
        self._split_sizes = self.w.splitter.get_sizes()
        self.gui_up = False

    def redo(self):
        if not self.gui_up:
            return
        image = self.fitsimage.get_image()
        if image is None or image.wcs is None or image.wcs.wcs is None:
            self.w.set_wcs.set_enabled(False)
            self.w.reproject.set_enabled(False)
            self.w.undistort.set_enabled(False)
        else:
            self.w.set_wcs.set_enabled(True)
            self.w.reproject.set_enabled(self.img_out is not None)
            self.w.undistort.set_enabled(image.wcs.wcs.sip is not None)

    def reproject(self, image, name=None, undistort_sip=False, cache_dir=None):
        if image is None or image.wcs is None:
            self.fv.show_error("Reproject: null target image or WCS")
            return
        wcs_in = image.wcs.wcs
        data_in = image.get_data()

        if undistort_sip:
            proj_out = copy.deepcopy(wcs_in)
            proj_out.sip = None
            shape = data_in.shape

        else:
            hdr_in = image.get_header()

            header = self.img_out.get_header()

            ((_xr, _yr),
             (cdelt1, cdelt2)) = wcs.get_xy_rotation_and_scale(hdr_in)

            # preserve transformed image's pixel scale
            header['CDELT1'] = cdelt1
            header['CDELT2'] = cdelt2

            # create shape big enough to handle rotation
            ht, wd = data_in.shape[:2]
            side = int(np.ceil(np.sqrt(wd ** 2 + ht ** 2)))
            header['NAXIS1'] = side
            header['NAXIS2'] = side
            header['CRPIX1'] = side / 2
            header['CRPIX2'] = side / 2

            proj_out = fits.Header(header)
            shape = (side, side)

        method = _choose[self._proj_type]['method']

        kwargs = dict(return_footprint=True, shape_out=shape)
        order = self.w.order.get_text()
        if order != 'n/a':
            kwargs['order'] = order

        # do reprojection
        data_out, mask = method((data_in, wcs_in), proj_out, **kwargs)

        # TODO: use mask (probably as alpha mask)
        hdu = fits.PrimaryHDU(data_out)

        # Add WCS to the new image
        # TODO: carry over other keywords besides WCS?
        if undistort_sip:
            hdu.header.update(proj_out.to_header())
        else:
            hdu.header.update(self.img_out.wcs.wcs.to_header())

        if name is None:
            name = self.get_name(image.get('name'), cache_dir)

        # Write image to cache directory, if one is defined
        path = None
        if cache_dir is not None:
            path = os.path.join(cache_dir, name + '.fits')
            hdulst = fits.HDUList([hdu])
            hdulst.writeto(path)
            self.logger.info("wrote {}".format(path))

        img_out = AstroImage.AstroImage(logger=self.logger)
        img_out.load_hdu(hdu)
        img_out.set(name=name, path=path)

        return img_out

    def set_wcs_cb(self, w):
        image = self.fitsimage.get_image()
        if image is None or image.wcs is None:
            return

        self.rpt_image.set_image(image)
        self.img_out = image
        self.w.reproject.set_enabled(True)
        self.rpt_image.onscreen_message("WCS set", delay=1.0)

    def _reproject_cont(self, future):
        self.fv.gui_call(self.w.status.set_text, "")
        try:
            img_out = future.get_value()

        except Exception as e:
            self.fv.show_error("reproject error: {}".format(e))
            return

        if img_out is not None:
            self.fv.gui_do(self.channel.add_image, img_out)

    def reproject_cb(self, w, undistort_sip):
        image = self.fitsimage.get_image()

        future = Future.Future()
        future.freeze(self.reproject, image, cache_dir=self.cache_dir,
                      undistort_sip=undistort_sip)
        future.add_callback('resolved', self._reproject_cont)

        self.w.status.set_text("Working...")
        self.fv.nongui_do_future(future)

    def get_name(self, name_in, cache_dir):
        found = False
        while not found:
            name = name_in + '-rpjt-{}'.format(self.count)
            self.count += 1

            # Write image to cache directory, if one is defined
            path = None
            if cache_dir is None:
                return name

            path = os.path.join(cache_dir, name + '.fits')
            if not os.path.exists(path):
                return name

    def set_reprojection_cb(self, w, idx):
        self._proj_type = w.get_text()
        self._adjust_orders()

    def _adjust_orders(self):
        order = _choose[self._proj_type]['order']
        self.w.order.clear()
        for name in order:
            self.w.order.insert_alpha(name)

    def __str__(self):
        return 'reproject'