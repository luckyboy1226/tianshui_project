#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)

@contextmanager
def safe_file_cleanup(file_paths: list, analyzer: Optional[object] = None):
    """
    安全的文件清理上下文管理器
    
    Args:
        file_paths: 需要清理的文件路径列表
        analyzer: 需要关闭的分析器对象
    """
    try:
        yield
    finally:
        # 关闭分析器资源
        if analyzer is not None and hasattr(analyzer, 'close'):
            try:
                analyzer.close()
                logger.info("分析器资源已关闭")
            except Exception as e:
                logger.warning(f"关闭分析器时出错: {e}")
        
        # 清理文件
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"已删除文件: {file_path}")
                except PermissionError:
                    logger.warning(f"无法删除文件 {file_path}，可能仍被占用")
                except Exception as e:
                    logger.warning(f"删除文件 {file_path} 时出错: {e}")

def safe_remove_file(file_path: str) -> bool:
    """
    安全删除文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否成功删除
    """
    if not file_path or not os.path.exists(file_path):
        return True
    
    try:
        os.remove(file_path)
        logger.info(f"已删除文件: {file_path}")
        return True
    except PermissionError:
        logger.warning(f"无法删除文件 {file_path}，可能仍被占用")
        return False
    except Exception as e:
        logger.warning(f"删除文件 {file_path} 时出错: {e}")
        return False

def get_cleanup_files(file_path: str) -> list:
    """
    获取需要清理的文件列表
    
    Args:
        file_path: 主文件路径
        
    Returns:
        list: 需要清理的文件路径列表
    """
    files_to_cleanup = []
    
    if file_path and os.path.exists(file_path):
        files_to_cleanup.append(file_path)
        
        # 添加可能的TIF文件
        tif_candidate = os.path.splitext(file_path)[0] + '.tif'
        if os.path.exists(tif_candidate):
            files_to_cleanup.append(tif_candidate)
    
    return files_to_cleanup
