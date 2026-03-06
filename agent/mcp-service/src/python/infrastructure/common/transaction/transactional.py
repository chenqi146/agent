'''
@File    :   transactional.py
@Time    :   2025/09/11 22:35:00
@Author  :   penghf 
@Version :   1.0
@Desc    :   统一的事务装饰器
'''

from functools import wraps
from typing import Callable, Any
from infrastructure.common.error.errcode import ErrorCode
import logging

def transactional(read_only: bool = False, isolation_level: str = None):
    """
    统一的事务装饰器，自动管理数据库事务
    
    Args:
        read_only: 是否为只读事务
        isolation_level: 事务隔离级别 (READ_UNCOMMITTED, READ_COMMITTED, REPEATABLE_READ, SERIALIZABLE)
    
    Usage:
        @transactional()  # 写事务
        @transactional(read_only=True)  # 只读事务
        @transactional(isolation_level="READ_COMMITTED")  # 自定义隔离级别
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 获取mysql_persistence实例
            mysql_persistence = None
            
            # 尝试从不同的属性中获取mysql_persistence
            if hasattr(self, 'mysql_persistence'):
                mysql_persistence = self.mysql_persistence
            elif hasattr(self, 'gun_camera_repository') and hasattr(self.gun_camera_repository, 'mysql_persistence'):
                mysql_persistence = self.gun_camera_repository.mysql_persistence
            elif hasattr(self, 'ptz_camera_repository') and hasattr(self.ptz_camera_repository, 'mysql_persistence'):
                mysql_persistence = self.ptz_camera_repository.mysql_persistence
            elif hasattr(self, 'parking_lot_repository') and hasattr(self.parking_lot_repository, 'mysql_persistence'):
                mysql_persistence = self.parking_lot_repository.mysql_persistence
            elif hasattr(self, 'parking_space_mng_unit_repository') and hasattr(self.parking_space_mng_unit_repository, 'mysql_persistence'):
                mysql_persistence = self.parking_space_mng_unit_repository.mysql_persistence
            elif hasattr(self, 'parking_space_repository') and hasattr(self.parking_space_repository, 'mysql_persistence'):
                mysql_persistence = self.parking_space_repository.mysql_persistence
            elif hasattr(self, 'gun_camera_svc') and hasattr(self.gun_camera_svc, 'gun_camera_repository') and hasattr(self.gun_camera_svc.gun_camera_repository, 'mysql_persistence'):
                mysql_persistence = self.gun_camera_svc.gun_camera_repository.mysql_persistence
            elif hasattr(self, 'ptz_camera_svc') and hasattr(self.ptz_camera_svc, 'ptz_camera_repository') and hasattr(self.ptz_camera_svc.ptz_camera_repository, 'mysql_persistence'):
                mysql_persistence = self.ptz_camera_svc.ptz_camera_repository.mysql_persistence
            elif hasattr(self, 'parking_svc') and hasattr(self.parking_svc, 'parking_lot_repository') and hasattr(self.parking_svc.parking_lot_repository, 'mysql_persistence'):
                mysql_persistence = self.parking_svc.parking_lot_repository.mysql_persistence
            elif hasattr(self, 'sche_threshold_info_repository') and hasattr(self.sche_threshold_info_repository, 'mysql_persistence'):
                mysql_persistence = self.sche_threshold_info_repository.mysql_persistence
            elif hasattr(self, 'camera_sche_info_repository') and hasattr(self.camera_sche_info_repository, 'mysql_persistence'):
                mysql_persistence = self.camera_sche_info_repository.mysql_persistence
            elif hasattr(self, 'camera_application_repository') and hasattr(self.camera_application_repository, 'mysql_persistence'):
                mysql_persistence = self.camera_application_repository.mysql_persistence
            elif hasattr(self, 'model_application_repository') and hasattr(self.model_application_repository, 'mysql_persistence'):
                mysql_persistence = self.model_application_repository.mysql_persistence
            elif hasattr(self, 'llm_application_repository') and hasattr(self.llm_application_repository, 'mysql_persistence'):
                mysql_persistence = self.llm_application_repository.mysql_persistence
            elif hasattr(self, 'event_constant_repository') and hasattr(self.event_constant_repository, 'mysql_persistence'):
                mysql_persistence = self.event_constant_repository.mysql_persistence
            elif hasattr(self, 'prompt_template_repository') and hasattr(self.prompt_template_repository, 'mysql_persistence'):
                mysql_persistence = self.prompt_template_repository.mysql_persistence
            else:
                # 如果找不到mysql_persistence，记录错误并返回
                logging.error("Cannot find mysql_persistence instance for transaction management")
                return ErrorCode.INTERNAL_ERROR
            
            # 检查是否已经在事务中
            in_transaction = False
            try:
                # 尝试检查当前事务状态
                check_error, result = mysql_persistence.execute_sql("SELECT @@autocommit")
                if check_error == ErrorCode.SUCCESS and result:
                    # 如果autocommit=0，说明已经在事务中
                    in_transaction = result[0].get('@@autocommit', 1) == 0
            except:
                # 如果检查失败，假设不在事务中
                in_transaction = False
            
            # 如果不在事务中，设置事务特性并开始事务
            if not in_transaction:
                # 设置事务隔离级别（在开始事务之前）
                if isolation_level:
                    isolation_sql = f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"
                    isolation_error, _ = mysql_persistence.execute_sql(isolation_sql)
                    if isolation_error != ErrorCode.SUCCESS:
                        logging.warning(f"Failed to set isolation level: {isolation_error}")
                
                # 设置只读事务（在开始事务之前）
                if read_only:
                    readonly_error, _ = mysql_persistence.execute_sql("SET TRANSACTION READ ONLY")
                    if readonly_error != ErrorCode.SUCCESS:
                        logging.warning(f"Failed to set read only: {readonly_error}")
                
                # 开始事务
                error_code = mysql_persistence.begin_transaction()
                if error_code != ErrorCode.SUCCESS:
                    logging.error(f"Failed to begin transaction: {error_code}")
                    # 返回错误码和None，保持与函数签名一致
                    return error_code, None
            else:
                logging.debug("Already in transaction, skipping transaction start")
            
            try:
                # 执行原方法
                result = func(self, *args, **kwargs)
                
                # 如果方法返回ErrorCode，检查是否需要回滚
                if isinstance(result, ErrorCode) and result != ErrorCode.SUCCESS:
                    if not in_transaction:
                        mysql_persistence.rollback()
                        logging.warning(f"Transaction rolled back due to error: {result}")
                    # 返回错误码和None，保持与函数签名一致
                    return result, None
                
                # 提交事务（只有在最外层事务中才提交）
                if not in_transaction:
                    commit_error = mysql_persistence.commit()
                    if commit_error != ErrorCode.SUCCESS:
                        logging.error(f"Failed to commit transaction: {commit_error}")
                        # 返回错误码和None，保持与函数签名一致
                        return commit_error, None
                
                return result
                
            except Exception as e:
                # 发生异常时回滚事务（只有在最外层事务中才回滚）
                if not in_transaction:
                    mysql_persistence.rollback()
                    logging.error(f"Transaction rolled back due to exception: {e}")
                # 返回错误码和None，保持与函数签名一致
                return ErrorCode.INTERNAL_ERROR, None
        
        return wrapper
    return decorator
