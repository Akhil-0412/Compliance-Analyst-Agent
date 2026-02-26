# Use the official Python fast alpine image as base
FROM python:3.10-slim

# Create a user to avoid running as root (Hugging Face Space requirement)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Create the working directory
WORKDIR $HOME/app

# Copy the requirements file and install dependencies
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the entire backend directory into the container
COPY --chown=user . .

# Expose the standard FastAPI port
EXPOSE 8000

# Run the uvicorn server binding to 0.0.0.0 and port 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
