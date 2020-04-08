"""Utilities"""

from getpass import getuser
from glob import glob
import subprocess
import time


def calc_progress(out_logs):
    for log in out_logs:
        with open(log, "r") as f:
            ll = f.readlines()
        if not 'indexable' in ll[-1]:
            continue
        print(log, ll[-1][4])
    print()


def wait_or_cancel(job_id, n_nodes, time_limit):
    """ Loop until queue is empty or time-limit reached """
    print(' waiting for job-array', job_id)
    time.sleep(3)
    out_logs = glob('slurm-*.out')
    max_time = '0:00'
    n_tasks = n_nodes
    while n_tasks > 0 and max_time <= time_limit:
        queue = subprocess.check_output(['squeue', '-u', getuser()])
        tasks = queue.decode('utf-8').split('\n')
        n_tasks = len(tasks) - 2   # header-line + trailing '\n' always present
        times = [ln.split()[5] for ln in tasks[1:-1]]
        if n_tasks > 0:
            max_time = max(times)
        calc_progress(out_logs)
        time.sleep(1)
