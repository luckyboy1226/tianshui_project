<template>
  <div v-if="visible" class="overlay-analysis-popup">
    <div class="popup-header">
      <div class="header-copy">
        <span class="header-kicker">Overlay Insight</span>
        <h3>叠加分析与监控</h3>
      </div>
      <button class="close-btn" @click="close" aria-label="关闭弹窗">×</button>
    </div>
    
    <div class="popup-content">
      <!-- 坐标信息 -->
      <div class="section">
        <div class="section-title"><span class="section-icon">📍</span><span>位置信息</span></div>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">经度</span>
            <span class="value">{{ formatCoordinate(coordinate.lng) }}</span>
          </div>
          <div class="info-item">
            <span class="label">纬度</span>
            <span class="value">{{ formatCoordinate(coordinate.lat) }}</span>
          </div>
        </div>
      </div>

      <!-- 生态栅格信息 -->
      <div class="section" v-if="ecologyData">
        <div class="section-title"><span class="section-icon">🌿</span><span>生态指数</span></div>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">{{ ecologyData.valueLabel || '生态指数值' }}</span>
            <span class="value" :class="getEcologyLevelClass(ecologyData)">
              {{ formatEcologyValue(ecologyData) }}
            </span>
          </div>
          <div class="info-item" v-if="ecologyData.level">
            <span class="label">生态等级</span>
            <span class="value" :class="getEcologyLevelClass(ecologyData)">
              {{ ecologyData.level }}<span v-if="ecologyData.shortLevel" class="level-alias">（{{ ecologyData.shortLevel }}）</span>
            </span>
          </div>
          <div class="info-item" v-if="ecologyData.sourceMode === 'continuous' && ecologyData.normalizedValue !== null">
            <span class="label">分级依据</span>
            <span class="value value-subtle">
              0.2 / 0.4 / 0.6 / 0.8 五级分段
            </span>
          </div>
        </div>
        <div class="risk-indicator" :class="getEcologyRiskClass(ecologyData)">
          <span class="indicator-icon">{{ getEcologyRiskIcon(ecologyData) }}</span>
          <span class="indicator-text">{{ getEcologyRiskText(ecologyData) }}</span>
        </div>
        <div v-if="ecologyData.isHighRisk" class="high-risk-banner">
          <span class="banner-badge">高风险区域</span>
          <span class="banner-text">该位置属于生态环境“差”等级，建议优先标注与修复。</span>
        </div>
      </div>
      <div class="section" v-else>
        <div class="section-title"><span class="section-icon">🌿</span><span>生态指数</span></div>
        <div class="no-data">该位置无生态指数数据</div>
      </div>
      <div class="section" v-if="ecologyData && getDisplayEntries(ecologyData.rawProperties).length">
        <details class="attribute-panel">
          <summary class="attribute-summary">
            <span class="section-title compact"><span class="section-icon">🧾</span><span>生态原始属性</span></span>
            <span class="summary-hint">展开查看全部字段</span>
          </summary>
          <div class="attribute-list">
            <div
              v-for="entry in getDisplayEntries(ecologyData.rawProperties)"
              :key="`ecology-${entry.key}`"
              class="attribute-row"
            >
              <span class="attribute-key">{{ entry.key }}</span>
              <span class="attribute-value">{{ entry.value }}</span>
            </div>
          </div>
        </details>
      </div>

      <!-- 经济矢量信息 -->
      <div class="section" v-if="economyData">
        <div class="section-title"><span class="section-icon">💰</span><span>经济数据</span></div>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">区域名称</span>
            <span class="value">{{ getEconomyRegionName(economyData) }}</span>
          </div>
          <div class="info-item" v-if="economyData.layer_name">
            <span class="label">图层类型</span>
            <span class="value">{{ economyData.layer_name }}</span>
          </div>
          <div class="info-item" v-if="economyData.code">
            <span class="label">编码</span>
            <span class="value">{{ economyData.code }}</span>
          </div>
          <div class="info-item" v-if="hasValue(economyData.area_km2)">
            <span class="label">面积</span>
            <span class="value">{{ formatArea(economyData.area_km2) }}</span>
          </div>
          <div class="info-item">
            <span class="label">2023 GDP（亿元）</span>
            <span class="value" :class="getGDPLevelClass(economyData.GDP)">
              {{ formatGDP(economyData.GDP_2023 ?? economyData.GDP) }}
            </span>
          </div>
          <div class="info-item">
            <span class="label">2020 GDP（亿元）</span>
            <span class="value">{{ formatGDP(economyData.GDP_2020) }}</span>
          </div>
          <div class="info-item">
            <span class="label">2015 GDP（亿元）</span>
            <span class="value">{{ formatGDP(economyData.GDP_2015) }}</span>
          </div>
          <div class="info-item">
            <span class="label">2023 人口</span>
            <span class="value">{{ formatPopulation(economyData.POP_2023 ?? economyData.POP) }}</span>
          </div>
          <div class="info-item">
            <span class="label">2020 人口</span>
            <span class="value">{{ formatPopulation(economyData.POP_2020) }}</span>
          </div>
          <div class="info-item">
            <span class="label">2015 人口</span>
            <span class="value">{{ formatPopulation(economyData.POP_2015) }}</span>
          </div>
        </div>
        <div class="risk-indicator" :class="getGDPLevelClass(economyData.GDP)">
          <span class="indicator-icon">💰</span>
          <span class="indicator-text">{{ getGDPLevelText(economyData.GDP) }}</span>
        </div>
        <details v-if="getDisplayEntries(economyData.rawProperties).length" class="attribute-panel">
          <summary class="attribute-summary">
            <span class="subsection-title">完整属性</span>
            <span class="summary-hint">展开查看全部字段</span>
          </summary>
          <div class="attribute-list">
            <div
              v-for="entry in getExpandedEntries(economyData.rawProperties, economySummaryKeys)"
              :key="`economy-${entry.key}`"
              class="attribute-row"
            >
              <span class="attribute-key">{{ entry.key }}</span>
              <span class="attribute-value">{{ entry.value }}</span>
            </div>
          </div>
        </details>
      </div>
      <div class="section" v-else>
        <div class="section-title"><span class="section-icon">💰</span><span>经济数据</span></div>
        <div class="no-data">该位置无经济数据</div>
      </div>

      <!-- 工程矢量信息 -->
      <div class="section" v-if="engineeringData && engineeringData.length > 0">
        <div class="section-title"><span class="section-icon">🏗️</span><span>工程项目</span></div>
        <div class="project-list">
          <div 
            v-for="(project, index) in engineeringData" 
            :key="index"
            class="project-item"
          >
            <div class="project-header">
              <span class="project-name">{{ getProjectName(project) }}</span>
              <span
                v-if="getProjectStatus(project)"
                class="project-status"
                :class="getStatusClass(getProjectStatus(project))"
              >
                {{ getProjectStatus(project) }}
              </span>
            </div>
            <div class="project-details">
              <div class="detail-item" v-if="getProjectSegment(project)">
                <span class="label">项目段</span>
                <span class="value">{{ getProjectSegment(project) }}</span>
              </div>
              <div class="detail-item">
                <span class="label">类型</span>
                <span class="value">{{ getProjectType(project) }}</span>
              </div>
              <div class="detail-item" v-if="hasValue(project.area_km2)">
                <span class="label">面积</span>
                <span class="value">{{ formatArea(project.area_km2) }}</span>
              </div>
              <div class="detail-item" v-if="project.start_date">
                <span class="label">开始时间</span>
                <span class="value">{{ project.start_date }}</span>
              </div>
            </div>
            <details v-if="getDisplayEntries(project.rawProperties).length" class="attribute-panel">
              <summary class="attribute-summary">
                <span class="subsection-title">完整属性</span>
                <span class="summary-hint">展开查看全部字段</span>
              </summary>
              <div class="attribute-list">
                <div
                  v-for="entry in getExpandedEntries(project.rawProperties, projectSummaryKeys)"
                  :key="`project-${index}-${entry.key}`"
                  class="attribute-row"
                >
                  <span class="attribute-key">{{ entry.key }}</span>
                  <span class="attribute-value">{{ entry.value }}</span>
                </div>
              </div>
            </details>
          </div>
        </div>
      </div>
      <div class="section" v-else>
        <div class="section-title"><span class="section-icon">🏗️</span><span>工程项目</span></div>
        <div class="no-data">该位置无工程项目</div>
      </div>

      <!-- 风险分析 -->
      <div class="section risk-analysis" v-if="riskAnalysis">
        <div class="section-title"><span class="section-icon">⚠️</span><span>风险分析</span></div>
        <div class="risk-summary">
          <div class="risk-item" :class="riskAnalysis.level">
            <span class="risk-icon">{{ getRiskIcon(riskAnalysis.level) }}</span>
            <span class="risk-text">{{ riskAnalysis.text }}</span>
          </div>
          <div class="risk-details" v-if="riskAnalysis.details">
            <div class="detail-text">{{ riskAnalysis.details }}</div>
          </div>
        </div>
      </div>

      <!-- 决策建议 -->
      <div class="section decision-recommendation" v-if="riskAnalysis && riskAnalysis.recommendation">
        <div class="section-title"><span class="section-icon">💡</span><span>决策建议</span></div>
        <div class="recommendation-content">
          <div class="recommendation-text">{{ riskAnalysis.recommendation }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const economySummaryKeys = [
  'admin_name', 'ADMIN_NAME', 'name', 'NAME', 'Name',
  'layer', 'LAYER',
  'code', 'CODE',
  'area_km2', 'AREA_KM2', 'area__k2', 'AREA__K2', 'area', 'AREA',
  '2015_GDP', 'GDP_2015', 'gdp_2015',
  '2020_GDP', 'GDP_2020', 'gdp_2020',
  '2023_GDP', 'GDP_2023', 'gdp_2023',
  '2015_POP', 'POP_2015', 'pop_2015',
  '2020_POP', 'POP_2020', 'pop_2020',
  '2023_POP', 'POP_2023', 'pop_2023',
  'GDP', 'gdp', 'Gdp',
  'POP', 'pop', 'Pop'
]

const projectSummaryKeys = [
  'proj_name', 'PROJ_NAME', 'project_name', 'PROJECT_NAME', 'name', 'NAME', '地名',
  'proj_segment', 'PROJ_SEGMENT', 'project_segment', 'PROJECT_SEGMENT', 'segment', 'SEGMENT', '项目段',
  'proj_type', 'PROJ_TYPE', 'project_type', 'PROJECT_TYPE', 'type', 'TYPE', 'category', 'CATEGORY', '项目类',
  'status', 'STATUS', 'state', 'STATE',
  'start_date', 'START_DATE', 'start_time', 'START_TIME', 'begin_date', 'BEGIN_DATE',
  'end_date', 'END_DATE', 'end_time', 'END_TIME', 'finish_date', 'FINISH_DATE',
  'area_km2', 'AREA_KM2', 'area', 'AREA'
]

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  coordinate: {
    type: Object,
    default: () => ({ lng: 0, lat: 0 })
  },
  ecologyData: {
    type: Object,
    default: null
  },
  economyData: {
    type: Object,
    default: null
  },
  engineeringData: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['close'])

