import argparse
import subprocess
import os
import shutil
import uuid
import json
import zipfile

from pathlib import Path
from PyPDF2 import PdfMerger

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


def rmapi_download(file_path_remote, local_output_dir):
    """
    Downloads a single file from the cloud to a corresponding local path
    and then processes it.

    Args:
        file_path_remote (str): The full path of the file on the cloud.
        local_output_dir (str): The base directory for local downloads.
    """
    # Get the absolute path for the final destination before any directory changes.
    absolute_output_dir = os.path.abspath(local_output_dir)
    
    # Construct the full absolute path for the final destination file.
    # This will be the final path where the file is moved.
    full_local_path = os.path.join(absolute_output_dir, file_path_remote.lstrip('/')) + '.rmdoc'

    # Get the name of the file that rmapi will create in the temporary directory.
    temp_file_name = os.path.basename(file_path_remote) + '.rmdoc'
    
    # Store the current working directory to return to later.
    original_dir = os.getcwd()

    # Create a unique temporary directory for the download.
    temp_dir_name = str(uuid.uuid4())
    temp_dir = os.path.join(os.path.abspath(os.path.join(os.sep, 'tmp')), temp_dir_name)
    os.makedirs(temp_dir)
    
    try:
        # Change the current working directory to the temporary directory.
        os.chdir(temp_dir)

        # 1. Download the file using rmapi. It will be saved in the temporary directory.
        print(f"Downloading '{file_path_remote}' to temporary location...")
        try:
            subprocess.run(
                ['rmapi', 'get', file_path_remote],
                check=True,
                capture_output=True,
                text=True
            )
            print("Download successful.")
        except subprocess.CalledProcessError as e:
            print(f"Error downloading file: {e.stderr}")
            return

        # 2. Ensure the parent directory for the final destination exists.
        local_dir = os.path.dirname(full_local_path)
        os.makedirs(local_dir, exist_ok=True)
        print(f"Ensured final directory exists at {local_dir}")

        # 3. Move the downloaded file from the temporary directory to the final destination.
        #    The source path is relative to the current working directory (temp_dir).
        #    The destination path is the full absolute path we constructed earlier.
        print(f"Moving '{temp_file_name}' to '{full_local_path}'")
        shutil.move(temp_file_name, full_local_path)
        print("Move successful.")

        # 4. Continue downstream processing.
        print(f"Processing file at {full_local_path}")
        
    finally:
        # Return to the original working directory regardless of success or failure.
        os.chdir(original_dir)
        # Clean up the temporary directory.
        shutil.rmtree(temp_dir)
        print(f"Cleaned up temporary directory {temp_dir}")



def merge_pdfs(pdf_list, output_path):
    """
    Merges a list of PDF files into a single PDF using PyPDF2.
    """
    if PdfMerger is None:
        print("PDF merging aborted. PyPDF2 is not installed.")
        return False
    
    try:
        merger = PdfMerger()
        for pdf_file in pdf_list:
            merger.append(pdf_file)
        
        with open(output_path, "wb") as f:
            merger.write(f)
        
        merger.close()
        print("PDF merge successful.")
        return True
    except Exception as e:
        print(f"Error merging PDFs with PyPDF2: {e}")
        return False


