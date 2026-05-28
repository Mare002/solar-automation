FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY solar_calculator.py .
COPY proposal_generator.py .
COPY api_server.py .

# Create directory for generated PDFs
RUN mkdir -p /app/generated_pdfs

EXPOSE 8000

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
