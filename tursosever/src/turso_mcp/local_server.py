"""本地 TursoDB MCP 服务。"""

from typing import Any, Optional
from mcp.server.fastmcp import FastMCP
from .database import DatabaseManager

# 创建 MCP 服务
mcp = FastMCP("turso-local")

# 全局数据库管理器实例
db_manager = DatabaseManager()


@mcp.tool()
def open_database(path: str) -> dict[str, Any]:
    """打开本地 Turso 数据库。

    参数:
        path: 数据库文件路径（例如：'local_tursodb/test.db' 或 ':memory:'）

    返回:
        包含成功状态和消息的字典
    """
    return db_manager.open_database(path)


@mcp.tool()
def current_database() -> dict[str, Any]:
    """获取当前打开的数据库信息。

    返回:
        包含连接状态和数据库路径的字典
    """
    return db_manager.get_current_database()


@mcp.tool()
def list_tables() -> dict[str, Any]:
    """列出当前数据库中的所有表。

    返回:
        包含表名列表的字典
    """
    return db_manager.list_tables()


@mcp.tool()
def describe_table(table_name: str) -> dict[str, Any]:
    """获取指定表的结构信息。

    参数:
        table_name: 要查看结构的表名

    返回:
        包含列和索引信息的字典
    """
    return db_manager.describe_table(table_name)


@mcp.tool()
def execute_query(query: str, params: Optional[list] = None) -> dict[str, Any]:
    """执行只读的 SELECT 查询。

    参数:
        query: 要执行的 SQL SELECT 或 PRAGMA 查询
        params: 可选的查询参数列表

    返回:
        包含查询结果（列和行）的字典
    """
    return db_manager.execute_query(query, params)


@mcp.tool()
def insert_data(table: str, data: dict[str, Any]) -> dict[str, Any]:
    """向表中插入数据。

    参数:
        table: 要插入数据的表名
        data: 包含列名和值的字典

    返回:
        包含成功状态和行 ID 的字典
    """
    return db_manager.insert_data(table, data)


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
    return db_manager.update_data(table, data, where, where_params)


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
    return db_manager.delete_data(table, where, where_params)


@mcp.tool()
def schema_change(sql: str) -> dict[str, Any]:
    """执行模式修改语句（CREATE TABLE、ALTER TABLE、DROP TABLE）。

    参数:
        sql: 要执行的 DDL SQL 语句

    返回:
        包含成功状态的字典
    """
    return db_manager.schema_change(sql)


def main():
    """运行 MCP 服务。"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
