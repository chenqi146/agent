'''
@File    :   mysql_persistence.py
@Time    :   2025/08/31 17:23:00
@Author  :   penghf 
@Version :   1.0
@Desc    :   mysql持久化
'''

import enum
import pymysql
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from contextlib import contextmanager
from pymysql.cursors import DictCursor, Cursor
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.common.logging.logging import logger

class SqlOpcode(enum.Enum):
    Select = "select"
    Insert = "insert"
    Update = "update"
    Delete = "delete"

@logger()
class MysqlPersistence:
    """
    MySQL database persistence class
    Provides database connection, CRUD operations and other basic operations
    """
    
    def __init__(self, host: str, port: int, username: str, password: str, 
                 database: str, charset: str = 'utf8mb4'):
        """
        Initialize MySQL connection parameters
        
        Args:
            host: Database host address
            port: Database port
            username: Username
            password: Password
            database: Database name
            charset: Character set
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.charset = charset
        self.connection = None       
        
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        
    def connect(self) -> ErrorCode:
        """
        Establish database connection
        
        Returns:
            ErrorCode: Connection result
        """
        try:
            # 首先尝试连接到指定的数据库
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.username,
                password=self.password,
                database=self.database,
                charset=self.charset,
                autocommit=True,
                cursorclass=DictCursor
            )
            self.log.info(f"Successfully connected to MySQL database: {self.host}:{self.port}/{self.database}")
            return ErrorCode.SUCCESS
        except Exception as e:
            self.log.error(f"Failed to connect to MySQL database: {str(e)}")
            return ErrorCode.DATABASE_CONNECTION_ERROR
            
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.log.info("MySQL database connection closed")
    
    def connect_without_database(self) -> ErrorCode:
        """
        Connect to MySQL server without specifying a database
        
        Returns:
            ErrorCode: Connection result
        """
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.username,
                password=self.password,
                charset=self.charset,
                autocommit=True,
                cursorclass=DictCursor
            )
            self.log.info(f"Successfully connected to MySQL server: {self.host}:{self.port}")
            return ErrorCode.SUCCESS
        except Exception as e:
            self.log.error(f"Failed to connect to MySQL server: {str(e)}")
            return ErrorCode.DATABASE_CONNECTION_ERROR
            
    def is_connected(self) -> bool:
        """
        Check database connection status
        
        Returns:
            bool: Whether the connection is valid
        """
        if not self.connection:
            return False
        try:
            self.connection.ping(reconnect=False)
            return True
        except:
            return False
            
    @contextmanager
    def get_cursor(self, cursor_class: type = DictCursor):
        """
        Get database cursor context manager
        
        Args:
            cursor_class: Cursor type, default DictCursor
            
        Yields:
            cursor: Database cursor
        """
        if not self.is_connected():
            err = self.connect()
            if err != ErrorCode.SUCCESS:
                raise Exception(f"Database connection failed with error: {err}")
            
        cursor = self.connection.cursor(cursor_class)
        try:
            yield cursor
        except Exception as e:
            self.connection.rollback()
            self.log.error(f"Database operation failed: {str(e)}")
            raise
        finally:
            cursor.close()
    
    def execute_sql_file(self, sql_file: str) -> Tuple[ErrorCode, Any]:
        """
        Execute SQL file with multiple statements
        """
        try:
            with open(sql_file, 'r', encoding='utf-8') as file:
                sql_content = file.read()
            
            # Split SQL statements by semicolon and filter out empty statements
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            results = []
            for statement in statements:
                if statement:
                    error_code, result = self.execute_sql(statement)
                    if error_code != ErrorCode.SUCCESS:
                        self.log.error(f"Failed to execute SQL statement: {statement}")
                        return error_code, None
                    results.append(result)
            
            return ErrorCode.SUCCESS, results
        except Exception as e:
            self.log.error(f"Failed to execute SQL file: {sql_file}, error: {str(e)}")
            return ErrorCode.DATABASE_EXECUTION_ERROR, None
            
    def execute_sql(self, sql: str, params: Optional[Tuple] = None) -> Tuple[ErrorCode, Any]:
        """
        Execute SQL statement
        
        Args:
            sql: SQL statement
            params: SQL parameters
            
        Returns:
            Tuple[ErrorCode, Any]: (Error code, Execution result)
        """
        try:
            import json
            
            with self.get_cursor() as cursor:
                cursor.execute(sql, params)
                result = cursor.fetchall()
                
                # 处理JSON字段反序列化
                if result and isinstance(result, list):
                    processed_result = []
                    for row in result:
                        if isinstance(row, dict):
                            processed_row = {}
                            for key, value in row.items():
                                # 检查是否是JSON字段（以_info结尾的字段通常是JSON）
                                if key.endswith('_info') and isinstance(value, str):
                                    try:
                                        processed_row[key] = json.loads(value)
                                    except (json.JSONDecodeError, TypeError):
                                        processed_row[key] = value
                                else:
                                    processed_row[key] = value
                            processed_result.append(processed_row)
                        else:
                            processed_result.append(row)
                    return ErrorCode.SUCCESS, processed_result
                
                return ErrorCode.SUCCESS, result
        except Exception as e:
            self.log.error(f"Failed to execute SQL: {sql}, params: {params}, error: {str(e)}")
            return ErrorCode.DATABASE_EXECUTION_ERROR, None
            
    def execute_many(self, sql: str, params_list: List[Tuple]) -> Tuple[ErrorCode, int]:
        """
        Execute SQL statements in batch
        
        Args:
            sql: SQL statement
            params_list: Parameter list
            
        Returns:
            Tuple[ErrorCode, int]: (Error code, Affected rows)
        """
        try:
            with self.get_cursor() as cursor:
                affected_rows = cursor.executemany(sql, params_list)
                return ErrorCode.SUCCESS, affected_rows
        except Exception as e:
            self.log.error(f"Failed to execute SQL in batch: {sql}, error: {str(e)}")
            return ErrorCode.DATABASE_EXECUTION_ERROR, 0
            
    def insert(self, table: str, data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        """
        Insert data
        
        Args:
            table: Table name
            data: Data dictionary to insert
            
        Returns:
            Tuple[ErrorCode, int]: (Error code, Inserted record ID)
        """
        try:
            import json
            
            # 处理JSON字段，将字典对象序列化为JSON字符串
            processed_data = {}
            for key, value in data.items():
                if isinstance(value, dict):
                    processed_data[key] = json.dumps(value, ensure_ascii=False)
                else:
                    processed_data[key] = value
            
            columns = ', '.join(processed_data.keys())
            placeholders = ', '.join(['%s'] * len(processed_data))
            sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            
            with self.get_cursor() as cursor:
                cursor.execute(sql, tuple(processed_data.values()))
                insert_id = cursor.lastrowid
                return ErrorCode.SUCCESS, insert_id
        except Exception as e:
            self.log.error(f"Failed to insert data: table={table}, data={data}, error={str(e)}")
            return ErrorCode.DATABASE_INSERT_ERROR, 0
            
    def batch_insert(self, table: str, data_list: List[Dict[str, Any]]) -> Tuple[ErrorCode, int]:
        """
        Insert data in batch
        
        Args:
            table: Table name
            data_list: Data list to insert
            
        Returns:
            Tuple[ErrorCode, int]: (Error code, Affected rows)
        """
        if not data_list:
            return ErrorCode.SUCCESS, 0
            
        try:
            import json
            
            # 处理JSON字段，将字典对象序列化为JSON字符串
            processed_data_list = []
            for data in data_list:
                processed_data = {}
                for key, value in data.items():
                    if isinstance(value, dict):
                        processed_data[key] = json.dumps(value, ensure_ascii=False)
                    else:
                        processed_data[key] = value
                processed_data_list.append(processed_data)
            
            columns = ', '.join(processed_data_list[0].keys())
            placeholders = ', '.join(['%s'] * len(processed_data_list[0]))
            sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            
            params_list = [tuple(data.values()) for data in processed_data_list]
            return self.execute_many(sql, params_list)
        except Exception as e:
            self.log.error(f"Failed to insert data in batch: table={table}, error={str(e)}")
            return ErrorCode.DATABASE_INSERT_ERROR, 0
            
    def delete(self, table: str, condition: str, params: Optional[Tuple] = None) -> Tuple[ErrorCode, int]:
        """
        Delete data
        
        Args:
            table: Table name
            condition: Delete condition
            params: Condition parameters
            
        Returns:
            Tuple[ErrorCode, int]: (Error code, Affected rows)
        """
        try:
            sql = f"DELETE FROM {table} WHERE {condition}"
            
            with self.get_cursor() as cursor:
                affected_rows = cursor.execute(sql, params)
                return ErrorCode.SUCCESS, affected_rows
        except Exception as e:
            self.log.error(f"Failed to delete data: table={table}, condition={condition}, error={str(e)}")
            return ErrorCode.DATABASE_DELETE_ERROR, 0
            
    def update(self, table: str, data: Dict[str, Any], condition: str, 
               params: Optional[Tuple] = None) -> Tuple[ErrorCode, int]:
        """
        Update data
        
        Args:
            table: Table name
            data: Data dictionary to update
            condition: Update condition
            params: Condition parameters
            
        Returns:
            Tuple[ErrorCode, int]: (Error code, Affected rows)
        """
        try:
            import json
            
            # 处理JSON字段，将字典对象序列化为JSON字符串
            processed_data = {}
            for key, value in data.items():
                if isinstance(value, dict):
                    processed_data[key] = json.dumps(value, ensure_ascii=False)
                else:
                    processed_data[key] = value
            
            set_clause = ', '.join([f"{k} = %s" for k in processed_data.keys()])
            sql = f"UPDATE {table} SET {set_clause} WHERE {condition}"
            
            # 合并更新数据和条件参数
            all_params = tuple(processed_data.values()) + (params or ())
            
            with self.get_cursor() as cursor:
                affected_rows = cursor.execute(sql, all_params)
                return ErrorCode.SUCCESS, affected_rows
        except Exception as e:
            self.log.error(f"Failed to update data: table={table}, data={data}, condition={condition}, error={str(e)}")
            return ErrorCode.DATABASE_UPDATE_ERROR, 0
            
    def select(self, table: str, columns: Optional[List[str]] = None, 
               condition: Optional[str] = None, params: Optional[Tuple] = None,
               order_by: Optional[str] = None, limit: Optional[int] = None,
               offset: Optional[int] = None) -> (ErrorCode, List[Dict]):
        """
        Query data
        
        Args:
            table: Table name
            columns: Column name list to query, None means query all columns
            condition: Query condition
            params: Condition parameters
            order_by: Order by condition
            limit: Limit returned rows
            offset: Offset
            
        Returns:
            Tuple[ErrorCode, List[Dict]]: (Error code, Query result list)
        """
        try:
            # Build SELECT clause
            if columns:
                select_clause = ', '.join(columns)
            else:
                select_clause = '*'
                
            sql = f"SELECT {select_clause} FROM {table}"
            
            # Add WHERE clause
            if condition:
                sql += f" WHERE {condition}"
                
            # Add ORDER BY clause
            if order_by:
                sql += f" ORDER BY {order_by}"
                
            # Add LIMIT clause
            if limit is not None:
                sql += f" LIMIT {limit}"
                if offset is not None:
                    sql += f" OFFSET {offset}"
                    
            return self.execute_sql(sql, params)
        except Exception as e:
            self.log.error(f"Failed to query data: table={table}, condition={condition}, error={str(e)}")
            return ErrorCode.DATABASE_QUERY_ERROR, []
            
    def select_one(self, table: str, columns: Optional[List[str]] = None,
                   condition: Optional[str] = None, params: Optional[Tuple] = None) -> Tuple[ErrorCode, Optional[Dict]]:
        """
        Query single record
        
        Args:
            table: Table name
            columns: Column name list to query
            condition: Query condition
            params: Condition parameters
            
        Returns:
            Tuple[ErrorCode, Optional[Dict]]: (Error code, Query result)
        """
        error_code, results = self.select(table, columns, condition, params, limit=1)
        if error_code == ErrorCode.SUCCESS and results:
            return ErrorCode.SUCCESS, results[0]
        return error_code, None
        
    def count(self, table: str, condition: Optional[str] = None, 
              params: Optional[Tuple] = None) -> Tuple[ErrorCode, int]:
        """
        Count records
        
        Args:
            table: Table name
            condition: Count condition
            params: Condition parameters
            
        Returns:
            Tuple[ErrorCode, int]: (Error code, Record count)
        """
        try:
            sql = f"SELECT COUNT(*) as count FROM {table}"
            if condition:
                sql += f" WHERE {condition}"
                
            error_code, result = self.execute_sql(sql, params)
            if error_code == ErrorCode.SUCCESS and result:
                return ErrorCode.SUCCESS, result[0]['count']
            return ErrorCode.DATABASE_QUERY_ERROR, 0
        except Exception as e:
            self.log.error(f"Failed to count records: table={table}, error={str(e)}")
            return ErrorCode.DATABASE_QUERY_ERROR, 0
            
    def exists(self, table: str, condition: str, params: Optional[Tuple] = None) -> Tuple[ErrorCode, bool]:
        """
        Check if record exists
        
        Args:
            table: Table name
            condition: Query condition
            params: Condition parameters
            
        Returns:
            Tuple[ErrorCode, bool]: (Error code, Whether exists)
        """
        error_code, count = self.count(table, condition, params)
        if error_code == ErrorCode.SUCCESS:
            return ErrorCode.SUCCESS, count > 0
        return error_code, False
        
    def begin_transaction(self) -> ErrorCode:
        """
        Begin transaction
        
        Returns:
            ErrorCode: Operation result
        """
        try:
            if self.connection:
                self.connection.begin()
                return ErrorCode.SUCCESS
            return ErrorCode.DATABASE_CONNECTION_ERROR
        except Exception as e:
            self.log.error(f"Failed to begin transaction: {str(e)}")
            return ErrorCode.DATABASE_TRANSACTION_ERROR
            
    def commit(self) -> ErrorCode:
        """
        Commit transaction
        
        Returns:
            ErrorCode: Operation result
        """
        try:
            if self.connection:
                self.connection.commit()
                return ErrorCode.SUCCESS
            return ErrorCode.DATABASE_CONNECTION_ERROR
        except Exception as e:
            self.log.error(f"Failed to commit transaction: {str(e)}")
            return ErrorCode.DATABASE_TRANSACTION_ERROR
            
    def rollback(self) -> ErrorCode:
        """
        Rollback transaction
        
        Returns:
            ErrorCode: Operation result
        """
        try:
            if self.connection:
                self.connection.rollback()
                return ErrorCode.SUCCESS
            return ErrorCode.DATABASE_CONNECTION_ERROR
        except Exception as e:
            self.log.error(f"Failed to rollback transaction: {str(e)}")
            return ErrorCode.DATABASE_TRANSACTION_ERROR
            
    def get_table_info(self, table: str) -> Tuple[ErrorCode, List[Dict]]:
        """
        Get table structure information
        
        Args:
            table: Table name
            
        Returns:
            Tuple[ErrorCode, List[Dict]]: (Error code, Table structure information)
        """
        sql = f"DESCRIBE {table}"
        return self.execute_sql(sql)
        
    def get_tables(self) -> Tuple[ErrorCode, List[str]]:
        """
        Get all table names in the database
        
        Returns:
            Tuple[ErrorCode, List[str]]: (Error code, Table name list)
        """
        sql = "SHOW TABLES"
        error_code, result = self.execute_sql(sql)
        if error_code == ErrorCode.SUCCESS:
            # Extract table names
            table_names = [list(row.values())[0] for row in result]
            return ErrorCode.SUCCESS, table_names
        return error_code, []
        
