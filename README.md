# onager

Lightweight python library for launching experiments and tuning hyperparameters, either locally or on a cluster.

By Cameron Allen & Neev Parikh

-----

## Installation

Currently requires Python 3.7+

Stable version:
```
pip install onager
```

Development version:
```
pip install git+https://github.com/camall3n/onager.git
```

-----

## Developer Documentation

- [System Overview](docs/system-overview.md)
  - [Multiworker design doc](docs/multiworker.md)

-----

## Usage

### Prelaunch
Prelaunch generates commands and adds them to a jobfile. The default behavior also prints the list of generated commands.

```
onager prelaunch +jobname experiment1 +command myscript +arg --learningrate 0.1 0.01 0.001 +arg --batchsize 32 64 128 +tag --mytag
```

Output:
```
myscript --learningrate 0.1 --batchsize 32 --mytag experiment1_1__learningrate_0.1__batchsize_32
myscript --learningrate 0.01 --batchsize 32 --mytag experiment1_2__learningrate_0.01__batchsize_32
myscript --learningrate 0.001 --batchsize 32 --mytag experiment1_3__learningrate_0.001__batchsize_32
myscript --learningrate 0.1 --batchsize 64 --mytag experiment1_4__learningrate_0.1__batchsize_64
myscript --learningrate 0.01 --batchsize 64 --mytag experiment1_5__learningrate_0.01__batchsize_64
myscript --learningrate 0.001 --batchsize 64 --mytag experiment1_6__learningrate_0.001__batchsize_64
myscript --learningrate 0.1 --batchsize 128 --mytag experiment1_7__learningrate_0.1__batchsize_128
myscript --learningrate 0.01 --batchsize 128 --mytag experiment1_8__learningrate_0.01__batchsize_128
myscript --learningrate 0.001 --batchsize 128 --mytag experiment1_9__learningrate_0.001__batchsize_128
```

Argument types:
```
+arg --argname [value ...]
```
- Add an argument with zero or more mutually exclusive values

```
+randarg --argname type min_val max_val
```
- Add an argument with a randomly sampled value
- Supported types:
  - `int`: Sample an integer between min_val and max_val (inclusive)
  - `float`: Sample a float between min_val and max_val
    - Optional: Add `log` parameter to sample in logarithmic space: `+randarg --lr float 0.00001 0.1 log`
    - Float values are formatted with 5 decimal places for readability
    - Very small (<0.001) or large (≥10000) numbers use scientific notation
  - `choice`: Sample from a list of options. Format: `+randarg --opt choice [option1,option2,option3]` or `+randarg --opt choice option1,option2,option3`
- Each +randarg will generate a single random value that will be treated as a fixed value in the grid search
- Use with +trials to generate multiple random configurations in a single command

```
+trials N
```
- Specify the number of random trials to generate when using +randarg (default: 1)
- When N > 1, N different random combinations will be sampled from all +randarg parameters
- Each trial is treated as a grid dimension and is combined with regular grid parameters (+arg)

```
+pos-arg value [value ...]
```

- Add a positional argument with one or more mutually exclusive values

```
+flag --flagname
```

- Add a boolean argument that will be toggled in the resulting commands


Options:
```
+tag [TAG]
```

- Passes a unique tag string for each run to the specified arg in the command, i.e. `--tag <tag-contents>`.

```
+tag-args --argname [--argname ...]
```

- Specifies which args go into the unique `<tag-contents>`. Default is all provided args.

```
+no-tag-number
```

- Disable auto-numbering when generating tags


### Launch
Launch reads a jobfile (or accepts a single user-specified command), and launches the associated job(s) on the specified backend. Currently onager supports 'slurm' and 'gridengine' as cluster backends, and 'local' for running on a single host.

```
onager launch --backend slurm --jobname experiment1
```

Output:
```
sbatch -J experiment1 -t 0-01:00:00 -n 1 -p batch --mem=2G -o .onager/logs/slurm/%x_%A_%a.o -e .onager/logs/slurm/%x_%A_%a.e --parsable --array=1,2,3,4,5,6,7,8,9 .onager/scripts/experiment1/wrapper.sh
```

Options:
```
--max-tasks MAX_TASKS
```

