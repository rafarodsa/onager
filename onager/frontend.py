import argparse

from onager import backends, constants

def parse_args(args=None):

    # yapf: disable
    parser = argparse.ArgumentParser(description='',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    subparsers = parser.add_subparsers(required=True, dest='subcommand')


    prelaunch_parser = subparsers.add_parser('prelaunch', prefix_chars='+',
        help='Generate commands based on lists of arguments')
    prelaunch_parser.add_argument('+command', type=str, required=True,
        help='Base command to add args to')
    prelaunch_parser.add_argument('+jobname', type=str, required=True,
        help='Name to label this run with, to be used with onager launch when submitting jobs')
    prelaunch_parser.add_argument('+jobfile', type=str, default=constants.defaultjobfile,
        help='json file to write jobs to. Use when running launch')
    prelaunch_parser.add_argument('+arg-mode', type=str, default='argparse',
        choices=['argparse', 'hydra'], help='Method for joining args with values')
    prelaunch_parser.add_argument('+arg', type=str, action='append', nargs='+',
        metavar=('--argname', 'value'),
        help='Add an argument with zero or more mutually exclusive values')
    prelaunch_parser.add_argument('+randarg', type=str, action='append', nargs='+',
        metavar='RANDARG',
        help='Add an argument with randomly sampled values; type can be:\n'
             ' - int: requires 4 args (--name int min_val max_val)\n'
             ' - float: requires 4 args (--name float min_val max_val [log])\n'
             '   optional "log" parameter enables logarithmic sampling\n'
             ' - choice: requires 3+ args (--name choice [choice1,choice2,...])')
    prelaunch_parser.add_argument('+trials', type=int, default=1,
        help='Number of random trials to generate when using +randarg')
    prelaunch_parser.add_argument('+pos-arg', type=str, action='append', nargs='+',
        metavar=('value', 'value'),
        help='Add a positional argument with one or more mutually exclusive values')
    prelaunch_parser.add_argument('+flag', type=str, action='append', metavar=('--flag'),
        help='Add a boolean argument that will be toggled in the resulting commands')
    prelaunch_parser.add_argument('+tag', type=str, nargs='?', const='--tag',
        help='Passes a unique tag string for each run to the specified arg in the command, i.e. --tag <tag-contents>')
    prelaunch_parser.add_argument('+tag-args', type=str, nargs='+',
        metavar=('--argname'),
        help='Specifies which args go into the unique <tag-contents>. Default is all provided args')
    prelaunch_parser.add_argument('+no-tag-number', action='store_true', dest='no_tag_number',
        help='Disable auto-numbering when generating tags')
    prelaunch_parser.add_argument('+a', '+append', action='store_true', dest='append',
        help='Add more jobs to existing jobfile')
    prelaunch_parser.add_argument('+q', '+quiet', action='store_true', dest='quiet',
        help='Quiet output')


    launch_parser = subparsers.add_parser('launch', help='Launch jobs using the specified backend')
    launch_parser.add_argument('--backend', choices=backends.__all__, required=True,
        help='The backend to use for launching jobs')
    launch_parser.add_argument('--jobname', type=str, required=True,
        help='A name for the job')
    launch_parser.add_argument('--command', type=str, default=None,
        help='Launch a single command instead of using a jobfile')
    launch_parser.add_argument('--jobfile', type=str, default=constants.defaultjobfile,
        help='Path to json file containing dictionary mapping run_ids to commands')
    launch_parser.add_argument('--cpus', type=int, default=1,
        help='Number of CPUs to request')
    launch_parser.add_argument('--gpus', type=int, default=0,
        help='Number of GPUs to request')
    launch_parser.add_argument('--mem', type=int, default=2,
        help='Amount of RAM (in GB) to request per node')
    launch_parser.add_argument('--venv', type=str, default=None,
        help='Path to python virtualenv')
    launch_parser.add_argument('--duration', type=str, default='0-01:00:00',
        help='Duration of job (d-hh:mm:ss)')
    launch_parser.add_argument('--tasklist', type=str, default=None,
        help='Comma separated list of task ID ranges to submit (e.g. "18-22:1,26,29,34-49:3,51")')
    launch_parser.add_argument('--max-tasks', type=int, default=-1,
        help='Maximum number of simultaneous tasks on backend')
    launch_parser.add_argument('--tasks-per-node', type=int, default=1,
        help='How many total tasks to process with each node')
    launch_parser.add_argument('--max-tasks-per-node', type=int, default=-1,
        help='Maximum number of simultaneous tasks to process with each node')
    launch_parser.add_argument('--debug', '--test', action='store_true', dest='debug',
        help="Submit a short-duration, high-priority job to the backend")
    launch_parser.set_defaults(debug=False)
    launch_parser.add_argument('-d','--dry-run', action='store_true',
        help="Don't actually submit jobs to backend")
    launch_parser.set_defaults(dry_run=False)
    launch_parser.add_argument('--hold_jid', type=str, default=None,
        help='Hold job until the specified jobid or jobid_taskid has finished')


    history_parser = subparsers.add_parser('history',
        help='Display command history')
    history_parser.add_argument('--prelaunch', action='store_true', help='Show prelaunch commands')
    history_parser.add_argument('--launch', action='store_true', help='Show launch commands')
    history_parser.add_argument('--no-dry-run', action='store_true', help='Hide dry-run commands')
    history_parser.add_argument('-n', metavar='N', type=int, default=None,
        help='Limit output to the most recent N entries')
    history_parser.add_argument('--since', type=str, nargs='+', metavar=('DATE', 'TIME'),
        default=None, help='Show commands since DATE (YYYY.mm.dd) [and TIME (HH:MM:SS)]')
    history_parser.add_argument('--full', action='store_true', help='Show full commands in table')
    history_parser.add_argument('--details', metavar='ID_or_JOBNAME', default=None,
        help='Show history details for a specific command ID or JOBNAME (or -1 for previous command)')
    history_parser.add_argument('--width', type=int, default=None,
        help='Maximum character width when printing table')


    list_parser = subparsers.add_parser('list',
        help='List previously launched commands by job_id and task_id')
    list_parser.add_argument('-j','--jobid', type=str,
        help='The job ID to list commands for')
    list_parser.add_argument('-t','--tasklist', type=str, default=None,
        help='Comma separated list of task IDs (e.g. "18-22:1,26,29,34-49:1")')
    list_parser.add_argument('--hide', type=str, nargs='+', default=None,
        help='Hide the specified columns')


    cancel_parser = subparsers.add_parser('cancel',
        help='Cancel previously submitted jobs/tasks on the specified backend')
    cancel_parser.add_argument('--backend', choices=backends.__all__, required=True,
        help='The backend to use for canceling jobs/tasks')
    cancel_parser.add_argument('-j','--jobid', type=str, required=True,
        help='The job ID to delete tasks from')
    cancel_parser.add_argument('-t','--tasklist', type=str, default=None,
        help='Comma separated list of task IDs (e.g. "18-22:1,26,29,34-49:1")')
    cancel_parser.add_argument('-d','--dry-run', action='store_true',
        help="Don't actually cancel jobs on backend")
    cancel_parser.set_defaults(dry_run=False)
    cancel_parser.add_argument('-q', '--quiet', action='store_true', help='Quiet output')


    config_parser = subparsers.add_parser('config',
        help='Configure onager settings')
    config_parser.add_argument('--global', action='store_true', dest='global_',
        help='Write to (or read from *only*) the global config: ~/.onagerconfig')
    config_parser.set_defaults(global_=False)
    config_parser.add_argument('--local', action='store_true',
        help='Write to (or read from *only*) the local config: .onager/config')
    config_parser.set_defaults(local=False)
    config_parser.add_argument('--read', action='store_true',
        help='Display all variables in config file, and their values')
    config_parser.set_defaults(list_=False)
    config_parser.add_argument('--write', type=str, nargs=3, action='append', dest='write',
        metavar=('backend', 'key', 'value'),
        help='Set configuration variables to the specified values')


    help_parser = subparsers.add_parser('help',
        help='Show usage information for a subcommand')
    help_parser.add_argument('help_command', type=str, nargs='?',
        choices=['prelaunch', 'launch', 'history', 'list', 'cancel', 'config', 'help'],
        help='Get help about a subcommand')
    # yapf: enable

    if args is None:
        return parser.parse_known_args()
    else:
        return parser.parse_known_args(args)
