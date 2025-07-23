# Use a slim Python base image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for tkinter and system monitoring tools
# procps is for 'top', lm-sensors is for the 'sensors' command
RUN apt-get update && apt-get install -y \
    procps \
    tk-dev \
    lm-sensors \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application script into the container
COPY hwmonitor.py .

# Command to run the application
CMD ["python", "hwmonitor.py"]

