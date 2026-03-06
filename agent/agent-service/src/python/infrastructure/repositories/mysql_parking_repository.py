# -*- coding: utf-8 -*-
"""MySQL+嵌入模型：车辆历史停车记录、停车记录写入"""
import logging
from typing import List, Optional, Any
from datetime import datetime
import numpy as np

from ...domain.entities import ParkingRecord, BehaviorType
from ..persistences.mysql_persistence import MysqlPersistence
from ..common.error.errcode import ErrorCode

logger = logging.getLogger(__name__)

TABLE_PARKING_RECORD = "parking_record"


class MysqlParkingRepository:
    """MySQL 存储停车记录；提供车辆历史停车记录供 GRU+Attention 使用"""

    def __init__(self, mysql: MysqlPersistence, embedding_model=None):
        self.mysql = mysql
        self.embedding_model = embedding_model  # 可选：对历史记录文本做嵌入

    def ensure_table(self):
        """创建表（若不存在）"""
        sql = """
        CREATE TABLE IF NOT EXISTS parking_record (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            plate_number VARCHAR(32) NOT NULL,
            behavior_type VARCHAR(32) NOT NULL COMMENT 'parking/passing_by',
            entry_time DATETIME NULL,
            exit_time DATETIME NULL,
            confidence FLOAT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            extra_info JSON NULL,
            INDEX idx_plate (plate_number),
            INDEX idx_created (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='停车/路过记录';
        """
        self.mysql.execute_sql(sql)

    def insert_parking_record(self, record: ParkingRecord) -> bool:
        """停车、路过 决策后写入 MySQL"""
        self.ensure_table()
        data = {
            "plate_number": record.plate_number,
            "behavior_type": record.behavior_type,
            "entry_time": record.entry_time,
            "exit_time": record.exit_time,
            "confidence": record.confidence,
            "extra_info": str(record.extra) if record.extra else None,
        }
        err, _ = self.mysql.insert(TABLE_PARKING_RECORD, data)
        if err == ErrorCode.SUCCESS:
            logger.info("insert_parking_record ok: %s %s", record.plate_number, record.behavior_type)
            return True
        return False

    def get_vehicle_historical_records(
        self, plate_number: str, limit: int = 50
    ) -> List[ParkingRecord]:
        """获取车辆历史停车记录（供 GRU+Attention 输入）"""
        self.ensure_table()
        sql = (
            "SELECT id, plate_number, behavior_type, entry_time, exit_time, confidence, created_at "
            "FROM parking_record WHERE plate_number = %s ORDER BY created_at DESC LIMIT %s"
        )
        err, rows = self.mysql.execute_sql(sql, (plate_number, limit))
        if err != ErrorCode.SUCCESS or not rows:
            return []
        out = []
        for r in rows:
            out.append(
                ParkingRecord(
                    id=r.get("id"),
                    plate_number=r.get("plate_number", ""),
                    behavior_type=r.get("behavior_type", ""),
                    entry_time=r.get("entry_time"),
                    exit_time=r.get("exit_time"),
                    confidence=float(r.get("confidence") or 0),
                    created_at=r.get("created_at"),
                )
            )
        return out
