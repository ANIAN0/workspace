"""为本地 TursoDB 创建测试数据库。"""

import turso

# 创建测试数据库
conn = turso.connect("local_tursodb/test.db")

# 创建用户表
conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT,
        created_at INTEGER DEFAULT (strftime('%s', 'now'))
    )
""")

# 创建帖子表
conn.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT,
        created_at INTEGER DEFAULT (strftime('%s', 'now')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
""")

# 插入示例数据
conn.execute(
    "INSERT INTO users (username, email) VALUES (?, ?)", ("alice", "alice@example.com")
)
conn.execute(
    "INSERT INTO users (username, email) VALUES (?, ?)", ("bob", "bob@example.com")
)
conn.execute(
    "INSERT INTO users (username, email) VALUES (?, ?)",
    ("charlie", "charlie@example.com"),
)

# 插入示例帖子
conn.execute(
    "INSERT INTO posts (user_id, title, content) VALUES (?, ?, ?)",
    (1, "First Post", "This is Alice's first post"),
)
conn.execute(
    "INSERT INTO posts (user_id, title, content) VALUES (?, ?, ?)",
    (1, "Second Post", "This is Alice's second post"),
)
conn.execute(
    "INSERT INTO posts (user_id, title, content) VALUES (?, ?, ?)",
    (2, "Bob's Post", "This is Bob's first post"),
)

conn.commit()

# 验证数据
cursor = conn.execute("SELECT COUNT(*) FROM users")
user_count = cursor.fetchone()[0]

cursor = conn.execute("SELECT COUNT(*) FROM posts")
post_count = cursor.fetchone()[0]

print(f"测试数据库创建成功!")
print(f"  - 用户表: {user_count} 行")
print(f"  - 帖子表: {post_count} 行")

conn.close()
