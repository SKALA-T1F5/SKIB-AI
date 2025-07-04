FROM docker.io/yoonalim2003/sk-team-09-ai-base:1.0.0

# ✅ Java 설치
RUN apt-get update && apt-get install -y     openjdk-17-jdk     && apt-get clean && rm -rf /var/lib/apt/lists/*

# ✅ JAVA_HOME 설정
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH

# ✅ PYTHONPATH 설정
ENV PYTHONPATH=/app

# ✅ 애플리케이션 복사 및 설정
COPY . /app
WORKDIR /app

EXPOSE 8000 8081 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--limit-max-requests", "200"]