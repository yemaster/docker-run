FROM openjdk:8-slim-bullseye

RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list
RUN apt update && apt install -y maven

COPY ./src /app
COPY ./service/docker-entrypoint.sh /docker-entrypoint.sh

EXPOSE 8080

WORKDIR /app

# 指定容器入口点
ENTRYPOINT [ "/bin/bash","/docker-entrypoint.sh" ]