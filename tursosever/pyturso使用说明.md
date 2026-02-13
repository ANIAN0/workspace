# Pyturso 使用说明

## 安装

```bash
uv pip install pyturso
```

---

## 版本一：本地数据库

适用于不需要云端同步的纯本地 SQLite 数据库操作。

### 基础用法

```python
import turso

# 连接到本地数据库文件
con = turso.connect("sqlite.db")

# 或使用内存数据库
# con = turso.connect(":memory:")

# 创建游标
cur = con.cursor()

# 创建表
cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL
    )
""")
con.commit()

# 插入数据
cur.execute("INSERT INTO users (username) VALUES (?)", ("alice",))
cur.execute("INSERT INTO users (username) VALUES (?)", ("bob",))
con.commit()

# 查询数据
res = cur.execute("SELECT * FROM users")
users = res.fetchall()
print(users)

# 关闭连接
con.close()
```

### 异步用法

```python
import asyncio
import turso.aio

async def main():
    # 连接数据库（支持 async with）
    async with turso.aio.connect(":memory:") as conn:
        # 执行多条语句
        await conn.executescript("""
            CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT);
            INSERT INTO t(name) VALUES ('alice'), ('bob');
        """)
        
        # 使用游标进行参数化查询
        cur = conn.cursor()
        await cur.execute("SELECT COUNT(*) FROM t WHERE name LIKE ?", ("a%",))
        count = (await cur.fetchone())[0]
        print(count)
        
        # 支持 JSON 和 generate_series
        await cur.execute("SELECT SUM(value) FROM generate_series(1, 10)")
        print((await cur.fetchone())[0])  # 输出: 55

asyncio.run(main())
```

### 特性

- **SQLite 兼容**: 支持 SQLite 查询语法和文件格式
- **进程内运行**: 无网络开销，直接在 Python 进程中运行
- **跨平台**: 支持 Linux、macOS、Windows
- **异步支持**: 内置 asyncio 集成，查询不会阻塞事件循环

---

## 版本二：同步云端数据库

适用于需要与 Turso Cloud 同步的本地数据库，支持离线使用和在线同步。

### 前置准备

1. 安装 Turso CLI 并创建数据库
2. 获取数据库 URL：`turso db show <db-name> --url`
3. 创建访问令牌：`turso db tokens create <db-name>`

### 基础同步用法

```python
import os
import turso.sync

# 连接本地数据库到远程 Turso 数据库
conn = turso.sync.connect(
    path="./app.db",                                  # 本地数据库路径
    remote_url="libsql://<db-name>.turso.io",         # 远程数据库 URL
    remote_auth_token=os.environ["TURSO_AUTH_TOKEN"], # 身份验证令牌
    # long_poll_timeout_ms=10_000,                    # 可选：服务器等待拉取的超时时间
    # bootstrap_if_empty=False,                       # 可选：首次运行时不从远程引导
)

# 创建表并插入数据
conn.execute("CREATE TABLE IF NOT EXISTS notes(id TEXT PRIMARY KEY, body TEXT)")
conn.commit()
conn.execute("INSERT INTO notes VALUES ('n1', 'hello')")
conn.commit()

# 推送本地更改到远程
conn.push()

# 拉取远程更改到本地
changed = conn.pull()
print("拉取的更改:", changed)  # 如果有新更改返回 True

# 查询数据
rows = conn.execute("SELECT * FROM notes").fetchall()
print(rows)

# 检查点（压缩本地 WAL）
conn.checkpoint()

# 查看同步统计信息
stats = conn.stats()
print({
    "cdc_operations": stats.cdc_operations,
    "main_wal_size": stats.main_wal_size,
    "revert_wal_size": stats.revert_wal_size,
    "network_received_bytes": stats.network_received_bytes,
    "network_sent_bytes": stats.network_sent_bytes,
    "last_pull_unix_time": stats.last_pull_unix_time,
    "last_push_unix_time": stats.last_push_unix_time,
    "revision": stats.revision,
})

conn.close()
```

### 部分同步（Partial Sync）

减少初始网络开销，按需加载数据库页面：

#### 前缀引导（Prefix Bootstrap）

下载数据库文件的前 N 字节作为初始数据：

