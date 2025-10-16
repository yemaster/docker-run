FROM python:3.9-slim-bookworm

# apt更换镜像源，并更新软件包列表信息
RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list
RUN apt-get update 

# 安装必要的python依赖库，如flask
RUN pip install -i https://mirrors.ustc.edu.cn/pypi/simple pip -U && \
    pip config set global.index-url https://mirrors.ustc.edu.cn/pypi/simple && \
    pip install flask

# 拷贝源码和启动脚本至根目录
COPY ./src/ /app
COPY ./service/docker-entrypoint.sh /

EXPOSE 8000

WORKDIR /app

# 指定容器入口点
ENTRYPOINT ["/bin/bash","/docker-entrypoint.sh"]