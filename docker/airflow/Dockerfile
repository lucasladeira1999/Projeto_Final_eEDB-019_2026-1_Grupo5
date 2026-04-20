FROM apache/airflow:2.11.1

COPY requirements.txt /tmp/requirements.txt

USER root
# Garante leitura do bundle de CAs no build (necessário para o pip em alguns ambientes CI/sandbox).
RUN chmod 755 /etc/ssl/certs
USER airflow
RUN CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt" \
    && python -m pip install --no-cache-dir -r /tmp/requirements.txt --constraint "${CONSTRAINT_URL}"
