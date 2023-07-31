import subprocess
import os
import signal
import threading
import queue
import time

from termcolor import colored

from utils.questionary import styled_text

def enqueue_output(out, q):
    for line in iter(out.readline, ''):
        q.put(line)
    out.close()

def run_command(command, q, pid_container):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    pid_container[0] = process.pid
    t = threading.Thread(target=enqueue_output, args=(process.stdout, q))
    t.daemon = True
    t.start()
    return process

def execute_command(command, timeout=5):
    answer = styled_text(
        f'Can i execute the command: `{command}`?\n' +
        'If yes, just press ENTER and if not, please paste the output of running this command here and press ENTER'
    )
    if answer != '':
        return answer[-2000:]

    q = queue.Queue()
    pid_container = [None]
    process = run_command(command, q, pid_container)
    output = ''
    start_time = time.time()

    while True:
        elapsed_time = time.time() - start_time

        # Check if process has finished
        if process.poll() is not None:
            # Get remaining lines from the queue
            time.sleep(0.1) # TODO this shouldn't be used
            while not q.empty():
                output_line = q.get_nowait()
                if output_line not in output:
                    print(colored('CLI OUTPUT:', 'green') + output_line, end='')
                    output += output_line
            break

        # If timeout is reached, kill the process
        if elapsed_time > timeout:
            os.kill(pid_container[0], signal.SIGKILL)
            break

        try:
            line = q.get_nowait()
        except queue.Empty:
            line = None

        if line:
            output += line
            print(colored('CLI OUTPUT:', 'green') + line, end='')

    stderr_output = process.stderr.read()
    return output[-2000:] if output != '' else stderr_output[-2000:]

def build_directory_tree(path, prefix="", ignore=None, is_last=False):
    """Build the directory tree structure in tree-like format.

    Args:
    - path: The starting directory path.
    - prefix: Prefix for the current item, used for recursion.
    - ignore: List of directory names to ignore.
    - is_last: Flag to indicate if the current item is the last in its parent directory.

    Returns:
    - A string representation of the directory tree.
    """
    if ignore is None:
        ignore = []

    if os.path.basename(path) in ignore:
        return ""

    output = ""
    indent = '|   ' if not is_last else '    '

    if os.path.isdir(path):
        # It's a directory, add its name to the output and then recurse into it
        output += prefix + "|-- " + os.path.basename(path) + "/\n"

        # List items in the directory
        items = os.listdir(path)
        for index, item in enumerate(items):
            item_path = os.path.join(path, item)
            output += build_directory_tree(item_path, prefix + indent, ignore, index == len(items) - 1)

    else:
        # It's a file, add its name to the output
        output += prefix + "|-- " + os.path.basename(path) + "\n"

    return output