#!/usr/bin/env python3

import sys
import os
import time
import threading
import concurrent.futures
import requests
import redis
import posixpath
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_URL = os.getenv('API_URL', 'https://api.pcloud.com')
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
UPLOAD_ROOT = os.getenv('UPLOAD_ROOT')
CONCURRENCY = os.getenv('CONCURRENCY', 4)
WATCHED_DIRECTORY = os.getenv('WATCHED_DIRECTORY')
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_SET = os.getenv('REDIS_SET', 'files_to_upload')

# Global session to maintain authentication
session = requests.Session()
auth_token = None
auth_lock = threading.Lock()

def check_environment():
    global UPLOAD_ROOT
    global CONCURRENCY
    global WATCHED_DIRECTORY

    # Check for required environment variable
    if not USERNAME:
        print("Error: USERNAME not set.")
        sys.exit(1)

    if not PASSWORD:
        print("Error: PASSWORD not set.")
        sys.exit(1)

    if not UPLOAD_ROOT:
        print("Warning: UPLOAD_ROOT not set, falling back to /.")
        UPLOAD_ROOT = '/'
    elif not UPLOAD_ROOT.startswith('/'):
        print(f"Note: UPLOAD_ROOT must be an absolute path, changed from {UPLOAD_ROOT} to /{{UPLOAD_ROOT}}.")
        UPLOAD_ROOT = '/' + UPLOAD_ROOT

    try:
        CONCURRENCY = int(CONCURRENCY)
    except ValueError:
        print("Error: Expected CONCURRENCY to be an integer but was '{CONCURRENCY}'.")
        sys.exit(1)

    # Set WATCHED_DIRECTORY to current directory if not set
    if not WATCHED_DIRECTORY:
        WATCHED_DIRECTORY = os.getcwd()
        print(f"Note: WATCHED_DIRECTORY not set. Using current directory: {WATCHED_DIRECTORY}")

def authenticate():
    global auth_token
    with auth_lock:
        if auth_token is None:
            # Authenticate with the pCloud API
            auth_url = f"{API_URL}/userinfo"
            params = {
                'getauth': 1,
                'logout': 1,
                'username': USERNAME,
                'password': PASSWORD
            }
            try:
                response = session.get(auth_url, params=params)
                response.raise_for_status()
                data = response.json()
                if data.get('result') == 0:
                    auth_token = data.get('auth')
                    session.params = {'auth': auth_token}
                    print("Authentication successful.")
                else:
                    error_message = data.get('error', 'Unknown error')
                    print(f"Authentication failed: {error_message}")
                    sys.exit(1)
            except Exception as e:
                print(f"Error during authentication: {e}")
                sys.exit(1)

def create_folder_if_not_exists(folder_path):
    # Ensure folder_path starts with '/'
    if not folder_path.startswith('/'):
        folder_path = '/' + folder_path

    # Split the folder path into parts
    parts = folder_path.strip('/').split('/')
    parts[0] = '/' + parts[0]
    current_path = ''
    for part in parts:
        current_path = posixpath.join(current_path, part)
        params = {
            'path': current_path,
        }
        create_folder_url = f"{API_URL}/createfolderifnotexists"
        try:
            response = session.get(create_folder_url, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get('result') == 0:
                # Folder exists or was created
                continue
            else:
                error_message = data.get('error', 'Unknown error')
                print(f"Failed to create folder '{current_path}': {error_message}")
                return False
        except Exception as e:
            print(f"Error creating folder '{current_path}': {e}")
            return False
    print(f"Folder '{folder_path}' exists or was created successfully.")
    return True

def upload_file(relative_path):
    result = {
        'success': False,
        'errorMessage': '',
        'filename': relative_path,
        'duration': 0
    }

    # Construct the full local file path
    local_file_path = os.path.join(WATCHED_DIRECTORY, relative_path.replace('/', os.sep))

    if not os.path.isfile(local_file_path):
        result['errorMessage'] = f"File '{local_file_path}' does not exist. Skipping."
        return result

    # Ensure authentication
    if auth_token is None:
        result['errorMessage'] = f"auth_token empty, unable to upload."
        return result

    start_time = time.time()
    try:
        file_name = os.path.basename(local_file_path)
        # Combine UPLOAD_ROOT with the relative path to form the destination path
        destination_path = posixpath.join(UPLOAD_ROOT, relative_path)
        destination_folder = posixpath.dirname(destination_path)

        # Create destination folder if it doesn't exist
        if not create_folder_if_not_exists(destination_folder):
            result['errorMessage'] = f"Failed to ensure destination folder exists: '{destination_folder}'"
            return result

        upload_url = f"{API_URL}/uploadfile"
        with open(local_file_path, 'rb') as f:
            files = {
                'file': (file_name, f),
            }
            params = {
                'path': destination_folder,
                'filename': file_name,
                'nopartial': 1,  # Don't create partial files
            }
            # Use session to include auth token
            response = session.post(upload_url, params=params, files=files)
            response.raise_for_status()
            data = response.json()
            if data.get('result') == 0:
                result['duration'] = time.time() - start_time
                result['success'] = True
            else:
                result['errorMessage'] = f"Upload failed: {data.get('result')}: {data.get('error', 'Unknown error')}"
    except Exception as e:
        result['errorMessage'] = f"Upload failed: {e}"
    return result

def main():
    check_environment()

    # Initialize Redis connection
    try:
        redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    except Exception as e:
        print(f"Error connecting to Redis: {e}")
        sys.exit(1)

    # Check if Redis set is empty before proceeding
    if redis_client.scard(REDIS_SET) == 0:
        print("No files to upload.")
        return

    # Ensure authentication before starting uploads
    authenticate()

    total_start_time = time.time()
    num_uploads = 0
    num_uploads_lock = threading.Lock()

    # Use ThreadPoolExecutor to handle concurrency
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = []
        while True:
            # Atomically pop a file path from the Redis set
            relative_path = redis_client.spop(REDIS_SET)
            if not relative_path:
                break  # No more files to process
            relative_path = relative_path.decode('utf-8')  # Convert bytes to string

            # Submit the upload task
            futures.append(executor.submit(upload_file, relative_path))

        if not futures:
            print("No files to upload.")
            return

        # Process completed futures
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result['success']:
                print(f"Uploaded {result['filename']} in {result['duration']:.2f} seconds.")
                with num_uploads_lock:
                    num_uploads += 1
            else:
                print(f"Error uploading {result['filename']}: {result['errorMessage']}.")
                redis_client.sadd(REDIS_SET, relative_path)
                pass

    total_duration = time.time() - total_start_time
    print(f"\nUploaded {num_uploads} files in {total_duration:.2f} seconds.")

if __name__ == "__main__":
    main()
