FROM python:3.11-slim

# Ortam değişkenleri
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV APP_HOME /app
ENV VENV_PATH $APP_HOME/.venv
ENV PATH="$VENV_PATH/bin:$PATH"               
ENV PYTHONPATH="$APP_HOME/src"                
WORKDIR $APP_HOME

# Sanal ortamı oluştur
RUN python -m venv $VENV_PATH

# Sisteme pip yerine uv yükle
RUN pip install uv

# Gereksinimleri yükle
COPY requirements.txt .
RUN uv pip install -r requirements.txt

# Proje dosyalarını kopyala
COPY ./src ./src
COPY .env .env

# Portu aç
EXPOSE 8000

# Uygulamayı başlat (sadece .venv içindeki şeyleri kullanır)
CMD ["uvicorn", "searchv2.main:app", "--host", "0.0.0.0", "--port", "8000"]
