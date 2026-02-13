"""支持同步功能的云端 TursoDB MCP 服务。"""

import os
from typing import Any, Optional
from mcp.server.fastmcp import FastMCP
import turso.sync

# 创建 MCP 服务
mcp = FastMCP("turso-cloud")

# 云端数据库的全局连接
cloud_connection = None
cloud_config = {"path": None, "remote_url": None, "remote_auth_token": None}


@mcp.tool()
def open_database(
    path: str, remote_url: str, remote_auth_token: Optional[str] = None
) -> dict[str, Any]:
    """打开支持同步功能的云端 Turso 数据库。

    参数:
        path: 同步数据库的本地路径（例如：'cloud_tursodb/app.db'）
        remote_url: 远程 Turso 数据库 URL（例如：'libsql://mydb.turso.io'）
        remote_auth_token: 身份验证令牌（默认为 TURSO_AUTH_TOKEN 环境变量）

    返回:
        包含成功状态和消息的字典
    """
    global cloud_connection, cloud_config

    try:
        # 如果未提供令牌，则使用环境变量
        auth_token = remote_auth_token or os.environ.get("TURSO_AUTH_TOKEN")

        if not auth_token:
            return {
                "success": False,
                "error": "未提供身份验证令牌。请设置 TURSO_AUTH_TOKEN 环境变量或传入 remote_auth_token 参数。",
            }

        # 存储配置
        cloud_config["path"] = path
        cloud_config["remote_url"] = remote_url
        cloud_config["remote_auth_token"] = auth_token

        # 打开连接
        cloud_connection = turso.sync.connect(
            path=path, remote_url=remote_url, auth_token=auth_token
        )

        return {
            "success": True,
            "path": path,
            "remote_url": remote_url,
            "message": f"云端数据库打开成功: {path} -> {remote_url}",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "打开云端数据库失败",
        }


@mcp.tool()
def current_database() -> dict[str, Any]:
    """获取当前打开的云端数据库信息。

    返回:
        包含连接状态和数据库信息的字典
    """
    if cloud_connection is None:
        return {"connected": False, "message": "当前没有打开的云端数据库"}

    return {
        "connected": True,
        "local_path": cloud_config.get("path"),
        "remote_url": cloud_config.get("remote_url"),
        "message": f"已连接到云端数据库: {cloud_config.get('remote_url')}",
    }


