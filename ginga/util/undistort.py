# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import copy
import numpy as np


# see https://github.com/astropy/astropy/issues/3675 for inspiration
# for this function

def quick_undistort_image(data_in, wcs_in):
    """Perform a quick undistortion of an image based on a WCS with
    SIP distortion correction.

    Parameters
    ----------
    data_in : ndarray
        2D image data

    wcs_in : ~astropy.wcs.WCS object
        The WCS object associated with the data.

    Returns
    -------
    data_out : ndarray
        Quickly undistorted 2D array

    wcs_out : ~astropy.wcs.WCS object
        A new WCS object without distortion correction.
    """

    # enumerate all pixels in input data
    ht, wd = data_in.shape
    yi, xi = np.mgrid[0:ht, 0:wd]
    pts = np.array((yi.ravel(), xi.ravel())).T

    # translate to world coordinates, taking into account all SIP
    # distortion corrections
    sky = wcs_in.all_pix2world(pts, 0, ra_dec_order=True)

    # translate back to pixel coordinates, *without* SIP corrections
    pts2 = wcs_in.wcs_world2pix(sky, 0)

    # round to integer pixels
    pts2 = np.round(pts2).astype(np.int)

    # determine size of new destination array
    y_min, y_max = pts2[:, 0].min(), pts2[:, 0].max()
    x_min, x_max = pts2[:, 1].min(), pts2[:, 1].max()
    new_ht, new_wd = y_max - y_min + 1, x_max - x_min + 1

    # create empty array holding NaNs
    out_arr = np.full((new_ht, new_wd), np.NaN)

    # deposit pixels in to output array
    y2i, x2i = pts2[:, 0] - y_min, pts2[:, 1] - x_min
    out_arr[y2i, x2i] = data_in[pts[:, 0], pts[:, 1]]

    # create a new WCS without the SIP info
    # TODO: need someone with knowledge of astropy.WCS to say if this
    # is sufficient
    new_wcs = copy.deepcopy(wcs_in)
    new_wcs.sip = None

    return out_arr, new_wcs
