# Use python:3.7-alpine as the base image
FROM python:3.7-alpine

# Specify your e-mail address as the maintainer of the container image
MAINTAINER Wen Wu "wwu@pdx.edu"

# Execute apk add and update 
#RUN apk add --update --no-cache 


# Copy the contents of the current directory into the container directory /app
COPY . /app

# Set the working directory of the container to /app
WORKDIR /app

# Install the Python packages specified by requirements.txt into the container
RUN pip install -r requirements.txt

# Set the program that is invoked upon container instantiation
#ENTRYPOINT ["python"]

# Set the parameters to the program
CMD gunicorn --bind :$PORT app:app
