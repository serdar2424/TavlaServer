# server/Dockerfile
FROM python:3.9

WORKDIR /app
COPY requirements.txt ./
COPY ./.env ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python", "main.py"]

