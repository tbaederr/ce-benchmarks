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

# Check compiler version and detect unoptimized builds
print(f"🔍 Checking compiler version...")
try:
    version_result = subprocess.run([CC, '--version'], capture_output=True, text=True, timeout=10)
    if version_result.returncode == 0:
        version_output = version_result.stdout
        print(f"✅ Compiler: {version_output.split()[0]} {version_output.split()[2] if len(version_output.split()) > 2 else 'unknown version'}")
        
        # Check if this is an unoptimized build
        if '+unoptimized' in version_output:
            print("⚠️  Detected unoptimized build - adding 5 second timeout to prevent hangs")
            SUBPROCESS_TIMEOUT = 5.0
        else:
            print("⚡ Optimized build detected - no timeout needed")
            SUBPROCESS_TIMEOUT = None
    else:
        print(f"❌ Failed to get compiler version: {version_result.stderr}")
        SUBPROCESS_TIMEOUT = None
except subprocess.TimeoutExpired:
    print("⏰ Compiler version check timed out")
    SUBPROCESS_TIMEOUT = None
except Exception as e:
    print(f"❌ Error checking compiler version: {e}")
    SUBPROCESS_TIMEOUT = None

print()

def update_progress(current, total, phase, filename):
    """Display a dynamic progress bar with enhanced styling"""
    progress = current / total
    bar_length = 50
    filled_length = int(bar_length * progress)
    
    # Create gradient effect with different block characters
    if filled_length > 0:
        if filled_length == bar_length:
            # Complete bar - all full blocks
            bar = '█' * filled_length
        else:
            # Partial bar with gradient effect
            bar = '█' * (filled_length - 1) + '▓' + '░' * (bar_length - filled_length)
    else:
        bar = '░' * bar_length
    
    percent = progress * 100
    
    # Color coding for different phases
    if "Normal" in phase:
        phase_color = '\033[96m'  # Cyan
        phase_icon = '⚡'
    elif "BC" in phase:
        phase_color = '\033[95m'  # Magenta
        phase_icon = '🧪'
    else:
        phase_color = '\033[93m'  # Yellow
        phase_icon = '🚀'
    
    reset_color = '\033[0m'
    
    # Enhanced progress bar with colors and better formatting
    filename_display = filename[:25] + '...' if len(filename) > 28 else filename
    print(f'\r\033[1m[\033[92m{bar}\033[0m\033[1m]\033[0m {percent:5.1f}% {phase_color}{phase_icon} {phase}{reset_color}: \033[97m{filename_display}\033[0m', end='', flush=True)

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
    # Track if this file hit any timeouts
    file_had_timeout = False
    
    # Run with normal options
    run_times_normal = []
    for i in range(N):
        # Show progress before starting the run
        update_progress(current_run, total_runs, f"Running Normal {i+1}/{N}", filename)
        
        start_time = time.perf_counter()
        try:
            # Run bin/clang with filename and first line content
            cmd = [CC, filepath] + first_line_stripped.split() + COMMON_CC_PARAMS
            if SUBPROCESS_TIMEOUT:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT)
            else:
                result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Print any errors from the subprocess
            if result.stderr:
                print(f"\nError from {filename} (normal, run {i+1}): {result.stderr.strip()}")
            if result.returncode != 0:
                print(f"\nProcess {filename} (normal, run {i+1}) exited with code: {result.returncode}")
        except subprocess.TimeoutExpired:
            file_had_timeout = True
        except Exception as e:
            print(f"\nException running {filename} (normal, run {i+1}): {e}")
        elapsed = time.perf_counter() - start_time
        run_times_normal.append(elapsed)
        
        current_run += 1
        
    # Run with experimental constant interpreter
    run_times_experimental = []
    for i in range(N):
        # Show progress before starting the run
        update_progress(current_run, total_runs, f"Running BC {i+1}/{N}", filename)
        
        start_time = time.perf_counter()
        try:
            # Run bin/clang with filename, first line content, and experimental flag
            cmd = [CC, filepath] + first_line_stripped.split() + COMMON_CC_PARAMS + ["-fexperimental-new-constant-interpreter"]
            if SUBPROCESS_TIMEOUT:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT)
            else:
                result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Print any errors from the subprocess
            if result.stderr:
                print(f"\nError from {filename} (experimental, run {i+1}): {result.stderr.strip()}")
            if result.returncode != 0:
                print(f"\nProcess {filename} (experimental, run {i+1}) exited with code: {result.returncode}")
        except subprocess.TimeoutExpired:
            file_had_timeout = True
        except Exception as e:
            print(f"\nException running {filename} (experimental, run {i+1}): {e}")
        elapsed = time.perf_counter() - start_time
        run_times_experimental.append(elapsed)
        
        current_run += 1
        
    # Only include results if no timeouts occurred
    if not file_had_timeout:
        results.append({
            'filename': filename,
            'first_line': first_line_stripped,
            'times_normal': run_times_normal,
            'times_experimental': run_times_experimental,
            'total_time_normal': sum(run_times_normal),
            'total_time_experimental': sum(run_times_experimental)
        })


