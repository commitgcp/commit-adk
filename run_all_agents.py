import subprocess
import signal
import sys
import os
import threading
import time

# List of commands to run the agents
# Assuming the script is run from the root of the repository
AGENT_COMMANDS = [
    ("agents.notion", [sys.executable, "-m", "agents.notion"]),
    ("agents.deep_research", [sys.executable, "-m", "agents.deep_research"]),
    ("agents.google_calendar", [sys.executable, "-m", "agents.google_calendar"]),
    ("agents.linkedin", [sys.executable, "-m", "agents.linkedin"]),
    ("agents.python_developer", [sys.executable, "-m", "agents.python_developer"]),
]

# To store the process objects
processes = []
threads = []

def stream_output(process_name, stream, stream_name):
    """Reads and prints output from a stream line by line."""
    try:
        for line in iter(stream.readline, b''):
            if not line: # Check if the line is empty (stream closed)
                break
            print(f"[{process_name} - {stream_name}]: {line.decode('utf-8', errors='replace').strip()}", flush=True)
    except ValueError: # Handle "I/O operation on closed file"
        print(f"[{process_name} - {stream_name}]: Stream closed unexpectedly.", flush=True)
    finally:
        if stream and not stream.closed:
            stream.close()

def signal_handler(sig, frame):
    print("\nShutting down all agents...", flush=True)
    for p_name, p_obj in processes:
        if p_obj.poll() is None:  # Check if process is still running
            print(f"Terminating {p_name} (PID: {p_obj.pid})...", flush=True)
            try:
                # Try to terminate gracefully first
                p_obj.terminate() 
                # Wait for a short period for graceful termination
                try:
                    p_obj.wait(timeout=5) 
                except subprocess.TimeoutExpired:
                    print(f"{p_name} did not terminate gracefully, killing...", flush=True)
                    p_obj.kill() # Force kill if terminate doesn't work
                print(f"{p_name} terminated.", flush=True)
            except Exception as e:
                print(f"Error terminating {p_name}: {e}", flush=True)
        else:
            print(f"{p_name} was already stopped.", flush=True)
    
    # Wait for all output streaming threads to finish
    print("Waiting for log streaming to complete...", flush=True)
    for t_name, thread_obj in threads:
        if thread_obj.is_alive():
            thread_obj.join(timeout=2)
        print(f"Log stream for {t_name} finished.", flush=True)

    print("All agents shut down. Exiting script.", flush=True)
    sys.exit(0)

if __name__ == "__main__":
    # Register the signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    # Also register for SIGTERM for more general termination signals
    signal.signal(signal.SIGTERM, signal_handler)

    print("Starting all A2A agents...", flush=True)
    print(f"Script PID: {os.getpid()}", flush=True)
    print("Press Ctrl+C to shut down all agents and exit.", flush=True)

    # Verify agent module paths (optional, for robustness)
    # This requires that these modules are importable in the current environment
    try:
        import agents.notion
        import agents.deep_research
        import agents.google_calendar
        import agents.linkedin 
        import agents.python_developer
        print("All agent modules seem to be importable.", flush=True)
    except ImportError as e:
        print(f"Warning: Could not import an agent module: {e}", flush=True)
        print("Please ensure all agent modules exist and PYTHONPATH is configured correctly.", flush=True)
        # Decide if you want to exit or continue if an agent module is not found
        # sys.exit(1) 


    for agent_name, cmd in AGENT_COMMANDS:
        try:
            print(f"Starting {agent_name} with command: {' '.join(cmd)}", flush=True)
            # Start the process
            # Set pipes for stdout and stderr
            # Use os.setsid to create a new session, so Ctrl+C in the parent doesn't directly affect children
            # (we'll handle termination explicitly)
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=False, # Read as bytes
                bufsize=1, # Line buffered
                preexec_fn=os.setsid if sys.platform != "win32" else None # New session for non-Windows
            )
            processes.append((agent_name, process))
            print(f"{agent_name} started with PID: {process.pid}", flush=True)

            # Create and start threads to stream stdout and stderr
            stdout_thread = threading.Thread(target=stream_output, args=(agent_name, process.stdout, "stdout"))
            stderr_thread = threading.Thread(target=stream_output, args=(agent_name, process.stderr, "stderr"))
            
            threads.append((f"{agent_name}_stdout", stdout_thread))
            threads.append((f"{agent_name}_stderr", stderr_thread))
            
            stdout_thread.start()
            stderr_thread.start()

        except FileNotFoundError:
            print(f"Error: Command for {agent_name} not found. Is Python installed and in PATH?", flush=True)
            print(f"Command was: {' '.join(cmd)}", flush=True)
        except Exception as e:
            print(f"Failed to start {agent_name}: {e}", flush=True)

    print(f"All {len(processes)} agent processes initiated. Monitoring logs...", flush=True)
    
    # Keep the main script alive while processes run and threads stream output
    try:
        while True:
            all_stopped = True
            for p_name, p_obj in processes:
                if p_obj.poll() is None:
                    all_stopped = False
                    break
            if all_stopped and processes: # Ensure processes list is not empty
                print("All agent processes have stopped.", flush=True)
                break
            time.sleep(1)  # Check every second
    except KeyboardInterrupt:
        # This will be caught by the signal_handler, but good to have a loop break
        print("\nKeyboardInterrupt received in main loop, invoking signal handler...", flush=True)
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        print(f"An unexpected error occurred in the main loop: {e}", flush=True)
        signal_handler(signal.SIGINT, None) # Attempt cleanup
    finally:
        # Ensure cleanup happens even if the loop exits unexpectedly without a signal
        if any(p.poll() is None for _, p in processes): # If any process is still running
             print("Main loop exited unexpectedly. Ensuring agents are shut down...", flush=True)
             signal_handler(signal.SIGINT, None) # Trigger cleanup just in case

    print("Main script finished.", flush=True) 