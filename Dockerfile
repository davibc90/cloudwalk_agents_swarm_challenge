FROM python:3.11.0

# Variáveis gerais de produção
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Locales (pt_BR e en_US) + timezone
RUN apt-get update && apt-get install -y --no-install-recommends locales tzdata \
    && sed -i 's/# pt_BR.UTF-8 UTF-8/pt_BR.UTF-8 UTF-8/' /etc/locale.gen \
    && sed -i 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen \
    && update-locale LANG=pt_BR.UTF-8 LC_ALL=pt_BR.UTF-8 LC_TIME=pt_BR.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

# Locale/idioma padrão do container + fuso (ajuste se quiser outro)
ENV LANG=pt_BR.UTF-8 \
    LANGUAGE=pt_BR:pt \
    LC_ALL=pt_BR.UTF-8 \
    TZ=America/Sao_Paulo

WORKDIR /challenge

# Dependências Python
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

# Código
COPY . .

# Usuário não-root
RUN useradd -ms /bin/bash appuser
USER appuser

EXPOSE 10000

# Uvicorn (ajuste workers conforme necessidade/recursos)
ENV UVICORN_WORKERS=1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000", "--workers", "1"]
