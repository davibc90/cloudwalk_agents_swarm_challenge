FROM python:3.11.0

# Production environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=pt_BR.UTF-8 \
    LANGUAGE=pt_BR:pt \
    LC_ALL=pt_BR.UTF-8

# Locale pt_BR.UTF-8
RUN apt-get update && apt-get install -y --no-install-recommends locales \
    && sed -i '/pt_BR.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /challenge
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 10000
RUN useradd -ms /bin/bash appuser
USER appuser
ENV UVICORN_WORKERS=1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000", "--workers", "1"]
