<template>
  <div class="ecological-indices-layer">
    <div v-if="indicesData" class="indices-legend">
      <div class="legend-header">
        <h4>生态指数图例</h4>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>
      <div class="legend-content">
        <div class="indices-info">
          <div class="info-item">
            <span class="info-label">数据源:</span>
            <span class="info-value">{{ indicesData.filename }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">计算时间:</span>
            <span class="info-value">{{ formatDate(indicesData.timestamp) }}</span>
          </div>
        </div>
        
        <div class="indices-list">
          <div v-for="(value, key) in indicesData.results" :key="key" class="index-item">
            <div class="index-header">
              <span class="index-name">{{ formatIndexName(key) }}</span>
              <span class="index-value">{{ formatIndexValue(value) }}</span>
            </div>
            <div class="index-bar-container">
              <div class="index-bar" :style="getBarStyle(key, value)"></div>
            </div>
            <div class="index-levels">
              <span class="level-marker excellent">优</span>
              <span class="level-marker good">良</span>
              <span class="level-marker moderate">中</span>
              <span class="level-marker poor">差</span>
              <span class="level-marker bad">劣</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'

// Props
const props = defineProps({
  indicesData: {
    type: Object,
    required: true
  }
})

// Emits
defineEmits(['close'])

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '未知时间'
  try {
    const date = new Date(dateString)
    return date.toLocaleString('zh-CN')
  } catch (e) {
    return dateString
  }
}

// 格式化指数名称
const formatIndexName = (key) => {
  const nameMap = {
    'fragmentation_index': '破碎化指数',
    'shannon_diversity': '多样性指数',
    'cohesion_index': '内聚力指数',
    'fragility_index': '脆弱性指数',
    'soil_erosion_index': '土壤侵蚀指数',
    'unused_land_proportion': '未利用土地比例(%)',
    'cultivated_construction_proportion': '耕地与建设用地比例(%)',
    'land_degradation_index': '土地退化指数'
  }
  
  return nameMap[key] || key.replace(/_/g, ' ')
}

// 格式化指数值
const formatIndexValue = (value) => {
  if (typeof value === 'number') {
    return value.toFixed(4)
  }
  return value
}

