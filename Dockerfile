FROM python:3.9

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir flask requests plexapi

EXPOSE 5000

CMD ["sh", "-c", "pip install --no-cache-dir -r /app/requirements.txt && python3 /app/app.py"]

