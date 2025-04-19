FROM python:3.13-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# Gera o Prisma Client
RUN python -m prisma generate

# Executa as migrations
RUN python -m prisma migrate deploy

# Porta padrão para o servidor
EXPOSE 8000

# Inicia o servidor
CMD ["python", "main.py", "-m", "server"]
