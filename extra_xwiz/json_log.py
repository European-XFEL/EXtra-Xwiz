"""Functions to store pipeline operation log into json files."""
import json
import math
import os.path as osp
import xarray as xr

from . import crystfel_info as cri
from . import workflow as wf

def save_slurm_info(
    job_id: int, n_nodes: int, job_duration: str, folder: str
) -> None:
    """Store SLURM job information as a json file in the job folder."""
    job_dict = {
        'job_id': job_id,
        'n_nodes': n_nodes,
        'job_duration': job_duration
    }
    with open(f"{folder}/slurm_info.json", 'w') as j_out:
        json.dump(job_dict, j_out)


class WorkflowJsonLog:

    def __init__(self, xwiz_workflow: 'wf.Workflow'):
        self.log = {}
        self.xwiz = xwiz_workflow

    def save_data(self):
        self.log['data'] = {}
        self.log['data']['proposal'] = self.xwiz.data_proposal
        self.log['data']['runs'] = self.xwiz.data_runs
        self.log['data']['n_frames_offset'] = self.xwiz.n_frames_offset
        self.log['data']['n_frames_max'] = self.xwiz.n_frames_max
        self.log['data']['n_frames_percent'] = self.xwiz.n_frames_percent
        self.log['data']['n_frames_total'] = self.xwiz.n_frames_total

    def save_crystfel_ver(self):
        self.log['crystfel'] = {}
        self.log['crystfel']['version'] = self.xwiz.crystfel_version

    def save_crystfel_job(self, job_name: str, folder: str):
        crystfel_version = self.log['crystfel']['version']
        self.log['crystfel'][job_name] = job_log = {}
        job_log['geometry_file'] = osp.abspath(self.xwiz.geometry)
        job_log['cell_file'] = osp.abspath(self.xwiz.cell_file)
        if cri.crystfel_info[crystfel_version]['contain_harvest']:
            with open(f"{folder}/crystfel_harvest.json", 'r') as j_harv:
                job_log['parameters'] = json.load(j_harv)
        else:
            job_log['parameters'] = "?"
        job_log['cell_tolerance'] = self.xwiz.cell_tolerance

    def save_partialator(self):
        self.log['partialator'] = part_log = {}
        part_log['point_group'] = self.xwiz.point_group
        part_log['scaling_model'] = self.xwiz.scale_model
        part_log['scaling_iterations'] = self.xwiz.scale_iter
        part_log['max_adu'] = self.xwiz.max_adu
        if self.xwiz.run_partialator_split:
            part_log['split'] = self.xwiz.partialator_split_config

    def save_partialator_foms(self, partialator_foms: xr.DataArray) -> None:
        """Store partialator foms as a json file in specified folder."""
        self.log['results'] = foms_dict = {}
        for dataset in partialator_foms.coords['dataset'].values:
            foms_dict[dataset] = {}
            for shell in partialator_foms.coords['shell'].values:
                foms_dict[dataset][shell] = {}
                for fom in partialator_foms.coords['fom'].values:
                    fom_value = partialator_foms.loc[dataset,shell,fom].item()
                    if math.isnan(fom_value):
                        fom_value = None
                    foms_dict[dataset][shell][fom] = fom_value

    def write_json(self):
        with open(f"output_xwiz.json", 'w') as j_out:
            json.dump(self.log, j_out)
