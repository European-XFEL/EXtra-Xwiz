"""
Internal module for converting EuXFEL detectors masks between HDF5 and
CrystFEL geometry files.
"""

# Standard library imports
import os
import re
import warnings

# Third party imports
import h5py
import numpy as np

# Local imports
from . import decomposition as dc
from . import detector_info as di
from . import mask_exceptions as mce


class MaskConverter:

    modes_avail = ('hd52geom', 'geom2hd5')
    write_modes = ('replace', 'add')

    def __init__(self, hd5file, geofile, run_mode, write_mode,
                 hd5path, hd5entry, detector, data_type, invert):
        """Construct a mask converter."""

        self._hd5file = hd5file
        self._hd5path = hd5path
        self._hd5entry = hd5entry
        self._geofile = geofile
        self._run_mode = run_mode
        self._write_mode = write_mode
        self._detector = detector
        self._data_type = data_type
        self._invert = invert

        if self._detector is None or self._data_type is None:
            self._guess_detector_info()

        if self._run_mode not in type(self).modes_avail:
            raise mce.MaskConvError(
                f"ERROR: Unknown MaskConverter run mode: "
                f"{self._run_mode}.",
                'conv_init_wrong_mode')
        if self._write_mode not in type(self).write_modes:
            raise mce.MaskConvError(
                f"ERROR: Unknown MaskConverter write mode: "
                f"{self._write_mode}.",
                'conv_init_wrong_mode')
        if self._detector not in di.detector_info.keys():
            raise mce.MaskConvError(
                f"ERROR: Unknown detector: {self._detector}.",
                'conv_init_unknown_detector')
        if self._data_type not in di.detector_info[self._detector].keys():
            raise mce.MaskConvError(
                f"ERROR: Missing info on '{self._data_type}' "
                f"data type for detector {self._detector}.",
                'conv_init_missing_data_type')

        self._det_info = di.detector_info[self._detector][self._data_type]

        self._read_mask()

    @property
    def mask(self):
        """Mask as numpy array accessible from outside."""
        return np.copy(self.__mask)

    def convert(self):
        self._convert_mask()
        self._write_mask()

    def _guess_detector_info(self):
        """
        Try to guess detector and data type if not provided by the user.
        """

        detectors = []
        data_types = []
        str_search_info_detector = ""
        str_search_info_data_type = ""

        if self._detector is None:
            detectors = list(di.detector_info.keys())
            str_search_info_detector = "detector name"
        else:
            detectors.append(self._detector)

        if self._data_type is None:
            data_types = di.get_data_types(detectors)
            if str_search_info_detector:
                str_search_info_data_type += " and"
            str_search_info_data_type += " data type"
        else:
            data_types.append(self._data_type)

        fits_di = np.zeros((len(detectors), len(data_types)), dtype=bool)
        fits_hd5 = np.copy(fits_di)
        fits_geo_detectors = np.zeros((len(detectors), 1), dtype=bool)
        fits_geo_data_types = np.zeros((1, len(data_types)), dtype=bool)

        # Check available information in detector_info
        for i_d, detector in enumerate(detectors):
            if detector in di.detector_info.keys():
                for i_t, data_type in enumerate(data_types):
                    if data_type in di.detector_info[detector].keys():
                        fits_di[i_d, i_t] = True

        # Compare mask shapes to the mask in HD5 file, if any
        try:
            with h5py.File(self._hd5file, 'r') as f_hd5:
                hd5_mask = f_hd5.get(self._hd5path)
                hd5_mask_shape = hd5_mask.shape
                hd5_mask_ndim = hd5_mask.ndim
        except (OSError, TypeError):
            # In case mask could not be read from HDF5 - do nothing
            pass
        else:
            for i_d, detector in enumerate(detectors):
                for i_t, data_type in enumerate(data_types):
                    mask_shape = di.detector_info[detector][data_type]['shape']
                    if all([
                        fits_di[i_d, i_t],
                        hd5_mask_shape[-len(mask_shape):] == mask_shape,
                        hd5_mask_ndim <= (len(mask_shape) + 1)
                    ]):
                        fits_hd5[i_d, i_t] = True

        # Check geometry file, if any
        # 'True' for detector or data type provided by user
        if self._detector is not None:
            fits_geo_detectors[detectors.index(self._detector)] = True
        if self._data_type is not None:
            fits_geo_data_types[data_types.index(self._data_type)] = True

        # Help function to prevent repeated code of re.search
        def geo_re_search(str_in):
            for i_d, detector in enumerate(detectors):
                if re.search(detector, str_in, re.IGNORECASE) is not None:
                    fits_geo_detectors[i_d, 0] = True
            for i_t, data_type in enumerate(data_types):
                if re.search(data_type, str_in, re.IGNORECASE) is not None:
                    fits_geo_data_types[0, i_t] = True

        # Match geometry file name
        geo_re_search(self._geofile)
        fits_geo = np.dot(fits_geo_detectors, fits_geo_data_types)

        if np.count_nonzero(fits_geo) != 1:
            # Search geometry file content
            if os.path.exists(self._geofile):
                with open(self._geofile, 'r') as f_geo:
                    geo_data = f_geo.read().replace('\n', ' ')
                    geo_re_search(geo_data)

            fits_geo = np.dot(fits_geo_detectors, fits_geo_data_types)

        # Gather search results
        fits_AND = np.logical_and(fits_di,
                                  np.logical_and(fits_hd5, fits_geo))
        fits_OR = np.logical_and(fits_di,
                                 np.logical_or(fits_hd5, fits_geo))
        str_found_in = ""

        if np.count_nonzero(fits_AND) == 1:
            fits_res = fits_AND
        elif np.count_nonzero(fits_OR) == 1:
            fits_res = fits_OR
        else:
            raise mce.MaskConvError(
                f"ERROR: {str_search_info_detector}"
                f"{str_search_info_data_type} could not be "
                f"guessed from the HD5 or geometry file.",
                'cannot_guess_detector_info')

        i_detector, j_data_type = np.transpose(np.nonzero(fits_res))[0]
        self._detector = detectors[i_detector]
        if str_search_info_detector:
            str_search_info_detector += f" as {detectors[i_detector]}"
        self._data_type = data_types[j_data_type]
        if str_search_info_data_type:
            str_search_info_data_type += f" as {data_types[j_data_type]}"

        if np.count_nonzero(fits_hd5) == 1:
            str_found_in = "HD5 file"
        elif np.count_nonzero(fits_geo) == 1:
            str_found_in = "geometry file"
        else:
            str_found_in = "HD5 and geometry files"

        warnings.warn(f"INFO: Estimated {str_search_info_detector}"
                      f"{str_search_info_data_type} from the information "
                      f"in {str_found_in}.")

    def _read_mask_hd5(self):
        """Read mask from the hdf5 file to numpy array."""

        res_mask = None
        mask_shape = self._det_info['shape']

        try:
            with h5py.File(self._hd5file, 'r') as f_hd5:
                hd5mask = f_hd5.get(self._hd5path)

                # Chack shape of the HDF5 mask
                mce.MaskConvError.check_hd5mask(
                    hd5mask, mask_shape, self._hd5entry)

                # Remove 'n_data' dimension, convert to np.array
                if hd5mask.ndim > len(mask_shape):
                    hd5mask = hd5mask[self._hd5entry]
                else:
                    hd5mask = np.array(hd5mask)
        # Catch an exception if HDF5 file cannot be accessed
        except OSError as err:
            err_file, err_n, err_mes = re.search(
                r".*?name = '(.*?)'"
                r".*?errno = (.*?),"
                r".*?error message = '(.*?)'",
                err.args[0]).groups()
            if err_n == '2':
                raise mce.MaskConvError(
                    f"ERROR: {err_mes} : {err_file}.",
                    'read_hd5_cannot_access_file') from err
            else:
                raise
        # Catch an exception of missing path in HDF5 file
        except TypeError as err:
            if 'NoneType' in err.args[0]:
                raise mce.MaskConvError(
                    f"ERROR: Could not read '{self._hd5path}' "
                    f"from '{self._hd5file}'.",
                    'read_hd5_wrong_path') from err
            else:
                raise
        else:
            # Convert mask values to True (masked) and False
            res_mask = self._det_info['read_mask'](hd5mask)

            if self._invert:
                res_mask = np.logical_not(res_mask)

        return res_mask

    def _read_mask_geo(self):
        """Read mask from the geometry file to rectangles dictionary."""

        res_dict = {}
        bad_dict = {}

        try:
            f_geo = open(self._geofile, 'r')
        # Catch file not found exception:
        except FileNotFoundError as err:
            if err.args[0] == 2:
                raise mce.MaskConvError(
                    f"ERROR: No such geomentry file: {self._geofile}.",
                    'read_geo_no_file') from err
            else:
                raise
        else:
            with f_geo:
                for line in f_geo:
                    # To ignore comments:
                    line = line.partition(';')[0].rstrip()

                    m_obj = re.search(r"bad_(.+)/(\S+)\s*=\s*(\S+)", line)
                    if m_obj is not None:
                        area, var, val = m_obj.groups()
                        if area not in bad_dict.keys():
                            bad_dict[area] = {
                                'min_fs': -1,
                                'max_fs': -1,
                                'min_ss': -1,
                                'max_ss': -1,
                                'panel': 'all'
                            }
                        if var == 'panel':
                            bad_dict[area][var] = val

                            # Check whether panel value is expected
                            if len(self._det_info['shape']) != 3:
                                raise mce.MaskConvError(
                                    f"ERROR: Geometry file - panel "
                                    f"description ({val}) not expected "
                                    f"for {self._data_type} data.",
                                    'read_geo_wrong_panel')

                            # Check <val> to be suitable description
                            # of a panel and asic
                            m_obj = re.match(r"(p\d+)(a\d+)", val)
                            if (m_obj is None
                                or m_obj.group(1) not in
                                    self._det_info['panel_names']
                                or m_obj.group(2) not in
                                    self._det_info['asic_names']):
                                raise mce.MaskConvError(
                                    f"ERROR: Geometry file - not suitable "
                                    f"panel description: {val}.",
                                    'read_geo_wrong_panel')
                        elif var in bad_dict[area].keys():
                            bad_dict[area][var] = int(val)
                        else:
                            warnings.warn(
                                f"WARNING: Geometry file - unsupported "
                                f"mask variable: {var} in bad_{area}.")

        # Check if rectangle information is complete
        i = 0
        for area in bad_dict.keys():
            if all([
                bad_dict[area]['min_fs'] >= 0,
                bad_dict[area]['max_fs'] >= 0,
                bad_dict[area]['min_ss'] >= 0,
                bad_dict[area]['max_ss'] >= 0
            ]):
                res_dict[i] = bad_dict[area]
                i += 1
            else:
                warnings.warn(
                    f"WARNING: Geometry file - incomplete information "
                    f"for bad_{area}.")

        return res_dict

    def _read_mask(self):
        """Read mask from hdf5 or geometry file, depending on mode."""

        self.__mask = np.zeros(self._det_info['shape'], dtype=bool)
        self.__rect = {}

        if self._run_mode == "hd52geom":
            self.__mask = self._read_mask_hd5()

            # Reduce mask in case of write option 'add'
            if self._write_mode == 'add' and os.path.exists(self._geofile):
                self.__rect = self._read_mask_geo()
                reduce_mask = self._convert_rectd2ndarr()
                self.__mask = np.logical_and(self.__mask,
                                             np.logical_not(reduce_mask))
                self.__rect = {}

        elif self._run_mode == "geom2hd5":
            self.__rect = self._read_mask_geo()

            # Read also mask from HD5 in case of write option 'add'
            if (self._write_mode == 'add'
                    and os.path.exists(self._hd5file)):
                self.__mask = self._read_mask_hd5()

    def _convert_ndarr2rectd(self):
        """Convert mask from numpy array to rectangles dictionary."""

        res_dict = {}

        # Help function to turn decomposition algorithm output into a
        # rectangles dictionary
        def rect2dict(rect, panel):
            d = {}
            rect2dict.n_area = getattr(rect2dict, 'n_area', -1)
            for rec in rect:
                rect2dict.n_area += 1
                d[rect2dict.n_area] = {
                    'min_fs': rec[0][0],
                    'max_fs': rec[0][1] - 1,  # Mask range is inclusive
                    'min_ss': rec[1][0],
                    'max_ss': rec[1][1] - 1,  # Mask range is inclusive
                    'panel': panel
                }
            return d

        # First check for regions to be excluded in all panels:
        if self.__mask.ndim == 3:
            panel_all = self.mask[0]
            for i in range(1, self.__mask.shape[0]):
                panel_all = np.logical_and(panel_all, self.__mask[i])
        else:
            panel_all = self.mask

        is_panel_all_empty = np.array_equiv(panel_all, False)
        if not is_panel_all_empty:
            res_dict.update(rect2dict(dc.gdm(panel_all), 'all'))

        if self.__mask.ndim == 3:
            panels = self._det_info['panel_names']
            asics = self._det_info['asic_names']
            asic_range = self._det_info['asic_range']

            # Loop over all panels:
            for i in range(len(panels)):
                if is_panel_all_empty:
                    panel_i = self.__mask[i]
                else:
                    panel_i = np.copy(self.__mask[i])
                    panel_i = np.logical_and(panel_i,
                                             np.logical_not(panel_all))

                # Loop over all asics in the panel:
                for j in range(len(asics)):
                    asic_j = np.zeros(panel_i.shape, dtype=bool)
                    asic_j[asic_range[i][j]] = True
                    panel_i_asic_j = np.logical_and(panel_i, asic_j)
                    res_dict.update(
                        rect2dict(dc.gdm(panel_i_asic_j),
                                  f"{panels[i]}{asics[j]}"))

        return res_dict

    def _convert_rectd2ndarr(self):
        """Convert mask from rectangles dictionary to numpy array."""

        shape = self._det_info['shape']
        res_mask = np.zeros(shape, dtype=bool)

        for area in self.__rect.keys():
            slice_ss = slice(self.__rect[area]['min_ss'],
                             self.__rect[area]['max_ss'] + 1)
            slice_fs = slice(self.__rect[area]['min_fs'],
                             self.__rect[area]['max_fs'] + 1)
            if self.__rect[area]['panel'] == 'all':
                if len(shape) == 3:
                    res_mask[:, slice_ss, slice_fs] = True
                else:
                    res_mask[slice_ss, slice_fs] = True
            else:
                assert len(shape) == 3, (
                    "Convert rectd2ndarr: mask has to be dimensions 3 to "
                    "apply rectangles per panel.")

                panel, asic = re.match(
                    r"(p\d+)(a\d+)", self.__rect[area]['panel']).groups()
                panel_n = self._det_info['panel_names'].index(panel)
                asic_n = self._det_info['asic_names'].index(asic)
                asic_range = self._det_info['asic_range'][panel_n][asic_n]

                slice_ss_in_asic = slice(
                    max(slice_ss.start, asic_range[0].start),
                    min(slice_ss.stop, asic_range[0].stop))
                slice_fs_in_asic = slice(
                    max(slice_fs.start, asic_range[1].start),
                    min(slice_fs.stop, asic_range[1].stop))

                res_mask[panel_n, slice_ss_in_asic, slice_fs_in_asic] = True

        return res_mask

    def _convert_mask(self):
        """Convert mask depending on mode."""
        if self._run_mode == "hd52geom":
            self.__rect = self._convert_ndarr2rectd()
        elif self._run_mode == "geom2hd5":
            rect_mask = self._convert_rectd2ndarr()
            self.__mask = np.logical_or(self.__mask, rect_mask)

    def _write_mask_hd5(self):
        """Write converted mask to the HD5 file."""

        mask_shape = self.__mask.shape
        mask_tmp = self.__mask
        if self._invert:
            mask_tmp = np.logical_not(mask_tmp)
        mask_to_write = self._det_info['write_mask'](mask_tmp)

        try:
            with h5py.File(self._hd5file, 'a') as f_hd5:
                if self._hd5path in f_hd5:
                    hd5mask = f_hd5[self._hd5path]

                    # Check shape of the existing HDF5 mask
                    mce.MaskConvError.check_hd5mask(
                        hd5mask, mask_shape, self._hd5entry)

                    if hd5mask.ndim > len(mask_shape):
                        hd5mask[self._hd5entry] = mask_to_write
                    else:
                        hd5mask[...] = mask_to_write
                else:
                    f_hd5.create_dataset(self._hd5path, data=mask_to_write)
        # Catch exception in case of no write permission to the file
        # TODO: Test also with VDS file
        except OSError as err:
            err_file, err_n = re.search(
                r".*?name = '(.*?)'"
                r".*?errno = (.*?)",
                err.args[0]).groups()
            if err_n == '17':
                raise mce.MaskConvError(
                    f"ERROR: Could not open '{err_file}' for "
                    f"writing - check file permissions.",
                    'write_hd5_no_permission') from err
            else:
                raise

    def _write_mask_geo(self):
        """Write converted mask to the geometry file."""

        text_before = text_after = []
        n_area_start = 0

        # Store and process content of the existing geometry file
        if os.path.exists(self._geofile):
            with open(self._geofile, 'r') as f_geo:
                contents = f_geo.readlines()

            idx_write = len(contents)
            for i, line in enumerate(contents):

                # Search for the mask information
                if re.search(r"bad_", line) is not None:
                    idx_write = i + 1

                    # Comment existing mask for the 'replace' mode
                    if all([
                        self._write_mode == 'replace',
                        re.search(r"bad_", line.partition(';')[0]) is not None
                    ]):
                        contents[i] = "; " + line

                    # Check existing numbered 'bad_area's
                    sa_obj = re.search(r"bad_area(\d+)/", line)
                    if sa_obj is not None:
                        sa_num = int(sa_obj.group(1))
                        n_area_start = max(n_area_start, sa_num + 1)

                # Search for the 'rigid_group'
                # (to put mask before it in case no 'bad_' area found)
                if all([
                    idx_write == len(contents),
                    re.search(r"rigid_group", line) is not None
                ]):
                    idx_write = i

            text_before = contents[:idx_write]
            text_after = contents[idx_write:]

        # Format mask as a list of text lines
        text_mask = []
        if (text_before
                and text_before[-1].strip() != ""):
            text_mask.append("\n")

        for area in self.__rect:
            for dim in ['min_fs', 'max_fs', 'min_ss', 'max_ss']:
                text_mask.append(
                    f"bad_area{n_area_start + area}/{dim} = "
                    f"{self.__rect[area][dim]}\n")
            if self.__rect[area]['panel'] != 'all':
                text_mask.append(
                    f"bad_area{n_area_start + area}/panel = "
                    f"{self.__rect[area]['panel']}\n")
            text_mask.append("\n")

        text_write = "".join(text_before + text_mask + text_after)

        try:
            with open(self._geofile, 'w') as f_geo:
                f_geo.write(text_write)
        # Catch exception in case of no write permission to the file
        except PermissionError as err:
            if err.args[0] == 13:
                raise mce.MaskConvError(
                    f"ERROR: Could not open '{self._geofile}' "
                    f"for writing - check file permissions.",
                    'write_geo_no_permission') from err
            else:
                raise

    def _write_mask(self):
        """Write the mask depending on mode."""
        if self._run_mode == "hd52geom":
            self._write_mask_geo()
        elif self._run_mode == "geom2hd5":
            self._write_mask_hd5()