const close = () => {
  emit('close')
}

const hasValue = (value) => value !== null && value !== undefined && value !== ''

const getProjectName = (project) => {
  return project?.proj_name || project?.PROJ_NAME || project?.project_name || project?.PROJECT_NAME || project?.name || project?.NAME || project?.['地名'] || '未知工程'
}

const getProjectSegment = (project) => {
  return project?.proj_segment || project?.PROJ_SEGMENT || project?.project_segment || project?.PROJECT_SEGMENT || project?.segment || project?.SEGMENT || project?.['项目段'] || ''
}

const getProjectType = (project) => {
  return project?.proj_type || project?.PROJ_TYPE || project?.project_type || project?.PROJECT_TYPE || project?.type || project?.TYPE || project?.category || project?.CATEGORY || project?.['项目类'] || '未知'
}

const getProjectStatus = (project) => {
  return project?.status || project?.STATUS || ''
}

const getEconomyRegionName = (economyData) => {
  return economyData?.admin_name || economyData?.ADMIN_NAME || economyData?.Name || economyData?.name || '未知'
}

const getDisplayEntries = (properties) => {
  if (!properties || typeof properties !== 'object') {
    return []
  }

  return Object.entries(properties)
    .filter(([key]) => key !== 'bbox')
    .map(([key, value]) => ({
      key,
      value: formatAttributeValue(value)
    }))
}