# Clear progress bar completely and add newline
print("\r" + " " * 120)  # Clear the entire progress bar line
print("\r" + "="*80)
print("🎉 \033[1m\033[92mBENCHMARK COMPLETED!\033[0m 🎉".center(80))
print("="*80)

# Clean up generated .o files
import glob
o_files = glob.glob(os.path.join(search_dir, "*.o"))
cleanup_count = 0
for o_file in o_files:
    try:
        os.remove(o_file)
        cleanup_count += 1
    except OSError as e:
        print(f"⚠️  Warning: Could not remove {o_file}: {e}")

# Silently clean up - no output needed

print()
print("📊 \033[1m\033[96mBENCHMARK RESULTS\033[0m")
print("─" * 80)

# Print the times in a table with prettier formatting
header = f"{'File':<22} {'Current':>14} {'Experimental':>18} {'Speedup':>14}"
print(f"\033[1m{header}\033[0m")
print("─" * 80)
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
    elif speed_up_percent < 0:
        speed_color = '\033[1m\033[91m'  # Bold Red
        exp_color = '\033[91m'  # Red
    else:
        speed_color = '\033[1m\033[93m'  # Bold Yellow
        exp_color = '\033[93m'  # Yellow
    reset_color = '\033[0m'
    
    normal_str = format_time(avg_normal)
    experimental_str = format_time(avg_experimental)
    speed_str = f"{speed_up_percent:+.1f}%"
    
    print(f"{res['filename']:<22} {normal_str:>14} {exp_color}{experimental_str:>18}{reset_color} {speed_color}{speed_str:>14}{reset_color}")

# Add summary statistics
print("─" * 80)
if results:
    # Calculate overall statistics
    total_speedups = []
    faster_count = 0
    slower_count = 0
    
    for res in results:
        avg_normal = res['total_time_normal'] / len(res['times_normal']) if res['times_normal'] else 0
        avg_experimental = res['total_time_experimental'] / len(res['times_experimental']) if res['times_experimental'] else 0
        if avg_normal > 0:
            speedup = ((avg_normal - avg_experimental) / avg_normal) * 100
            total_speedups.append(speedup)
            if speedup > 0:
                faster_count += 1
            elif speedup < 0:
                slower_count += 1
    
    if total_speedups:
        avg_speedup = sum(total_speedups) / len(total_speedups)
        print(f"\033[1m📊 SUMMARY:\033[0m")
        print(f"   Files tested: {len(results)}")
        print(f"   Faster: \033[92m{faster_count}\033[0m | Slower: \033[91m{slower_count}\033[0m | Same: {len(results) - faster_count - slower_count}")
        
        if avg_speedup > 0:
            print(f"   Average speedup: \033[1m\033[92m📈 +{avg_speedup:.1f}%\033[0m")
        elif avg_speedup < 0:
            print(f"   Average speedup: \033[1m\033[91m📉 {avg_speedup:.1f}%\033[0m")
        else:
            print(f"   Average speedup: \033[1m\033[93m➡️  {avg_speedup:.1f}%\033[0m")

print("="*80)






