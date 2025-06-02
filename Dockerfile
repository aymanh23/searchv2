# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV APP_HOME /app

# Set the working directory in the container
WORKDIR $APP_HOME

# Install uv (Python package installer)
RUN pip install uv

# Copy requirements.txt
COPY requirements.txt ./

# Install project dependencies from requirements.txt
# Using --system to install into the system Python, common for containers
RUN uv pip install -r requirements.txt --system

# Copy the rest of the application's source code from the host to the container
COPY ./src $APP_HOME/src
COPY .env $APP_HOME/.env

# Expose the port the app runs on
EXPOSE 8000

# Define the command to run your app using uvicorn
# It will look for an app instance in src.searchv2.main
CMD ["uvicorn", "src.searchv2.main:app", "--host", "0.0.0.0", "--port", "8000"]