@mcp.tool()
def list_tables() -> dict[str, Any]:
    """列出当前云端数据库中的所有表。

    返回:
        包含表名列表的字典
    """
    if cloud_connection is None:
        return {"success": False, "error": "当前没有打开的云端数据库"}

    try:
        cursor = cloud_connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]
        return {"success": True, "tables": tables, "count": len(tables)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def describe_table(table_name: str) -> dict[str, Any]:
    """获取指定表的结构信息。

    参数:
        table_name: 要查看结构的表名

    返回:
        包含列和索引信息的字典
    """
    if cloud_connection is None:
        return {"success": False, "error": "当前没有打开的云端数据库"}

    try:
        # 获取表信息
        cursor = cloud_connection.execute(f"PRAGMA table_info({table_name})")
        columns = []
        for row in cursor.fetchall():
            columns.append(
                {
                    "cid": row[0],
                    "name": row[1],
                    "type": row[2],
                    "notnull": bool(row[3]),
                    "default_value": row[4],
                    "pk": bool(row[5]),
                }
            )

        # 获取索引
        cursor = cloud_connection.execute(f"PRAGMA index_list({table_name})")
        indexes = []
        for row in cursor.fetchall():
            index_name = row[1]
            cursor2 = cloud_connection.execute(f"PRAGMA index_info({index_name})")
            index_columns = [r[2] for r in cursor2.fetchall()]
            indexes.append(
                {"name": index_name, "unique": bool(row[2]), "columns": index_columns}
            )

        return {
            "success": True,
            "table_name": table_name,
            "columns": columns,
            "indexes": indexes,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def execute_query(query: str, params: Optional[list] = None) -> dict[str, Any]:
    """执行只读的 SELECT 查询。

    参数:
        query: 要执行的 SQL SELECT 或 PRAGMA 查询
        params: 可选的查询参数列表

    返回:
        包含查询结果（列和行）的字典
    """
    if cloud_connection is None:
        return {"success": False, "error": "当前没有打开的云端数据库"}

    # 确保查询是只读的
    query_upper = query.strip().upper()
    if not query_upper.startswith("SELECT") and not query_upper.startswith("PRAGMA"):
        return {"success": False, "error": "只允许 SELECT 和 PRAGMA 查询"}

    try:
        if params:
            cursor = cloud_connection.execute(query, params)
        else:
            cursor = cloud_connection.execute(query)

        # 获取列名
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
        else:
            columns = []

        # 获取行数据
        rows = cursor.fetchall()

        # 转换为字典列表
        results = []
        for row in rows:
            result = {}
            for i, col in enumerate(columns):
                result[col] = row[i]
            results.append(result)

        return {
            "success": True,
            "columns": columns,
            "rows": results,
            "count": len(results),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def insert_data(table: str, data: dict[str, Any]) -> dict[str, Any]:
    """向表中插入数据。

    参数:
        table: 要插入数据的表名
        data: 包含列名和值的字典

    返回:
        包含成功状态和行 ID 的字典
    """
    if cloud_connection is None:
        return {"success": False, "error": "当前没有打开的云端数据库"}

    try:
        columns = list(data.keys())
        placeholders = ", ".join(["?" for _ in columns])
        columns_str = ", ".join(columns)

        query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
        values = [data[col] for col in columns]

        cloud_connection.execute(query, values)
        cloud_connection.commit()

        # 获取最后插入的行 ID
        cursor = cloud_connection.execute("SELECT last_insert_rowid()")
        last_id = cursor.fetchone()[0]

        return {
            "success": True,
            "message": f"数据成功插入到表 {table}",
            "row_id": last_id,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def update_data(
    table: str, data: dict[str, Any], where: str, where_params: Optional[list] = None
) -> dict[str, Any]:
    """更新表中已有的数据。

    参数:
        table: 要更新的表名
        data: 包含列名和新值的字典
        where: WHERE 子句条件
        where_params: WHERE 子句的可选参数

    返回:
        包含成功状态和受影响行数的字典
    """
    if cloud_connection is None:
        return {"success": False, "error": "当前没有打开的云端数据库"}

    try:
        set_clause = ", ".join([f"{col} = ?" for col in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"

        values = list(data.values())
        if where_params:
            values.extend(where_params)

        cursor = cloud_connection.execute(query, values)
        cloud_connection.commit()

        return {
            "success": True,
            "message": f"表 {table} 中的数据更新成功",
            "rows_affected": cursor.rowcount,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def delete_data(
    table: str, where: str, where_params: Optional[list] = None
) -> dict[str, Any]:
    """从表中删除数据。

    参数:
        table: 要删除数据的表名
        where: WHERE 子句条件
        where_params: WHERE 子句的可选参数

    返回:
        包含成功状态和受影响行数的字典
    """
    if cloud_connection is None:
        return {"success": False, "error": "当前没有打开的云端数据库"}

    try:
        query = f"DELETE FROM {table} WHERE {where}"

        if where_params:
            cursor = cloud_connection.execute(query, where_params)
        else:
            cursor = cloud_connection.execute(query)

        cloud_connection.commit()

        return {
            "success": True,
            "message": f"成功从表 {table} 中删除数据",
            "rows_affected": cursor.rowcount,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def schema_change(sql: str) -> dict[str, Any]:
    """执行模式修改语句（CREATE TABLE、ALTER TABLE、DROP TABLE）。

    参数:
        sql: 要执行的 DDL SQL 语句

    返回:
        包含成功状态的字典
    """
    if cloud_connection is None:
        return {"success": False, "error": "当前没有打开的云端数据库"}

    # 验证是否为 DDL 语句
    sql_upper = sql.strip().upper()
    allowed_prefixes = ["CREATE", "ALTER", "DROP"]

    if not any(sql_upper.startswith(prefix) for prefix in allowed_prefixes):
        return {
            "success": False,
            "error": "只允许 CREATE、ALTER 和 DROP 语句",
        }

    try:
        cloud_connection.execute(sql)
        cloud_connection.commit()

        return {"success": True, "message": "模式修改执行成功"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def push() -> dict[str, Any]:
    """将本地更改推送到云端。

    返回:
        包含成功状态的字典
    """
    if cloud_connection is None:
        return {"success": False, "error": "当前没有打开的云端数据库"}

    try:
        cloud_connection.push()
        return {"success": True, "message": "更改成功推送到云端"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def pull() -> dict[str, Any]:
    """从云端拉取远程更改。

    返回:
        包含成功状态和是否收到更改的字典
    """
    if cloud_connection is None:
        return {"success": False, "error": "当前没有打开的云端数据库"}

    try:
        changed = cloud_connection.pull()
        return {
            "success": True,
            "changed": changed,
            "message": f"从云端拉取更改: {changed}",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def checkpoint() -> dict[str, Any]:
    """压缩本地 WAL 以限制磁盘使用。

    返回:
        包含成功状态的字典
    """
    if cloud_connection is None:
        return {"success": False, "error": "当前没有打开的云端数据库"}

    try:
        cloud_connection.checkpoint()
        return {"success": True, "message": "检查点完成"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def sync_stats() -> dict[str, Any]:
    """获取同步统计信息。

    返回:
        包含同步统计信息的字典
    """
    if cloud_connection is None:
        return {"success": False, "error": "当前没有打开的云端数据库"}

    try:
        stats = cloud_connection.stats()
        return {
            "success": True,
            "stats": {
                "cdc_operations": stats.cdc_operations,
                "main_wal_size": stats.main_wal_size,
                "revert_wal_size": stats.revert_wal_size,
                "network_received_bytes": stats.network_received_bytes,
                "network_sent_bytes": stats.network_sent_bytes,
                "last_pull_unix_time": stats.last_pull_unix_time,
                "last_push_unix_time": stats.last_push_unix_time,
                "revision": stats.revision,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    """运行 MCP 服务。"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
