FROM python:3.9-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制应用文件
COPY . .

# 暴露端口
EXPOSE 7860

# 启动服务
CMD ["python", "app.py"]