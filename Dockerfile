FROM python:3.13-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# Gera o Prisma Client (pode ser feito na build)
RUN python -m prisma generate

# Porta padrão para o servidor
EXPOSE 8000

# Inicia o servidor
CMD ["python", "main.py", "-m", "server"]
