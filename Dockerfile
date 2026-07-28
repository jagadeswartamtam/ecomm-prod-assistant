FROM python:3.11-slim

WORKDIR /app

# install git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
COPY prod_assistant ./prod_assistant

RUN pip install --no-cache-dir torch==2.5.1+cpu \
    --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x start-services.sh

EXPOSE 8000
EXPOSE 8001

CMD ["./start-services.sh"]