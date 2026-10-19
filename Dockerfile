# Ixtiyoriy — Render'da render.yaml (native python) yetarli.
# Bu Dockerfile boshqa hostlar (Fly.io, Koyeb, VPS) uchun ham ishlaydi.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render/Koyeb $PORT beradi; health-server shu portda ochiladi.
EXPOSE 8080

CMD ["python", "bot.py"]