const getFilteredDisplayEntries = (properties, excludedKeys = []) => {
  const excluded = new Set(excludedKeys)
  return getDisplayEntries(properties).filter((entry) => !excluded.has(entry.key))
}

const getExpandedEntries = (properties, excludedKeys = []) => {
  const filteredEntries = getFilteredDisplayEntries(properties, excludedKeys)
  if (filteredEntries.length > 0) {
    return filteredEntries
  }
  return getDisplayEntries(properties)
}

const formatAttributeValue = (value) => {
  if (value === null || value === undefined || value === '') {
    return 'N/A'
  }
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value)
    } catch {
      return String(value)
    }
  }
  return String(value)
}

// 格式化坐标
const formatCoordinate = (coord) => {
  if (coord === null || coord === undefined || isNaN(coord) || coord === 'NaN') {
    return 'N/A'
  }
  if (typeof coord === 'number') {
    return coord.toFixed(4)
  }
  if (typeof coord === 'string' && coord !== 'NaN') {
    return coord
  }
  return 'N/A'
}

// 格式化生态指数值
const formatEcologyValue = (ecologyData) => {
  if (!ecologyData) return 'N/A'

  if (ecologyData.displayValueText) {
    return ecologyData.displayValueText
  }

  const value = ecologyData.displayValue ?? ecologyData.normalizedValue ?? ecologyData.value
  if (value === null || value === undefined || Number.isNaN(value)) return 'N/A'
  if (Number.isInteger(value)) return String(value)
  return Number(value).toFixed(3)
}

