from collections import OrderedDict
import os
import random
import re
from warnings import warn
import sys
import math

from .utils import load_jobfile, save_jobfile
from .constants import SEP, WSEP, FLAG_ON, FLAG_OFF
from .history import add_new_history_entry

def _is_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

def _is_int(value):
    try:
        int(value)
        return True
    except ValueError:
        return False

def _sample_random_value(param_type, min_val, max_val, sampling_space='linear'):
    """Sample a random value based on the parameter type.
    
    Args:
        param_type: Type of parameter (int, float, or choice)
        min_val: Minimum value or choices for 'choice' type (as comma-separated string in brackets or directly)
        max_val: Maximum value or not used for 'choice' type
        sampling_space: Space to sample in ('linear' or 'log') for float parameters
    
    Returns:
        A string representation of the sampled value
    """
    if param_type.lower() == 'choice':
        # Handle choice from a list of values
        choices = []
        
        # Check if format is [choice1,choice2,choice3]
        if min_val.startswith('[') and min_val.endswith(']'):
            choices_str = min_val[1:-1]  # Remove brackets
            choices = [choice.strip() for choice in choices_str.split(',') if choice.strip()]
        else:
            # If not in bracket format, split by commas directly
            choices = [choice.strip() for choice in min_val.split(',') if choice.strip()]
        
        if choices:
            return random.choice(choices)
                
        warn(RuntimeWarning(f"No valid choices found in {min_val}"))
        return min_val  # fallback
    
    elif param_type.lower() == 'int':
        # Case: integer range
        try:
            min_int = int(min_val)
            max_int = int(max_val)
            return str(random.randint(min_int, max_int))
        except ValueError:
            warn(RuntimeWarning(f"Could not convert {min_val} or {max_val} to int"))
            return min_val
    
    elif param_type.lower() == 'float':
        # Case: float range
        try:
            min_float = float(min_val)
            max_float = float(max_val)
            
            # Generate random value based on sampling space
            if sampling_space.lower() == 'log':
                # Ensure positive values for log sampling
                if min_float <= 0:
                    warn(RuntimeWarning(f"Log sampling requires positive values. Min value {min_float} replaced with 1e-10"))
                    min_float = 1e-10
                
                # Sample in log space
                log_min = math.log(min_float)
                log_max = math.log(max_float)
                random_value = math.exp(log_min + random.random() * (log_max - log_min))
            else:
                # Linear sampling
                random_value = min_float + random.random() * (max_float - min_float)
            
            # Use scientific notation for very small or large numbers
            if abs(random_value) < 0.001 or abs(random_value) >= 10000:
                return '{:.5e}'.format(random_value)
            else:
                return '{:.5f}'.format(random_value)
        except ValueError:
            warn(RuntimeWarning(f"Could not convert {min_val} or {max_val} to float"))
            return min_val
    
    else:
        # Invalid type
        warn(RuntimeWarning(f"Unknown parameter type: {param_type}"))
        return min_val