- Maximum number of simultaneous tasks on backend. This argument can be used to limit the number of jobs to avoid flooding the cluster or to override the default parallelism of the local backend. When `--tasks-per-node` is greater than 1, `--max-tasks` governs the number of nodes, and `--max-tasks-per-node` governs the number of tasks per node.

```
--tasks-per-node TASKS_PER_NODE
```

- Enables running multiple tasks in parallel on the backend by spawning another "local" backend on each node.

```
--max-tasks-per-node MAX_TASKS_PER_NODE
```

- Maximum number of simultaneous tasks to process with each node.

### Config
By default, onager will simply launch commands for you. If you need to do additional initialization or cleanup, you can configure it using the `config` subcommand and writing to the `header` or `footer` fields of the appropriate backend.

```
onager config --write slurm header "module load python/3.7.4
module load cuda/10.2
module load cudnn/7.6.5
source ./venv/bin/activate"
```

### History
History is useful for displaying information about previously executed onager commands. It allows for filtering with `--launch`, `--prelaunch`, and `--no-dry-run`, as well as restricting the output to the most recent N entries (`-n N`) or entries `--since` a particular date (and optional time).

```
onager history
```

Output:
```
  id  date        time          jobname    mode       args
----  ----------  ------------  ---------  ---------  -------------------------------------------------------------------------------
   0  2022.12.15  11:52:06.184  exp_01     prelaunch  +jobname exp_01 +command myscript --name foo +arg --seed 1 2 3 --lr 0.003 0.001
   1  2022.12.15  12:05:29.798  exp_01     launch     --jobname exp_01 --backend local --duration 00:03:00 --cpus 2 --mem 10
   2  2022.12.15  12:05:40.920  exp_01     launch     --jobname exp_01 --backend local --duration 00:30:00 --cpus 4 --mem 8 --dry-run
   3  2022.12.15  12:05:50.410  exp_02     prelaunch  +jobname exp_02 +command myscript --name foo +arg --seed 4 5 6 --lr 0.003 0.001
   4  2022.12.15  14:43:55.837  exp_02     launch     --jobname exp_02 --backend local --duration 00:30:00 --cpus 4 --mem 8
```

To see the details and full command for a specific command ID or jobname, use `--details ID` or `--details JOBNAME`. The ID `-1` gives details for the most recent command.

```
onager history --details -1
```

Output:
```
  id  date        time          jobname    mode
----  ----------  ------------  ---------  ---------
   4  2022.12.15  14:43:55.837  exp_02     launch

onager launch --jobname exp_02 --backend local --duration 00:30:00 --cpus 4 --mem 8
```

### List
List is useful for displaying information about launched jobs and tasks, since the backend will typically assign the same jobname to all subtasks.

```
onager list
```

Output:
```
  job_id    task_id  jobname      command                                                                                                   tag
--------  ---------  -----------  --------------------------------------------------------------------------------------------------------  ------------------------------------------------
13438569          1  experiment1  'myscript --learningrate 0.1 --batchsize 32 --mytag experiment1_1__learningrate_0.1__batchsize_32'        experiment1_1__learningrate_0.1__batchsize_32
13438569          2  experiment1  'myscript --learningrate 0.01 --batchsize 32 --mytag experiment1_2__learningrate_0.01__batchsize_32'      experiment1_2__learningrate_0.01__batchsize_32
13438569          3  experiment1  'myscript --learningrate 0.001 --batchsize 32 --mytag experiment1_3__learningrate_0.001__batchsize_32'    experiment1_3__learningrate_0.001__batchsize_32
13438569          4  experiment1  'myscript --learningrate 0.1 --batchsize 64 --mytag experiment1_4__learningrate_0.1__batchsize_64'        experiment1_4__learningrate_0.1__batchsize_64
13438569          5  experiment1  'myscript --learningrate 0.01 --batchsize 64 --mytag experiment1_5__learningrate_0.01__batchsize_64'      experiment1_5__learningrate_0.01__batchsize_64
13438569          6  experiment1  'myscript --learningrate 0.001 --batchsize 64 --mytag experiment1_6__learningrate_0.001__batchsize_64'    experiment1_6__learningrate_0.001__batchsize_64
13438569          7  experiment1  'myscript --learningrate 0.1 --batchsize 128 --mytag experiment1_7__learningrate_0.1__batchsize_128'      experiment1_7__learningrate_0.1__batchsize_128
13438569          8  experiment1  'myscript --learningrate 0.01 --batchsize 128 --mytag experiment1_8__learningrate_0.01__batchsize_128'    experiment1_8__learningrate_0.01__batchsize_128
13438569          9  experiment1  'myscript --learningrate 0.001 --batchsize 128 --mytag experiment1_9__learningrate_0.001__batchsize_128'  experiment1_9__learningrate_0.001__batchsize_128
```

