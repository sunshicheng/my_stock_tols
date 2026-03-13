/** PM2 进程配置，用于在服务器上管理后端服务。使用方式见 README。 */
module.exports = {
  apps: [
    {
      name: 'stock-api',
      script: 'python',
      args: '-m uvicorn backend.main:app --host 0.0.0.0 --port 8000',
      cwd: __dirname,
      interpreter: 'none',
      /** 若使用虚拟环境，改为 venv 下 Python 路径，例如：.venv/bin/python */
      // interpreter: '/path/to/my_stock_tols/.venv/bin/python',
      env: { PYTHONUNBUFFERED: '1' },
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
    },
  ],
};
