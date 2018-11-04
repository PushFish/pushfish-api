FROM python:3-slim

ENV HOME_DIR=/usr/src/app
WORKDIR $HOME_DIR

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV FLASK_APP=$HOME_DIR/application.py
ENV PUSHFISH_CONFIG=$HOME_DIR/pushfish-api.cfg
ENV PUSHFISH_DB=sqlite:////$HOME_DIR/pushfish-api.db
CMD ["flask", "run", "--host", "0.0.0.0"]
