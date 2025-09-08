# 
#from rmrl import render

#from rmcl import Item, Document, Folder

# import trio
import argparse
import subprocess
import os
from pathlib import Path




# Must login using the rmapi GO application first

def parse_arguments():
    # 1. Create an ArgumentParser object
    parser = argparse.ArgumentParser(
        description="rmcloud2pdf import documents from Remarkable cloud and convert to pdf"
    )

    # 2. Add arguments to the parser
    parser.add_argument(
        '-o', '--output', 
        type=str, 
        required=True, 
        help='Defines the output path.'
    )
    
    parser.add_argument(
        '-i', '--ignore-dirs', 
        type=str, 
        nargs='+',  # This tells argparse to accept one or more arguments
        default=[],
        help='Defines a list of directory names to ignore.'
    )

    parser.add_argument(
        '-s', '--sync-dirs', 
        type=str, 
        nargs='+',  # This tells argparse to accept one or more arguments
        default=[],
        help='Defines a list of directory names to sync files in'
    )

    # 3. Parse the arguments from the command line
    parsed_args = parser.parse_args()

    # 4. Print the values to confirm they were parsed correctly
    print(f"Output path: {parsed_args.output}")
    print(f"Directories to ignore: {parsed_args.ignore_dirs}")
    print(f"Directories to sync: {parsed_args.sync_dirs}")

    return parsed_args

def rmapi_find():
    """
    Runs the 'rmapi find .' command and returns its standard output.

    Returns:
        str: The standard output of the rmapi command if successful.
        None: If the command fails or 'rmapi' is not found.
    """
    try:
        # Run the command and capture its output
        result = subprocess.run(
            ['rmapi', 'find', '.'], 
            capture_output=True, 
            text=True, 
            check=True
        )
        return result.stdout
    
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        print(f"Stderr: {e.stderr}")
        return None
        
    except FileNotFoundError:
        print("The 'rmapi' command was not found.")
        return None


def parse_rmapi_find(rmapi_find_output):
    """
    Parses the string output from 'rmapi find' and separates file and
    directory paths into two lists.

    Args:
        rmapi_find_output (str): The raw string output from the 'rmapi find .' command.
                             e.g., "[d] /path/to/dir\n[f] /path/to/file.pdf"

    Returns:
        tuple: A tuple containing two lists:
               - The first list contains full paths of directories.
               - The second list contains full paths of files.
               Returns ([], []) if the input string is empty.
    """
    directories = []
    files = []

    # Split the input string into individual lines and remove any leading/trailing whitespace
    lines = rmapi_find_output.strip().split('\n')

    for line in lines:
        # Ignore empty lines that might be in the output
        if not line:
            continue
            
        # Check for the directory marker '[d]'
        if line.startswith('[d] '):
            # Extract the path by slicing the string after the marker
            dir_path = line[4:]
            directories.append(dir_path)
            
        # Check for the file marker '[f]'
        elif line.startswith('[f] '):
            # Extract the path by slicing the string after the marker
            file_path = line[4:]
            files.append(file_path)

    return (directories, files)

def ensure_directories_exist(output_path, dir_list):
    """
    Checks if each directory in a list exists within a specified output path
    and creates it if it doesn't.

    Args:
        output_path (str): The root path where the directories should be created.
        dir_list (list): A list of relative or absolute directory paths to create.
    """
    print(f"Checking and creating directories within: {output_path}")

    # Ensure the base output path exists first
    try:
        os.makedirs(output_path, exist_ok=True)
    except OSError as e:
        print(f"Error creating base output path {output_path}: {e}")
        return

    for directory in dir_list:
        # Construct the full path by joining the output path and the directory
        full_path = os.path.join(output_path, directory.lstrip('/'))
        
        try:
            # os.makedirs creates the directory and any necessary parent directories
            os.makedirs(full_path, exist_ok=True)
            print(f"Directory created or already exists: {full_path}")
        except OSError as e:
            # Handle potential permissions issues or other OS errors
            print(f"Error creating directory {full_path}: {e}")

# --- Example Usage ---

if __name__ == "__main__":
    args = parse_arguments()

    # Now you can call the function and store the output in a variable
    rmapi_find_out = rmapi_find()

    if rmapi_find_out:
        print("Command output successfully captured:")
        print(rmapi_find_out)
    # Now you can work with rmapi_find_out
    # For example, you can parse it or save it to a file.
    else:
        print("Failed to get command output.")

# --- Example Usage with your provided output ---

# Call the function to parse the sample output
    rmapi_dir_list, rmapi_file_list = parse_rmapi_find(rmapi_find_out)

# Print the results to verify
    print("Found the following directories:")
    for directory in rmapi_dir_list:
        print(f"- {directory}")

    print("\nFound the following files:")
    for file in rmapi_file_list:
        print(f"- {file}")


    ensure_directories_exist(args.output, rmapi_dir_list)











