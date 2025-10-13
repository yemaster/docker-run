# Docker Run

## 项目简介

Docker Run 是一个旨在为用户提供快速 Docker 容器运行环境的工具，方便测试和开发。通过管理员创建的 Docker 模板，用户可以一键创建 Docker 容器，快速搭建测试环境。每个容器有以下特性：
- **限时运行**：每个容器默认运行时间为 2 小时。
- **续期功能**：当容器剩余有效期少于 20 分钟时，用户可续期 1 小时，最多续期 2 次。
- **容器管理**：用户可以查看容器的统计数据（CPU、内存占用、端口转发等）、容器日志，连接容器终端，以及管理容器内的文件。

## 技术栈

- **后端**：Flask（Python 轻量级 Web 框架）
- **依赖管理**：通过 `requirements.txt` 管理项目依赖

## 安装与运行
### 前提条件

- Python 3.8 或以上版本
- Docker 环境已正确配置

### 安装步骤
1. 克隆项目仓库：
   ```bash
   git clone https://github.com/yemaster/docker-run
   cd docker-run
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 配置环境变量

   ```bash
   copy .env.example .env
   ```

   编辑 `.env` 的配置，包括数据库配置等

4. 运行开发服务器：

   ```bash
   python app.py
   ```

### 项目结构
```
docker-run/
├── app.py                # Flask 主应用文件
├── requirements.txt      # 项目依赖
├── templates/            # HTML 模板（前端页面）
├── static/               # 静态文件（CSS、JS 等）
└── README.md             # 项目说明文档
```

## 使用说明
1. **创建容器**：登录系统后，选择管理员提供的 Docker 模板，点击“一键创建”即可启动容器。
2. **查看统计数据**：在容器管理界面，查看 CPU、内存占用、端口转发等实时数据。
3. **日志与终端**：通过界面查看容器日志或连接到容器终端进行操作。
4. **文件管理**：支持上传、下载和管理容器内的文件。
5. **续期容器**：当容器剩余时间少于 20 分钟时，可选择续期（最多 2 次，每次 1 小时）。

## 贡献
欢迎提交 Issue 或 Pull Request，为项目提供改进建议或新功能。

## 许可证
本项目采用 MIT 许可证，详情见 `LICENSE` 文件。