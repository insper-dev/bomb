FROM python:3.13-slim

WORKDIR /app

COPY . .

RUN chmod +x entrypoint.sh

RUN pip install --no-cache-dir -r requirements.txt

RUN python -m prisma generate

EXPOSE 8000

ENTRYPOINT [ "./entrypoint.sh" ]
CMD ["python", "main.py", "-m", "server"]
