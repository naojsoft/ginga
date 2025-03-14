#
# io_rgb.py -- RGB image file handling.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time
import mimetypes
from io import BytesIO

import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS

from ginga.BaseImage import Header, ImageError
from ginga.util import iohelper, rgb_cms
from ginga.util.io import io_base
from ginga.misc import Bunch
from ginga import trcalc

# optional imports
try:
    # do we have opencv available?
    import cv2
    have_opencv = True
except ImportError:
    have_opencv = False

# exifread library for getting metadata, in case we are using OpenCv
try:
    import exifread
    have_exif = True
except ImportError:
    have_exif = False

try:
    # for opening HEIC (Apple image) files)
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass
# For testing...
#have_exif = False
#have_opencv = False


def load_file(filepath, idx=None, logger=None, **kwargs):
    """
    Load an object from a RGB file.

    """
    opener = RGBFileHandler(logger)
    return opener.load_file(filepath, **kwargs)


class BaseRGBFileHandler(io_base.BaseIOHandler):

    name = 'RGB'

    def __init__(self, logger):
        super(BaseRGBFileHandler, self).__init__(logger)

        self._path = None
        self.fileinfo = None

        self.clr_mgr = rgb_cms.ColorManager(self.logger)

    def load_file(self, filespec, dstobj=None, **kwargs):
        info = iohelper.get_fileinfo(filespec)
        if not info.ondisk:
            raise ValueError("File does not appear to be on disk: %s" % (
                info.url))

        filepath = info.filepath
        if dstobj is None:
            # Put here to avoid circular import
            from ginga.RGBImage import RGBImage
            dstobj = RGBImage(logger=self.logger)

        header = Header()
        metadata = {'header': header, 'path': filepath}

        data_np = self.imload(filepath, metadata)

        dstobj.set_data(data_np, metadata=metadata)

        if dstobj.name is not None:
            dstobj.set(name=dstobj.name)
        else:
            name = iohelper.name_image_from_path(filepath, idx=None)
            dstobj.set(name=name)

        if 'order' in metadata:
            dstobj.order = metadata['order']
        dstobj.set(path=filepath, idx=None, image_loader=self.load_file)
        return dstobj

    def open_file(self, filespec, **kwargs):
        self._path = filespec
        return self

    def close(self):
        self._path = None

    def __len__(self):
        return 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __del__(self):
        self.close()

    def load_idx_cont(self, idx_spec, loader_cont_fn, **kwargs):

        # TODO: raise an error if idx_spec doesn't match a single image
        idx = 0
        if idx_spec is not None and idx_spec != '':
            idx = int(idx_spec)

        data_obj = self.load_idx(idx, **kwargs)

        # call continuation function
        loader_cont_fn(data_obj)

    def imload(self, filepath, metadata):
        """Load an image file, guessing the format, and return a numpy
        array containing an RGB image.  If EXIF keywords can be read
        they are returned in the metadata.
        """
        start_time = time.time()
        typ, enc = mimetypes.guess_type(filepath)
        if not typ:
            typ = 'image/jpeg'
        typ, subtyp = typ.split('/')
        self.logger.debug("MIME type is %s/%s" % (typ, subtyp))

        data_np = self._imload(filepath, metadata)

        end_time = time.time()
        self.logger.debug("loading time %.4f sec" % (end_time - start_time))
        return data_np

    def imresize(self, data, new_wd, new_ht, method='bilinear'):
        """Scale an image in numpy array _data_ to the specified width and
        height.  A smooth scaling is preferred.
        """
        start_time = time.time()

        newdata = self._imresize(data, new_wd, new_ht, method=method)

        end_time = time.time()
        self.logger.debug("scaling time %.4f sec" % (end_time - start_time))

        return newdata

    def get_thumb(self, filepath):
        if not have_exif:
            raise Exception("Install exifread to use this method")

        try:
            with open(filepath, 'rb') as in_f:
                info = exifread.process_file(in_f)
            buf = info['JPEGThumbnail']

        except Exception as e:
            return None

        image = Image.open(BytesIO(buf))
        data_np = np.array(image)
        return data_np

    def _getexif(self, filepath, kwds):
        if have_exif:
            try:
                with open(filepath, 'rb') as in_f:
                    info = exifread.process_file(in_f, details=False)
                if info is not None:
                    kwds.update(info)
                    o_tag = 'Image Orientation'
                    if o_tag in info:
                        val = info[o_tag].values[0]
                        kwds[o_tag] = val

            except Exception as e:
                self.logger.warning("Failed to get image metadata: %s" % (str(e)))

        else:
            self.logger.warning("Please install 'exifread' module to get image metadata")

    def get_buffer(self, data_np, header, format, output=None):
        """Get image as a buffer in (format).
        Format should be 'jpeg', 'png', etc.
        """
        image = Image.fromarray(data_np)
        buf = output
        if buf is None:
            buf = BytesIO()
        image.save(buf, format)
        return buf

    def get_frame(self, num):
        raise NotImplementedError("subclass should implement this method")

    def get_directory(self):
        return self.hdu_db

    def get_info_idx(self, idx):
        return self.hdu_db[idx]


