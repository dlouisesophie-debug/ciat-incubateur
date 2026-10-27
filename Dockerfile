FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PRODUCTION=1 PORT=8000
EXPOSE 8000
# seed.py ne charge les données de démonstration que si la base est vide
CMD ["sh", "-c", "python seed.py && gunicorn app:app --bind 0.0.0.0:$PORT --workers 2"]
