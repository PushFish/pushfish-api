FROM python:3-slim

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV FLASK_APP=/usr/src/app/application.py
CMD ["flask", "run", "--host", "0.0.0.0"]
