import csv
from itertools import count, groupby
import json

from . import backends
from .constants import default_index

def prepare_backend(args):
    if args.backend == 'local':
        backend = backends.local.LocalBackend()
    elif args.backend == 'gridengine':
        backend = backends.gridengine.GridEngineBackend()
    elif args.backend == 'slurm':
        backend = backends.slurm.SlurmBackend()
    else:
        raise NotImplementedError('Invalid backend')

    return backend

def load_jobfile(jobfile_path):
    with open(jobfile_path, 'r') as file:
        job_records = json.load(file)
    # json stores all keys as strings, so we convert to ints
    jobs = {int(id_): record[0] for id_, record in job_records.items()}
    tags = {int(id_): record[1] for id_, record in job_records.items()}
    return jobs, tags

def save_jobfile(jobs, jobfile_path, tag=None):
    with open(jobfile_path, "w+") as jobfile:
        json.dump(jobs, jobfile)

def load_jobindex():
    try:
        with open(default_index, 'r', newline='') as job_index:
            csv_reader = csv.reader(job_index, delimiter=',', quotechar='|')
            index = {job_entry[0]: job_entry[1:] for job_entry in csv_reader}
    except IOError:
        index = {}
    return index

def update_jobindex(job_entries, append=True):
    mode = 'w+' if not append else 'a+'
    with open(default_index, mode, newline='') as job_index:
        csv_writer = csv.writer(job_index, delimiter=',', quotechar='|')
        csv_writer.writerows(job_entries)

def condense_ids(id_list):
    G = (list(x) for _, x in groupby(id_list, lambda x, c=count(): next(c) - x))
    return ",".join("-".join(map(str, (g[0], g[-1])[:len(g)])) for g in G)

def expand_ids(tasklist):
    return [i for r in _generate_id_ranges(tasklist) for i in r]

def _generate_id_ranges(tasklist):
    task_blocks = tasklist.split(',')
    for task_block in task_blocks:
        if ':' in task_block:
            task_block, step = task_block.split(':')
            step = int(step)
        else:
            step = 1
        if '-' in task_block:
            first, last = map(int, task_block.split('-'))
        else:
            first = int(task_block)
            last = first
        yield range(first, last + 1, step)