```python
import turso.sync

conn = turso.sync.connect(
    path="./app.db",
    remote_url="libsql://<db-name>.turso.io",
    remote_auth_token=os.environ["TURSO_AUTH_TOKEN"],
    partial_sync_opts=turso.sync.PartialSyncOpts(
        bootstrap_strategy=turso.sync.PartialSyncPrefixBootstrap(length=128 * 1024),  # 128 KiB
    ),
)
```

#### 查询引导（Query Bootstrap）

只下载特定查询相关的数据页面：

```python
import turso.sync

conn = turso.sync.connect(
    path="./app.db",
    remote_url="libsql://<db-name>.turso.io",
    remote_auth_token=os.environ["TURSO_AUTH_TOKEN"],
    partial_sync_opts=turso.sync.PartialSyncOpts(
        bootstrap_strategy=turso.sync.PartialSyncQueryBootstrap(
            query="SELECT * FROM messages WHERE user_id = 'u_123' LIMIT 100"
        ),
    ),
)
```

#### 高级选项

```python
conn = turso.sync.connect(
    path="./app.db",
    remote_url="libsql://<db-name>.turso.io",
    remote_auth_token=os.environ["TURSO_AUTH_TOKEN"],
    partial_sync_opts=turso.sync.PartialSyncOpts(
        bootstrap_strategy=turso.sync.PartialSyncPrefixBootstrap(length=128 * 1024),
        segment_size=16 * 1024,  # 设置段大小（批量读取）
        prefetch=True,            # 启用预取优化
    ),
)
```

### 异步同步用法

```python
import asyncio
import turso.aio.sync

async def main():
    conn = await turso.aio.sync.connect(
        ":memory:", 
        remote_url="libsql://<db-name>.turso.io",
        remote_auth_token=os.environ["TURSO_AUTH_TOKEN"],
    )
    
    # 读取数据
    rows = await (await conn.execute("SELECT * FROM t")).fetchall()
    print(rows)
    
    # 拉取和推送
    await conn.pull()
    await conn.execute("INSERT INTO t VALUES ('hello from asyncio')")
    await conn.commit()
    await conn.push()
    
    # 统计信息和维护
    stats = await conn.stats()
    print("Main WAL size:", stats.main_wal_size)
    await conn.checkpoint()
    
    await conn.close()

asyncio.run(main())
```

### 同步工作原理

#### Push（推送）
- 将本地更改发送到 Turso Cloud
- 冲突策略："最后推送获胜"
- 逻辑语句级别同步

#### Pull（拉取）
- 获取远程更改并应用到本地
- 如果有未推送的本地更改：
  1. 回滚到上次同步状态
  2. 应用远程更改
  3. 重放本地更改
- 返回布尔值表示是否有更改

#### Checkpoint（检查点）
- 压缩本地 WAL（预写日志）
- 限制磁盘使用
- 必须手动调用（自动检查点已禁用）

### 最佳实践

1. **定期推送**: 及时将本地更改推送到云端
2. **拉取前推送**: 在拉取前先推送本地更改，减少冲突
3. **定期检查点**: 大量写入后调用 `checkpoint()` 回收磁盘空间
4. **监控 WAL 大小**: 使用 `stats().main_wal_size` 监控并适时检查点
5. **使用部分同步**: 大数据库使用 Partial Sync 减少初始加载时间

### 注意事项

- **Beta 版本**: 软件处于测试阶段，生产环境请务必备份
- **首次连接**: 默认会从远程引导数据，远程必须可访问
- **冲突解决**: 使用 "最后推送获胜" 策略
- **离线支持**: 支持完全离线操作，联网后同步

---

## SQL 语言参考

Turso 旨在完全兼容 SQLite，支持标准 SQL 语法。

### 支持的 SQL 语句

#### 数据定义（DDL）

```sql
-- 创建表
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT,
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- 修改表
ALTER TABLE users RENAME TO customers;
ALTER TABLE customers ADD COLUMN phone TEXT;
ALTER TABLE customers DROP COLUMN phone;

-- 创建索引（实验性功能）
CREATE INDEX idx_username ON users(username);

-- 删除索引和表
DROP INDEX idx_username;
DROP TABLE users;
```

#### 数据操作（DML）

