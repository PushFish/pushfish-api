FROM python:3-slim

ENV HOME_DIR=/usr/src/app
WORKDIR $HOME_DIR

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV FLASK_APP=$HOME_DIR/application.py
ENV PUSHROCKET_CONFIG=$HOME_DIR/pushrocket-api.cfg
ENV PUSHROCKET_DB=sqlite:////$HOME_DIR/pushrocket-api.db
CMD ["flask", "run", "--host", "0.0.0.0"]
