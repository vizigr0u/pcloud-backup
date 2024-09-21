# Folder Backup to pCloud using Docker

A Docker-based solution to watch a local folder and automatically back it up to your pCloud account. This tool monitors a specified directory for file changes and uploads new or modified files to your pCloud storage.

## Features

 - Automatic Backup: Continuously watches a local directory and uploads files to pCloud.
 - Concurrent Uploads: Supports concurrent file uploads for efficiency.
 - Dockerized: Runs inside a Docker container for easy deployment.
 - Simple Configuration: Configure via environment variables in the .env file.

## Prerequisites

- Docker installed on your system.
- A pCloud account and storage.
- Git (if cloning the repository).

## Getting Started

1. Clone the Repository

```bash
git clone https://github.com/yourusername/your-repo-name.git
cd your-repo-name
```

2. Configure environment variables

Copy `example.env` file to `.env`:

```bash
cp example.env .env
```

Edit the `.env` file and set your pCloud username and password:

```dotenv
USERNAME=your_pcloud_username
PASSWORD=your_pcloud_password
```

## Running

### Run using Docker Compose

Replace `/dir/to/watch` inside `docker-compose.yml` with the directory you want to monitor.

```bash
docker-compose up -d
```

### Run Docker

```bash
docker run -d \
  -e USERNAME=your_pcloud_username \
  -e PASSWORD=your_pcloud_password \
  -v /dir/to/watch:/watched \
  --name pcloud-backup \
  vizigr0u/pcloud-backup:latest
```

Replace `/dir/to/watch` with the directory you want to monitor.

## Configuration

All configurations are handled via environment variables set in the `.env` file.
### Environment Variables

 - `USERNAME`: Your pCloud username.
 - `PASSWORD`: Your pCloud password.
 - `UPLOAD_ROOT`: The root directory in pCloud where files will be uploaded (e.g., /Backup).
 - `CONCURRENCY`: Number of concurrent uploads (default is 4).
 - `UPLOAD_DELAY_SECONDS`: Delay in seconds between each upload cycle (default is 60).

## Directory Structure

```bash
├── Dockerfile
├── .gitignore
├── .env
├── example.env
├── docker-compose.yml
├── requirements.txt
├── upload_files.py
├── entrypoint.sh
├── README.md
└── LICENSE
```
 - `Dockerfile`: Defines the Docker image.
 - `docker-compose.yml`: Configuration for Docker Compose.
 - `example.env`: Sample environment configuration file.
 - `upload_files.py`: The main Python script that handles file uploads.
 - `entrypoint.sh`: The entrypoint script that starts Redis and the upload process.
 - `requirements.txt`: Python dependencies.
 - `LICENSE`: License information.
 - `README.md`: Documentation (this file).

## Contributing

Feel free to open pull-request but I can't guarantee I'll be very reactive. Your best bet is probably to fork this repo.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
Support

## FAQ

Q: Can I watch multiple directories?

A: Currently, the script only watches a single directory.

Q: Is my data secure during upload?

A: The script uses pCloud's API over HTTPS, which encrypts data in transit. Ensure you trust the network and environment where the Docker container runs. Also don't share your environment