### Cancel
Quickly cancel the specified jobs (and subtasks) on the backend

```
onager cancel --backend slurm --jobid 13438569 --tasklist 1-3:1,5,8-9
```

Output:
```
scancel 13438569_1 13438569_2 13438569_3 13438569_5 13438569_8 13438569_9
```

### Re-launch
Launch also supports re-running selected subtasks from a previously launched job

```
onager launch --backend slurm --jobname experiment1 --tasklist 1-3:1,5,8-9
```

Output:
```
sbatch -J experiment1 -t 0-01:00:00 -n 1 -p batch --mem=2G -o .onager/logs/slurm/%x_%A_%a.o -e .onager/logs/slurm/%x_%A_%a.e --parsable --array=1-3:1,5,8-9 .onager/scripts/experiment1/wrapper.sh
```

### Help
For a list of the available subcommands and their respective arguments, use the `help` subcommand:

```
onager help
onager help launch
```

-----

## Example: MNIST
Let's consider a toy MNIST example to concretely see how this would be used in a more realistic setting.

### Setup
If you have the repository cloned, install the `examples/mnist/requirements.txt` in some virtualenv.
You now have a pretty standard setup for an existing project. To use onager, all you have to do is
`pip install onager`.

```
cd examples/mnist
source venv/bin/activate
pip install onager
```

### Prelaunch
Say we need to tune the hyperparameters on our very important MNIST example. We say we want to tune
the learning rate between these values `0.3, 1.0, 3.0` and the batch-size between `32, 64`. We need
to run this for at least 3 seeds each, giving us a total of 18 runs in this experiment. We can use
the prelaunch to generate these commands using the following command:

```
onager prelaunch +command "python mnist.py --epochs 1 --gamma 0.7 --no-cuda" +jobname mnist_lr_bs +arg --lr 0.3 1.0 3.0 +arg --batch-size 32 64 +arg --seed {0..2} +tag --run-tag
```

Output:
```
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --lr 0.3 --batch-size 32 --seed 0 --run-tag mnist_lr_bs_01__lr_0.3__batchsize_32__seed_0
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --lr 1.0 --batch-size 32 --seed 0 --run-tag mnist_lr_bs_02__lr_1.0__batchsize_32__seed_0
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --lr 3.0 --batch-size 32 --seed 0 --run-tag mnist_lr_bs_03__lr_3.0__batchsize_32__seed_0
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --lr 0.3 --batch-size 64 --seed 0 --run-tag mnist_lr_bs_04__lr_0.3__batchsize_64__seed_0
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --lr 1.0 --batch-size 64 --seed 0 --run-tag mnist_lr_bs_05__lr_1.0__batchsize_64__seed_0
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --lr 3.0 --batch-size 64 --seed 0 --run-tag mnist_lr_bs_06__lr_3.0__batchsize_64__seed_0
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --lr 0.3 --batch-size 32 --seed 1 --run-tag mnist_lr_bs_07__lr_0.3__batchsize_32__seed_1
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --lr 1.0 --batch-size 32 --seed 1 --run-tag mnist_lr_bs_08__lr_1.0__batchsize_32__seed_1
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --lr 3.0 --batch-size 32 --seed 1 --run-tag mnist_lr_bs_09__lr_3.0__batchsize_32__seed_1
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --lr 0.3 --batch-size 64 --seed 1 --run-tag mnist_lr_bs_10__lr_0.3__batchsize_64__seed_1
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --lr 1.0 --batch-size 64 --seed 1 --run-tag mnist_lr_bs_11__lr_1.0__batchsize_64__seed_1
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --lr 3.0 --batch-size 64 --seed 1 --run-tag mnist_lr_bs_12__lr_3.0__batchsize_64__seed_1
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --lr 0.3 --batch-size 32 --seed 2 --run-tag mnist_lr_bs_13__lr_0.3__batchsize_32__seed_2
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --lr 1.0 --batch-size 32 --seed 2 --run-tag mnist_lr_bs_14__lr_1.0__batchsize_32__seed_2
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --lr 3.0 --batch-size 32 --seed 2 --run-tag mnist_lr_bs_15__lr_3.0__batchsize_32__seed_2
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --lr 0.3 --batch-size 64 --seed 2 --run-tag mnist_lr_bs_16__lr_0.3__batchsize_64__seed_2
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --lr 1.0 --batch-size 64 --seed 2 --run-tag mnist_lr_bs_17__lr_1.0__batchsize_64__seed_2
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --lr 3.0 --batch-size 64 --seed 2 --run-tag mnist_lr_bs_18__lr_3.0__batchsize_64__seed_2
```