class OpenCvFileHandler(BaseRGBFileHandler):
    """For loading common RGB image formats (e.g. JPEG, etc).
    """

    name = 'OpenCv'
    mimetypes = ['image/jpeg',
                 'image/tiff',
                 'image/png',
                 'image/gif',
                 'image/x-portable-pixmap',
                 'image/ppm',
                 'image/x-portable-anymap',
                 'image/pnm',
                 'image/x-portable-bitmap',
                 'image/pbm',
                 'image/x-portable-graymap',
                 'image/x-portable-greymap',
                 'image/pgm',
                 'image/vnd.microsoft.icon',
                 'image/bmp',
                 'image/x-tga',
                 'video/x-msvideo',
                 'video/mp4',
                 'video/quicktime',
                 'video/x-matroska']

    @classmethod
    def check_availability(cls):
        import cv2   # noqa

    def open_file(self, filespec, **kwargs):

        info = iohelper.get_fileinfo(filespec)
        if not info.ondisk:
            raise ImageError("File does not appear to be on disk: %s" % (
                info.url))

        self.fileinfo = info
        filepath = info.filepath

        self._path = filepath
        self.rgb_f = cv2.VideoCapture(filepath)

        idx = 0
        extver_db = {}
        self.hdu_info = []
        self.hdu_db = {}
        self.numframes = int(self.rgb_f.get(cv2.CAP_PROP_FRAME_COUNT))
        self.logger.debug("number of frames: {}".format(self.numframes))

        name = "image{}".format(idx)
        extver = 0
        # prepare a record of pertinent info about the HDU for
        # lookups by numerical index or (NAME, EXTVER)
        # NOTE: dtype is uint8 even though we may later read it at a higher
        # bit depth--because there doesn't seem to be a straightforward way
        # to know the bit depth before reading the data, unfortunately
        d = Bunch.Bunch(index=idx, name=name, extver=extver,
                        dtype='uint8', htype='imagehdu')
        self.hdu_info.append(d)
        # different ways of accessing this HDU:
        # by numerical index
        self.hdu_db[idx] = d
        # by (hduname, extver)
        key = (name, extver)
        if key not in self.hdu_db:
            self.hdu_db[key] = d

        self.extver_db = extver_db
        return self

    def close(self):
        self._path = None
        if self.rgb_f is not None:
            self.rgb_f.release()
        self.rgb_f = None

    def __len__(self):
        return len(self.hdu_info)

    def load_idx(self, idx, **kwargs):
        if self.rgb_f is None:
            raise ValueError("Please call open_file() first!")

        if idx is None:
            idx = 0

        metadata = dict()
        if idx == 0:
            data_np = self.imload(self.fileinfo.filepath, metadata)
        else:
            raise IndexError(f"index {idx} out of range")

        from ginga.RGBImage import RGBImage
        data_obj = RGBImage(data_np=data_np, metadata=metadata,
                            logger=self.logger)
        data_obj.io = self

        data_obj.axisdim = [self.numframes] + list(data_np.shape[:2])
        data_obj.naxispath = [0, 0, 0]

        name = self.fileinfo.name + '[{}]'.format(idx)
        data_obj.set(name=name, path=self.fileinfo.filepath, idx=idx)

        return data_obj

    def get_frame(self, num, metadata=None):
        if self.rgb_f is None:
            if self.fileinfo is None:
                raise ValueError("Please call open_file() first!")
            # re-open file/stream, if not open already
            self._path = self.fileinfo.filepath
            self.rgb_f = cv2.VideoCapture(self._path)

        if num < 0 or num >= self.numframes:
            raise IndexError(f"Frame outside valid range of 0-{self.numframes}")

        self.rgb_f.set(cv2.CAP_PROP_POS_FRAMES, num)
        okay, data_np = self.rgb_f.read()
        if not okay:
            raise IndexError(f"Error reading frame {num}")

        data_np = self._reorder_array(data_np, metadata=metadata)

        return data_np

    def save_file_as(self, filepath, data_np, header):
        # TODO: save keyword metadata!
        if not have_opencv:
            raise ImageError("Install 'opencv' to be able to save images")

        # First choice is OpenCv, because it supports high-bit depth
        # multiband images
        cv2.imwrite(filepath, data_np)

    def _imload(self, filepath, metadata):
        if not have_opencv:
            raise ImageError("Install 'opencv' to be able to load images")

        # OpenCv supports high-bit depth multiband images if you use
        # IMREAD_UNCHANGED.
        # NOTE: IMREAD_IGNORE_ORIENTATION does not seem to be obeyed here!
        # Seems to need to be combined with IMREAD_COLOR, which forces an
        # 8bpp image
        data_np = cv2.imread(filepath,
                             cv2.IMREAD_UNCHANGED + cv2.IMREAD_IGNORE_ORIENTATION)
        if data_np is None:
            self.rgb_f.set(cv2.CAP_PROP_POS_FRAMES, 0)
            okay, data_np = self.rgb_f.read()
            if not okay:
                raise IndexError("Error reading frame 0")

        return self._process_opencv_array(data_np, metadata, filepath)

    def _process_opencv_array(self, data_np, metadata, filepath):

        kwds = metadata.get('header', None)
        if kwds is None:
            kwds = Header()
            metadata['header'] = kwds

        # OpenCv doesn't "do" image metadata, so we punt to exifread
        # library (if installed)
        self._getexif(filepath, kwds)

        data_np = self._reorder_array(data_np, metadata)

        # OpenCv added a feature to do auto-orientation when loading
        # (see https://github.com/opencv/opencv/issues/4344)
        # So reset these values to prevent auto-orientation from
        # happening later
        # NOTE: this is only needed if IMREAD_IGNORE_ORIENTATION
        # (see above) is not working
        kwds['Orientation'] = 1
        kwds['Image Orientation'] = 1

        return data_np

    def _reorder_array(self, data_np, metadata=None):
        # opencv returns BGR images, whereas PIL and others return RGB
        if len(data_np.shape) >= 3 and data_np.shape[2] >= 3:
            if data_np.shape[2] == 3:
                order = 'BGR'
                dst_order = 'RGB'
            else:
                order = 'BGRA'
                dst_order = 'RGBA'
            data_np = trcalc.reorder_image(dst_order, data_np, order)

            if metadata is not None:
                metadata['order'] = dst_order

                # convert to working color profile, if can
                if self.clr_mgr.can_profile():
                    kwds = metadata.get('header', None)
                    if kwds is None:
                        kwds = Header()
                        metadata['header'] = kwds
                    data_np = self.clr_mgr.profile_to_working_numpy(data_np,
                                                                    kwds)

        return data_np

    def _imresize(self, data, new_wd, new_ht, method='bilinear'):
        # TODO: take into account the method parameter
        if not have_opencv:
            raise ImageError("Install 'opencv' to be able to resize RGB images")

        # First choice is OpenCv, because it supports high-bit depth
        # multiband images
        newdata = cv2.resize(data, dsize=(new_wd, new_ht),
                             interpolation=cv2.INTER_CUBIC)

        return newdata