def meta_launch(args):
    base_cmd = args.command

    if args.arg_mode == 'argparse':
        VAR_SEP = ' '
    elif args.arg_mode == 'hydra':
        VAR_SEP = '='
    else:
        raise NotImplementedError(f'Unknown arg mode: {args.arg_mode}')

    # Regular grid search arguments
    if args.arg is not None:
        variables = OrderedDict({arglist[0]: arglist[1:] for arglist in args.arg})
    else:
        variables = OrderedDict()

    if args.pos_arg is not None:
        pos_variables = args.pos_arg
    else:
        pos_variables = []

    if args.flag is not None:
        flag_variables = args.flag
    else:
        flag_variables = []

    # Process random arguments and generate trials
    rand_variables = OrderedDict()
    trial_commands = []  # Store commands for trials
    
    if args.randarg is not None:
        # Get number of trials to generate
        num_trials = args.trials if hasattr(args, 'trials') else 1
        
        # Store random parameter specifications
        for rand_arglist in args.randarg:
            # Validate the arguments based on parameter type
            if len(rand_arglist) < 3:
                error_msg = f"Error: +randarg requires at least 3 arguments: parameter_name type value_or_choices\n"
                error_msg += f"Got: {' '.join(rand_arglist)}\n"
                error_msg += "Examples:\n"
                error_msg += "  +randarg --lr float 0.001 0.1     # For float range: min and max values\n"
                error_msg += "  +randarg --bs int 16 128          # For int range: min and max values\n"
                error_msg += "  +randarg --opt choice [adam,sgd]  # For choice: list of options (no max value needed)"
                sys.stderr.write(error_msg + "\n")
                sys.exit(1)
                
            arg_name = rand_arglist[0]
            param_type = rand_arglist[1].lower()
            
            # Different validation logic based on parameter type
            if param_type == 'choice':
                choices = rand_arglist[2]
                
                # Validate choices format
                if not (choices.startswith('[') and choices.endswith(']')) and ',' not in choices:
                    error_msg = f"Error: Choices for 'choice' type must be a comma-separated list in brackets or separated by commas.\n"
                    error_msg += f"Got: {choices}\n"
                    error_msg += "Examples: [adam,sgd,rmsprop] or adam,sgd,rmsprop"
                    sys.stderr.write(error_msg + "\n")
                    sys.exit(1)
                    
                # Check if there are any choices
                choice_list = []
                if choices.startswith('[') and choices.endswith(']'):
                    choice_list = [choice.strip() for choice in choices[1:-1].split(',') if choice.strip()]
                else:
                    choice_list = [choice.strip() for choice in choices.split(',') if choice.strip()]
                    
                if not choice_list:
                    error_msg = f"Error: Empty choices list provided for parameter '{arg_name}'.\n"
                    error_msg += "You must provide at least one choice."
                    sys.stderr.write(error_msg + "\n")
                    sys.exit(1)
                    
                # For choice, max_val isn't used, so set it to empty string
                min_val = choices
                max_val = ""
                
                # Warn about extra arguments for choice type
                if len(rand_arglist) > 3:
                    extra_args = ' '.join(rand_arglist[3:])
                    warn(RuntimeWarning(f"Warning: Ignoring extra arguments for choice type: {extra_args}"))
                
            elif param_type in ['int', 'float']:
                if len(rand_arglist) < 4:
                    error_msg = f"Error: +randarg with '{param_type}' type requires 4 arguments: parameter_name {param_type} min_value max_value\n"
                    error_msg += f"Got: {' '.join(rand_arglist)}\n"
                    error_msg += f"Example: +randarg --lr {param_type} 0.001 0.1"
                    sys.stderr.write(error_msg + "\n")
                    sys.exit(1)
                    
                min_val = rand_arglist[2]
                max_val = rand_arglist[3]
                
                # Check for optional sampling space parameter (for float type)
                sampling_space = 'linear'  # default
                if param_type == 'float' and len(rand_arglist) > 4 and rand_arglist[4].lower() == 'log':
                    sampling_space = 'log'
                    
                    # If there are more arguments beyond the sampling space
                    if len(rand_arglist) > 5:
                        extra_args = ' '.join(rand_arglist[5:])
                        warn(RuntimeWarning(f"Warning: Ignoring extra arguments for +randarg: {extra_args}"))
                elif len(rand_arglist) > 4:
                    # Warn about extra arguments that are not the sampling space
                    extra_args = ' '.join(rand_arglist[4:])
                    warn(RuntimeWarning(f"Warning: Ignoring extra arguments for +randarg: {extra_args}"))
                
                # Additional validation for numeric types
                try:
                    if param_type == 'int':
                        min_num = int(min_val)
                        max_num = int(max_val)
                    else:  # float
                        min_num = float(min_val)
                        max_num = float(max_val)
                        
                        # For log sampling, ensure min > 0
                        if sampling_space == 'log' and min_num <= 0:
                            warn(RuntimeWarning(f"Log sampling requires positive values. Min value will be adjusted when sampling."))
                        
                    if min_num >= max_num:
                        error_msg = f"Error: min_value must be less than max_value for +randarg.\n"
                        error_msg += f"Got: min={min_val}, max={max_val}"
                        sys.stderr.write(error_msg + "\n")
                        sys.exit(1)
                except ValueError:
                    error_msg = f"Error: Could not convert min/max values to {param_type}.\n"
                    error_msg += f"Got: min={min_val}, max={max_val}"
                    sys.stderr.write(error_msg + "\n")
                    sys.exit(1)
            
            else:
                # Invalid parameter type
                error_msg = f"Error: Invalid parameter type '{param_type}' for +randarg.\n"
                error_msg += "Supported types: int, float, choice"
                sys.stderr.write(error_msg + "\n")
                sys.exit(1)
                
            # Store the validated parameter specification
            rand_variables[arg_name] = (param_type, min_val, max_val, sampling_space if param_type == 'float' else 'linear')
        
        # Generate specified number of random trials
        if num_trials > 1:
            trial_commands = []
            # Add a special trial parameter to ensure one command per trial
            variables['__trial__'] = list(range(num_trials))
            
            # Generate trial-based commands
            for trial_idx in range(num_trials):
                # Create a map of random values for this trial
                trial_values = OrderedDict()
                
                # Generate random values for all parameters for this trial
                for arg_name, (param_type, min_val, max_val, sampling_space) in rand_variables.items():
                    random_value = _sample_random_value(param_type, min_val, max_val, sampling_space)
                    trial_values[arg_name] = random_value
                
                # Need to create a copy of the original variables for this trial
                trial_variables = variables.copy()
                
                # Add grid search based on trial_values for all random parameters
                cmd_prefix_list = [base_cmd]
                
                # First add positional arguments
                for value_list in pos_variables:
                    cmd_prefix_list = [prefix + ' {}' for prefix in cmd_prefix_list]
                    cmd_prefix_list = [prefix.format(v) for v in value_list for prefix in cmd_prefix_list]
                
                # Then add all grid search parameters
                for key, value_list in trial_variables.items():
                    # Skip the virtual '__trial__' parameter 
                    if key == '__trial__':
                        continue
                        
                    cmd_prefix_list = [prefix + ' ' + key for prefix in cmd_prefix_list]
                    if len(value_list) > 0:
                        cmd_prefix_list = [prefix + VAR_SEP + '{}' for prefix in cmd_prefix_list]
                        cmd_prefix_list = [prefix.format(v) for v in value_list for prefix in cmd_prefix_list]
                
                # Then add all random parameters for this trial
                for key, value in trial_values.items():
                    cmd_prefix_list = [prefix + ' ' + key + VAR_SEP + value for prefix in cmd_prefix_list]
                
                # Add commands for this trial
                trial_commands.extend(cmd_prefix_list)
        else:
            # Just generate one random value per parameter
            for arg_name, (param_type, min_val, max_val, sampling_space) in rand_variables.items():
                variables[arg_name] = [_sample_random_value(param_type, min_val, max_val, sampling_space)]

    base_cmd_args = list(variables.keys())
    
    # If we have trials with random values, use those instead of normal grid processing
    if trial_commands:
        cmd_prefix_list = trial_commands
    else:
        cmd_prefix_list = [base_cmd]

        # Normal grid search processing (for when no trials or only 1 trial)
        if args.tag == '':
            raise ValueError("+tag cannot be an empty string")

        if args.tag is not None:
            cmd_suffix_list = ['']
            if args.tag_args is None:
                # Remove '__trial__' from tag args if it exists
                args.tag_args = [arg for arg in base_cmd_args if arg != '__trial__']
            else:
                for tag_arg in args.tag_args:
                    if tag_arg not in base_cmd_args:
                        warn(RuntimeWarning("{} is not a command arg: {}".format(tag_arg,
                            base_cmd_args)))

        # Positional arguments
        for value_list in pos_variables:
            cmd_prefix_list = [prefix + ' {}' for prefix in cmd_prefix_list]
            cmd_prefix_list = [prefix.format(v) for v in value_list for prefix in cmd_prefix_list]
            if args.tag is not None:
                value_slot = WSEP + '{}'
                cmd_suffix_list = [
                    suffix + value_slot for suffix in cmd_suffix_list
                ]
                cmd_suffix_list = [
                    suffix.format(v) for v in value_list for suffix in cmd_suffix_list
                ]

        # Optional arguments (includes random args when num_trials=1)
        for key, value_list in variables.items():
            # Skip the virtual '__trial__' parameter if it exists
            if key == '__trial__':
                continue
                
            cmd_prefix_list = [prefix + ' ' + key for prefix in cmd_prefix_list]
            if len(value_list) > 0:
                cmd_prefix_list = [prefix + VAR_SEP + '{}' for prefix in cmd_prefix_list]
                cmd_prefix_list = [prefix.format(v) for v in value_list for prefix in cmd_prefix_list]
            if args.tag is not None:
                if key in args.tag_args:
                    value_slot = SEP + '{}' if len(value_list) > 0 else ''
                    keyname = key.replace('_', '').replace('-', '').replace('=','_').replace('/','.')
                    cmd_suffix_list = [
                        suffix + WSEP + keyname + value_slot for suffix in cmd_suffix_list
                    ]
                    if len(value_list) > 0:
                        cmd_suffix_list = [
                            suffix.format(v) for v in value_list for suffix in cmd_suffix_list
                        ]
                        
                        # Format float values in tag args to 5 decimal places if they're from random float parameters
                        if args.tag is not None and key in args.tag_args and key in rand_variables and rand_variables[key][0] == 'float':
                            # Create new suffix list with formatted float values
                            new_suffix_list = []
                            for suffix in cmd_suffix_list:
                                # Find the value in the suffix
                                # The pattern looks for keyname + SEP + value
                                pattern = keyname + SEP + r'([0-9.e+-]+)'
                                match = re.search(pattern, suffix)
                                if match:
                                    try:
                                        float_val = float(match.group(1))
                                        # Use scientific notation for very small or large numbers
                                        if abs(float_val) < 0.001 or abs(float_val) >= 10000:
                                            formatted_val = '{:.5e}'.format(float_val)
                                        else:
                                            formatted_val = '{:.5f}'.format(float_val)
                                        # Replace the original value with the formatted one
                                        new_suffix = suffix.replace(match.group(1), formatted_val)
                                        new_suffix_list.append(new_suffix)
                                    except ValueError:
                                        new_suffix_list.append(suffix)  # Keep original if not a valid float
                                else:
                                    new_suffix_list.append(suffix)  # Keep original if pattern not found
                                    
                            cmd_suffix_list = new_suffix_list
                else:
                    cmd_suffix_list = [suffix for v in value_list for suffix in cmd_suffix_list]

        # Flag/Boolean arguments
        for flag in flag_variables:
            cmd_prefix_list = [prefix + ' {}' for prefix in cmd_prefix_list] + cmd_prefix_list
            cmd_prefix_list = [
                prefix.format(flag) if '{}' in prefix else prefix
                for prefix in cmd_prefix_list
            ]
            if args.tag is not None:
                cmd_suffix_list = [
                    suffix + '{}' for suffix in cmd_suffix_list
                ]
                cmd_suffix_list = [
                    suffix.format(WSEP + s + flag.replace(FLAG_OFF, '').replace(FLAG_ON, ''))
                    for s in [FLAG_ON, FLAG_OFF]
                    for suffix in cmd_suffix_list
                ]

    # Process tag for all commands
    if args.tag is not None and not trial_commands:
        if args.no_tag_number:
            tag_list = [args.jobname + suffix for suffix in cmd_suffix_list]
        else:
            jobfile_path = args.jobfile.format(jobname=args.jobname)
            os.makedirs(os.path.dirname(jobfile_path), exist_ok=True)
            if args.append:
                cmds, tags = load_jobfile(jobfile_path)
                start_jobid = max(cmds.keys()) + 1
            else:
                start_jobid = 1

            n_digits = len(str(start_jobid + len(cmd_suffix_list) - 1))
            tag_number_format = '{{:0{0}d}}'.format(n_digits)
            tag_list = [
                args.jobname + SEP + tag_number_format.format(i) + suffix
                for (i, suffix) in enumerate(cmd_suffix_list, start_jobid)
            ]

        cmd_prefix_list = [
            (prefix + ' ' + args.tag + VAR_SEP + suffix)
            for (prefix, suffix) in zip(cmd_prefix_list, tag_list)
        ]
    else:
        # For trial-based random commands, create tags based on trial index
        if trial_commands and args.tag is not None:
            n_digits = len(str(num_trials))
            tag_number_format = '{{:0{0}d}}'.format(n_digits)
            
            new_cmd_list = []
            for i, cmd in enumerate(cmd_prefix_list, 1):
                # Create the components for the tag
                tag_components = []
                
                # 1. Start with the jobname and trial number
                tag_components.append(args.jobname + SEP + tag_number_format.format(i))
                
                # 2. Extract all parameter values from the command
                # First find all positional arguments (they appear without parameter names)
                cmd_parts = cmd.split()
                base_cmd_parts = base_cmd.split()
                
                # Skip the base command to find positional arguments
                pos_values = []
                pos_idx = 0
                param_mode = False
                
                for j, part in enumerate(cmd_parts):
                    # Skip the base command parts
                    if j < len(base_cmd_parts):
                        continue
                        
                    # If this is a parameter name (starts with --), next part is its value
                    if part.startswith('--'):
                        param_mode = True
                        continue
                    
                    # If we're in parameter mode, this is a parameter value
                    if param_mode:
                        param_mode = False
                        continue
                        
                    # This must be a positional argument
                    pos_values.append(part)
                
                # Add positional arguments to tag components
                for pos_idx, pos_value in enumerate(pos_values):
                    if pos_idx < len(pos_variables) and len(pos_variables[pos_idx]) > 0:
                        tag_components.append(f"__pos{pos_idx}__" + SEP + pos_value)
                
                # 3. Extract named parameter values
                # Random parameters
                for arg_name, (param_type, min_val, max_val, sampling_space) in rand_variables.items():
                    match = re.search(r'{}[= ]([^ ]+)'.format(re.escape(arg_name)), cmd)
                    if match:
                        value = match.group(1)
                        # Format float values appropriately
                        if param_type == 'float':
                            try:
                                float_val = float(value)
                                if abs(float_val) < 0.001 or abs(float_val) >= 10000:
                                    value = '{:.5e}'.format(float_val)
                                else:
                                    value = '{:.5f}'.format(float_val)
                            except ValueError:
                                pass
                        
                        # Add to tag components with cleaned parameter name
                        keyname = arg_name.replace('_', '').replace('-', '').replace('=','_').replace('/','.')
                        tag_components.append(keyname + SEP + value)
                
                # Grid parameters
                for arg_name, value_list in variables.items():
                    if arg_name != '__trial__' and len(value_list) > 0:
                        match = re.search(r'{}[= ]([^ ]+)'.format(re.escape(arg_name)), cmd)
                        if match:
                            value = match.group(1)
                            keyname = arg_name.replace('_', '').replace('-', '').replace('=','_').replace('/','.')
                            tag_components.append(keyname + SEP + value)
                
                # 4. Join all tag components with double underscore separator
                tag = WSEP.join(tag_components)
                
                # 5. Add the tag to the command
                new_cmd_list.append(cmd + ' ' + args.tag + VAR_SEP + tag)
            
            cmd_prefix_list = new_cmd_list
            tag_list = [""] * len(cmd_prefix_list)
        else:
            tag_list = [""] * len(cmd_prefix_list)

    jobfile_path = args.jobfile.format(jobname=args.jobname)
    os.makedirs(os.path.dirname(jobfile_path), exist_ok=True)

    if args.append:
        cmds, tags = load_jobfile(jobfile_path)
        start_jobid = max(cmds.keys()) + 1
        jobs = {i: (cmds[i], tags[i]) for i in cmds.keys()}
    else:
        jobs = dict()
        start_jobid = 1

    for i, (cmd,tag) in enumerate(zip(cmd_prefix_list,tag_list), start_jobid):
        if not args.quiet:
            print(cmd)
        jobs[i] = (cmd,tag)

    save_jobfile(jobs, jobfile_path, args.tag)
    add_new_history_entry(jobname=args.jobname, dry_run=False)