def process_rmdoc_file(rmdoc_file_path):
    """
    Unzips a .rmdoc file, extracts page IDs, converts .rm pages to PDF,
    and merges them into a single PDF document.

    Args:
        rmdoc_file_path (str): The full path to the .rmdoc file.
    """
    print(f"Starting to process {rmdoc_file_path}...")

    # Define temporary directories and file paths
    # Create a unique temporary directory for extraction
    temp_extract_dir = os.path.join(os.path.dirname(rmdoc_file_path), f"temp_extract_{uuid.uuid4()}")
    
    base_name = os.path.basename(rmdoc_file_path).replace('.rmdoc', '')
    final_pdf_path = os.path.join(os.path.dirname(rmdoc_file_path), f"{base_name}.pdf")
    
    # List to hold the paths of the individual PDF pages
    pdf_pages = []

    try:
        # 1. Unzip the .rmdoc file
        with zipfile.ZipFile(rmdoc_file_path, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_dir)
        print(f"Successfully unzipped to {temp_extract_dir}")

        # 2. Find and parse the .content JSON file to get page IDs
        content_file = None
        # Walk through the extracted directory to find the content file
        for root, _, files in os.walk(temp_extract_dir):
            for file in files:
                if file.endswith('.content'):
                    content_file = os.path.join(root, file)
                    break
            if content_file:
                break
        
        if not content_file:
            print("Error: .content file not found in the archive.")
            return

        with open(content_file, 'r') as f:
            content_data = json.load(f)

        # Get the UUID from the content file name
        content_uuid = Path(content_file).stem

        # Check for the presence of a PDF file with the same UUID
        pdf_file_path = os.path.join(temp_extract_dir, f"{content_uuid}.pdf")
        if os.path.exists(pdf_file_path):
            print(f"Found imported PDF file: {pdf_file_path}. Copying directly.")
            shutil.copyfile(pdf_file_path, final_pdf_path)
            print(f"Copied {pdf_file_path} to {final_pdf_path}.")
        else:
            # If no PDF is found, assume it's a native notebook and proceed with conversion
            try:
                page_ids = [page['id'] for page in content_data['cPages']['pages']]
                print(f"Extracted page IDs: {page_ids}")

                # 3. Convert each .rm page to a PDF using the 'rmc' program
                for page_id in page_ids:
                    rm_file_path = None
                    # Walk through the extracted directory again to find the .rm files
                    for root, _, files in os.walk(temp_extract_dir):
                        for file in files:
                            # The filename starts with the page ID and ends with .rm
                            if file.startswith(page_id) and file.endswith('.rm'):
                                rm_file_path = os.path.join(root, file)
                                break
                        if rm_file_path:
                            break
                    
                    if rm_file_path:
                        pdf_page_path = os.path.join(temp_extract_dir, f"{page_id}.pdf")
                        pdf_pages.append(pdf_page_path)

                        print(f"Converting '{rm_file_path}' to '{pdf_page_path}'...")
                        try:
                            # Corrected command for rmc
                            subprocess.run(
                                ['rmc', '-f', 'rm', '-t', 'pdf', '-o', pdf_page_path, rm_file_path],
                                check=True,
                                capture_output=True,
                                text=True
                            )
                            print("Conversion successful.")
                        except subprocess.CalledProcessError as e:
                            print(f"Error converting page: {e.stderr}")
                            continue
                    else:
                        print(f"Warning: .rm file for ID {page_id} not found.")

                # 4. Join the individual PDF pages into a single document
                if not pdf_pages:
                    print("No PDF pages were created. Aborting.")
                    return
                
                print(f"Joining {len(pdf_pages)} pages into {final_pdf_path}...")
                merge_pdfs(pdf_pages, final_pdf_path)

            except KeyError:
                print(f"Skipping conversion for {rmdoc_file_path} because it lacks 'cPages' and is not a native notebook.")
                
                # Fallback to general file copy
                original_file = None
                for root, _, files in os.walk(temp_extract_dir):
                    for file in files:
                        if not file.endswith('.content') and not file.endswith('.metadata') and not file.endswith('.pagedata') and not file.endswith('.pdf'):
                            original_file = os.path.join(root, file)
                            break
                    if original_file:
                        break
                
                if original_file:
                    shutil.copyfile(original_file, final_pdf_path)
                    print(f"Copied {original_file} to {final_pdf_path}.")
                else:
                    print(f"Error: Could not find original file to copy in {temp_extract_dir}")
            
    finally:
        # 5. Clean up temporary files
        print(f"Cleaning up temporary directory {temp_extract_dir}...")
        shutil.rmtree(temp_extract_dir, ignore_errors=True)
        print("Cleanup complete.")

    print(f"Final PDF created at: {final_pdf_path}")













# MAIN

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

    # Loop through the list of files to download and process them
    for file in rmapi_file_list:
        rmapi_download(file, args.output)
        
        # After downloading, process the .rmdoc file to convert it to a PDF
        # We need to construct the full absolute path to the downloaded .rmdoc file
        absolute_output_dir = os.path.abspath(args.output)
        rmdoc_file_path = os.path.join(absolute_output_dir, file.lstrip('/')) + '.rmdoc'
        
        process_rmdoc_file(rmdoc_file_path)