// 获取指数条形图样式 - 与生态环境评估界面保持一致的标准
const getBarStyle = (key, value) => {
  if (typeof value !== 'number') return { width: '0%' }
  
  // 不同指数有不同的计算方式
  let percentage = 0
  let color = ''
  
  switch (key) {
    case 'fragmentation_index':
      // 破碎化指数：0表示完全未破碎，1表示极度破碎
      percentage = Math.min(value * 100, 100)
      
      if (value === 0) color = '#52c41a' // 优：完全未破碎
      else if (value < 0.3) color = '#1890ff' // 良：轻微破碎
      else if (value < 0.5) color = '#faad14' // 中：中度破碎
      else if (value < 0.7) color = '#fa8c16' // 差：严重破碎
      else color = '#f5222d' // 劣：极度破碎
      break
      
    case 'shannon_diversity':
      // 多样性指数：值越高表示多样性越丰富，通常在0-3之间
      percentage = Math.min(value / 3 * 100, 100)
      
      if (value > 2.0) color = '#52c41a' // 优：非常丰富的多样性
      else if (value > 1.5) color = '#1890ff' // 良：较好的多样性
      else if (value > 1.0) color = '#faad14' // 中：中等多样性
      else if (value > 0.5) color = '#fa8c16' // 差：较低多样性
      else color = '#f5222d' // 劣：极低多样性
      break
      
    case 'cohesion_index':
      // 内聚力指数：值越高表示连接性越好，0-1范围
      percentage = Math.min(value * 100, 100)
      
      if (value === 0) color = '#f5222d' // 劣：无连接性
      else if (value < 0.3) color = '#fa8c16' // 差：低连接性
      else if (value < 0.5) color = '#faad14' // 中：中等连接性
      else if (value < 0.8) color = '#1890ff' // 良：良好连接性
      else color = '#52c41a' // 优：极佳连接性
      break
      
    case 'fragility_index':
      // 脆弱性指数：值越低表示抵抗力越强，0-1范围
      percentage = Math.min(value * 100, 100)
      
      if (value < 0.2) color = '#52c41a' // 优：极低脆弱性
      else if (value < 0.3) color = '#1890ff' // 良：低脆弱性
      else if (value < 0.5) color = '#faad14' // 中：中等脆弱性
      else if (value < 0.7) color = '#fa8c16' // 差：高脆弱性
      else color = '#f5222d' // 劣：极高脆弱性
      break
      
    case 'soil_erosion_index':
      // 土壤侵蚀指数：值越低表示侵蚀程度越轻，0-1范围
      percentage = Math.min(value * 100, 100)
      
      if (value < 0.2) color = '#52c41a' // 优：微度侵蚀
      else if (value < 0.3) color = '#1890ff' // 良：轻度侵蚀
      else if (value < 0.5) color = '#faad14' // 中：中度侵蚀
      else if (value < 0.7) color = '#fa8c16' // 差：重度侵蚀
      else color = '#f5222d' // 劣：极重度侵蚀
      break
      
    case 'land_degradation_index':
      // 土地退化指数：值越低表示退化程度越轻，0-1范围
      percentage = Math.min(value * 100, 100)
      
      if (value < 0.2) color = '#52c41a' // 优：微度退化
      else if (value < 0.3) color = '#1890ff' // 良：轻度退化
      else if (value < 0.5) color = '#faad14' // 中：中度退化
      else if (value < 0.7) color = '#fa8c16' // 差：重度退化
      else color = '#f5222d' // 劣：极重度退化
      break
      
    case 'unused_land_proportion':
      // 未利用土地比例：按照生态环境评估界面标准
      percentage = Math.min(value * 5, 100) // 将比例放大5倍以便可视化
      
      if (value < 5) color = '#52c41a' // 优：极低比例
      else if (value < 10) color = '#1890ff' // 良：低比例
      else if (value < 15) color = '#faad14' // 中：中等比例
      else if (value < 20) color = '#fa8c16' // 差：高比例
      else color = '#f5222d' // 劣：极高比例
      break
      
    case 'cultivated_construction_proportion':
      // 耕地与建设用地比例：按照生态环境评估界面标准
      percentage = Math.min(value, 100)
      
      if (value >= 35 && value <= 45) color = '#52c41a' // 优：最佳平衡
      else if (value >= 30 && value < 35 || value > 45 && value <= 50) color = '#1890ff' // 良：良好平衡
      else if (value >= 25 && value < 30 || value > 50 && value <= 55) color = '#faad14' // 中：一般平衡
      else if (value >= 20 && value < 25 || value > 55 && value <= 60) color = '#fa8c16' // 差：较差平衡
      else color = '#f5222d' // 劣：严重失衡
      break
      
    default:
      // 默认假设0-1范围
      percentage = Math.min(value * 100, 100)
      color = '#1890ff'
  }
  
  return {
    width: `${percentage}%`,
    backgroundColor: color
  }
}
</script>

<style scoped>
.ecological-indices-layer {
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 1000;
  width: 300px;
}

.indices-legend {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  overflow: hidden;
}

.legend-header {
  background: #fafafa;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.legend-header h4 {
  margin: 0;
  font-size: 14px;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 18px;
  color: #999;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: #333;
}

.legend-content {
  padding: 16px;
}

.indices-info {
  margin-bottom: 16px;
}

.info-item {
  display: flex;
  margin-bottom: 8px;
  font-size: 12px;
}

.info-label {
  width: 70px;
  color: #666;
}

.info-value {
  flex: 1;
  color: #333;
  word-break: break-all;
}

.indices-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.index-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.index-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.index-name {
  font-size: 13px;
  color: #333;
  font-weight: 500;
}

.index-value {
  font-size: 13px;
  color: #1890ff;
  font-weight: 600;
}

.index-bar-container {
  height: 8px;
  background: #f5f5f5;
  border-radius: 4px;
  overflow: hidden;
}

.index-bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.index-levels {
  display: flex;
  justify-content: space-between;
  margin-top: 2px;
}

.level-marker {
  font-size: 10px;
  color: #999;
}

.level-marker.excellent {
  color: #52c41a;
}

.level-marker.good {
  color: #1890ff;
}

.level-marker.moderate {
  color: #faad14;
}

.level-marker.poor {
  color: #fa8c16;
}

.level-marker.bad {
  color: #f5222d;
}
</style>