Note that the `--run-tag` is a simple identifier the program accepts that uniquely tags each
run of the script. This could to be used to create a unique directory to store loss/reward etc.

Now this command will generate a `jobs.json` in the default location for the *jobfile*. It is
located here: `.onager/scripts/mnist_lr_bs/jobs.json`. You can customize this by specifying a custom
`+jobfile` argument. See `onager help prelaunch` for more details.

### Launch

Say we want to run this on a Slurm backend somewhere. We need to run prelaunch as described above
and then you simply specify what kind of hardware you need. More details can be found via
`onager help launch`. For this example, we used:

```
onager launch --backend slurm --jobname mnist_lr_bs --cpus 2 --mem 5 --venv ./venv/ --duration 00:30:00 -max 5
```

We specified the same jobname as we did during prelaunch. This lets onager find the right jobfile
automatically. If you'd like, you can provide a custom jobfile too.

And that's it! We now can check `.onager/logs/slurm/` for our logs. To keep track of which jobs are
scheduled, we can use `onager list`. Say you want to cancel some jobs; an easy way to cancel is via
`onager cancel`

-----

## Example: Managing GridEngine 'Eqw' errors
Sometimes GridEngine inexplicably fails to launch certain jobs, causing them to permanently remain in 'Eqw' state. The only known fix for this is to re-run the jobs, but that requires manually parsing the `qstat` output and resubmitting only the affected jobs.

We can use onager to automatically handle this problem for us.

```
cd ..
onager prelaunch +command ./myscript +pos-arg {0001..1000} +tag +jobname test-eqw
onager launch --backend gridengine --duration 00:02:00 --jobname test-eqw --venv mnist/venv/
```

Suppose `qstat` gives the following output:
```
job-ID  prior   name       user         state submit/start at     queue                          slots ja-task-ID
-----------------------------------------------------------------------------------------------------------------
[...]
2323537 0.50500 test-eqw   csal         r     06/12/2020 00:31:27 short.q@mblade1309.cs.brown.ed     1 327
2323537 0.50500 test-eqw   csal         r     06/12/2020 00:31:27 short.q@mblade1309.cs.brown.ed     1 328
2323537 0.50500 test-eqw   csal         r     06/12/2020 00:31:27 short.q@mblade1309.cs.brown.ed     1 329
2323537 0.50500 test-eqw   csal         r     06/12/2020 00:31:34 short.q@dblade41.cs.brown.edu      1 330
2323537 0.50500 test-eqw   csal         Eqw   06/12/2020 00:31:09                                    1 35-40:1,57,138-201:1
```

We can cancel the 'Eqw' jobs and re-launch them with:
```
onager cancel --backend gridengine --jobid 2323537 --tasklist 35-40:1,57,138-201:1
onager launch --backend gridengine --duration 00:02:00 --jobname test-eqw --venv mnist/venv/ --tasklist 35-40:1,57,138-201:1
```

If there are multiple ranges (as in this example), onager will automatically handle splitting those ranges up into separate `qdel` and `qsub` commands.

-----

## Example: Launching Jobs Locally
Sometimes a cluster is overkill, and you just want to launch jobs locally. Onager supports this as well.

```
onager prelaunch +jobname experiment1 +command ./myscript +pos-arg {1..10} +tag
onager launch --backend local --jobname experiment1 --maxtasks 4
```

### Using Random Search

If you want to use random search instead of grid search, you can use `+randarg` to sample random values:

