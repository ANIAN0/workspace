"""TursoDB MCP 服务的共享数据库工具类。"""

from typing import Any, Optional
import turso


class DatabaseManager:
    """管理 Turso 数据库连接和操作。"""

    def __init__(self):
        self.connection: Optional[turso.Connection] = None
        self.db_path: Optional[str] = None

    def open_database(self, path: str) -> dict[str, Any]:
        """打开数据库连接。"""
        try:
            self.connection = turso.connect(path)
            self.db_path = path
            return {
                "success": True,
                "path": path,
                "message": f"数据库打开成功: {path}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"打开数据库失败: {path}",
            }

    def get_current_database(self) -> dict[str, Any]:
        """获取当前数据库的信息。"""
        if self.connection is None:
            return {"connected": False, "message": "当前没有打开的数据库"}

        return {
            "connected": True,
            "path": self.db_path,
            "message": f"已连接到: {self.db_path}",
        }

    def list_tables(self) -> dict[str, Any]:
        """列出数据库中的所有表。"""
        if self.connection is None:
            return {"success": False, "error": "当前没有打开的数据库"}

        try:
            cursor = self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in cursor.fetchall()]
            return {"success": True, "tables": tables, "count": len(tables)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def describe_table(self, table_name: str) -> dict[str, Any]:
        """获取指定表的结构信息。"""
        if self.connection is None:
            return {"success": False, "error": "当前没有打开的数据库"}

        try:
            # 获取表信息
            cursor = self.connection.execute(f"PRAGMA table_info({table_name})")
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
            cursor = self.connection.execute(f"PRAGMA index_list({table_name})")
            indexes = []
            for row in cursor.fetchall():
                index_name = row[1]
                cursor2 = self.connection.execute(f"PRAGMA index_info({index_name})")
                index_columns = [r[2] for r in cursor2.fetchall()]
                indexes.append(
                    {
                        "name": index_name,
                        "unique": bool(row[2]),
                        "columns": index_columns,
                    }
                )

            return {
                "success": True,
                "table_name": table_name,
                "columns": columns,
                "indexes": indexes,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute_query(
        self, query: str, params: Optional[list] = None
    ) -> dict[str, Any]:
        """执行只读的 SELECT 查询。"""
        if self.connection is None:
            return {"success": False, "error": "当前没有打开的数据库"}

        # 确保查询是只读的
        query_upper = query.strip().upper()
        if not query_upper.startswith("SELECT") and not query_upper.startswith(
            "PRAGMA"
        ):
            return {
                "success": False,
                "error": "只允许 SELECT 和 PRAGMA 查询",
            }

        try:
            if params:
                cursor = self.connection.execute(query, params)
            else:
                cursor = self.connection.execute(query)

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

    def insert_data(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        """向表中插入数据。"""
        if self.connection is None:
            return {"success": False, "error": "当前没有打开的数据库"}

        try:
            columns = list(data.keys())
            placeholders = ", ".join(["?" for _ in columns])
            columns_str = ", ".join(columns)

            query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
            values = [data[col] for col in columns]

            self.connection.execute(query, values)
            self.connection.commit()

            # 获取最后插入的行 ID
            cursor = self.connection.execute("SELECT last_insert_rowid()")
            last_id = cursor.fetchone()[0]

            return {
                "success": True,
                "message": f"数据成功插入到表 {table}",
                "row_id": last_id,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_data(
        self,
        table: str,
        data: dict[str, Any],
        where: str,
        where_params: Optional[list] = None,
    ) -> dict[str, Any]:
        """更新表中的数据。"""
        if self.connection is None:
            return {"success": False, "error": "当前没有打开的数据库"}

        try:
            set_clause = ", ".join([f"{col} = ?" for col in data.keys()])
            query = f"UPDATE {table} SET {set_clause} WHERE {where}"

            values = list(data.values())
            if where_params:
                values.extend(where_params)

            cursor = self.connection.execute(query, values)
            self.connection.commit()

            return {
                "success": True,
                "message": f"表 {table} 中的数据更新成功",
                "rows_affected": cursor.rowcount,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_data(
        self, table: str, where: str, where_params: Optional[list] = None
    ) -> dict[str, Any]:
        """从表中删除数据。"""
        if self.connection is None:
            return {"success": False, "error": "当前没有打开的数据库"}

        try:
            query = f"DELETE FROM {table} WHERE {where}"

            if where_params:
                cursor = self.connection.execute(query, where_params)
            else:
                cursor = self.connection.execute(query)

            self.connection.commit()

            return {
                "success": True,
                "message": f"成功从表 {table} 中删除数据",
                "rows_affected": cursor.rowcount,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def schema_change(self, sql: str) -> dict[str, Any]:
        """执行模式修改语句。"""
        if self.connection is None:
            return {"success": False, "error": "当前没有打开的数据库"}

        # 验证是否为 DDL 语句
        sql_upper = sql.strip().upper()
        allowed_prefixes = ["CREATE", "ALTER", "DROP"]

        if not any(sql_upper.startswith(prefix) for prefix in allowed_prefixes):
            return {
                "success": False,
                "error": "只允许 CREATE、ALTER 和 DROP 语句",
            }

        try:
            self.connection.execute(sql)
            self.connection.commit()

            return {"success": True, "message": "模式修改执行成功"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def close(self):
        """关闭数据库连接。"""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.db_path = None
