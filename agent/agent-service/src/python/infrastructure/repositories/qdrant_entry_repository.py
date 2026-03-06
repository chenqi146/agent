# -*- coding: utf-8 -*-
"""写入/读取 QDrant：驶入车辆特征、车牌特征、车牌元数据、驶入时间"""
import uuid
import logging
from typing import Optional, List, Any
import numpy as np
from qdrant_client.http import models as rest

from ...domain.entities import EntryVehicleData
from ..persistences.qdrant_persistence import QDrantPersistence

logger = logging.getLogger(__name__)

COLLECTION_ENTRY = "parking_entry_features"
VECTOR_SIZE = 512


class QdrantEntryRepository:
    """驶入信息写入 QDrant，驶出时按车牌读取当前车辆驶入信息"""

    def __init__(self, qdrant: QDrantPersistence, vector_size: int = VECTOR_SIZE):
        self.qdrant = qdrant
        self.vector_size = vector_size
        self._ensure_collection()

    def _ensure_collection(self):
        self.qdrant.init_collection(
            collection_name=COLLECTION_ENTRY,
            vectors_config=rest.VectorParams(size=self.vector_size, distance=rest.Distance.COSINE),
        )

    def _to_vector(self, data: EntryVehicleData) -> List[float]:
        v = data.vehicle_features
        if isinstance(v, np.ndarray):
            v = v.flatten()
        v = v.tolist() if hasattr(v, "tolist") else list(v)
        if len(v) > self.vector_size:
            v = v[:self.vector_size]
        elif len(v) < self.vector_size:
            v = v + [0.0] * (self.vector_size - len(v))
        return [float(x) for x in v]

    def write_entry(self, data: EntryVehicleData) -> bool:
        """写入 QDrant 数据库：驶入车辆特征、车牌特征、车牌元数据、驶入时间"""
        try:
            vector = self._to_vector(data)
            point = rest.PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "plate_number": data.plate_number,
                    "entry_time": data.entry_time,
                    "plate_metadata": data.plate_metadata,
                    "plate_features": data.plate_features.tolist() if hasattr(data.plate_features, "tolist") else list(data.plate_features),
                    "vehicle_features": data.vehicle_features.tolist() if hasattr(data.vehicle_features, "tolist") else list(data.vehicle_features),
                },
            )
            from infrastructure.common.error.errcode import ErrorCode
            err, _ = self.qdrant.insert_point_struct(point, COLLECTION_ENTRY)
            if err != ErrorCode.SUCCESS:
                logger.warning("qdrant insert_point_struct returned %s", err)
                return False
            logger.info("QDrant write_entry ok: %s", data.plate_number)
            return True
        except Exception as e:
            logger.exception("write_entry failed: %s", e)
            return False

    def get_current_vehicle_entry(self, plate_number: str) -> Optional[EntryVehicleData]:
        """根据车牌获取当前车辆驶入信息（供 GRU+Attention 使用）"""
        try:
            from qdrant_client.http import models as rest
            filter_obj = rest.Filter(
                must=[rest.FieldCondition(key="plate_number", match=rest.MatchValue(value=plate_number))]
            )
            from infrastructure.common.error.errcode import ErrorCode
            err, points = self.qdrant.query_point_struct(
                collection_name=COLLECTION_ENTRY,
                filter=filter_obj,
                limit=1,
                with_payload=True,
            )
            if err != ErrorCode.SUCCESS or not points:
                return None
            p = points[0]
            payload = p.payload if hasattr(p, "payload") else p.get("payload", {})
            return EntryVehicleData(
                plate_number=payload.get("plate_number", ""),
                vehicle_features=np.array(payload.get("vehicle_features", []), dtype=np.float32),
                plate_features=np.array(payload.get("plate_features", []), dtype=np.float32),
                plate_metadata=payload.get("plate_metadata", {}),
                entry_time=payload.get("entry_time", ""),
                extra=payload,
            )
        except Exception as e:
            logger.exception("get_current_vehicle_entry failed: %s", e)
            return None

    def delete_entry(self, plate_number: str) -> bool:
        """驶出并写入停车记录后，可删除该车牌的驶入记录"""
        try:
            filter_obj = rest.Filter(
                must=[rest.FieldCondition(key="plate_number", match=rest.MatchValue(value=plate_number))]
            )
            old_coll = getattr(self.qdrant, "collection_name", None)
            self.qdrant.collection_name = COLLECTION_ENTRY
            self.qdrant.delete(filter=filter_obj)
            if old_coll is not None:
                self.qdrant.collection_name = old_coll
            return True
        except Exception as e:
            logger.exception("delete_entry failed: %s", e)
            return False