```
onager prelaunch +command "python mnist.py --epochs 1 --gamma 0.7 --no-cuda" +jobname mnist_random +randarg --lr float 0.1 5.0 +randarg --batch-size int 16 128 +randarg --seed int 0 10 +tag --run-tag
```

This will generate a single command with randomly sampled values for learning rate (between 0.1 and 5.0), batch size (between 16 and 128 as an integer), and seed (between 0 and 10 as an integer).

To generate multiple random trials in a single command, use the `+trials` parameter:

```
onager prelaunch +command "python mnist.py --epochs 1 --gamma 0.7 --no-cuda" +jobname mnist_random +randarg --lr float 0.1 5.0 +randarg --batch-size int 16 128 +randarg --seed int 0 10 +trials 10 +tag --run-tag
```

This will create 10 different commands, each with a different random combination of learning rate, batch size, and seed values.

You can also combine random parameters with grid search parameters:

```
onager prelaunch +command "python mnist.py --epochs 1 --gamma 0.7 --no-cuda" +jobname mnist_mixed +randarg --lr float 0.1 5.0 +arg --optimizer adam sgd rmsprop +trials 5 +tag --run-tag
```

This will generate 15 commands (5 random trials × 3 optimizer options), where each command has a randomly sampled learning rate combined with one of the optimizer options.

You can also randomly select from a predefined list of choices:

```
onager prelaunch +command "python mnist.py --epochs 1 --gamma 0.7 --no-cuda" +jobname mnist_choice +randarg --optimizer choice [adam,sgd,rmsprop] 0 +arg --lr 0.001 0.01 0.1 +trials 2 +tag --run-tag
```

Output (example):
```
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --optimizer sgd --lr 0.001 --run-tag mnist_choice_1__optimizer_sgd__lr_0.001
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --optimizer sgd --lr 0.01 --run-tag mnist_choice_2__optimizer_sgd__lr_0.01
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --optimizer sgd --lr 0.1 --run-tag mnist_choice_3__optimizer_sgd__lr_0.1
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --optimizer adam --lr 0.001 --run-tag mnist_choice_4__optimizer_adam__lr_0.001
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --optimizer adam --lr 0.01 --run-tag mnist_choice_5__optimizer_adam__lr_0.01
python mnist.py --epochs 1 --gamma 0.7 --no-cuda --optimizer adam --lr 0.1 --run-tag mnist_choice_6__optimizer_adam__lr_0.1
```

### Examples with Random Parameters

#### Linear vs Log Sampling
For parameters that span multiple orders of magnitude, log sampling often gives better coverage:

```
# Linear sampling (uniform across the range)
onager prelaunch +command python train.py +jobname linear_sample +randarg --lr float 0.00001 0.1 +trials 5 +tag

# Log sampling (more samples in lower ranges)
onager prelaunch +command python train.py +jobname log_sample +randarg --lr float 0.00001 0.1 log +trials 5 +tag
```

The log sampling will concentrate more values in the lower range, which is often desirable for learning rates that typically work better in ranges like 0.001-0.01 than in ranges like 0.05-0.1.

#### Random Choice Parameters
Sample from a discrete set of options:

```
onager prelaunch +command python train.py +jobname optimizer_test +randarg --optimizer choice [adam,sgd,rmsprop] +trials 3 +tag
```

#### Large Parameter Ranges with Scientific Notation
Scientific notation is automatically used for very small or large values:

```
# Small values use scientific notation in tags
onager prelaunch +command python train.py +jobname small_values +randarg --weight_decay float 0.0000001 0.00001 +tag

# Large values use scientific notation in tags
onager prelaunch +command python train.py +jobname large_values +randarg --scale float 10000 1000000 +tag
```

#### Multiple Random Parameters with Multiple Trials
Combine multiple random parameters with multiple trials to explore a wide range of configurations:

```
onager prelaunch +command python train.py +jobname hyperparameter_search \
  +randarg --lr float 0.0001 0.01 log \
  +randarg --dropout float 0.1 0.5 \
  +randarg --optimizer choice [adam,sgd,rmsprop] \
  +randarg --batch_size int 16 128 \
  +trials 10 +tag
```

This would generate 10 different random combinations of learning rate, dropout rate, optimizer, and batch size.