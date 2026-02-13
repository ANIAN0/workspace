# TursoDB MCP Services

基于 Model Context Protocol (MCP) 的 TursoDB 数据库服务，包含本地数据库和云端同步数据库两个版本。

## 项目结构

```
tursosever/
├── local_tursodb/          # 本地 TursoDB 数据目录
│   └── test.db            # 测试数据库（已创建）
├── cloud_tursodb/          # 云端 TursoDB 数据目录
├── src/turso_mcp/          # MCP 服务源代码
│   ├── __init__.py
│   ├── database.py        # 数据库管理类（共享）
│   ├── local_server.py    # 本地 MCP 服务
│   └── cloud_server.py    # 云端 MCP 服务
├── create_test_db.py      # 测试数据库创建脚本
├── pyproject.toml         # 项目配置
└── README.md              # 本文件
```

## 安装依赖

```bash
uv pip install -e "."
```

## MCP 服务工具列表

### 通用工具（本地和云端都支持）

1. **open_database** - 打开数据库连接
2. **current_database** - 获取当前数据库信息
3. **list_tables** - 列出所有表
4. **describe_table** - 查看表结构
5. **execute_query** - 执行只读 SELECT 查询
6. **insert_data** - 插入数据
7. **update_data** - 更新数据
8. **delete_data** - 删除数据
9. **schema_change** - 执行 DDL 语句（CREATE/ALTER/DROP）

### 云端特有工具

10. **push** - 推送本地更改到云端
11. **pull** - 拉取云端更改到本地
12. **checkpoint** - 压缩本地 WAL
13. **sync_stats** - 获取同步统计信息

## 在其他项目中使用

本项目的 MCP 服务可以通过以下方式在其他项目中使用：

### 方法1：克隆并安装（推荐）

```bash
# 克隆仓库到任意位置
git clone <repository-url> /path/to/turso-mcp
cd /path/to/turso-mcp

# 安装依赖
uv pip install -e "."

# 现在可以在任何项目中使用以下命令启动 MCP 服务
uv run turso-local-mcp
uv run turso-cloud-mcp
```

### 方法2：在 Python 项目中作为依赖

在你的项目的 `pyproject.toml` 中添加：

```toml
[tool.uv.sources]
turso-mcp = { path = "/absolute/path/to/turso-mcp" }

[project.dependencies]
turso-mcp = { path = "/absolute/path/to/turso-mcp" }
```

然后运行 `uv pip install -e .` 安装。

### 方法3：在 OpenCode 中配置

在项目的 `opencode.json` 或 `opencode.jsonc` 中添加：

```json
{
  "mcp": {
    "turso-local": {
      "type": "local",
      "command": ["uv", "run", "--project", "/absolute/path/to/turso-mcp", "turso-local-mcp"],
      "enabled": true
    },
    "turso-cloud": {
      "type": "local",
      "command": ["uv", "run", "--project", "/absolute/path/to/turso-mcp", "turso-cloud-mcp"],
      "enabled": true,
      "environment": {
        "TURSO_AUTH_TOKEN": "{env:TURSO_AUTH_TOKEN}"
      }
    }
  }
}
```

### 方法4：在 Claude Desktop 中配置

编辑 Claude Desktop 的配置文件（通常位于 `~/.config/claude/config.json`）：

```json
{
  "mcpServers": {
    "turso-local": {
      "command": "uv",
      "args": ["run", "--project", "/absolute/path/to/turso-mcp", "turso-local-mcp"],
      "env": {}
    },
    "turso-cloud": {
      "command": "uv",
      "args": ["run", "--project", "/absolute/path/to/turso-mcp", "turso-cloud-mcp"],
      "env": {
        "TURSO_AUTH_TOKEN": "your-auth-token"
      }
    }
  }
}
```

### 方法5：直接运行（无需安装）

```bash
# 直接从仓库运行，无需安装
uv run --project /path/to/turso-mcp turso-local-mcp
uv run --project /path/to/turso-mcp turso-cloud-mcp
```

## 使用方法

### 本地 MCP 服务

启动本地 MCP 服务：

```bash
uv run turso-local-mcp
```

或在 Claude Desktop 中配置：

```json
{
  "mcpServers": {
    "turso-local": {
      "command": "uv",
      "args": ["run", "turso-local-mcp"],
      "env": {}
    }
  }
}
```

### 云端 MCP 服务

云端服务需要配置 Turso Cloud 的认证信息：

**方式1：环境变量**

