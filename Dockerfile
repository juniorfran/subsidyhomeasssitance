# Usa python slim como base
FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio
WORKDIR /app

# Copiar dependencias
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copiar el proyecto
COPY . .

# Recopilar archivos estáticos (si aplica)
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Comando por defecto
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
