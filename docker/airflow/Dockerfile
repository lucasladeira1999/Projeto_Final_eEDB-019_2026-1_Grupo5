FROM apache/airflow:2.11.1

COPY requirements.txt /tmp/requirements.txt
USER root
# Garante leitura do bundle de CAs no build (necessário para o pip em alguns ambientes CI/sandbox).
RUN chmod 755 /etc/ssl/certs \
    && python -m pip install --no-cache-dir -r /tmp/requirements.txt
USER airflow
