import base64
import os

class ImageFunc:
    @staticmethod
    def image_to_base64(image_file:str)->str:
        try:
            """将本地图片转换为 base64 data URL"""
            with open(image_file, 'rb') as f:
                image_data = f.read()
            
            # 根据扩展名确定 MIME 类型
            ext = os.path.splitext(image_file)[1].lower()
            mime_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            mime_type = mime_types.get(ext, 'image/jpeg')
            
            base64_data = base64.b64encode(image_data).decode('utf-8')
            return f"data:{mime_type};base64,{base64_data}"
        except Exception as e:
            print(f"image to base64 except,{e}")
            return None