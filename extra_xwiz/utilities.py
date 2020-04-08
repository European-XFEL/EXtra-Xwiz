"""Utilities"""

from getpass import getuser
from glob import glob
import subprocess
import time


def seconds(tm_str):
    units = tm_str.split(':')
    secs = 0
    for i in range(len(units)):
        j = len(units) - 1 - i
        secs += int(units[j]) * pow(60, i)
    # print(secs)
    return secs


def print_progress_bar(i, n, length=80, fill='█'):
    percent = '{0:.1f}'.format(100 * (i / float(n)))
    filled_len = int(length * i // n)
    bar = fill * filled_len + '-' * (length - filled_len)
    print('\rProgress: |%s| %s%% complete' % (bar, percent), end='\r')


def calc_progress(out_logs, n_total):
    n_current = []
    for log in out_logs:
        with open(log, "r") as f:
            ll = f.readlines()
        if not 'indexable' in ll[-1]:
            continue
        # print(log, ll[-1].split()[4])
        n_current.append(int(ll[-1].split()[4]))
    if len(n_current) > 0:
        n_slowest = min(n_current)
        print_progress_bar(n_slowest, n_total, length=50)


def wait_or_cancel(job_id, n_nodes, n_total, time_limit):
    """ Loop until queue is empty or time-limit reached """
    print(' Waiting for job-array', job_id)
    time.sleep(3)
    out_logs = glob('slurm-*.out')
    max_time = '0:00'
    n_tasks = n_nodes
    while n_tasks > 0 and seconds(max_time) <= seconds(time_limit):
        queue = subprocess.check_output(['squeue', '-u', getuser()])
        tasks = queue.decode('utf-8').split('\n')
        n_tasks = len(tasks) - 2   # header-line + trailing '\n' always present
        times = [ln.split()[5] for ln in tasks[1:-1]]
        if n_tasks > 0:
            max_time = max(times)
        calc_progress(out_logs, n_total)
        time.sleep(1)
