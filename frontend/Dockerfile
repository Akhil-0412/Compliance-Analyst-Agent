# Use Python 3.11 slim for smaller image size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed for extensions, but keeping it clean for now)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies (no cache to save space)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port (Render/Railway typically use PORT env var)
# We default to 8000
EXPOSE 8000

# Run the application with uvicorn
# We use api.main:app and read PORT from env
CMD ["python", "api/main.py"]
