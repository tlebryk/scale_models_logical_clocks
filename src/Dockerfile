FROM python:3.12-slim

WORKDIR /app

# Copy all Python files into the container
COPY *.py ./

# Create logs directory
RUN mkdir -p /app/logs

# Expose ports for VM communication
EXPOSE 5001-5003

CMD ["python", "run.py"]