// 获取生态等级
const getEcologyLevelClass = (ecologyData) => {
  const levelCode = ecologyData?.levelCode
  if (!levelCode) return 'unknown'
  return levelCode
}

// 获取生态风险等级
const getEcologyRiskClass = (ecologyData) => {
  const level = getEcologyLevelClass(ecologyData)
  if (level === 'bad') return 'high-risk'
  if (level === 'poor' || level === 'moderate') return 'medium-risk'
  if (level === 'good' || level === 'excellent') return 'low-risk'
  if (String(level).startsWith('class_')) return 'unknown'
  return 'low-risk'
}

const getEcologyRiskIcon = (ecologyData) => {
  const level = getEcologyLevelClass(ecologyData)
  if (level === 'bad') return '🔴'
  if (level === 'poor' || level === 'moderate') return '🟡'
  if (String(level).startsWith('class_')) return '🔘'
  return '🟢'
}

const getEcologyRiskText = (ecologyData) => {
  const level = getEcologyLevelClass(ecologyData)
  if (level === 'bad') return '高风险区域：生态环境差，建议优先标注与修复'
  if (level === 'poor') return '生态环境较差，建议重点巡查'
  if (level === 'moderate') return '生态环境中等，建议持续监测'
  if (String(level).startsWith('class_')) return '当前为上传的分类栅格，已显示分类编码，可结合原始属性辅助判读'
  return '生态环境整体较好'
}

// 格式化GDP
const formatGDP = (gdp) => {
  if (gdp === null || gdp === undefined || Number.isNaN(gdp)) return 'N/A'
  return Number(gdp).toFixed(1)
}

// 获取GDP等级
const getGDPLevelClass = (gdp) => {
  if (gdp === null || gdp === undefined) return 'unknown'
  if (gdp >= 500) return 'high'
  if (gdp >= 100) return 'medium'
  return 'low'
}

const getGDPLevelText = (gdp) => {
  const level = getGDPLevelClass(gdp)
  if (level === 'high') return '高经济强度区域'
  if (level === 'medium') return '中等经济强度区域'
  return '低经济强度区域'
}

// 格式化人口
const formatPopulation = (pop) => {
  if (pop === null || pop === undefined || Number.isNaN(pop)) return 'N/A'
  const numericPop = Number(pop)
  if (Number.isNaN(numericPop)) return 'N/A'
  if (numericPop >= 10000) {
    return (numericPop / 10000).toFixed(1) + '万'
  }
  return numericPop.toString()
}

// 格式化面积
const formatArea = (area) => {
  if (area === null || area === undefined || Number.isNaN(area)) return 'N/A'
  return Number(area).toFixed(2) + ' km²'
}

// 获取状态样式类
const getStatusClass = (status) => {
  if (!status) return 'unknown'
  if (status === '已完工') return 'completed'
  if (status === '进行中') return 'ongoing'
  if (status === '规划中') return 'planned'
  return 'unknown'
}

