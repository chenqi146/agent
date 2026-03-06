# MySQL 持久化层使用说明

## 概述

`MysqlPersistence` 类提供了完整的 MySQL 数据库操作功能，包括连接管理、增删改查、事务处理等。

## 功能特性

- ✅ 数据库连接管理
- ✅ 上下文管理器支持
- ✅ 基本的 CRUD 操作
- ✅ 批量操作支持
- ✅ 事务管理
- ✅ 错误处理和日志记录
- ✅ 表结构查询
- ✅ 参数化查询（防SQL注入）

## 安装依赖

确保已安装 `pymysql` 库：

```bash
pip install pymysql==1.1.0
```

## 基本使用

### 1. 初始化连接

```python
from infrastructure.persistences.mysql_persistence import MysqlPersistence
from infrastructure.common.error.errcode import ErrorCode

# 创建实例
mysql = MysqlPersistence(
    host='127.0.0.1',
    port=3306,
    username='root',
    password='123456',
    database='parking_mng_db',
    charset='utf8mb4'
)

# 连接数据库
error_code = mysql.connect()
if error_code != ErrorCode.SUCCESS:
    print("连接失败")
```

### 2. 使用上下文管理器（推荐）

```python
with MysqlPersistence(
    host='127.0.0.1',
    port=3306,
    username='root',
    password='123456',
    database='parking_mng_db'
) as mysql:
    # 执行数据库操作
    error_code, result = mysql.execute_sql("SELECT * FROM vehicle_info_tbl")
```

## 核心方法

### 连接管理

- `connect()` - 建立数据库连接
- `close()` - 关闭数据库连接
- `is_connected()` - 检查连接状态

### 基本操作

#### 插入数据

```python
# 单条插入
data = {
    'name': '测试车辆',
    'location': 'A区-001',
    'status': '已停车',
    'structure_info': '{"plate_type": "普通车牌"}',
    'num': 1
}
error_code, insert_id = mysql.insert('vehicle_info_tbl', data)

# 批量插入
data_list = [data1, data2, data3]
error_code, affected_rows = mysql.batch_insert('vehicle_info_tbl', data_list)
```

#### 查询数据

```python
# 查询所有数据
error_code, results = mysql.select('vehicle_info_tbl')

# 条件查询
error_code, results = mysql.select(
    table='vehicle_info_tbl',
    condition='status = %s',
    params=('已停车',)
)

# 查询单条记录
error_code, result = mysql.select_one(
    table='vehicle_info_tbl',
    condition='id = %s',
    params=(1,)
)

# 分页查询
error_code, results = mysql.select(
    table='vehicle_info_tbl',
    order_by='id DESC',
    limit=10,
    offset=0
)
```

#### 更新数据

```python
update_data = {'status': '已离开'}
error_code, affected_rows = mysql.update(
    table='vehicle_info_tbl',
    data=update_data,
    condition='id = %s',
    params=(1,)
)
```

#### 删除数据

```python
error_code, affected_rows = mysql.delete(
    table='vehicle_info_tbl',
    condition='id = %s',
    params=(1,)
)
```

### 高级操作

#### 事务管理

```python
# 开始事务
error_code = mysql.begin_transaction()
if error_code == ErrorCode.SUCCESS:
    try:
        # 执行多个操作
        mysql.insert('table1', data1)
        mysql.update('table2', data2, 'id = %s', (1,))
        
        # 提交事务
        mysql.commit()
    except Exception as e:
        # 回滚事务
        mysql.rollback()
```

#### 统计和检查

```python
# 统计记录数
error_code, count = mysql.count('vehicle_info_tbl')

# 条件统计
error_code, count = mysql.count(
    'vehicle_info_tbl',
    condition='status = %s',
    params=('已停车',)
)

# 检查记录是否存在
error_code, exists = mysql.exists(
    'vehicle_info_tbl',
    condition='name = %s',
    params=('测试车辆',)
)
```

#### 表信息查询

```python
# 获取表结构
error_code, table_info = mysql.get_table_info('vehicle_info_tbl')

# 获取所有表名
error_code, tables = mysql.get_tables()
```

#### 自定义SQL执行

```python
# 执行自定义SQL
error_code, result = mysql.execute_sql(
    "SELECT * FROM vehicle_info_tbl WHERE status = %s",
    ('已停车',)
)

# 批量执行
sql = "INSERT INTO vehicle_info_tbl (name, status) VALUES (%s, %s)"
params_list = [('车辆1', '已停车'), ('车辆2', '已停车')]
error_code, affected_rows = mysql.execute_many(sql, params_list)
```

## 错误处理

所有方法都返回 `(ErrorCode, result)` 的元组：

```python
error_code, result = mysql.insert('table', data)
if error_code == ErrorCode.SUCCESS:
    print("操作成功")
else:
    print(f"操作失败: {error_code}")
```

### 常见错误码

- `ErrorCode.SUCCESS` - 操作成功
- `ErrorCode.DATABASE_CONNECTION_ERROR` - 数据库连接错误
- `ErrorCode.DATABASE_EXECUTION_ERROR` - SQL执行错误
- `ErrorCode.DATABASE_INSERT_ERROR` - 插入操作错误
- `ErrorCode.DATABASE_UPDATE_ERROR` - 更新操作错误
- `ErrorCode.DATABASE_DELETE_ERROR` - 删除操作错误
- `ErrorCode.DATABASE_QUERY_ERROR` - 查询操作错误
- `ErrorCode.DATABASE_TRANSACTION_ERROR` - 事务操作错误

## 最佳实践

1. **使用上下文管理器**：自动管理连接的生命周期
2. **参数化查询**：防止SQL注入攻击
3. **错误处理**：始终检查返回的错误码
4. **事务管理**：对相关操作使用事务确保数据一致性
5. **连接池**：在生产环境中考虑使用连接池

## 示例代码

完整的使用示例请参考 `mysql_persistence_example.py` 文件。

## 注意事项

1. 确保数据库服务正在运行
2. 检查数据库连接参数的正确性
3. 确保数据库用户有足够的权限
4. 在生产环境中使用强密码
5. 定期备份数据库
