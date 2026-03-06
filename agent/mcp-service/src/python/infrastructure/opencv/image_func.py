import cv2
import numpy as np
from typing import List, Tuple

from infrastructure.common.error.errcode import (
    ErrorCode, create_error, success, is_success,
    ErrorCode as EC
)

class ImageFunc:
    @staticmethod
    def crop_and_resize(image:np.ndarray,bbox:List[int],target_size:Tuple[int,int]=(336,336)) ->(ErrorCode, np.ndarray,np.ndarray): # type: ignore
        """
        根据给定 bbox 从图像中裁剪出区域，并按 target_size 进行缩放。

        Args:
            image: 输入图像，BGR 格式 numpy.ndarray，shape=(H, W, C)
            bbox: 裁剪框，格式 [x1, y1, x2, y2]
            target_size: 目标大小 (width, height)，默认 (336, 336)

        Returns:
            (ErrorCode, np.ndarray): 错误码 + 裁剪并缩放后的图像
        """
        try:
            if image is None or not isinstance(image, np.ndarray):
                return EC.INVALID_PARAMETER, None,None  # type: ignore

            if bbox is None or len(bbox) != 4:
                return EC.INVALID_PARAMETER, None,None  # type: ignore

            h, w = image.shape[:2]
            x1, y1, x2, y2 = bbox

            # 允许 x1>x2 / y1>y2，自动纠正
            x1, x2 = int(min(x1, x2)), int(max(x1, x2))
            y1, y2 = int(min(y1, y2)), int(max(y1, y2))

            # 边界裁剪
            x1 = max(0, min(x1, w - 1))
            x2 = max(0, min(x2, w))
            y1 = max(0, min(y1, h - 1))
            y2 = max(0, min(y2, h))

            if x2 <= x1 or y2 <= y1:
                return EC.INVALID_PARAMETER, None,None  # type: ignore

            crop = image[y1:y2, x1:x2]
            if crop.size == 0:
                return EC.INVALID_PARAMETER, None,None  # type: ignore

            resized = cv2.resize(crop, target_size, interpolation=cv2.INTER_LINEAR)
            return EC.SUCCESS, resized,crop  # type: ignore
        except Exception:
            return EC.EXCEPTION_ERROR, None  # type: ignore
    
    @staticmethod
    def generate_augmented_views(image:np.ndarray,num_views:int=4) ->(ErrorCode, List[np.ndarray]): # type: ignore
        """
        生成图像的多视角增强结果：原图、水平翻转、亮度调整、轻微旋转等。

        Args:
            image: 输入图像，BGR 格式 numpy.ndarray，shape=(H, W, C)
            num_views: 期望返回的视角数量（最多返回可用的增强数，含原图）

        Returns:
            (ErrorCode, List[np.ndarray]): 错误码 + 增强后的图像列表
        """
        try:
            if image is None or not isinstance(image, np.ndarray):
                return EC.INVALID_PARAMETER, []  # type: ignore

            views: List[np.ndarray] = []

            # 1. 原图
            views.append(image.copy())

            # 2. 水平翻转
            try:
                flipped = cv2.flip(image, 1)
                views.append(flipped)
            except Exception:
                pass

            # 3. 轻微旋转（例如 ±5°）
            # 注意：移除了亮度/对比度调整，因为它会改变颜色，导致不同颜色的车辆特征过于相似
            try:
                h, w = image.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, 5, 1.0)
                rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
                views.append(rotated)
            except Exception:
                pass

            # 截断或返回所有可用视角
            if num_views > 0 and len(views) > num_views:
                views = views[:num_views]

            return EC.SUCCESS, views  # type: ignore
        except Exception:
            return EC.EXCEPTION_ERROR, []  # type: ignore
    
    @staticmethod
    def pca_dim_reduction(features:List[float],dim:int=64) -> List[float]:
        """
        对特征向量进行 PCA 降维。

        说明：
        - 输入为一条高维特征（List[float]），先视为 shape = (1, D) 的样本矩阵
        - 对于单样本情况，PCA 无法真正降维，直接截断/补零到目标维度
        - 对于多样本情况，使用 SVD 实现 PCA，将其投影到 dim 维
        - 输出为一条长度为 dim 的向量
        - 当 dim > 原始维度时，会自动补零到目标维度
        """
        try:
            if features is None or len(features) == 0:
                return [0.0] * dim  # 返回零向量

            x = np.asarray(features, dtype=np.float32).reshape(1, -1)  # (1, D)
            n_samples, n_features = x.shape
            if n_features == 0:
                return [0.0] * dim

            # 对于单样本情况（n_samples=1），PCA 无法真正降维，直接截断/补零
            if n_samples == 1:
                vec_1d = x.flatten().tolist()
                if len(vec_1d) >= dim:
                    # 截断到目标维度
                    return vec_1d[:dim]
                else:
                    # 补零到目标维度
                    return vec_1d + [0.0] * (dim - len(vec_1d))

            # 多样本情况：使用 SVD 实现 PCA
            k = min(dim, n_features)

            # 零均值化
            mean = x.mean(axis=0, keepdims=True)
            x_centered = x - mean

            # 使用 SVD 实现 PCA：X = U S V^T，主成分在 V 中
            try:
                U, S, Vt = np.linalg.svd(x_centered, full_matrices=False)
            except np.linalg.LinAlgError:
                # SVD 失败时，回退到截断/补零
                vec_1d = x.flatten().tolist()
                if len(vec_1d) >= dim:
                    return vec_1d[:dim]
                else:
                    return vec_1d + [0.0] * (dim - len(vec_1d))

            components = Vt[:k, :]        # (k, D)
            x_reduced = np.dot(x_centered, components.T)  # (n_samples, k)
            
            # 如果是多样本，取平均（或者取第一个样本）
            if x_reduced.shape[0] > 1:
                vec = x_reduced.mean(axis=0).astype(np.float32).tolist()  # 平均
            else:
                vec = x_reduced.reshape(-1).astype(np.float32).tolist()

            # 确保输出维度是 dim（如果 k < dim，补零）
            if len(vec) < dim:
                vec = vec + [0.0] * (dim - len(vec))
            elif len(vec) > dim:
                vec = vec[:dim]

            return vec
        except Exception as e:
            # 异常时返回零向量
            return [0.0] * dim

    @staticmethod
    def interpolation_image(src_image_file: str, dst_image_file: str, interpolation: int = cv2.INTER_LINEAR, dst_size: Tuple[int, int] = (28, 28)) -> Tuple[ErrorCode, np.ndarray,str]:
        """
        对图像进行插值缩放并保存到目标文件
        
        Args:
            src_image_file: 源图像文件路径
            dst_image_file: 目标图像文件路径
            interpolation: 插值方法，默认 cv2.INTER_LINEAR
                可选值：
                - cv2.INTER_NEAREST: 最近邻插值（最快，质量最低）
                - cv2.INTER_LINEAR: 双线性插值（默认，平衡速度和质量）
                - cv2.INTER_CUBIC: 双三次插值（较慢，质量较高）
                - cv2.INTER_AREA: 区域插值（适合缩小图像）
                - cv2.INTER_LANCZOS4: Lanczos 插值（最慢，质量最高）
            dst_size: 目标尺寸 (width, height)，默认 (28, 28)
        
        Returns:
            (ErrorCode, np.ndarray): 错误码 + 插值后的图像（numpy 数组）
        """
        try:
            import os
            
            # 1. 检查源文件是否存在
            if not os.path.exists(src_image_file):
                return EC.INVALID_PARAMETER, None, None  # type: ignore
            
            # 2. 读取源图像
            src_image = cv2.imread(src_image_file)
            if src_image is None:
                return EC.INVALID_IMAGE, None, None  # type: ignore
            
            # 3. 检查目标尺寸有效性
            if dst_size[0] <= 0 or dst_size[1] <= 0:
                return EC.INVALID_PARAMETER, None, None  # type: ignore
            
            # 4. 使用指定的插值方法调整图像大小
            # INSERT_YOUR_CODE
            # 计算缩放比例，使最小边缩放为 dst_size 指定，保持长宽比
            h, w = src_image.shape[:2]
            dst_w, dst_h = dst_size

            # 目标最小边
            min_dst_side = min(dst_w, dst_h)
            min_src_side = min(w, h)
            scale = min_dst_side / min_src_side

            # 计算缩放后的尺寸
            new_w = int(round(w * scale))
            new_h = int(round(h * scale))

            # 防止缩放为0
            new_w = max(1, new_w)
            new_h = max(1, new_h)

            resized_image = cv2.resize(src_image, (new_w, new_h), interpolation=interpolation)
            
            # 5. 确保目标目录存在
            dst_dir = os.path.dirname(dst_image_file)
            if dst_dir and not os.path.exists(dst_dir):
                os.makedirs(dst_dir, exist_ok=True)
            
            # 6. 保存到目标文件
            success = cv2.imwrite(dst_image_file, resized_image)
            if not success:
                return EC.EXCEPTION_ERROR, None, None  # type: ignore
            
            return EC.SUCCESS, resized_image,dst_image_file  # type: ignore
        except Exception as e:
            return EC.EXCEPTION_ERROR, None, None  # type: ignore
