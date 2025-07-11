ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim

EXPOSE 8080

ENV PYTHONUNBUFFERED=1

WORKDIR /bot

COPY * /bot/

RUN pip install --no-cache-dir -r requirements.txt

CMD python bot.py