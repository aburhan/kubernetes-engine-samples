FROM python:3.10

# Set up argument and environment variable for the project subdirectory
ARG PROJECT_SUBDIRECTORY
ENV PROJECT_SUBDIRECTORY=$PROJECT_SUBDIRECTORY

# Set the working directory to the project subdirectory
WORKDIR ${PROJECT_SUBDIRECTORY}

# Define entrypoint for the Docker container to execute commands with bash
ENTRYPOINT ["/bin/bash", "-e", "-x", "-c"]


CMD [ "\
    python3 -m venv .venv && \
    . .venv/bin/activate && \
    python3 -m pip install --upgrade pip && \
    python3 -m pip install --no-cache-dir --use-pep517 -e . && \
    python3 -m unittest discover -s . -p 'test_*.py' \
  " ]
