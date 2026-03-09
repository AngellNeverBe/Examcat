## Assistant

# Examcat - 现代化多题库考试系统

[![Flask](https://img.shields.io/badge/Flask-2.0%2B-blue?logo=flask)](https://flask.palletsprojects.com/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-green?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

## 📖 项目简介

**Examcat** 是一个现代化的多题库在线考试系统，基于 Flask 框架开发，专为教育机构、培训企业和个人学习设计。本项目源于 [EXAM-MASTER](https://github.com/ExamMaster/EXAM-MASTER)，但经过全面重构和优化，提供了更完善的功能和更好的用户体验。

### ✨ 项目起源

Examcat 是基于原始 EXAM-MASTER 项目进行深度重构的版本。我们保留了原项目的核心功能，但在以下方面进行了重大改进：
- 🔄 **项目结构重构** - 采用模块化设计，代码更清晰易维护
- 📚 **多题库支持** - 完全重写题库管理机制，支持多个独立题库
- 🎨 **界面重设计** - 现代化 UI 设计，提供更好的用户体验
- ⚡ **性能优化** - 优化数据库查询和页面加载速度，支持多线程
- 🔧 **配置系统** - 灵活的配置管理系统，支持环境变量和配置文件

## 🚀 主要特性

### 1. 多题库管理
### 2. 现代化界面
### 3. 智能考试系统
### 4. 用户管理和管理员系统
### 5. 集成artalk在线评论

## 📦 快速开始

### 环境要求
- Python 3.8+
- pip 20.0+
- SQLite3

### 安装步骤

#### 1. 克隆项目
```bash
git clone https://github.com/yourusername/examcat.git
cd examcat
```

#### 3. 安装依赖
```bash
pip install -r requirements.txt
```

#### 3. 配置环境变量
复制示例配置文件并修改：
```bash
cp .env.example .env
# 编辑 .env 文件，设置必要的配置
```

#### 4. 运行开发服务器
```bash
python run.py
```

访问 http://localhost:32220 开始使用！

## 🚢 生产环境部署

### 1. 使用 systemd 管理服务

创建 systemd 服务文件 `/etc/systemd/system/examcat.service`：

```ini
[Unit]
Description=Examcat Flask Application
After=network.target
Requires=network.target

[Service]
Type=simple
User=examcat
Group=examcat
WorkingDirectory=#你的工作目录
EnvironmentFile=#你的.env文件
ExecStart=#你的gunicorn位置 -c gunicorn_conf.py "run:app"
Restart=always
RestartSec=3
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=examcat

# 安全限制
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/var/log/examcat #你的工作目录

[Install]
WantedBy=multi-user.target
```

随后，你可以直接启动examcat了：
```bash
# 1. 重新加载 systemd 配置
sudo systemctl daemon-reload
# 2. 启动服务
sudo systemctl start examcat
# 3. 检查状态
sudo systemctl status examcat
# 4. 查看详细日志
sudo journalctl -u examcat -f
# 5. 如果启动成功，启用开机自启
sudo systemctl enable examcat
```

### 2. 配置 Nginx 反向代理

创建 Nginx 配置文件 `/etc/nginx/sites-available/examcat`：

```nginx
server {
    listen 80;
    server_name exam.你的域名.com;
}

server {
    listen 443 ssl http2;
    server_name exam.你的域名.com;
    
    # SSL 证书配置
    # ssl_certificate /etc/ssl/certs/your-cert.pem;
    # ssl_certificate_key /etc/ssl/private/your-key.key;
    
    # 静态文件服务
    location /static/ {
        alias /opt/examcat/app/static/;
        expires 30d;
    }
    
    # 反向代理到 Gunicorn
    location / {
        proxy_pass http://127.0.0.1:32220;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # 客户端最大 body 大小
    client_max_body_size 10M;
}
```

## ⚙️ 配置系统

Examcat 使用灵活的配置系统，支持多种配置方式：

### 配置文件结构
```
examcat/
├── config.py              # 主要配置类
├── .env                   # 环境变量
└── gunicorn_conf.py       # Gunicorn 配置
```

### 配置优先级
1. 系统环境变量
2. `.env` 文件
3. `config.py` 默认值


## 📚 题库格式

Examcat 支持 CSV 格式的题库文件：

```csv
"题号","题干","A","B","C","D","E","答案","难度","题型"
"1","毛泽东思想产生的社会历史条件有()。","十月革命开辟的世界无产阶级革命的新时代","近代中国社会矛盾和革命运动的发展","工人阶级队伍壮大及工人运动的发展","中国共产党领导的中国新民主主义革命的伟大实践","","ABCD","无","多选题"
"2","毛泽东思想的科学含义是()。","是马克思列宁主义在中国的运用和发展","是被实践证明了的关于中国革命的正确的理论原则和经验总结","是中国共产党集体智慧的结晶","建设中国特色社会主义的理论","","ABC","无","多选题"
"3","毛泽东思想的活的灵魂是()。","群众路线","独立自主","实事求是","理论与实际相结合","","ABC","无","多选题"
```

### 批量导入题库
```bash
# 将题库文件放入 questions-bank 目录
cp your_questions.csv /opt/examcat/app/questions-bank/
```

## 🔧 开发指南

### 项目结构
```
examcat/
├── app/
│   ├── __init__.py       # 应用工厂
│   ├── routes/           # 路由定义
│   ├── utils/            # 工具函数
│   ├── templates/        # 模板文件
│   └── static/           # 静态资源
├── questions-bank/       # 题库目录
├── config.py             # 配置类
├── run.py                # 应用入口
├── gunicorn_conf.py      # 生产服务器配置
└── requirements.txt      # 依赖列表
```


## 📈 监控与日志

### 日志配置
- 访问日志: `/var/log/examcat/access.log`
- 错误日志: `/var/log/examcat/error.log`
- 数据日志：`/var/log/examcat/database.log`
- Systemd 日志: `journalctl -u examcat`

### 监控端点
```bash
# 检查服务状态
sudo systemctl status examcat

# 查看实时日志
sudo journalctl -u examcat -f

# 检查端口占用
sudo netstat -tulnp | grep :32220

# 监控进程资源
top -p $(pgrep -f gunicorn)
```

## 🔒 安全建议

1. **定期更新 SECRET_KEY**
2. **启用 HTTPS**
3. **设置防火墙规则**
4. **定期备份数据库**
5. **监控异常访问**
6. **限制文件上传类型和大小**

## 🤝 贡献指南

我们欢迎各种形式的贡献！

### 报告问题
请使用 [GitHub Issues](https://github.com/AngellNeverBe/examcat/issues) 报告 bug 或提出建议。

## 📄 许可证

本项目基于 MIT 许可证开源 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- 感谢原始 [EXAM-MASTER](https://github.com/ExamMaster/EXAM-MASTER) 项目的启发
- 感谢使用 Examcat 的每一位用户

## 📞 支持与联系

- 📧 扣扣邮箱：2687869894@qq.com
- 💬 在这提问：[GitHub Issues](https://github.com/AngellNeverBe/examcat/issues)
- 📖 俺的博客：[PARAISLAND](https://blog.paraisland.top)

---

<div align="center">
  <p>Made with ❤️ by paracat</p>
  <p>如果这个项目对你有帮助，请给俺一个 ⭐️！</p>
</div>
