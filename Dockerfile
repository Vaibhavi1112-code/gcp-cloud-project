# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /home/vaibhavipanchal3524/helloworld-python/app1-tutorial/

# Copy the current directory contents into the container
COPY . /home/vaibhavipanchal3524/helloworld-python/app1-tutorial/


# Install the required Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8080 available to the world outside the container
EXPOSE 5000

# Define environment variable
ENV PORT=5000

# Run the application
CMD ["python", "main.py"]
