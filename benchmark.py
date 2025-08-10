#!/usr/bin/env python3

import os
import sys
import subprocess
import time
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description='Benchmark clang compilation with and without experimental constant interpreter')
parser.add_argument('-n', '--iterations', type=int, default=25, help='Number of iterations to run (default: 25)')
parser.add_argument('-t', '--tuning', type=int, default=10, help='TUNING value for -DTUNING (default: 10)')
parser.add_argument('-cc', '--compiler', default="/home/tbaeder/code/llvm-project/build/bin/clang", help='Path to clang compiler (default: /home/tbaeder/code/llvm-project/build/bin/clang)')
parser.add_argument('directory', nargs='?', default='.', help='Directory to search for .c and .cpp files (default: current directory)')

args = parser.parse_args()
N = args.iterations
search_dir = args.directory
tuning_value = args.tuning
CC = args.compiler

def update_progress(current, total, phase, filename):
    """Display a dynamic progress bar"""
    progress = current / total
    bar_length = 40
    filled_length = int(bar_length * progress)
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    percent = progress * 100
    print(f'\r[{bar}] {percent:6.1f}% - {phase}: {filename}', end='', flush=True)

results = []

# First, collect all valid files
valid_files = []
for filename in os.listdir(search_dir):
    if filename.endswith('.c') or filename.endswith('.cpp'):
        filepath = os.path.join(search_dir, filename)
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline()
            # Check if first line starts with "//"
            if not first_line.strip().startswith('//'):
                print(f"Error: {filename} - First line does not start with '//'")
                continue
            # Strip "//" and whitespace
            first_line_stripped = first_line.replace('//', '').strip()
            valid_files.append((filename, filepath, first_line_stripped))

# Sort files by name for consistent ordering
valid_files.sort(key=lambda x: x[0])

# Common compiler parameters
COMMON_CC_PARAMS = ["-c", "-fconstexpr-steps=1000000000", f"-DTUNING={tuning_value}"]

total_runs = len(valid_files) * N * 2  # 2 runs per file (normal + experimental)
current_run = 0

print(f"Running {len(valid_files)} files with {N} iterations each. Tuning value: {tuning_value}")
print()

# Show initial progress bar at 0%
update_progress(0, total_runs, "Starting", "")

# Process each valid file
for file_idx, (filename, filepath, first_line_stripped) in enumerate(valid_files):
    # Run with normal options
    run_times_normal = []
    for i in range(N):
        start_time = time.perf_counter()
        try:
            # Run bin/clang with filename and first line content
            cmd = [CC, filepath] + first_line_stripped.split() + COMMON_CC_PARAMS
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Print any errors from the subprocess
            if result.stderr:
                print(f"\nError from {filename} (normal, run {i+1}): {result.stderr.strip()}")
            if result.returncode != 0:
                print(f"\nProcess {filename} (normal, run {i+1}) exited with code: {result.returncode}")
        except Exception as e:
            print(f"\nException running {filename} (normal, run {i+1}): {e}")
        elapsed = time.perf_counter() - start_time
        run_times_normal.append(elapsed)
        
        current_run += 1
        update_progress(current_run, total_runs, f"Normal {i+1}/{N}", filename)
        
    # Run with experimental constant interpreter
    run_times_experimental = []
    for i in range(N):
        start_time = time.perf_counter()
        try:
            # Run bin/clang with filename, first line content, and experimental flag
            cmd = [CC, filepath] + first_line_stripped.split() + COMMON_CC_PARAMS + ["-fexperimental-new-constant-interpreter"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Print any errors from the subprocess
            if result.stderr:
                print(f"\nError from {filename} (experimental, run {i+1}): {result.stderr.strip()}")
            if result.returncode != 0:
                print(f"\nProcess {filename} (experimental, run {i+1}) exited with code: {result.returncode}")
        except Exception as e:
            print(f"\nException running {filename} (experimental, run {i+1}): {e}")
        elapsed = time.perf_counter() - start_time
        run_times_experimental.append(elapsed)
        
        current_run += 1
        update_progress(current_run, total_runs, f"BC {i+1}/{N}", filename)
        
    results.append({
        'filename': filename,
        'first_line': first_line_stripped,
        'times_normal': run_times_normal,
        'times_experimental': run_times_experimental,
        'total_time_normal': sum(run_times_normal),
        'total_time_experimental': sum(run_times_experimental)
    })

# Clear progress bar and add newline
print("\nCompleted!")

# Clean up generated .o files
import glob
o_files = glob.glob(os.path.join(search_dir, "*.o"))
for o_file in o_files:
    try:
        os.remove(o_file)
    except OSError as e:
        print(f"Warning: Could not remove {o_file}: {e}")

print()

# Print the times in a table
header = f"{'File':<20} {'Curr':>12} {'BC':>16} {'Speedup':>12}"
print(header)
print('-' * len(header))
for res in results:
    avg_normal = res['total_time_normal'] / len(res['times_normal']) if res['times_normal'] else 0
    avg_experimental = res['total_time_experimental'] / len(res['times_experimental']) if res['times_experimental'] else 0
    
    # Format times with appropriate units
    def format_time(time_seconds):
        if time_seconds < 1.0:
            return f"{time_seconds * 1000:.3f}ms"
        else:
            return f"{time_seconds:.3f}s"
    
    # Calculate speed up percentage
    if avg_normal > 0:
        speed_up_percent = ((avg_normal - avg_experimental) / avg_normal) * 100
    else:
        speed_up_percent = 0
    
    # Color code based on performance: green if faster (positive), red if slower (negative)
    if speed_up_percent > 0:
        speed_color = '\033[1m\033[92m'  # Bold Green
        exp_color = '\033[92m'  # Green
    else:
        speed_color = '\033[1m\033[91m'  # Bold Red
        exp_color = '\033[91m'  # Red
    reset_color = '\033[0m'
    
    normal_str = format_time(avg_normal)
    experimental_str = format_time(avg_experimental)
    speed_str = f"{speed_up_percent:+.1f}%"
    
    print(f"{res['filename']:<20} {normal_str:>12} {exp_color}{experimental_str:>16}{reset_color} {speed_color}{speed_str:>12}{reset_color}")






