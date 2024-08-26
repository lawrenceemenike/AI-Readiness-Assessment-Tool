FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/instance && chmod 777 /app/instance

CMD ["gunicorn", "main:app", "-b", "0.0.0.0:7860"]