```bash
export TURSO_AUTH_TOKEN="your-auth-token"
uv run turso-cloud-mcp
```

**方式2：Claude Desktop 配置**

```json
{
  "mcpServers": {
    "turso-cloud": {
      "command": "uv",
      "args": ["run", "turso-cloud-mcp"],
      "env": {
        "TURSO_AUTH_TOKEN": "your-auth-token"
      }
    }
  }
}
```

## 测试数据库

已创建的测试数据库包含：

- **users 表**: 3 条测试用户数据
- **posts 表**: 3 条测试帖子数据

可以使用以下 SQL 测试：

```sql
-- 列出所有表
.list_tables

-- 查看 users 表结构
.describe_table table_name="users"

-- 查询所有用户
.execute_query query="SELECT * FROM users"

-- 查询用户的帖子
.execute_query query="SELECT u.username, p.title FROM users u JOIN posts p ON u.id = p.user_id"
```

## 工具使用示例

### 打开数据库

```python
# 本地数据库
open_database(path="local_tursodb/test.db")

# 云端数据库
open_database(
    path="cloud_tursodb/app.db",
    remote_url="libsql://your-db.turso.io",
    remote_auth_token="your-token"  # 或从环境变量读取
)
```

### 查询数据

```python
# 简单查询
execute_query(query="SELECT * FROM users")

# 带参数的查询
execute_query(
    query="SELECT * FROM users WHERE username = ?",
    params=["alice"]
)
```

### 插入数据

```python
insert_data(
    table="users",
    data={
        "username": "david",
        "email": "david@example.com"
    }
)
```

### 更新数据

```python
update_data(
    table="users",
    data={"email": "newalice@example.com"},
    where="username = ?",
    where_params=["alice"]
)
```

### 删除数据

```python
delete_data(
    table="users",
    where="username = ?",
    where_params=["david"]
)
```

### 修改表结构

```python
# 创建新表
schema_change(sql="""
    CREATE TABLE comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        created_at INTEGER DEFAULT (strftime('%s', 'now'))
    )
""")

# 添加列
schema_change(sql="ALTER TABLE users ADD COLUMN age INTEGER")

# 删除表
schema_change(sql="DROP TABLE comments")
```

### 云端同步

```python
# 推送本地更改到云端
push()

# 拉取云端更改到本地
pull()

# 压缩 WAL
checkpoint()

# 查看同步统计
sync_stats()
```

## 注意事项

1. **Beta 版本**: Turso 处于测试阶段，生产环境请务必备份
2. **本地服务**: 纯本地 SQLite 兼容数据库，无需网络
3. **云端服务**: 支持离线使用和在线同步，需要 Turso Cloud 账号
4. **事务**: 支持 DEFERRED、IMMEDIATE 和 CONCURRENT (MVCC) 三种事务模式
5. **查询限制**: `execute_query` 只允许 SELECT 和 PRAGMA 语句

## 已知问题

### 1. 云端数据库连接参数名问题 ⚠️

**问题描述**: 官方文档中 `turso.sync.connect()` 函数的参数名为 `remote_auth_token`，但实际代码使用的是 `auth_token`。

**官方文档示例**:
```python
conn = turso.sync.connect(
    path="./app.db",
    remote_url="libsql://...",
    remote_auth_token=os.environ["TURSO_AUTH_TOKEN"],  # 文档写的是这个
)
```

**实际可用代码**:
```python
conn = turso.sync.connect(
    path="./app.db",
    remote_url="libsql://...",
    auth_token=os.environ["TURSO_AUTH_TOKEN"],  # 实际用这个
)
```

**解决方案**: 代码中已将工具参数保持为 `remote_auth_token`（与文档一致），但内部调用时转换为 `auth_token`。

### 2. 云端数据库 describe_table 工具限制 ⚠️

**问题描述**: 在云端同步数据库上使用 `describe_table` 工具时，可能会报错：
```
Parse error: Not a valid pragma name
```

**原因**: 云端同步数据库不支持某些 PRAGMA 查询（如 `PRAGMA table_info`、`PRAGMA index_list`）。

**解决方案**: 使用 `execute_query` 工具代替：
```sql
-- 查看表结构
PRAGMA table_info(table_name)

-- 或使用 sqlite_master
SELECT sql FROM sqlite_master WHERE type='table' AND name='table_name'
```

## 参考资料

- [Turso 官方文档](https://docs.turso.tech)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [pyturso 文档](https://github.com/tursodatabase/turso)
