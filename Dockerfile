FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY files/ ./files/

RUN mkdir -p /app/uploads

EXPOSE 8000 8501

RUN echo '#!/bin/bash\n\
echo "Starting FastAPI backend..."\n\
cd /app && python files/main.py &\n\
echo "Starting Streamlit frontend..."\n\
cd /app && streamlit run files/app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true\n\
' > start.sh && chmod +x start.sh

CMD ["./start.sh"]