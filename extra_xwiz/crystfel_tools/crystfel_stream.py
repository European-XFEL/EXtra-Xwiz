"""Module for reading CrystFEL stream file."""

from typing import TextIO

chunk_tmp_dict = {
    'file_name': "",
    'event': -1,
    'hit': -1,
    'indexed_by': "none",
    'n_indexing_tries': -1,
    'photon_energy_eV': -1,
    'beam_divergence': -1,
    'beam_bandwidth': -1,
    'average_camera_length': -1,
    'num_peaks': -1,
    'peak_resolution': -1,
    'peaks': None,
    'crystal': None
}

peak_tmp_dict = {
    'fs': -1,
    'ss': -1,
    '1/d': -1,
    'intensity': -1,
    'panel': ""
}

crystal_tmp_dict = {
    'cell_parameters': None,
    'astar': None,
    'bstar': None,
    'cstar': None,
    'lattice_type': "",
    'centering': "",
    'unique_axis': "",
    'profile_radius': -1,
    'final_residual': -1,
    'det_shift': None,
    'diffraction_resolution_limit': -1,
    'num_reflections': -1,
    'num_saturated_reflections': -1,
    'num_implausible_reflections': -1,
    'reflections': None
}

reflections_tmp_dict = {
    'h': 0,
    'k': 0,
    'l': 0,
    'I': 0,
    'sigma_I': 0,
    'peak': -1,
    'background': -1,
    'fs': -1,
    'ss': -1,
    'panel': ""
}

chunk_pars_type = {
    'hit': int,
    'indexed_by': str,
    'n_indexing_tries': int,
    'photon_energy_eV': float,
    'beam_divergence': float,
    'beam_bandwidth': float,
    'average_camera_length': float,
    'num_peaks': int,
    'peak_resolution': float
}

crystal_pars_type = {
    'lattice_type': str,
    'centering': str,
    'unique_axis': str,
    'profile_radius': float,
    'diffraction_resolution_limit': float,
    'num_reflections': int,
    'num_saturated_reflections': int,
    'num_implausible_reflections': int
}


def read_crystfel_stream(stream: TextIO) -> dict:
    """Read CrystFEL stream file into a dictionary with values for each
    frame.

    Parameters
    ----------
    stream : TextIO
        Content of the CrystFEL stream file.

    Returns
    -------
    dict
        A dictionary  with a tuple of file name and frame number as keys
        matched to the dictionaries with peakfinder and indexer results.
    """
    fr_data = {}

    in_chunk = False
    in_peaks = False
    in_crystal = False
    in_reflections = False

    for line in stream:
        if in_chunk:
            if line.startswith('----- End chunk -----'):
                fr_key = (curr_fr_data['file_name'], curr_fr_data['event'])
                fr_data[fr_key] = curr_fr_data
                in_chunk = False
            elif in_peaks:
                if line.startswith('End of peak list'):
                    in_peaks = False
                elif not line.startswith('  fs/px'):
                    curr_fr_data['peaks'].append(peak_tmp_dict.copy())
                    peak_dict = curr_fr_data['peaks'][-1]
                    peak_data = line.split()
                    peak_dict['fs'] = float(peak_data[0])
                    peak_dict['ss'] = float(peak_data[1])
                    peak_dict['1/d'] = float(peak_data[2])
                    peak_dict['intensity'] = float(peak_data[3])
                    peak_dict['panel'] = peak_data[4]
            elif line.startswith('Peaks from peak search'):
                in_peaks = True
                curr_fr_data['peaks'] = list()
            elif in_crystal:
                if line.startswith('--- End crystal'):
                    in_crystal = False
                elif in_reflections:
                    if line.startswith('End of reflections'):
                        in_reflections = False
                    elif not line.startswith('   h    k    l'):
                        curr_fr_data['crystal']['reflections'].append(
                            reflections_tmp_dict.copy())
                        refl_dict = curr_fr_data['crystal']['reflections'][-1]
                        refl_data = line.split()
                        refl_dict['h'] = int(refl_data[0])
                        refl_dict['k'] = int(refl_data[1])
                        refl_dict['l'] = int(refl_data[2])
                        refl_dict['I'] = float(refl_data[3])
                        refl_dict['sigma_I'] = float(refl_data[4])
                        refl_dict['peak'] = float(refl_data[5])
                        refl_dict['background'] = float(refl_data[6])
                        refl_dict['fs'] = float(refl_data[7])
                        refl_dict['ss'] = float(refl_data[8])
                        refl_dict['panel'] = refl_data[9]
                elif line.startswith('Reflections measured after indexing'):
                    in_reflections = True
                    curr_fr_data['crystal']['reflections'] = list()
                else:
                    crystal_dict = curr_fr_data['crystal']
                    for par_name, par_type in crystal_pars_type.items():
                        if line.startswith(par_name):
                            crystal_dict[par_name] = par_type(line.split()[2])
                            break
                    else:
                        if line.startswith("Cell parameters"):
                            cell_pars = [
                                float(line.split()[i])
                                for i in [2, 3, 4, 6, 7, 8]
                            ]
                            crystal_dict['cell_parameters'] = cell_pars
                        elif line.startswith("predict_refine/final_residual"):
                            crystal_dict['final_residual'] = float(
                                line.split()[2]
                            )
                        elif line.startswith("predict_refine/det_shift"):
                            det_shift = [
                                float(line.split()[i]) for i in [3, 6]
                            ]
                            crystal_dict['det_shift'] = det_shift
                        else:
                            for par_name in ['astar', 'bstar', 'cstar']:
                                if line.startswith(par_name):
                                    par_val = [
                                        float(line.split()[i])
                                        for i in [2, 3, 4]
                                    ]
                                    crystal_dict[par_name] = par_val
                                    break
            elif line.startswith('--- Begin crystal'):
                in_crystal = True
                curr_fr_data['crystal'] = crystal_tmp_dict.copy()
            else:
                for par_name, par_type in chunk_pars_type.items():
                    if line.startswith(par_name):
                        curr_fr_data[par_name] = par_type(line.split()[2])
                        break
                else:
                    if line.startswith("Image filename:"):
                        curr_fr_data['file_name'] = line.split()[2]
                    elif line.startswith("Event:"):
                        curr_fr_data['event'] = int(line.split('//')[1].strip())
        elif line.startswith('----- Begin chunk -----'):
            in_chunk = True
            curr_fr_data = chunk_tmp_dict.copy()

    return fr_data
