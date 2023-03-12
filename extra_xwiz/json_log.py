"""Functions to store pipeline operation log into json files."""
import json
import math
import xarray as xr


def save_partialator_foms(
    partialator_foms: xr.DataArray, folder: str
) -> None:
    """Store partialator foms as a json file in the specified folder."""
    foms_dict = {}
    for dataset in partialator_foms.coords['dataset'].values:
        foms_dict[dataset] = {}
        for shell in partialator_foms.coords['shell'].values:
            foms_dict[dataset][shell] = {}
            for fom in partialator_foms.coords['fom'].values:
                fom_value = partialator_foms.loc[dataset, shell, fom].item()
                if math.isnan(fom_value):
                    fom_value = None
                foms_dict[dataset][shell][fom] = fom_value
    with open(f"{folder}/datasets_foms.json", 'w') as j_out:
        json.dump(foms_dict, j_out)


def save_frame_counts(
    frame_counts: xr.DataArray, folder: str
) -> None:
    """Store frame rates as a json file in the specified folder."""
    frame_counts_dict = {}
    for dataset in frame_counts.coords['dataset'].values:
        frame_counts_dict[dataset] = {}
        for count in frame_counts.coords['frame_count'].values:
            count_value = frame_counts.loc[dataset, count].item()
            if 'N_' in count:
                count_value = int(count_value)
            if math.isnan(count_value):
                count_value = None 
            frame_counts_dict[dataset][count] = count_value
    with open(f"{folder}/frame_counts.json", 'w') as j_out:
        json.dump(frame_counts_dict, j_out)
