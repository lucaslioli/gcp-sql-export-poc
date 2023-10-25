# Use an official Python runtime as a parent image
FROM python:3.11

# Set the working directory in the container to /job
WORKDIR /job
COPY job/ /job

COPY ../data/ /data

# Install all dependencies from requirements.txt
RUN pip install -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Run job file when the container launches
CMD ["python", "sql_export.py"]
