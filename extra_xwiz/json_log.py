"""Functions to store pipeline operation log into json files."""
import json
import xarray as xr


def save_partialator_foms(
    partialator_foms: xr.DataArray, folder: str
) -> None:
    """Store partialator foms as a json file in specified folder."""
    foms_dict = {}
    for dataset in partialator_foms.coords['dataset'].values:
        foms_dict[dataset] = {}
        for shell in partialator_foms.coords['shell'].values:
            foms_dict[dataset][shell] = {}
            for fom in partialator_foms.coords['fom'].values:
                foms_dict[dataset][shell][fom] = partialator_foms.loc[
                    dataset, shell, fom
                ].item()
    with open(f"{folder}/datasets_foms.json", 'w') as j_out:
        json.dump(foms_dict, j_out)