```sql
-- 插入数据
INSERT INTO users (username, email) VALUES ('alice', 'alice@example.com');
INSERT INTO users VALUES (1, 'bob', 'bob@example.com', 1704067200);

-- 批量插入
INSERT INTO users (username) VALUES ('user1'), ('user2'), ('user3');

-- 查询数据
SELECT * FROM users;
SELECT username, email FROM users WHERE id > 1;
SELECT * FROM users ORDER BY created_at DESC LIMIT 10;
SELECT COUNT(*) FROM users GROUP BY status;

-- 更新数据
UPDATE users SET email = 'new@example.com' WHERE id = 1;

-- 删除数据
DELETE FROM users WHERE id = 1;
```

---

## 事务类型

Turso 支持三种事务类型，可通过 `BEGIN` 语句指定：

### 1. DEFERRED（默认）

```python
# 默认模式，事务开始时无锁
conn.execute("BEGIN DEFERRED TRANSACTION")
# 或简写
conn.execute("BEGIN")

# 首次读操作开始读事务
conn.execute("SELECT * FROM users")

# 首次写操作升级为写事务
conn.execute("INSERT INTO users VALUES (?)", ("alice",))
conn.commit()
```

- 事务开始时处于挂起状态，不立即获取锁
- 首次读操作开始读事务，首次写操作升级为写事务
- 允许多个读事务并发，但同一时间只允许一个写事务

### 2. IMMEDIATE / EXCLUSIVE

```python
# 立即获取写锁
conn.execute("BEGIN IMMEDIATE TRANSACTION")
# 或
conn.execute("BEGIN EXCLUSIVE TRANSACTION")

conn.execute("INSERT INTO users VALUES (?)", ("bob",))
conn.commit()
```

- 事务开始时立即获取保留写锁
- 阻止其他写事务并发，但允许读事务
- `EXCLUSIVE` 是 `IMMEDIATE` 的别名

### 3. CONCURRENT（MVCC 模式）

```sql
-- 先启用 MVCC 模式
PRAGMA journal_mode = experimental_mvcc;

-- 使用并发事务
BEGIN CONCURRENT TRANSACTION;
```

```python
# MVCC 模式下允许多个读写事务并发
conn.execute("PRAGMA journal_mode = experimental_mvcc")
conn.execute("BEGIN CONCURRENT TRANSACTION")
conn.execute("UPDATE users SET name = 'new_name' WHERE id = 1")
conn.commit()  # 提交时检测冲突，如冲突返回 SQLITE_BUSY
```

**特性：**
- 允许多个读写事务真正并发执行
- 提供快照隔离级别（Snapshot Isolation）
- 提交时进行行级冲突检测
- 冲突时返回 `SQLITE_BUSY` 错误，应用需重试

**MVCC 限制：**
- 不支持索引创建和使用
- 大数据库首次加载需全部载入内存
- 仅支持 `PRAGMA wal_checkpoint(TRUNCATE)`
- 某些功能可能无法工作或导致 panic
- 从 MVCC 切换回 WAL 模式需先 checkpoint

---

## 高级功能

### 向量搜索（Vector Search）

Turso 支持向量搜索，适用于语义搜索、推荐系统等场景。

#### 向量类型

| 类型 | 说明 | 存储 |
|------|------|------|
| `vector32` | 32位浮点密集向量 | 4字节/维度 |
| `vector64` | 64位浮点密集向量 | 8字节/维度 |
| `vector32_sparse` | 32位浮点稀疏向量 | 仅存储非零值 |

#### 创建向量

```python
# 创建密集向量
conn.execute("""
    CREATE TABLE documents (
        id INTEGER PRIMARY KEY,
        content TEXT,
        embedding BLOB
    )
""")

# 插入向量数据
conn.execute("""
    INSERT INTO documents (content, embedding) 
    VALUES ('Machine learning basics', vector32('[0.2, 0.5, 0.1, 0.8]'))
""")
conn.commit()
```

#### 距离函数

```python
# 余弦距离（0=相同方向，2=相反方向）
query = vector32('[0.25, 0.55, 0.15, 0.75]')
rows = conn.execute("""
    SELECT content, vector_distance_cos(embedding, vector32(?)) AS distance
    FROM documents
    ORDER BY distance
    LIMIT 5
""", (str(query),)).fetchall()

# 欧氏距离
rows = conn.execute("""
    SELECT content, vector_distance_l2(embedding, vector32(?)) AS distance
    FROM documents
    ORDER BY distance
    LIMIT 5
""", (str(query),)).fetchall()

# Jaccard 距离（适合稀疏向量）
rows = conn.execute("""
    SELECT content, vector_distance_jaccard(sparse_embedding, vector32_sparse(?)) AS distance
    FROM documents
    ORDER BY distance
    LIMIT 5
""", (str(sparse_vector),)).fetchall()
```

