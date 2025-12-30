# 🐳 Docker 部署指南

一键启动 AAA-StoryMaker，无需配置 Python 环境。

## 📋 前置要求

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac)
- 或 Docker + Docker Compose (Linux)
- LLM API 密钥（OpenRouter / 智谱清言 / OpenAI 任选其一）

## 🚀 快速启动

### Windows 用户

```powershell
# 1. 双击 start.bat
# 或在命令行运行：
.\start.bat
```

### Linux / Mac 用户

```bash
# 1. 添加执行权限
chmod +x start.sh

# 2. 运行启动脚本
./start.sh
```

### 手动启动

```bash
# 1. 复制环境配置文件
cp template.env .env

# 2. 编辑 .env，填入API密钥
# 推荐使用 OpenRouter (可用 Gemini 免费模型)
# OPENROUTER_API_KEY=your_key_here

# 3. 启动服务
docker-compose up --build

# 4. 访问
# 前端: http://localhost:3000
# 后端: http://localhost:8000
```

## 🎮 使用流程

1. 打开浏览器访问 `http://localhost:3000`
2. 选择一个故事世界（如：江城市、白鹿原）
3. 输入玩家名称，开始游戏
4. 在输入框中输入你的行动，与故事互动

## 📁 数据持久化

以下目录会被挂载到容器外部，数据不会丢失：

| 目录 | 说明 |
|------|------|
| `data/novels/` | 小说源文件 |
| `data/worlds/` | 解析后的世界数据 |
| `data/runtime/` | 游戏运行时存档 |
| `logs/` | 运行日志 |

## 🛠️ 常用命令

```bash
# 查看运行状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 仅查看后端日志
docker-compose logs -f backend

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 重新构建（代码更新后）
docker-compose up --build -d
```

## 🔧 配置说明

### 环境变量 (.env)

```env
# LLM 提供商选择
LLM_PROVIDER=openrouter  # 可选: openrouter, zhipu, openai

# OpenRouter (推荐，支持 Gemini)
OPENROUTER_API_KEY=your_key
OPENROUTER_MODEL=google/gemini-2.0-flash-001

# 智谱清言
ZHIPU_API_KEY=your_key

# OpenAI
OPENAI_API_KEY=your_key
```

### 端口配置

默认端口：
- 前端: `3000`
- 后端: `8000`

如需修改，编辑 `docker-compose.yml` 中的 `ports` 配置。

## 🐛 常见问题

### Q: 启动失败，提示端口被占用
```bash
# 检查占用端口的进程
netstat -ano | findstr :3000
netstat -ano | findstr :8000

# 修改 docker-compose.yml 中的端口映射
ports:
  - "3001:80"  # 改为其他端口
```

### Q: 后端API连接失败
检查 `.env` 文件中的 API 密钥是否正确配置。

### Q: 没有可用的故事世界
需要先添加小说并运行创世组生成世界数据：
```bash
# 进入后端容器
docker-compose exec backend bash

# 运行创世组
python run_world_builder.py --novel your_novel.txt
```

## 📊 资源占用

| 组件 | 内存 | 磁盘 |
|------|------|------|
| 后端 | ~500MB | ~1GB |
| 前端 | ~100MB | ~200MB |
| 总计 | ~600MB | ~1.2GB |

## 🔄 更新版本

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up --build -d
```

