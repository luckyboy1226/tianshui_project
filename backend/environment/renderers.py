"""
自定义渲染器，确保JSON响应使用UTF-8编码
"""
from rest_framework.renderers import JSONRenderer


class UTF8JSONRenderer(JSONRenderer):
    """
    自定义JSON渲染器，确保使用UTF-8编码
    """
    charset = 'utf-8'
    
    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        渲染数据为JSON格式，使用UTF-8编码
        """
        if data is None:
            return b''
        
        # 确保响应头包含正确的Content-Type
        if renderer_context:
            response = renderer_context.get('response')
            if response:
                response['Content-Type'] = 'application/json; charset=utf-8'
        
        return super().render(data, accepted_media_type, renderer_context)



