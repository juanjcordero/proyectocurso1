# IMAGEN BASE
FROM python:3.11-slim
# INSTRUCCIONES
WORKDIR /app

RUN pip install psycopg2-binary
RUN pip install --no-cache-dir requests


# Copiar el archivo de la aplicación
COPY app.py .

# Exponer el puerto 3000
EXPOSE 3005

# ENTRYPOINT
CMD ["python", "app.py"]