// 计算风险分析
const riskAnalysis = computed(() => {
  const hasEcology = props.ecologyData && props.ecologyData.value !== null
  const economyValue = props.economyData?.GDP_2023 ?? props.economyData?.GDP
  const hasEconomy = props.economyData && economyValue !== null && economyValue !== undefined
  const hasEngineering = props.engineeringData && props.engineeringData.length > 0
  
  if (!hasEcology && !hasEconomy) return null
  
  let riskLevel = 'low'
  let riskText = '风险较低'
  let riskDetails = ''
  let recommendation = ''
  
  // 生态指数较差
  const ecologyBad = hasEcology && getEcologyLevelClass(props.ecologyData) === 'bad'
  const ecologyPoor = hasEcology && getEcologyLevelClass(props.ecologyData) === 'poor'
  const ecologyModerate = hasEcology && getEcologyLevelClass(props.ecologyData) === 'moderate'
  // GDP高
  const economyHigh = hasEconomy && getGDPLevelClass(economyValue) === 'high'
  // GDP中等
  const economyMedium = hasEconomy && getGDPLevelClass(economyValue) === 'medium'
  // 无治理工程
  const noEngineering = !hasEngineering || props.engineeringData.length === 0
  
  // 风险等级判断逻辑
  // 极高风险场景：生态差 + 高GDP + 无治理工程
  if (ecologyBad && economyHigh && noEngineering) {
    riskLevel = 'critical'
    riskText = '⚠️ 极高风险'
    riskDetails = '该位置属于生态环境差等级的高风险区域，且位于高GDP区域，但无工程项目。'
    recommendation = '建议尽快部署生态修复工程，优先考虑生态敏感区域保护。'
  } 
  // 高风险场景：生态差 + 中GDP + 无治理工程
  else if (ecologyBad && economyMedium && noEngineering) {
    riskLevel = 'high'
    riskText = '⚠️ 高风险'
    riskDetails = '该位置属于生态环境差等级的高风险区域，且位于中GDP区域，但无工程项目。'
    recommendation = '建议部署生态修复工程，加强生态保护措施。'
  }
  // 中高风险场景：生态差 + 无治理工程
  else if (ecologyBad && noEngineering) {
    riskLevel = 'high'
    riskText = '⚠️ 中高风险'
    riskDetails = '该位置属于生态环境差等级的高风险区域，但无工程项目。'
    recommendation = '建议考虑部署生态修复工程，改善生态环境质量。'
  }
  // 中高风险场景：生态较差 + 高GDP + 无治理工程
  else if (ecologyPoor && economyHigh && noEngineering) {
    riskLevel = 'high'
    riskText = '⚠️ 高风险'
    riskDetails = '该位置生态环境较差，且位于高GDP区域，但无工程项目。'
    recommendation = '建议将该区域列入重点监测清单，必要时提前介入生态修复。'
  }
  // 中等风险场景：生态中等 + 高GDP + 无治理工程
  else if (ecologyModerate && economyHigh && noEngineering) {
    riskLevel = 'medium'
    riskText = '⚠️ 中等风险'
    riskDetails = '该位置生态指数中等，且位于高GDP区域，但无工程项目。'
    recommendation = '建议加强生态监测，必要时部署生态修复工程。'
  }
  // 中等风险场景：生态中等 + 无治理工程
  else if (ecologyModerate && noEngineering) {
    riskLevel = 'medium'
    riskText = '⚠️ 中等风险'
    riskDetails = '该位置生态指数中等，但无工程项目。'
    recommendation = '建议加强生态监测，预防生态恶化。'
  }
  // 中等风险场景：生态较差 + 无治理工程
  else if (ecologyPoor && noEngineering) {
    riskLevel = 'medium'
    riskText = '⚠️ 重点关注'
    riskDetails = '该位置生态环境较差，建议持续巡查并评估是否需要修复工程。'
    recommendation = '建议结合周边工程布局，优先安排风险排查和生态跟踪。'
  }
  // 低风险场景：已有治理工程
  else if (hasEngineering) {
    riskLevel = 'low'
    riskText = '✅ 已有治理工程'
    riskDetails = '该位置已有工程项目，生态风险相对可控。'
    recommendation = '建议持续监控工程效果，确保生态修复效果。'
  }
  // 低风险场景：生态良好
  else if (hasEcology && !ecologyBad && !ecologyPoor && !ecologyModerate) {
    riskLevel = 'low'
    riskText = '✅ 生态状况良好'
    riskDetails = '该位置生态指数良好，生态风险较低。'
    recommendation = '建议继续保持良好的生态环境，定期监测。'
  }
  
  return {
    level: riskLevel,
    text: riskText,
    details: riskDetails,
    recommendation: recommendation
  }
})

const getRiskIcon = (level) => {
  if (level === 'critical') return '🔴'
  if (level === 'high') return '🟠'
  if (level === 'medium') return '🟡'
  return '🟢'
}
</script>

