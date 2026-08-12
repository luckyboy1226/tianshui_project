"""
重大工程叠加分析模块
用于分析生态指数文件和生态修复工程文件的叠加影响
"""

import json
import os
import logging
import tempfile
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from django.utils import timezone
from django.conf import settings
from osgeo import ogr, osr, gdal
import numpy as np
from .models import OverlayAnalysisTask, EcologicalIndexFile, EcologicalProjectFile
from .geoserver_config import get_geoserver_manager

gdal.UseExceptions()
logger = logging.getLogger(__name__)


class OverlayAnalyzer:
    """叠加分析器"""
    
    def __init__(self, task: OverlayAnalysisTask):
        self.task = task
        self.ecological_index_file = task.ecological_index_file
        self.ecological_project_file = task.ecological_project_file
        
    def analyze(self) -> Dict[str, Any]:
        """执行叠加分析"""
        try:
            # 更新任务状态
            self.task.status = 'processing'
            self.task.started_at = timezone.now()
            self.task.current_step = '开始分析'
            self.task.progress = 10
            self.task.save()
            
            # 步骤1: 解析生态指数数据
            self.task.current_step = '解析生态指数数据'
            self.task.progress = 20
            self.task.save()
            
            ecological_indices = self._parse_ecological_indices()
            
            # 步骤2: 解析工程项目数据
            self.task.current_step = '解析工程项目数据'
            self.task.progress = 40
            self.task.save()
            
            projects = self._parse_projects()
            
            # 步骤3: 执行风险分析
            self.task.current_step = '执行风险分析'
            self.task.progress = 60
            self.task.save()
            
            risk_analysis = self._perform_risk_analysis(ecological_indices, projects)
            
            # 步骤4: 生成监控建议
            self.task.current_step = '生成监控建议'
            self.task.progress = 80
            self.task.save()
            
            monitoring_recommendations = self._generate_monitoring_recommendations(
                ecological_indices, projects, risk_analysis
            )
            
            # 步骤5: 生成栅格图层
            self.task.current_step = '生成栅格图层'
            self.task.progress = 85
            self.task.save()
            
            raster_metadata = self._generate_raster_layers(projects, risk_analysis)
            
            # 步骤6: 汇总结果
            self.task.current_step = '汇总分析结果'
            self.task.progress = 95
            self.task.save()
            
            results = {
                'ecological_indices': ecological_indices,
                'projects': projects,
                'risk_analysis': risk_analysis,
                'monitoring_recommendations': monitoring_recommendations,
                'analysis_summary': self._generate_summary(risk_analysis),
                'analysis_timestamp': timezone.now().isoformat(),
                'raster_layers': raster_metadata  # 添加栅格图层元数据
            }
            
            # 完成分析
            self.task.status = 'completed'
            self.task.progress = 100
            self.task.current_step = '分析完成'
            self.task.completed_at = timezone.now()
            self.task.analysis_results = results
            self.task.overall_risk_level = self._determine_overall_risk_level(risk_analysis)
            self.task.raster_layers_metadata = raster_metadata
            self.task.save()
            
            return results
            
        except Exception as e:
            logger.error(f"叠加分析失败: {str(e)}")
            self.task.status = 'failed'
            self.task.error_message = str(e)
            self.task.save()
            raise
    
    def _parse_ecological_indices(self) -> Dict[str, Any]:
        """解析生态指数数据"""
        try:
            indices_data = self.ecological_index_file.indices_data
            
            # 如果是字符串，尝试解析为JSON
            if isinstance(indices_data, str):
                indices_data = json.loads(indices_data)
            
            return {
                'filename': self.ecological_index_file.filename,
                'timestamp': indices_data.get('timestamp'),
                'results': indices_data.get('results', {}),
                'summary': indices_data.get('summary', {}),
                'processed_at': self.ecological_index_file.processed_at.isoformat() if self.ecological_index_file.processed_at else None
            }
        except Exception as e:
            raise ValueError(f"解析生态指数数据失败: {str(e)}")
    
    def _parse_projects(self) -> List[Dict[str, Any]]:
        """解析工程项目数据"""
        try:
            geojson_data = self.ecological_project_file.geojson_data
            
            # 如果是字符串，尝试解析为JSON
            if isinstance(geojson_data, str):
                geojson_data = json.loads(geojson_data)
            
            projects = []
            features = geojson_data.get('features', [])
            
            for feature in features:
                properties = feature.get('properties', {})
                geometry = feature.get('geometry', {})
                
                project = {
                    'id': properties.get('id'),
                    'name': properties.get('name'),
                    'type': properties.get('type'),
                    'area': properties.get('area'),
                    'status': properties.get('status'),
                    'start_date': properties.get('startDate'),
                    'end_date': properties.get('endDate'),
                    'description': properties.get('description'),
                    'geometry_type': geometry.get('type'),
                    'coordinates': geometry.get('coordinates')
                }
                projects.append(project)
            
            return projects
        except Exception as e:
            raise ValueError(f"解析工程项目数据失败: {str(e)}")
    
    def _perform_risk_analysis(self, ecological_indices: Dict[str, Any], projects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行风险分析"""
        results = ecological_indices.get('results', {})
        
        # 基础风险评估指标
        risk_factors = {
            'fragmentation_index': results.get('fragmentation_index', 0),
            'fragility_index': results.get('fragility_index', 0),
            'soil_erosion_index': results.get('soil_erosion_index', 0),
            'land_degradation_index': results.get('land_degradation_index', 0),
            'unused_land_proportion': results.get('unused_land_proportion', 0),
            'cultivated_construction_proportion': results.get('cultivated_construction_proportion', 0)
        }
        
        # 计算各项风险等级
        risk_levels = {}
        
        # 生态脆弱性风险
        fragility_risk = self._calculate_fragility_risk(
            risk_factors['fragility_index'],
            risk_factors['fragmentation_index']
        )
        risk_levels['fragility_risk'] = fragility_risk
        
        # 土壤侵蚀风险
        erosion_risk = self._calculate_erosion_risk(
            risk_factors['soil_erosion_index'],
            risk_factors['land_degradation_index']
        )
        risk_levels['erosion_risk'] = erosion_risk
        
        # 土地利用风险
        land_use_risk = self._calculate_land_use_risk(
            risk_factors['unused_land_proportion'],
            risk_factors['cultivated_construction_proportion']
        )
        risk_levels['land_use_risk'] = land_use_risk
        
        # 工程叠加风险
        project_risk = self._calculate_project_risk(projects)
        risk_levels['project_risk'] = project_risk
        
        # 综合风险评估
        overall_risk = self._calculate_overall_risk(risk_levels)
        
        return {
            'risk_factors': risk_factors,
            'risk_levels': risk_levels,
            'overall_risk': overall_risk,
            'risk_details': self._generate_risk_details(risk_levels, projects)
        }
    
    def _calculate_fragility_risk(self, fragility_index: float, fragmentation_index: float) -> Dict[str, Any]:
        """计算生态脆弱性风险"""
        # 综合脆弱性指数
        combined_index = (fragility_index + fragmentation_index) / 2
        
        if combined_index >= 0.7:
            level = 'critical'
            description = '生态系统极度脆弱，急需保护措施'
        elif combined_index >= 0.5:
            level = 'high'
            description = '生态系统脆弱性较高，需要重点关注'
        elif combined_index >= 0.3:
            level = 'medium'
            description = '生态系统脆弱性中等，需要适度保护'
        else:
            level = 'low'
            description = '生态系统相对稳定'
        
        return {
            'level': level,
            'score': combined_index,
            'description': description
        }
    
    def _calculate_erosion_risk(self, erosion_index: float, degradation_index: float) -> Dict[str, Any]:
        """计算土壤侵蚀风险"""
        combined_index = (erosion_index + degradation_index) / 2
        
        if combined_index >= 0.6:
            level = 'critical'
            description = '土壤侵蚀严重，急需治理'
        elif combined_index >= 0.4:
            level = 'high'
            description = '土壤侵蚀风险较高'
        elif combined_index >= 0.2:
            level = 'medium'
            description = '土壤侵蚀风险中等'
        else:
            level = 'low'
            description = '土壤侵蚀风险较低'
        
        return {
            'level': level,
            'score': combined_index,
            'description': description
        }
    
    def _calculate_land_use_risk(self, unused_proportion: float, construction_proportion: float) -> Dict[str, Any]:
        """计算土地利用风险"""
        # 未利用土地比例过高或建设用地比例过高都是风险
        risk_score = max(unused_proportion / 100, construction_proportion / 100)
        
        if risk_score >= 0.5:
            level = 'high'
            description = '土地利用结构不合理'
        elif risk_score >= 0.3:
            level = 'medium'
            description = '土地利用结构需要优化'
        else:
            level = 'low'
            description = '土地利用结构相对合理'
        
        return {
            'level': level,
            'score': risk_score,
            'description': description
        }
    
    def _calculate_project_risk(self, projects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算工程项目风险"""
        if not projects:
            return {
                'level': 'low',
                'score': 0,
                'description': '无工程项目'
            }
        
        # 统计不同状态的项目
        status_counts = {}
        for project in projects:
            status = project.get('status', '未知')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # 计算风险分数
        total_projects = len(projects)
        ongoing_projects = status_counts.get('进行中', 0)
        planned_projects = status_counts.get('规划中', 0)
        
        # 进行中和规划中的项目越多，风险越高
        risk_score = (ongoing_projects + planned_projects) / total_projects
        
        if risk_score >= 0.7:
            level = 'high'
            description = f'大量工程项目同时进行，可能对生态环境造成叠加影响'
        elif risk_score >= 0.4:
            level = 'medium'
            description = f'多个工程项目进行中，需要协调管理'
        else:
            level = 'low'
            description = f'工程项目数量适中'
        
        return {
            'level': level,
            'score': risk_score,
            'description': description,
            'project_counts': status_counts
        }
    
    def _calculate_overall_risk(self, risk_levels: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """计算综合风险等级"""
        # 风险等级权重
        weights = {
            'fragility_risk': 0.3,
            'erosion_risk': 0.3,
            'land_use_risk': 0.2,
            'project_risk': 0.2
        }
        
        # 风险等级映射
        level_scores = {
            'low': 1,
            'medium': 2,
            'high': 3,
            'critical': 4
        }
        
        # 计算加权平均分
        total_score = 0
        for risk_type, weight in weights.items():
            risk_level = risk_levels.get(risk_type, {}).get('level', 'low')
            score = level_scores.get(risk_level, 1)
            total_score += score * weight
        
        # 确定综合风险等级
        if total_score >= 3.5:
            level = 'critical'
            description = '综合风险极高，需要立即采取措施'
        elif total_score >= 2.5:
            level = 'high'
            description = '综合风险较高，需要重点关注'
        elif total_score >= 1.5:
            level = 'medium'
            description = '综合风险中等，需要持续监控'
        else:
            level = 'low'
            description = '综合风险较低，保持现有管理水平'
        
        return {
            'level': level,
            'score': total_score,
            'description': description
        }
    
    def _generate_risk_details(self, risk_levels: Dict[str, Dict[str, Any]], projects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成详细风险说明"""
        details = []
        
        for risk_type, risk_info in risk_levels.items():
            if risk_info['level'] in ['high', 'critical']:
                detail = {
                    'risk_type': risk_type,
                    'level': risk_info['level'],
                    'description': risk_info['description'],
                    'recommendations': self._get_risk_recommendations(risk_type, risk_info['level'])
                }
                details.append(detail)
        
        return details
    
    def _get_risk_recommendations(self, risk_type: str, level: str) -> List[str]:
        """获取风险应对建议"""
        recommendations = {
            'fragility_risk': {
                'high': ['加强生态保护区建设', '限制人类活动干扰', '实施生态修复工程'],
                'critical': ['立即停止破坏性活动', '紧急实施生态保护措施', '建立生态监测系统']
            },
            'erosion_risk': {
                'high': ['实施水土保持工程', '加强植被覆盖', '控制坡面径流'],
                'critical': ['紧急实施防护工程', '大规模植树造林', '建设拦沙坝等设施']
            },
            'land_use_risk': {
                'high': ['优化土地利用结构', '合理规划建设用地', '提高土地利用效率'],
                'critical': ['重新规划土地利用', '严格控制建设用地扩张', '实施土地整治工程']
            },
            'project_risk': {
                'high': ['协调各工程项目进度', '加强环境影响评估', '建立统一监管机制'],
                'critical': ['暂停部分工程项目', '重新评估环境影响', '制定综合管理方案']
            }
        }
        
        return recommendations.get(risk_type, {}).get(level, ['加强监测和管理'])
    
    def _generate_monitoring_recommendations(self, ecological_indices: Dict[str, Any], 
                                           projects: List[Dict[str, Any]], 
                                           risk_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成监控建议"""
        overall_risk = risk_analysis['overall_risk']
        
        # 基础监控建议
        monitoring_plan = {
            'monitoring_frequency': self._determine_monitoring_frequency(overall_risk['level']),
            'key_indicators': self._identify_key_indicators(risk_analysis['risk_levels']),
            'monitoring_areas': self._identify_monitoring_areas(projects, risk_analysis),
            'early_warning_thresholds': self._set_warning_thresholds(ecological_indices['results']),
            'recommended_actions': self._generate_action_plan(risk_analysis)
        }
        
        return monitoring_plan
    
    def _determine_monitoring_frequency(self, risk_level: str) -> str:
        """确定监控频率"""
        frequency_map = {
            'low': '季度监控',
            'medium': '月度监控',
            'high': '周度监控',
            'critical': '日常监控'
        }
        return frequency_map.get(risk_level, '月度监控')
    
    def _identify_key_indicators(self, risk_levels: Dict[str, Dict[str, Any]]) -> List[str]:
        """识别关键监控指标"""
        indicators = []
        
        for risk_type, risk_info in risk_levels.items():
            if risk_info['level'] in ['high', 'critical']:
                if risk_type == 'fragility_risk':
                    indicators.extend(['植被覆盖度', '生物多样性指数', '生态连通性'])
                elif risk_type == 'erosion_risk':
                    indicators.extend(['土壤侵蚀量', '植被覆盖率', '坡面稳定性'])
                elif risk_type == 'land_use_risk':
                    indicators.extend(['土地利用变化', '建设用地扩张', '农田保护'])
                elif risk_type == 'project_risk':
                    indicators.extend(['工程进度', '环境影响', '生态补偿'])
        
        return list(set(indicators))  # 去重
    
    def _identify_monitoring_areas(self, projects: List[Dict[str, Any]], risk_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别重点监控区域"""
        areas = []
        
        # 基于工程项目识别监控区域
        for project in projects:
            if project.get('status') in ['进行中', '规划中']:
                area = {
                    'name': project.get('name'),
                    'type': '工程影响区',
                    'priority': 'high' if project.get('status') == '进行中' else 'medium',
                    'coordinates': project.get('coordinates'),
                    'monitoring_focus': ['工程进度', '环境影响', '生态变化']
                }
                areas.append(area)
        
        return areas
    
    def _set_warning_thresholds(self, current_indices: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        """设置预警阈值"""
        thresholds = {}
        
        for indicator, current_value in current_indices.items():
            if indicator in ['fragmentation_index', 'fragility_index', 'soil_erosion_index', 'land_degradation_index']:
                # 对于负面指标，设置上升预警
                thresholds[indicator] = {
                    'yellow_warning': current_value * 1.2,  # 黄色预警：增加20%
                    'red_warning': current_value * 1.5,     # 红色预警：增加50%
                    'current_value': current_value
                }
            elif indicator in ['shannon_diversity', 'cohesion_index']:
                # 对于正面指标，设置下降预警
                thresholds[indicator] = {
                    'yellow_warning': current_value * 0.8,  # 黄色预警：下降20%
                    'red_warning': current_value * 0.6,     # 红色预警：下降40%
                    'current_value': current_value
                }
        
        return thresholds
    
    def _generate_action_plan(self, risk_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成行动计划"""
        actions = []
        
        overall_risk = risk_analysis['overall_risk']
        
        # 基于综合风险等级制定行动计划
        if overall_risk['level'] in ['high', 'critical']:
            actions.append({
                'priority': 'urgent',
                'action': '立即启动应急响应机制',
                'timeline': '1周内',
                'responsible_party': '环境保护部门'
            })
            
            actions.append({
                'priority': 'high',
                'action': '组织专家评估团队',
                'timeline': '2周内',
                'responsible_party': '科研机构'
            })
        
        if overall_risk['level'] in ['medium', 'high', 'critical']:
            actions.append({
                'priority': 'medium',
                'action': '加强监测网络建设',
                'timeline': '1个月内',
                'responsible_party': '监测部门'
            })
        
        actions.append({
            'priority': 'low',
            'action': '定期评估和更新风险分析',
            'timeline': '季度',
            'responsible_party': '管理部门'
        })
        
        return actions
    
    def _generate_summary(self, risk_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成分析摘要"""
        overall_risk = risk_analysis['overall_risk']
        risk_levels = risk_analysis['risk_levels']
        
        # 统计各风险等级数量
        risk_counts = {}
        for risk_info in risk_levels.values():
            level = risk_info['level']
            risk_counts[level] = risk_counts.get(level, 0) + 1
        
        return {
            'overall_risk_level': overall_risk['level'],
            'overall_risk_score': overall_risk['score'],
            'overall_description': overall_risk['description'],
            'risk_distribution': risk_counts,
            'high_risk_count': risk_counts.get('high', 0) + risk_counts.get('critical', 0),
            'total_risk_factors': len(risk_levels),
            'analysis_date': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _determine_overall_risk_level(self, risk_analysis: Dict[str, Any]) -> str:
        """确定总体风险等级"""
        return risk_analysis['overall_risk']['level']
    
    def _generate_raster_layers(self, projects: List[Dict[str, Any]], risk_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成栅格图层并发布到GeoServer"""
        try:
            # 确保输出目录存在
            media_root = settings.MEDIA_ROOT
            raster_dir = os.path.join(media_root, 'overlay_analysis', 'rasters')
            os.makedirs(raster_dir, exist_ok=True)
            
            task_id = str(self.task.id)
            raster_metadata = {}
            
            # 1. 生成风险等级栅格（基于项目影响范围）
            try:
                risk_raster_path = self._create_risk_raster(projects, risk_analysis, raster_dir, task_id)
                if risk_raster_path and os.path.exists(risk_raster_path):
                    # 保存文件引用到任务
                    relative_path = os.path.relpath(risk_raster_path, media_root)
                    self.task.risk_raster_file.name = relative_path
                    
                    # 发布到GeoServer（可选）
                    layer_name = f"risk_layer_{task_id}"
                    wms_url, actual_layer_name = self._publish_raster_to_geoserver(risk_raster_path, layer_name)
                    
                    # 构建栅格图层元数据（即使没有WMS URL也返回文件路径）
                    # 使用实际图层名称（如果存在），否则使用期望的图层名称
                    final_layer_name = actual_layer_name if actual_layer_name else layer_name
                    raster_metadata['risk_layer'] = {
                        'layer_name': final_layer_name,
                        'wms_url': wms_url,  # 可能为None
                        'file_path': relative_path,
                        'file_url': f'/media/{relative_path}',  # 直接访问文件的URL
                        'type': 'risk_distribution',
                        'description': '风险等级空间分布栅格图层',
                        'published': wms_url is not None  # 标记是否已发布
                    }
                    
                    if wms_url:
                        logger.info(f"✅ 风险等级栅格图层生成并发布成功: {final_layer_name}")
                        logger.info(f"   WMS URL: {wms_url}")
                    else:
                        logger.warning(f"⚠️  风险等级栅格图层生成成功，但GeoServer发布失败: {relative_path}")
                        logger.warning(f"   提示：栅格文件已保存，但需要通过GeoServer才能在地图上显示")
            except Exception as e:
                logger.error(f"生成风险等级栅格失败: {e}", exc_info=True)
            
            # 2. 生成影响强度栅格
            try:
                impact_raster_path = self._create_impact_raster(projects, risk_analysis, raster_dir, task_id)
                if impact_raster_path and os.path.exists(impact_raster_path):
                    # 保存文件引用到任务
                    relative_path = os.path.relpath(impact_raster_path, media_root)
                    self.task.impact_raster_file.name = relative_path
                    
                    # 发布到GeoServer（可选）
                    layer_name = f"impact_layer_{task_id}"
                    wms_url, actual_layer_name = self._publish_raster_to_geoserver(impact_raster_path, layer_name)
                    
                    # 构建栅格图层元数据（即使没有WMS URL也返回文件路径）
                    # 使用实际图层名称（如果存在），否则使用期望的图层名称
                    final_layer_name = actual_layer_name if actual_layer_name else layer_name
                    raster_metadata['impact_layer'] = {
                        'layer_name': final_layer_name,
                        'wms_url': wms_url,  # 可能为None
                        'file_path': relative_path,
                        'file_url': f'/media/{relative_path}',  # 直接访问文件的URL
                        'type': 'impact_intensity',
                        'description': '工程影响强度空间分布栅格图层',
                        'published': wms_url is not None  # 标记是否已发布
                    }
                    
                    if wms_url:
                        logger.info(f"✅ 影响强度栅格图层生成并发布成功: {final_layer_name}")
                        logger.info(f"   WMS URL: {wms_url}")
                    else:
                        logger.warning(f"⚠️  影响强度栅格图层生成成功，但GeoServer发布失败: {relative_path}")
                        logger.warning(f"   提示：栅格文件已保存，但需要通过GeoServer才能在地图上显示")
            except Exception as e:
                logger.error(f"生成影响强度栅格失败: {e}", exc_info=True)
            
            return raster_metadata
            
        except Exception as e:
            logger.error(f"生成栅格图层失败: {e}", exc_info=True)
            return {}
    
    def _create_risk_raster(self, projects: List[Dict[str, Any]], risk_analysis: Dict[str, Any], 
                           output_dir: str, task_id: str, pixel_size: float = 100.0) -> Optional[str]:
        """创建风险等级栅格"""
        try:
            if not projects:
                logger.warning("无工程项目数据，跳过风险栅格生成")
                return None
            
            # 计算所有项目的边界
            all_coords = []
            for project in projects:
                coords = project.get('coordinates')
                if coords:
                    if isinstance(coords[0][0], list):
                        # MultiPolygon or Polygon with holes
                        for ring in coords:
                            all_coords.extend(ring)
                    else:
                        # Simple Polygon
                        all_coords.extend(coords)
            
            if not all_coords:
                logger.warning("无有效坐标数据，跳过风险栅格生成")
                return None
            
            # 计算范围
            lons = [coord[0] for coord in all_coords]
            lats = [coord[1] for coord in all_coords]
            min_lon, max_lon = min(lons), max(lons)
            min_lat, max_lat = min(lats), max(lats)
            
            # 扩大范围（添加缓冲）
            buffer = 0.01  # 约1km
            min_lon -= buffer
            max_lon += buffer
            min_lat -= buffer
            max_lat += buffer
            
            # 计算栅格尺寸
            width = int((max_lon - min_lon) / pixel_size * 111000)  # 转换为米，再除以像素大小
            height = int((max_lat - min_lat) / pixel_size * 111000)
            
            if width <= 0 or height <= 0:
                logger.warning(f"栅格尺寸无效: {width}x{height}")
                return None
            
            # 创建栅格数据
            # 风险等级映射：low=1, medium=2, high=3, critical=4
            risk_level_map = {
                'low': 1,
                'medium': 2,
                'high': 3,
                'critical': 4
            }
            
            overall_risk_level = risk_analysis.get('overall_risk', {}).get('level', 'medium')
            risk_value = risk_level_map.get(overall_risk_level, 2)
            
            # 创建栅格数组（初始值为背景值）
            raster_array = np.full((height, width), 0, dtype=np.float32)
            
            # 将项目区域赋值为风险值（简化处理：在整个范围内赋相同值）
            # 实际应用中可以根据项目位置和缓冲区计算
            raster_array.fill(risk_value)
            
            # 创建输出文件
            output_path = os.path.join(output_dir, f'risk_raster_{task_id}.tif')
            
            # 创建GeoTIFF
            driver = gdal.GetDriverByName('GTiff')
            dst_ds = driver.Create(output_path, width, height, 1, gdal.GDT_Float32)
            
            if dst_ds is None:
                raise RuntimeError('无法创建输出栅格文件')
            
            # 设置地理变换参数（使用WGS84，经纬度）
            geotransform = (min_lon, pixel_size / 111000, 0, max_lat, 0, -pixel_size / 111000)
            dst_ds.SetGeoTransform(geotransform)
            
            # 设置投影（WGS84）
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(4326)
            dst_ds.SetProjection(srs.ExportToWkt())
            
            # 写入数据
            band = dst_ds.GetRasterBand(1)
            band.WriteArray(raster_array)
            band.SetNoDataValue(0)
            band.SetDescription('Risk Level')
            
            # 设置统计信息
            valid_data = raster_array[raster_array > 0]
            if len(valid_data) > 0:
                band.SetStatistics(
                    float(np.min(valid_data)),
                    float(np.max(valid_data)),
                    float(np.mean(valid_data)),
                    float(np.std(valid_data))
                )
            
            band.FlushCache()
            dst_ds.FlushCache()
            dst_ds = None
            
            logger.info(f"风险等级栅格已创建: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"创建风险等级栅格失败: {e}", exc_info=True)
            return None
    
    def _create_impact_raster(self, projects: List[Dict[str, Any]], risk_analysis: Dict[str, Any], 
                              output_dir: str, task_id: str, pixel_size: float = 100.0) -> Optional[str]:
        """创建影响强度栅格"""
        try:
            if not projects:
                logger.warning("无工程项目数据，跳过影响强度栅格生成")
                return None
            
            # 计算所有项目的边界
            all_coords = []
            for project in projects:
                coords = project.get('coordinates')
                if coords:
                    if isinstance(coords[0][0], list):
                        for ring in coords:
                            all_coords.extend(ring)
                    else:
                        all_coords.extend(coords)
            
            if not all_coords:
                logger.warning("无有效坐标数据，跳过影响强度栅格生成")
                return None
            
            # 计算范围
            lons = [coord[0] for coord in all_coords]
            lats = [coord[1] for coord in all_coords]
            min_lon, max_lon = min(lons), max(lons)
            min_lat, max_lat = min(lats), max(lats)
            
            # 扩大范围
            buffer = 0.01
            min_lon -= buffer
            max_lon += buffer
            min_lat -= buffer
            max_lat += buffer
            
            # 计算栅格尺寸
            width = int((max_lon - min_lon) / pixel_size * 111000)
            height = int((max_lat - min_lat) / pixel_size * 111000)
            
            if width <= 0 or height <= 0:
                logger.warning(f"栅格尺寸无效: {width}x{height}")
                return None
            
            # 基于项目数量和状态计算影响强度
            # 影响强度 = 项目数量 * 状态权重
            status_weights = {
                '进行中': 1.0,
                '规划中': 0.8,
                '已完成': 0.3
            }
            
            total_impact = sum(status_weights.get(p.get('status', '进行中'), 0.5) for p in projects)
            impact_intensity = min(total_impact / len(projects) if projects else 0, 5.0)  # 归一化到0-5
            
            # 创建栅格数组
            raster_array = np.full((height, width), impact_intensity, dtype=np.float32)
            
            # 创建输出文件
            output_path = os.path.join(output_dir, f'impact_raster_{task_id}.tif')
            
            # 创建GeoTIFF
            driver = gdal.GetDriverByName('GTiff')
            dst_ds = driver.Create(output_path, width, height, 1, gdal.GDT_Float32)
            
            if dst_ds is None:
                raise RuntimeError('无法创建输出栅格文件')
            
            # 设置地理变换参数
            geotransform = (min_lon, pixel_size / 111000, 0, max_lat, 0, -pixel_size / 111000)
            dst_ds.SetGeoTransform(geotransform)
            
            # 设置投影
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(4326)
            dst_ds.SetProjection(srs.ExportToWkt())
            
            # 写入数据
            band = dst_ds.GetRasterBand(1)
            band.WriteArray(raster_array)
            band.SetNoDataValue(-9999)
            band.SetDescription('Impact Intensity')
            
            # 设置统计信息
            valid_data = raster_array[raster_array > 0]
            if len(valid_data) > 0:
                band.SetStatistics(
                    float(np.min(valid_data)),
                    float(np.max(valid_data)),
                    float(np.mean(valid_data)),
                    float(np.std(valid_data))
                )
            
            band.FlushCache()
            dst_ds.FlushCache()
            dst_ds = None
            
            logger.info(f"影响强度栅格已创建: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"创建影响强度栅格失败: {e}", exc_info=True)
            return None
    
    def _publish_raster_to_geoserver(self, raster_path: str, layer_name: str) -> Tuple[Optional[str], Optional[str]]:
        """将栅格发布到GeoServer并返回(WMS URL, 实际图层名称)"""
        try:
            geoserver = get_geoserver_manager()
            
            logger.info(f"开始发布栅格图层到GeoServer: {layer_name}")
            logger.info(f"栅格文件路径: {raster_path}")
            logger.info(f"GeoServer URL: {geoserver.base_url}")
            logger.info(f"工作空间: {geoserver.workspace}")
            
            # 确保工作空间存在
            workspace_created = geoserver.create_workspace()
            if workspace_created:
                logger.info(f"工作空间 {geoserver.workspace} 创建成功")
            else:
                logger.info(f"工作空间 {geoserver.workspace} 已存在或创建失败")
            
            # 创建CoverageStore（每次任务使用独立的CoverageStore）
            coverage_store_name = f"overlay_{self.task.id}"
            
            # 发布栅格图层（使用CoverageStore）
            logger.info(f"开始发布栅格图层: {layer_name} 到CoverageStore: {coverage_store_name}")
            publish_success = geoserver.publish_raster(coverage_store_name, layer_name, raster_path)
            
            if publish_success:
                # 验证图层是否存在，如果期望的图层名称不存在，查找实际创建的图层名称
                import time
                time.sleep(2)  # 等待GeoServer处理完成
                
                actual_layer_name = layer_name
                full_layer_name = f"{geoserver.workspace}:{layer_name}"
                layer_check = geoserver.get_layer_info(full_layer_name)
                
                if not layer_check:
                    logger.info(f"⚠️ 期望图层名称 {layer_name} 不存在，尝试查找实际创建的图层...")
                    try:
                        coverage_list = geoserver._make_request('GET', f'workspaces/{geoserver.workspace}/coveragestores/{coverage_store_name}/coverages.json')
                        if coverage_list and 'coverages' in coverage_list:
                            coverages = coverage_list['coverages'].get('coverage', [])
                            if isinstance(coverages, list) and len(coverages) > 0:
                                coverage_obj = coverages[0]
                                if isinstance(coverage_obj, dict):
                                    actual_layer_name = coverage_obj.get('name', layer_name)
                                else:
                                    actual_layer_name = coverage_store_name
                            elif isinstance(coverages, dict):
                                actual_layer_name = coverages.get('name', layer_name)
                            else:
                                actual_layer_name = coverage_store_name
                            
                            logger.info(f"找到实际图层名称: {actual_layer_name}")
                            full_actual_name = f"{geoserver.workspace}:{actual_layer_name}"
                            layer_check = geoserver.get_layer_info(full_actual_name)
                            if layer_check:
                                logger.info(f"✅ 找到实际创建的图层: {actual_layer_name}")
                                actual_layer_name = actual_layer_name
                            else:
                                logger.warning(f"⚠️ 实际图层名称 {actual_layer_name} 也不存在，可能GeoServer尚未完全处理")
                    except Exception as e:
                        logger.warning(f"⚠️ 查找实际图层名称时出错: {e}")
                
                # 使用实际图层名称生成WMS URL
                final_layer_name = actual_layer_name if layer_check else layer_name
                wms_url = f"{geoserver.base_url}/ows?service=WMS&version=1.3.0&request=GetMap&layers={geoserver.workspace}:{final_layer_name}&format=image/png&transparent=true"
                
                logger.info(f"✅ 栅格图层发布成功: {layer_name}")
                if final_layer_name != layer_name:
                    logger.info(f"⚠️ 实际使用的图层名称: {final_layer_name}（期望: {layer_name}）")
                logger.info(f"WMS URL: {wms_url}")
                
                # 验证WMS URL是否可访问
                try:
                    import requests
                    test_url = f"{geoserver.base_url}/ows?service=WMS&version=1.3.0&request=GetCapabilities"
                    test_response = requests.get(test_url, auth=geoserver.auth, timeout=5)
                    if test_response.status_code == 200:
                        logger.info("WMS服务验证成功")
                    else:
                        logger.warning(f"WMS服务验证失败: HTTP {test_response.status_code}")
                except Exception as test_e:
                    logger.warning(f"WMS服务验证失败: {test_e}")
                
                return wms_url, final_layer_name
            else:
                logger.error(f"❌ 栅格图层发布失败: {layer_name}")
                logger.error("可能的原因：")
                logger.error("  1. GeoServer未运行或无法连接")
                logger.error("  2. 文件路径错误或文件不存在")
                logger.error("  3. GeoServer权限不足")
                logger.error("  4. 数据存储创建失败")
                return None, None
                
        except Exception as e:
            logger.error(f"发布栅格到GeoServer时发生异常: {e}", exc_info=True)
            # 即使GeoServer发布失败，也返回栅格文件路径，前端可以直接加载
            return None, None


def perform_overlay_analysis(task_id: str) -> Dict[str, Any]:
    """执行叠加分析的入口函数"""
    try:
        task = OverlayAnalysisTask.objects.get(id=task_id)
        analyzer = OverlayAnalyzer(task)
        return analyzer.analyze()
    except OverlayAnalysisTask.DoesNotExist:
        raise ValueError(f"分析任务不存在: {task_id}")
    except Exception as e:
        logger.error(f"叠加分析执行失败: {str(e)}")
        raise
