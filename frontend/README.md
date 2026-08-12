# 天水平台前端

## 启动

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 3000
```

默认访问地址：

- `http://localhost:3000`

## 构建

```powershell
cd frontend
npm run build
```

构建产物输出到 `frontend/dist`。

## 后端联调

- 开发环境默认通过 Vite 代理访问 Django：`http://127.0.0.1:8000`
- 如需修改代理目标，可配置环境变量 `VITE_PROXY_TARGET`
- 如需前端直连接口前缀，可配置 `VITE_API_BASE_URL`

示例：

```text
VITE_PROXY_TARGET=http://127.0.0.1:8000
VITE_API_BASE_URL=/api
```

## 交付说明

- 交付机器上优先使用根目录 `start_dev.ps1` 一键启动前后端。
- 若前端页面打开但接口失败，优先检查后端 `8000` 端口、浏览器控制台和 Django 日志。