<style scoped>
.overlay-analysis-popup {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid rgba(219, 227, 236, 0.92);
  border-radius: 24px;
  box-shadow: 0 24px 54px rgba(31, 53, 83, 0.18);
  backdrop-filter: blur(14px);
  min-width: 460px;
  max-width: 640px;
  max-height: 82vh;
  overflow-y: auto;
  z-index: 2000;
}

.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 24px 28px 22px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.18);
  background:
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.22), transparent 32%),
    linear-gradient(135deg, #1c7ed6 0%, #4ba3ea 100%);
  color: white;
  border-radius: 24px 24px 0 0;
}

.header-copy {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.header-kicker {
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.72);
}

.popup-header h3 {
  margin: 0;
  font-size: 30px;
  line-height: 1.05;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.close-btn {
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.22);
  font-size: 28px;
  cursor: pointer;
  color: white;
  padding: 0;
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background 0.2s ease, transform 0.2s ease, border-color 0.2s ease;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.24);
  border-color: rgba(255, 255, 255, 0.32);
  transform: rotate(90deg);
}

.popup-content {
  padding: 20px 28px 28px;
  background:
    linear-gradient(180deg, rgba(244, 247, 250, 0.42) 0%, rgba(255, 255, 255, 0.96) 20%),
    #ffffff;
  position: relative;
}

.popup-content::before {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 120px;
  background:
    radial-gradient(circle at 15% 0%, rgba(73, 163, 234, 0.12), transparent 38%),
    radial-gradient(circle at 90% 10%, rgba(28, 126, 214, 0.08), transparent 30%);
  pointer-events: none;
}

.section {
  margin-bottom: 18px;
  padding: 18px 4px 20px;
  border-bottom: 1px solid #e8eff5;
}

.section:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.section-title {
  font-size: 14px;
  font-weight: 700;
  color: #24384d;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  letter-spacing: 0.01em;
}

.section-title.compact {
  margin-bottom: 0;
}

