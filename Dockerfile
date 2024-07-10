FROM python:3.11-slim


COPY requirements.txt .
RUN python -m pip install -r requirements.txt

WORKDIR /app
COPY . /app
RUN adduser -u 1000 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# RUN export AIRTABLE_BASE_ID=${AIRTABLE_BASE_ID} && export AIRTABLE_TOKEN=${AIRTABLE_TOKEN} && export TELEGRAM_TOKEN=${TELEGRAM_TOKEN} && export NOTION_API_TOKEN=${NOTION_TOKEN}}
CMD ["python", "main.py"]