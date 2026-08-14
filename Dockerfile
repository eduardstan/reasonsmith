FROM python:3.13-slim

WORKDIR /app
COPY . .
RUN python -m pip install --no-cache-dir .

ENTRYPOINT ["reasonsmith"]