.section-icon {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: linear-gradient(135deg, #eef5fb 0%, #f8fbfd 100%);
  box-shadow: inset 0 0 0 1px #dbe6f0;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 92px;
  padding: 14px 16px;
  border-radius: 16px;
  background: linear-gradient(180deg, #fbfdff 0%, #f4f8fb 100%);
  border: 1px solid #e1e9f0;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.info-item .label {
  font-size: 12px;
  color: #708398;
  font-weight: 600;
  letter-spacing: 0.03em;
}

.info-item .value {
  font-size: 15px;
  color: #26384a;
  font-weight: 700;
  line-height: 1.5;
  word-break: break-word;
}

.level-alias {
  font-size: 12px;
  margin-left: 4px;
  opacity: 0.82;
}

.value.value-subtle {
  font-size: 13px;
  color: #667d92;
  font-weight: 600;
}

/* 生态等级颜色 */
.value.excellent {
  color: #1f8f4d;
}

.value.good {
  color: #4c9a2a;
}

.value.moderate {
  color: #cf8a18;
}

.value.poor {
  color: #d97706;
}

.value.bad {
  color: #d64545;
}

/* GDP等级颜色 */
.value.high {
  color: #d64545;
}

.value.medium {
  color: #cf8a18;
}

.value.low {
  color: #1f8f4d;
}

.risk-indicator {
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  font-weight: 600;
}

.risk-indicator.high-risk {
  background: #fff4f2;
  border: 1px solid #ffd6d2;
  color: #be3f3f;
}

.risk-indicator.medium-risk {
  background: #fff9ec;
  border: 1px solid #f4deb0;
  color: #b97b12;
}

.risk-indicator.low-risk {
  background: #f3fbf4;
  border: 1px solid #cfe7d3;
  color: #2e7b45;
}

.indicator-icon {
  font-size: 17px;
}

.high-risk-banner {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-radius: 16px;
  background:
    linear-gradient(135deg, rgba(214, 69, 69, 0.12) 0%, rgba(255, 245, 242, 0.96) 100%);
  border: 1px solid rgba(214, 69, 69, 0.24);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.62);
}

.banner-badge {
  flex: 0 0 auto;
  padding: 5px 10px;
  border-radius: 999px;
  background: #d64545;
  color: #fff;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.banner-text {
  color: #8d2e2e;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.6;
}

.no-data {
  color: #8a9aab;
  font-size: 13px;
  padding: 16px 18px;
  border-radius: 16px;
  background: linear-gradient(180deg, #fbfdff 0%, #f5f8fb 100%);
  border: 1px dashed #d4e0ea;
}

.project-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.project-item {
  background:
    radial-gradient(circle at top right, rgba(75, 163, 234, 0.08), transparent 28%),
    linear-gradient(180deg, #fbfdff 0%, #f5f8fb 100%);
  border-radius: 18px;
  padding: 16px;
  border: 1px solid #dfe7ef;
  box-shadow: 0 10px 22px rgba(46, 72, 98, 0.06);
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.project-name {
  font-size: 15px;
  font-weight: 700;
  color: #25384a;
}

.project-status {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}

.project-status.completed {
  background: #edf9ef;
  color: #2e7b45;
}

.project-status.ongoing {
  background: #fff8e8;
  color: #b97b12;
}

.project-status.planned {
  background: #eef6ff;
  color: #1e6fc8;
}

.project-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.raw-attributes {
  margin-top: 14px;
}

.subsection-title {
  font-size: 12px;
  font-weight: 700;
  color: #567089;
  letter-spacing: 0.04em;
}

.attribute-panel {
  margin-top: 16px;
  border: 1px solid #dbe7f1;
  border-radius: 16px;
  background: linear-gradient(180deg, #fcfeff 0%, #f5f9fc 100%);
  overflow: hidden;
}

.attribute-summary {
  list-style: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 16px;
  color: #2a4258;
  user-select: none;
}

.attribute-summary::-webkit-details-marker {
  display: none;
}

.summary-hint {
  font-size: 12px;
  color: #7b90a4;
  white-space: nowrap;
}

.attribute-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 14px 14px;
}

.attribute-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #e3ecf3;
}

.attribute-key {
  flex: 0 0 38%;
  color: #6f8498;
  font-size: 12px;
  font-weight: 600;
  word-break: break-word;
}

.attribute-value {
  flex: 1;
  color: #26384a;
  font-size: 13px;
  font-weight: 600;
  text-align: right;
  word-break: break-word;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  font-size: 12px;
  padding-top: 8px;
  border-top: 1px dashed #dde6ee;
}

.detail-item .label {
  color: #718396;
}

.detail-item .value {
  color: #24384d;
  font-weight: 600;
  text-align: right;
}

.risk-analysis {
  background: linear-gradient(180deg, #f9fbfd 0%, #f4f8fb 100%);
  border-radius: 18px;
  padding: 16px;
  border: 1px solid #dce6ef;
}

.risk-summary {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.risk-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  padding: 12px 14px;
  border-radius: 14px;
}

.risk-item.critical {
  background: #fff2f0;
  color: #bf3a3a;
}

.risk-item.high {
  background: #fff7ea;
  color: #bd6f14;
}

.risk-item.medium {
  background: #fffbea;
  color: #b58117;
}

.risk-item.low {
  background: #f1fbf3;
  color: #2e7b45;
}

.risk-icon {
  font-size: 18px;
}

.risk-details {
  padding: 12px 14px;
  background: white;
  border-radius: 14px;
  font-size: 13px;
  color: #627486;
  line-height: 1.7;
  border: 1px solid #e5edf4;
}

.detail-text {
  margin: 0;
}

.decision-recommendation {
  background: linear-gradient(180deg, #f4fbff 0%, #eef7fc 100%);
  border-radius: 18px;
  padding: 16px;
  border: 1px solid #d7e7f3;
}

.recommendation-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: rgba(255, 255, 255, 0.9);
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid #e4edf4;
}

.recommendation-text {
  font-size: 14px;
  color: #314456;
  line-height: 1.7;
}

@media (max-width: 768px) {
  .overlay-analysis-popup {
    min-width: 0;
    width: calc(100vw - 24px);
    max-width: calc(100vw - 24px);
    max-height: 78vh;
    border-radius: 20px;
  }

  .popup-header {
    padding: 20px 20px 18px;
    border-radius: 20px 20px 0 0;
  }

  .popup-header h3 {
    font-size: 24px;
  }

  .popup-content {
    padding: 16px 20px 22px;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }

  .project-header,
  .detail-item,
  .attribute-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .attribute-summary {
    flex-direction: column;
    align-items: flex-start;
  }

  .detail-item .value,
  .attribute-value {
    text-align: left;
  }
}
</style>

