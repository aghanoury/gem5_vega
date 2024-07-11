# Import necessary libraries
import argparse
import concurrent.futures
import json
import os
import random
import subprocess
import sys
import threading
import time
from datetime import datetime
from itertools import product


parser = argparse.ArgumentParser()
parser.add_argument(
    "-d", "--dry-run", action="store_true", default=False, help="Dry run the command"
)
parser.add_argument(
    "-b",
    "--bench",
    "--benchmark",
    nargs="+",
    help="Benchmark to run[^1^][1]. Without this, program runs all by default",
)
parser.add_argument(
    "-r",
    "--redirect",
    action="store_false",
    default=True,
    help="Redirect outputs to terminal",
)
parser.add_argument(
    "--run_name",
    type=str,
    default="memory_ravens",
    help="Name of the run to be used in the output directory",
)
args = parser.parse_args()


cmds = [
    {
        "name": "DNNMark",
        "args": '--benchmark-root=bench/gem5-resources/src/gpu/DNNMark/build/benchmarks/test_fwd_softmax -cdnnmark_test_fwd_softmax --options=\\"-config bench/gem5-resources/src/gpu/DNNMark/config_example/softmax_config.dnnmark --mmap bench/gem5-resources/src/gpu/DNNMark/mmap.bin\\"',
        "dir": ".",
    },
    {
        "name": "pennant",
        "args": '--benchmark-root=bench/gem5-resources/src/gpu/pennant/build -cpennant --options=\\"bench/gem5-resources/src/gpu/pennant/test/noh/noh.pnt\\"',
        "dir": ".",
    },
    {
        "name": "square",
        "args": "-c bench/gem5-resources/src/gpu/square/bin/square",
        "dir": ".",
    },
    {
        "name": "lulesh",
        "args": "--mem-size=8GB --benchmark-root=bench/gem5-resources/src/gpu/lulesh/bin -clulesh",
        "dir": ".",
    },
    {
        'name': 'heterosync',
        'args': '-c bench/gem5-resources/src/gpu/heterosync/bin/allSyncPrims-1kernel  --options=\\"sleepMutex 10 16 4\\"',
        'dir': '.',
    },
    {
        'name': 'halo-finder',
        'args': '--benchmark-root=bench/gem5-resources/src/gpu/halo-finder/src/hip -cForceTreeTest --options=\\"0.5 0.1 64 0.1 1 N 12 rcb\\"',
        'dir': '.',
    }
]



# simulation parameters
cwd = os.getcwd() + "/"
gem5_bin = cwd + "gem5/build/GCN3_X86/gem5.debug"
project_dir = "covert_channel"
config_file = cwd + "gem5/configs/example/apu_se.py"

# debug_flags = ["SecureModuleCpp"]
debug_flags = []

# Create session and trace directories based on current date and time
session_dir = (
    cwd + f"runs/{project_dir}/" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
)

trace_dir = session_dir + "/traces/"
os.makedirs(session_dir, exist_ok=True)
os.makedirs(trace_dir, exist_ok=True)

fast_forward = 10000000
maxinsts = 250000000
redirect = args.redirect

print(f"Session directory: {session_dir}")
print(f"Trace directory: {trace_dir}")

cmd_strs = []
for c in cmds:
    if args.bench and c["name"] not in args.bench:
        continue

    benchmark = c["name"]
    largs = c["args"]
    path = cwd + c["dir"]

    cs = f"(cd {path} && rundockercmd {gem5_bin} --outdir={session_dir}/stats/{benchmark} "
    for d in debug_flags:
        cs += f"--debug-flag {d} "
    cs += f" {config_file} -n3 "
    cs += f"{largs})"

    if redirect:
        cs += f"1> {trace_dir}/{benchmark}.stdout 2> {trace_dir}/{benchmark}.stderr"

    cmd_strs.append((benchmark, cs))


print("=====================================")
print(f"INFO: session directory is {session_dir}")
print(
    "WARNING: if a benchmark fails, make sure it is precompiled before hand. Follow the instructions in each benchmark's README.md"
)
if redirect:
    print(f"INFO: redirecting stdout to {trace_dir}/<benchmark>.stdout")
print("=====================================")
print(f"INFO: fastforwarding {fast_forward} instructions")
print(f"INFO: stopping after {maxinsts} instructions")


if args.dry_run:
    print("INFO: DRY RUN MODE")
    print(f"INFO: would execute {len(cmd_strs)} runs")
    for i in cmd_strs:
        print(f"INFO: running benchmark {i[0]} with command: {i[1]}")
    exit(0)
    # cs = f"{gem5_bin} -d {session_dir}/{benchmark} {config_file} --fast-forward={fast_forward} --maxinsts={maxinsts} --redirect-stdout={redirect} --redirect


# Function to execute command strings
# returns exit code
def execute(cmd):
    # get the word after "--cmd" in the cmd_str
    result = subprocess.run(cmd[1], shell=True)
    return result.returncode


def do_sleep(start_time):
    sleep_time = random.randint(5, 10)
    time.sleep(sleep_time)
    return time.time() - start_time  # Return the elapsed time


print(
    "INFO: launching all threads. check .stdout and .stderr files in the traces directory."
)
print("=====================================")


num_threads = len(cmd_strs)
# Initialize the status display
print("\n" * num_threads)  # Create initial space for the status lines
with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
    # Record the start time for each thread and submit the tasks
    start_times = [time.time() for _ in range(num_threads)]
    end_times = [0 for _ in range(num_threads)]
    futures = [
        executor.submit(
            execute,
            cmd_strs[i],
        )
        for i in range(num_threads)
    ]

    # update simulation status
    try:
        while True:
            # Move the cursor up by 'num_threads' lines to update the statuses in place
            print(f"\033[{num_threads}A", end="")

            for i, future in enumerate(futures):
                # elapsed_time = time.time() - start_times[i]
                if future.running():
                    end_times[i] = time.time()
                    elapsed_time = end_times[i] - start_times[i]
                    status = "Running ⏳"
                elif future.done():
                    elapsed_time = end_times[i] - start_times[i]
                    if future.result() == 0:
                        status = "Done ✅"
                    else:
                        status = f"Failed ❌"
                else:
                    status = "Waiting 🕑"
                    start_times[i] = time.time()
                    elapsed_time = 0
                print(
                    f"{cmd_strs[i][0]:<15} {i+1:<3} | {'Status':<10} {status:<10} | {'Elapsed Time':<15} {elapsed_time:0.0f}s | "
                )

            if all(future.done() for future in futures):
                break
            time.sleep(1)  # Wait for 1 second before the next status update

    except KeyboardInterrupt:
        print(
            "\n❌ Keyboard interrupt received, cancelling tasks...\nYou may need to run `pkill gem5` to make sure all threads are taken care of! 🚨"
        )
        for future in futures:
            future.cancel()  # Attempt to cancel each future

# Final messages and exit
print(f"INFO: Done running all benchmarks. Exiting.")
print(
    f"INFO: Trace files are stored in {session_dir}. It is highly recommended to move them to a different location or rename the folder."
)
exit(0)