#### 向量工具函数

```sql
-- 向量拼接
SELECT vector_concat(vector32('[1.0, 2.0]'), vector32('[3.0, 4.0]'));
-- 结果: [1.0, 2.0, 3.0, 4.0]

-- 向量切片
SELECT vector_slice(vector32('[1.0, 2.0, 3.0, 4.0, 5.0]'), 1, 4);
-- 结果: [2.0, 3.0, 4.0]

-- 提取向量显示
SELECT vector_extract(embedding) FROM documents;
```

### 全文搜索（FTS - 实验性）

基于 Tantivy 搜索引擎的全文搜索功能。

#### 创建 FTS 索引

```python
# 创建表
conn.execute("""
    CREATE TABLE articles (
        id INTEGER PRIMARY KEY,
        title TEXT,
        content TEXT,
        category TEXT
    )
""")

# 创建 FTS 索引（需编译时启用 fts 特性）
conn.execute("""
    CREATE INDEX idx_articles ON articles USING fts (title, content)
    WITH (tokenizer = 'default', weights = 'title=2.0,content=1.0')
""")
conn.commit()
```

#### 分词器选项

| 分词器 | 说明 | 适用场景 |
|--------|------|---------|
| `default` | 小写、标点分割、40字符限制 | 通用英文文本 |
| `raw` | 无分词，精确匹配 | ID、UUID、标签 |
| `simple` | 基础空白/标点分割 | 不分词的简单文本 |
| `whitespace` | 仅空白分割 | 空格分隔的令牌 |
| `ngram` | 2-3 字符 n-grams | 自动补全、子串匹配 |

#### FTS 查询

```python
# 基本搜索
rows = conn.execute("""
    SELECT id, title 
    FROM articles 
    WHERE fts_match(title, content, 'database')
""").fetchall()

# 带相关性评分
rows = conn.execute("""
    SELECT 
        id, 
        title, 
        fts_score(title, content, 'Rust database') AS score
    FROM articles
    WHERE fts_match(title, content, 'Rust database')
    ORDER BY score DESC
    LIMIT 10
""").fetchall()

# 高亮匹配文本
rows = conn.execute("""
    SELECT 
        id,
        title,
        fts_highlight(content, '<mark>', '</mark>', 'database') AS snippet
    FROM articles
    WHERE fts_match(title, content, 'database')
""").fetchall()
```

#### FTS 查询语法

```python
# AND / OR / NOT
query = "database AND sql"
query = "database NOT nosql"

# 短语搜索
query = '"full text search"'

# 前缀搜索
query = "data*"

# 列过滤
query = "title:database"

# 加权
query = "title:database^2"
```

#### 索引优化

```sql
-- 优化特定索引
OPTIMIZE INDEX idx_articles;

-- 优化所有 FTS 索引
OPTIMIZE INDEX;
```

**FTS 限制：**
- 不使用 `MATCH` 操作符，使用 `fts_match()` 函数
- 事务内不支持读自己的写入，FTS 变更仅在 COMMIT 后可见

### CDC（Change Data Capture - 实验性）

实时追踪和记录数据库变更。

#### 启用 CDC

```python
# 启用 CDC（full 模式记录前后状态）
conn.execute("PRAGMA unstable_capture_data_changes_conn('full')")

# 其他模式：'id', 'before', 'after', 'off'
# 可指定自定义表名：'full,my_cdc_table'
```

#### CDC 表结构

启用后自动创建 `turso_cdc` 表：

| 列名 | 类型 | 说明 |
|------|------|------|
| `change_id` | INTEGER | 单调递增主键 |
| `change_time` | INTEGER | Unix 时间戳（秒） |
| `change_type` | INTEGER | 1=INSERT, 0=UPDATE, -1=DELETE |
| `table_name` | TEXT | 表名 |
| `id` | INTEGER | 受影响行的 rowid |
| `before` | BLOB | 更新/删除前的行状态 |
| `after` | BLOB | 插入/更新后的行状态 |
| `updates` | BLOB | 变更详细信息 |

#### 查询 CDC 记录

