FROM python:3.8-slim


WORKDIR /app


COPY Broker.py .


RUN pip install Flask


RUN pip install flask-cors


CMD ["python3", "Broker.py"]