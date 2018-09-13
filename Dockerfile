FROM python:3-slim

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV FLASK_APP=/usr/src/app/application.py
ENV PUSHROCKET_CONFIG=pushrocket-api.cfg
ENV PUSHROCKET_DB=sqlite:////pushrocket-api.db
CMD ["flask", "run", "--host", "0.0.0.0"]