class PillowFileHandler(BaseRGBFileHandler):
    """For loading common RGB image formats (e.g. JPEG, etc).
    """
    name = 'Pillow'
    mimetypes = ['image/jpeg',
                 'image/png',
                 'image/tiff',
                 'image/gif',
                 'image/x-portable-pixmap',
                 'image/ppm',
                 'image/x-portable-anymap',
                 'image/pnm',
                 'image/x-portable-bitmap',
                 'image/pbm',
                 'image/x-portable-graymap',
                 'image/x-portable-greymap',
                 'image/pgm',
                 'image/bmp',
                 'image/x-tga',
                 'image/x-icns',
                 'image/vnd.microsoft.icon',
                 'image/heif']

    @classmethod
    def check_availability(cls):
        from PIL import Image    # noqa

    def open_file(self, filespec, **kwargs):

        info = iohelper.get_fileinfo(filespec)
        if not info.ondisk:
            raise ImageError("File does not appear to be on disk: %s" % (
                info.url))

        self.fileinfo = info
        filepath = info.filepath

        self._path = filepath
        self.rgb_f = Image.open(filepath)

        idx = 0
        extver_db = {}
        self.hdu_info = []
        self.hdu_db = {}
        if hasattr(self.rgb_f, 'n_frames'):
            self.numframes = self.rgb_f.n_frames - 1
        else:
            self.numframes = 0
        self.logger.debug("number of frames: {}".format(self.numframes))

        name = "image{}".format(idx)
        extver = 0
        # prepare a record of pertinent info about the HDU for
        # lookups by numerical index or (NAME, EXTVER)
        d = Bunch.Bunch(index=idx, name=name, extver=extver,
                        dtype='uint8', htype='imagehdu')
        self.hdu_info.append(d)
        # different ways of accessing this HDU:
        # by numerical index
        self.hdu_db[idx] = d
        # by (hduname, extver)
        key = (name, extver)
        if key not in self.hdu_db:
            self.hdu_db[key] = d

        self.extver_db = extver_db
        return self

    def close(self):
        self._path = None
        self.rgb_f = None

    def __len__(self):
        return len(self.hdu_info)

    def get_frame(self, num, metadata=None):
        if self.rgb_f is None:
            if self.fileinfo is None:
                raise ValueError("Please call open_file() first!")
            # re-open file, if not open already
            self._path = self.fileinfo.filepath
            self.rgb_f = Image.open(self._path)

        if num < 0 or num >= self.numframes:
            raise IndexError(f"Frame outside valid range of 0-{self.numframes}")

        # NOTE: pillow does not seem to be consistent on supporting
        # 0-based indexing on RGB images--it seems to depend on whether
        # there is a "base image"
        #self.rgb_f.seek(num)
        self.rgb_f.seek(num + 1)

        image_pil = self.rgb_f
        return self._process_image(image_pil, metadata=metadata)

    def save_file_as(self, filepath, data_np, header):
        # TODO: save keyword metadata!
        img = Image.fromarray(data_np)

        # pillow is not happy saving images to JPG with an alpha channel
        img = img.convert('RGB')

        img.save(filepath)

    def load_idx(self, idx, **kwargs):
        if self.rgb_f is None:
            raise ValueError("Please call open_file() first!")

        if idx is None:
            idx = 0

        if idx > 0:
            raise IndexError(f"index {idx} out of range")

        kwds = Header()
        metadata = dict(header=kwds)

        if self.numframes > 0:
            self.rgb_f.seek(idx + 1)

        image_pil = self.rgb_f
        data_np = self._process_image(image_pil, metadata=metadata)

        from ginga.RGBImage import RGBImage
        data_obj = RGBImage(data_np=data_np, metadata=metadata,
                            logger=self.logger, order=image_pil.mode)
        data_obj.io = self

        data_obj.axisdim = [self.numframes] + list(data_np.shape[:2])
        data_obj.naxispath = [0, 0, 0]

        name = self.fileinfo.name + '[{}]'.format(idx)
        data_obj.set(name=name, path=self.fileinfo.filepath, idx=idx,
                     header=kwds)

        return data_obj

    def _get_header(self, image_pil, kwds):
        if hasattr(image_pil, 'getexif'):
            info = image_pil.getexif()
            if info is not None:
                for tag, value in info.items():
                    kwd = TAGS.get(tag, tag)
                    kwds[kwd] = value

        else:
            self.logger.warning("can't get EXIF data; no getexif() method")

        # is there an embedded color profile?
        if 'icc_profile' in image_pil.info:
            kwds['icc_profile'] = image_pil.info['icc_profile']

    def _imload(self, filepath, metadata):
        image_pil = Image.open(filepath)
        data_np = self._process_image(image_pil, metadata=metadata)
        return data_np

    def _process_image(self, image_pil, metadata=None):
        if metadata is not None:
            metadata['order'] = image_pil.mode
            kwds = metadata.get('header', None)
            if kwds is None:
                kwds = Header()
                metadata['header'] = kwds
        else:
            kwds = Header()

        try:
            self._get_header(image_pil, kwds)
        except Exception as e:
            self.logger.warning("Failed to get image metadata: {!r}".format(e))

        # convert to working color profile, if can
        if self.clr_mgr.can_profile():
            image_pil = self.clr_mgr.profile_to_working_pil(image_pil, kwds)

        # convert from PIL to numpy
        data_np = np.array(image_pil)
        return data_np

    def _imresize(self, data, new_wd, new_ht, method='bilinear'):
        # TODO: take into account the method parameter

        image_pil = Image.fromarray(data)
        image_pil = image_pil.resize((new_wd, new_ht), Image.BICUBIC)
        newdata = np.array(image_pil)

        return newdata


RGBFileHandler = PillowFileHandler