```python
# 查看所有变更
rows = conn.execute("SELECT * FROM turso_cdc").fetchall()

# 查看特定表的变更
rows = conn.execute("""
    SELECT change_id, change_time, change_type, table_name, id
    FROM turso_cdc
    WHERE table_name = 'users'
    ORDER BY change_id DESC
""").fetchall()
```

**CDC 注意事项：**
- CDC 记录在事务提交前可见
- 失败操作（约束违反）不会记录
- CDC 表本身变更也会被记录
- 不支持 `WITHOUT ROWID` 表
- Full 模式下频繁更新会增加磁盘 I/O

### 加密（实验性）

数据库加密功能，需使用 `--experimental-encryption` 标志。

#### 支持的算法

- AES-GCM (128/256-bit)
- AEGIS-256 / AEGIS-256-X2 / AEGIS-256-X4
- AEGIS-128L / AEGIS-128-X2 / AEGIS-128-X4

#### 生成密钥

```bash
openssl rand -hex 32
# 输出: 2d7a30108d3eb3e45c90a732041fe54778bdcf707c76749fab7da335d1b39c1d
```

#### 使用加密

```python
# 方法1: 使用 PRAGMA
conn.execute("PRAGMA cipher = 'aegis256'")
conn.execute("PRAGMA hexkey = '2d7a30108d3eb3e45c90a732041fe54778bdcf707c76749fab7da335d1b39c1d'")

# 方法2: 使用 URI（推荐用于重新打开加密数据库）
# 连接字符串格式：
# file:database.db?cipher=aegis256&hexkey=32字节十六进制密钥
```

**注意：** 重新打开已加密的数据库必须使用 URI 格式提供 cipher 和 hexkey 参数。

### Journal Mode

控制事务日志和并发模式。

```python
# 查询当前模式
result = conn.execute("PRAGMA journal_mode").fetchone()
print(result[0])  # 输出: wal

# 切换到 WAL 模式（默认）
conn.execute("PRAGMA journal_mode = wal")

# 切换到 MVCC 模式（实验性）
conn.execute("PRAGMA journal_mode = experimental_mvcc")
```

| 模式 | 说明 |
|------|------|
| `wal` | 写前日志模式，良好的读写并发（默认） |
| `experimental_mvcc` | 多版本并发控制，支持快照隔离（实验性） |

**注意：** 传统 SQLite 模式（delete, truncate, persist, memory, off）不被支持。

---

## 限制和兼容性

### 一般限制

Turso 旨在完全兼容 SQLite，但存在以下限制：

| 限制 | 说明 |
|------|------|
| 查询结果顺序 | 不保证与 SQLite 相同 |
| 多进程访问 | ❌ 不支持 |
| 多线程 | ❌ 不支持 |
| Savepoints | ❌ 不支持 |
| Triggers | ❌ 不支持 |
| Views | ❌ 不支持（有实验性标志） |
| Vacuum | ❌ 不支持 |
| 字符编码 | 仅支持 UTF-8 |
| 索引 | 实验性功能 |
| FTS | 需编译时启用 fts 特性 |

### MVCC 特定限制

- 不支持索引创建和使用带索引的数据库
- 大数据库首次访问需全部加载到内存（启动慢、内存占用高）
- 仅支持 `PRAGMA wal_checkpoint(TRUNCATE)` 且阻塞读写
- 某些功能可能无法工作或导致 panic
- 查询可能返回错误结果
- MVCC 写入后非 MVCC 模式打开需先 checkpoint

### 版本兼容性

- 旧版 SQLite 数据库打开时自动转换为 WAL 模式
- 切换 Journal Mode 会触发 checkpoint

---

## 两种版本对比

| 特性 | 本地数据库 | 同步云端数据库 |
|------|-----------|--------------|
| 模块 | `turso` / `turso.aio` | `turso.sync` / `turso.aio.sync` |
| 云端同步 | ❌ | ✅ |
| 离线使用 | ✅ | ✅ |
| 连接参数 | 数据库路径 | 路径 + 远程URL + 令牌 |
| 额外方法 | 无 | `push()`, `pull()`, `checkpoint()`, `stats()` |
| 适用场景 | 纯本地应用 | 需要多端同步的应用 |

---

## 参考资料

- [官方文档](https://docs.turso.tech)
- [GitHub Issues](https://github.com/tursodatabase/turso/issues)
- [Discord 社区](https://tur.so/discord)
