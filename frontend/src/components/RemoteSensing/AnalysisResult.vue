<template>
  <div class="result-panel-apple">
    <template v-if="status === 'waiting'">
      <div class="placeholder-apple">请先上传数据并开始分析</div>
    </template>
    <template v-else-if="status === 'analyzing'">
      <div class="loading-apple">
        <el-icon class="loading-icon-apple"><Loading /></el-icon>
        <span class="loading-text-apple">正在分析，请稍候...</span>
      </div>
    </template>
    <template v-else-if="status === 'done'">
      <div class="result-content-apple">
        <div class="result-header-apple">
          <h2 class="result-title-apple">{{ indexLabelMap[selectedIndex] }}分析结果</h2>
          <el-button type="primary" @click="downloadResults" class="download-btn-apple">
            <el-icon><Download /></el-icon>
            下载数据
          </el-button>
          </div>

        <div v-if="resultData?.preview_mode || resultData?.preview_message" class="result-notice is-preview">
          <div class="notice-title">当前为大文件预览分析</div>
          <div class="notice-text">{{ resultData?.preview_message || '系统已自动切换为预览模式。' }}</div>
        </div>

        <div v-if="resultData?.supported_index_labels?.length" class="result-notice is-hint">
          <div class="notice-title">当前影像支持的指数</div>
          <div class="notice-text">{{ resultData.supported_index_labels.join('、') }}</div>
        </div>

        <div v-if="primaryVisualizationUrl" class="visualization-section">
          <img
            :src="primaryVisualizationUrl"
            alt="指数可视化结果"
            class="visualization-image"
            @error="handleVisualizationError"
          />
        </div>
        <div v-if="visualizationLoadError" class="result-notice is-warning">
          <div class="notice-title">可视化图片加载失败</div>
          <div class="notice-text">{{ visualizationLoadError }}</div>
        </div>

        <ResultCompareMap
          v-if="primaryCompareOverlay"
          title="遥感结果叠加对比"
          description="打开遥感影像底图后，可直接把当前彩色分析结果叠加在上面做对比。"
          :compare-overlay="primaryCompareOverlay"
        />

        <!-- 加载中 -->
        <div v-if="loading" class="loading-data-apple">
          <el-icon class="loading-icon-small"><Loading /></el-icon>
          <span>正在加载结果数据...</span>
        </div>

        <!-- 统计数据卡片 -->
        <div v-if="indicesData.length > 0" class="statistics-section">
          <div class="stats-cards">
            <div v-for="index in indicesData" :key="index.id" class="stat-card">
              <div class="stat-card-header">
                <span class="stat-card-title">{{ getIndexDisplayName(index.index_type) }}</span>
                <el-tag :type="getIndexTagType(index.mean_value)" size="small">
                  {{ getIndexLevel(index.mean_value) }}
                </el-tag>
              </div>
              <div class="stat-card-body">
                <div class="stat-item">
                  <span class="stat-label">平均值</span>
                  <span class="stat-value">{{ formatValue(index.mean_value) }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">最小值</span>
                  <span class="stat-value">{{ formatValue(index.min_value) }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">最大值</span>
                  <span class="stat-value">{{ formatValue(index.max_value) }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">标准差</span>
                  <span class="stat-value">{{ formatValue(index.std_value) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 图表区域 - 始终显示 -->
        <div class="charts-section">
          <!-- 面积分布饼图 -->
          <div class="chart-container">
            <h3 class="chart-title">生态质量等级面积分布</h3>
            <div ref="pieChartRef" class="chart-canvas"></div>
          </div>

          <!-- 统计值数值解读 -->
          <div class="chart-container">
            <h3 class="chart-title">统计值数值解读</h3>
            <div class="interpretation-content">
              <div v-if="indicesData.length > 0" class="interpretation-text">
                <div v-for="index in indicesData" :key="index.id" class="index-interpretation">
                  <h4 class="index-name">{{ getIndexDisplayName(index.index_type) }}</h4>
                  <div class="interpretation-items">
                    <div class="interpretation-item">
                      <span class="item-label">平均值解读：</span>
                      <span class="item-content">{{ getMeanInterpretation(index) }}</span>
                    </div>
                    <div class="interpretation-item">
                      <span class="item-label">数值范围：</span>
                      <span class="item-content">{{ getRangeInterpretation(index) }}</span>
                    </div>
                    <div class="interpretation-item">
                      <span class="item-label">变化程度：</span>
                      <span class="item-content">{{ getVariationInterpretation(index) }}</span>
                    </div>
                    <div class="interpretation-item">
                      <span class="item-label">生态意义：</span>
                      <span class="item-content">{{ getEcologicalMeaning(index) }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="no-data-text">
                <p>暂无分析结果数据</p>
                <p class="hint-text">请等待计算完成或重新开始分析</p>
              </div>
            </div>
          </div>
        </div>

        <!-- 无数据提示 -->
        <div v-if="indicesData.length === 0 && !loading" class="no-data-apple">
          <p>暂无分析结果数据</p>
          <p class="hint-text">请等待计算完成或重新开始分析</p>
        </div>
      </div>
    </template>
    <template v-else-if="status === 'error'">
      <div class="error-state-card">
        <h3 class="error-title">分析未完成</h3>
        <p class="error-message">{{ resultData?.error || '发生未知错误' }}</p>
        <p v-if="resultData?.details" class="error-details">{{ resultData.details }}</p>
        <div v-if="resultData?.supported_index_labels?.length" class="error-supported">
          建议改用：{{ resultData.supported_index_labels.join('、') }}
        </div>
        <div v-if="resultData?.bands_count" class="error-meta">
          当前识别波段数：{{ resultData.bands_count }}
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { ElIcon, ElButton, ElTag, ElMessage } from 'element-plus';
import { Loading, Download } from '@element-plus/icons-vue';
import * as echarts from 'echarts';
import { remoteSensingService } from '../../services/api.js';
import ResultCompareMap from '../Map/ResultCompareMap.vue';

const props = defineProps({
  status: String, // waiting | analyzing | done
  resultData: Object,
  selectedIndex: String,
  taskId: String
});

const loading = ref(false);
const indicesData = ref([]);
const pieChartRef = ref(null);
const visualizationLoadError = ref('');
let pieChart = null;
let removeResizeListener = null;

const indexLabelMap = computed(() => ({
  ndvi: '绿化指数 (NDVI)',
  heat: '热度指数 (LST)',
  ndwi: '湿度指数 (NDWI)',
  ndbi: '建筑指数 (NDBI)',
  dryness: '干度指数 (NDBSI)',
  wetness: '湿度指数',
  greenness: '绿度指数',
  rsei: 'RSEI',
  uploaded_raster: '上传成果栅格'
}));

const primaryIndex = computed(() => {
  if (!indicesData.value.length) return null;
  return indicesData.value.find((item) => item.index_type === 'rsei') || indicesData.value[0];
});

const primaryVisualizationUrl = computed(() => {
  const primary = primaryIndex.value;
  return normalizeVisualizationUrl(primary?.visualization_file_url || primary?.visualization_file || null);
});

const primaryCompareOverlay = computed(() => {
  const primary = primaryIndex.value;
  return primary?.compare_overlay || null;
});

function normalizeVisualizationUrl(url) {
  if (!url || typeof url !== 'string') return null;

  if (url.startsWith('/media/')) {
    return url;
  }

  try {
    const parsed = new URL(url, window.location.origin);
    if (parsed.pathname.startsWith('/media/')) {
      return `${parsed.pathname}${parsed.search}${parsed.hash}`;
    }
    return parsed.toString();
  } catch (error) {
    console.warn('解析可视化图片地址失败:', url, error);
    return url;
  }
}

// 监听状态变化，当完成时加载数据
watch(() => props.status, async (newStatus) => {
  if (newStatus === 'done' && props.resultData) {
    await loadIndicesData();
  }
});

// 加载生态指数数据
async function loadIndicesData() {
  if (!props.resultData) {
    console.log('没有结果数据，无法加载指数');
    return;
  }

  loading.value = true;
  visualizationLoadError.value = '';

  try {
    // 尝试多种方式获取影像ID
    let imageId = null;

    if (props.resultData.remote_sensing_image_id) {
      imageId = props.resultData.remote_sensing_image_id;
    } else if (props.resultData.remote_sensing_image) {
      imageId = props.resultData.remote_sensing_image.id || props.resultData.remote_sensing_image;
    }

    if (!imageId) {
      if (Array.isArray(props.resultData.indices)) {
        indicesData.value = props.resultData.indices;
        await nextTick();
        initCharts();
        return;
      }

      console.error('无法获取影像ID，resultData:', props.resultData);
      ElMessage.warning('无法获取影像ID');
      return;
    }

    console.log('加载影像指数数据，影像ID:', imageId);

    const response = await remoteSensingService.getIndices(imageId);
    console.log('获取到的指数数据:', response);
    console.log('响应结构:', {
      hasIndices: !!response.indices,
      indicesLength: response.indices?.length,
      indicesData: response.indices
    });

    if (response && response.indices) {
      indicesData.value = response.indices;
      console.log('设置indicesData:', indicesData.value);
      console.log('indicesData长度:', indicesData.value.length);

      // 等待DOM更新后初始化图表
      await nextTick();
      initCharts();
    } else {
      console.log('暂无指数数据，响应:', response);
      indicesData.value = Array.isArray(props.resultData.indices) ? props.resultData.indices : [];
    }
  } catch (error) {
    console.error('加载指数数据失败:', error);
    if (Array.isArray(props.resultData.indices)) {
      indicesData.value = props.resultData.indices;
      await nextTick();
      initCharts();
    } else {
      ElMessage.error('加载分析结果失败: ' + (error.message || '未知错误'));
    }
  } finally {
    loading.value = false;
  }
}

// 初始化图表
function initCharts() {
  console.log('开始初始化图表，数据长度:', indicesData.value.length);
  console.log('图表数据:', indicesData.value);

  // 初始化饼图
  if (pieChartRef.value) {
    console.log('初始化饼图，DOM元素:', pieChartRef.value);
    pieChart = echarts.init(pieChartRef.value);
    updatePieChart();

    // 监听窗口尺寸变化，带防抖，动态调整图例布局，避免与右侧面板遮挡
    const debounce = (fn, delay = 200) => {
      let timer = null;
      return (...args) => {
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
      };
    };

    const onResize = debounce(() => {
      if (!pieChart || pieChart.isDisposed()) return;
      pieChart.resize();
      updatePieChart();
    }, 150);

    window.addEventListener('resize', onResize);
    removeResizeListener = () => window.removeEventListener('resize', onResize);
  } else {
    console.log('饼图DOM元素不存在');
  }

}

// 更新饼图
function updatePieChart() {
  if (!pieChart) return;
  
  if (indicesData.value.length === 0) {
    const option = {
      title: {
        text: '暂无数据',
        left: 'center',
        top: 'center',
        textStyle: {
          color: '#999',
          fontSize: 16
        }
      },
      series: []
    };
    pieChart.setOption(option);
    return;
  }

  // 使用第一个指数的面积数据（通常是主要指数）
  const firstIndex = primaryIndex.value;
  if (!firstIndex) {
    pieChart.setOption({ series: [] });
    return;
  }
  
  console.log('饼图数据 - 第一个指数:', firstIndex);
  console.log('面积字段:', {
    excellent_area: firstIndex.excellent_area,
    good_area: firstIndex.good_area,
    moderate_area: firstIndex.moderate_area,
    poor_area: firstIndex.poor_area,
    bad_area: firstIndex.bad_area
  });

  const pieData = [
    { value: firstIndex.excellent_area || 0, name: '优秀', itemStyle: { color: '#67C23A' } },
    { value: firstIndex.good_area || 0, name: '良好', itemStyle: { color: '#95D475' } },
    { value: firstIndex.moderate_area || 0, name: '中等', itemStyle: { color: '#E6A23C' } },
    { value: firstIndex.poor_area || 0, name: '较差', itemStyle: { color: '#F56C6C' } },
    { value: firstIndex.bad_area || 0, name: '差', itemStyle: { color: '#C0392B' } }
  ].filter(item => item.value > 0);
  
  console.log('过滤后的饼图数据:', pieData);

  // 如果没有面积数据，显示提示信息
  if (pieData.length === 0) {
    const option = {
      title: {
        text: '暂无面积分布数据',
        left: 'center',
        top: 'center',
        textStyle: {
          color: '#999',
          fontSize: 16
        }
      },
      series: []
    };
    pieChart.setOption(option);
    return;
  }

  const chartWidth = pieChart.getWidth();
  const isWide = chartWidth >= 900; // 宽屏时图例在右侧，窄屏时放到底部

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} km² ({d}%)'
    },
    legend: isWide
      ? {
          orient: 'vertical',
          right: '6%',
          top: 'middle',
          textStyle: { fontSize: 14 }
        }
      : {
          type: 'scroll',
          orient: 'horizontal',
          bottom: 0,
          left: 'center',
          textStyle: { fontSize: 12 },
          pageIconColor: '#409EFF'
        },
    series: [
      {
        name: '面积分布',
        type: 'pie',
        radius: ['40%', '70%'],
        center: isWide ? ['40%', '50%'] : ['50%', '45%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          formatter: '{b}\n{d}%',
          fontSize: 12
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold'
          }
        },
        data: pieData
      }
    ]
  };

  pieChart.setOption(option);
  console.log('饼图配置已设置，数据项数:', pieData.length);
  
  // 检查图表是否正确渲染
  setTimeout(() => {
    if (pieChart && !pieChart.isDisposed()) {
      console.log('饼图渲染状态检查:', {
        isDisposed: pieChart.isDisposed(),
        width: pieChart.getWidth(),
        height: pieChart.getHeight(),
        containerVisible: pieChartRef.value?.offsetWidth > 0 && pieChartRef.value?.offsetHeight > 0
      });
      
      // 强制重新渲染
      pieChart.resize();
    }
  }, 100);
}


// 获取指数显示名称
function getIndexDisplayName(indexType) {
  return indexLabelMap.value[indexType] || indexType.toUpperCase();
}

// 获取平均值解读
function getMeanInterpretation(index) {
  const mean = index.mean_value || 0;
  const indexType = index.index_type;
  
  switch (indexType) {
    case 'dryness':
      if (mean < -5000) return '区域整体偏向湿润，植被覆盖良好，生态质量较高';
      else if (mean < 0) return '区域整体湿润，植被覆盖较好，生态质量中等偏上';
      else if (mean < 2000) return '区域干湿适中，植被与建筑用地并存';
      else return '区域整体偏向干燥，建筑用地较多，生态质量需要改善';
    
    case 'heat':
      if (mean < -5000) return '区域温度较低，植被覆盖良好，热岛效应不明显';
      else if (mean < 0) return '区域温度适中，植被覆盖较好，热环境良好';
      else if (mean < 2000) return '区域温度偏高，存在一定热岛效应';
      else return '区域温度较高，热岛效应明显，需要增加绿化';
    
    case 'ndvi':
      if (mean > 0.6) return '区域植被覆盖极好，生态质量优秀';
      else if (mean > 0.3) return '区域植被覆盖良好，生态质量较好';
      else if (mean > 0.1) return '区域植被覆盖一般，生态质量中等';
      else return '区域植被覆盖较差，生态质量需要改善';
    
    case 'ndwi':
      if (mean > 0.3) return '区域水体丰富，湿度较高，生态环境良好';
      else if (mean > 0.1) return '区域湿度适中，水体分布合理';
      else if (mean > -0.1) return '区域湿度一般，水体分布较少';
      else return '区域湿度较低，水体缺乏，需要增加水体';
    
    case 'wetness':
      if (mean > 1000) return '区域湿度很高，植被和水体丰富，生态质量优秀';
      else if (mean > 0) return '区域湿度较高，植被覆盖良好，生态质量较好';
      else if (mean > -1000) return '区域湿度适中，生态质量中等';
      else return '区域湿度较低，生态质量需要改善';
    
    default:
      return '数值分析需要结合具体指数类型进行解读';
  }
}

// 获取数值范围解读
function getRangeInterpretation(index) {
  const min = index.min_value || 0;
  const max = index.max_value || 0;
  const range = max - min;
  
  if (range > 30000) return '数值变化极大，区域内部差异显著，空间异质性很强';
  else if (range > 10000) return '数值变化较大，区域内部存在明显差异，空间异质性较强';
  else if (range > 5000) return '数值变化适中，区域内部有一定差异，空间异质性中等';
  else return '数值变化较小，区域内部相对均匀，空间异质性较弱';
}

// 获取变化程度解读
function getVariationInterpretation(index) {
  const std = index.std_value || 0;
  const min = index.min_value || 0;
  const max = index.max_value || 0;
  const range = max - min;
  
  // 基于标准差和数值范围的变化程度评估
  if (std > 10000) return '标准差极大，数据变化剧烈，空间分布极不均匀，存在显著的空间差异';
  else if (std > 5000) return '标准差较大，数据变化明显，空间分布不均匀，存在较大的空间差异';
  else if (std > 2000) return '标准差中等，数据变化适中，空间分布相对均匀，存在一定的空间差异';
  else if (std > 500) return '标准差较小，数据变化平缓，空间分布较为均匀，空间差异较小';
  else return '标准差很小，数据变化微弱，空间分布非常均匀，空间差异很小';
}

// 获取生态意义解读
function getEcologicalMeaning(index) {
  const indexType = index.index_type;
  const mean = index.mean_value || 0;
  
  switch (indexType) {
    case 'dryness':
      if (mean < -5000) return '建议加强植被保护，维持现有生态优势，可适当发展生态旅游';
      else if (mean < 0) return '建议适度增加绿化，平衡发展与生态保护，提升生态质量';
      else return '建议大力增加绿化覆盖，减少建筑密度，改善生态环境';
    
    case 'heat':
      if (mean < -5000) return '建议保持现有植被覆盖，避免过度开发，维持良好的热环境';
      else if (mean < 0) return '建议适度增加绿化，减少热岛效应，改善城市热环境';
      else return '建议增加绿化面积，建设生态廊道，缓解热岛效应';
    
    case 'ndvi':
      if (mean > 0.6) return '建议保护现有植被，建立生态保护区，维持生态优势';
      else if (mean > 0.3) return '建议适度增加植被覆盖，提升生态质量，建设生态城市';
      else return '建议大力植树造林，增加绿化面积，改善生态环境';
    
    case 'ndwi':
      if (mean > 0.3) return '建议保护现有水体，维持湿地生态，发展生态旅游';
      else if (mean > 0.1) return '建议适度增加水体面积，提升生态多样性';
      else return '建议建设人工水体，增加湿地面积，改善生态环境';
    
    case 'wetness':
      if (mean > 1000) return '建议保护现有湿地和植被，维持生态优势，发展生态产业';
      else if (mean > 0) return '建议适度增加湿地面积，提升生态质量';
      else return '建议增加水体面积，改善土壤湿度，提升生态质量';
    
    default:
      return '建议根据具体指数类型制定相应的生态保护和管理策略';
  }
}

// 获取指数等级
function getIndexLevel(value) {
  if (value >= 0.8) return '优秀';
  if (value >= 0.6) return '良好';
  if (value >= 0.4) return '中等';
  if (value >= 0.2) return '较差';
  return '差';
}

// 获取标签类型
function getIndexTagType(value) {
  if (value >= 0.8) return 'success';
  if (value >= 0.6) return 'info';
  if (value >= 0.4) return 'warning';
  return 'danger';
}

// 格式化数值
function formatValue(value) {
  if (value === null || value === undefined) return 'N/A';
  return typeof value === 'number' ? value.toFixed(4) : value;
}

function handleVisualizationError(event) {
  const failedUrl = event?.target?.currentSrc || event?.target?.src || primaryVisualizationUrl.value || '';
  console.error('可视化图片加载失败:', failedUrl);
  if (failedUrl && failedUrl.includes('/media/')) {
    visualizationLoadError.value = '结果图片文件已不存在，通常是旧缓存或后台结果文件已被清理。请重新分析，或删除这条历史记录后再生成。';
    return;
  }

  visualizationLoadError.value = failedUrl
    ? `图片地址无法访问：${failedUrl}`
    : '图片地址为空或服务未返回有效文件。';
}

// 下载结果
function downloadResults() {
  if (indicesData.value.length === 0) {
    ElMessage.warning('暂无数据可下载');
    return;
  }

  // 生成CSV数据
  const headers = ['指数类型', '平均值', '最小值', '最大值', '标准差', '优秀面积(km²)', '良好面积(km²)', '中等面积(km²)', '较差面积(km²)', '差面积(km²)'];
  const rows = indicesData.value.map(item => [
    getIndexDisplayName(item.index_type),
    formatValue(item.mean_value),
    formatValue(item.min_value),
    formatValue(item.max_value),
    formatValue(item.std_value),
    formatValue(item.excellent_area),
    formatValue(item.good_area),
    formatValue(item.moderate_area),
    formatValue(item.poor_area),
    formatValue(item.bad_area)
  ]);

  const csvContent = [headers, ...rows].map(row => row.join(',')).join('\n');
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);

  link.setAttribute('href', url);
  link.setAttribute('download', `遥感生态指数分析结果_${new Date().getTime()}.csv`);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  ElMessage.success('数据下载成功');
}

// 组件挂载时检查是否需要加载数据
onMounted(() => {
  if (props.status === 'done' && props.resultData) {
    loadIndicesData();
  }
});

// 卸载时清理监听
onUnmounted(() => {
  if (removeResizeListener) removeResizeListener();
  if (pieChart && !pieChart.isDisposed()) {
    pieChart.dispose();
  }
});
</script>

<style scoped>
.result-panel-apple {
  width: 100%;
  min-height: 400px;
  display: flex;
  flex-direction: column;
  background: transparent;
  padding: 0;
}

.placeholder-apple {
  align-self: center;
  margin: auto;
  padding: 28px 32px;
  border: 1px dashed #dbe6f0;
  border-radius: 12px;
  background: #ffffff;
  color: #8a98a8;
  font-size: 14px;
  box-shadow: 0 8px 20px rgba(30, 50, 70, 0.05);
  letter-spacing: 0.2px;
  text-align: center;
}

.loading-apple {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 80px 32px;
}

.loading-icon-apple {
  font-size: 48px;
  color: #5e9cff;
  animation: apple-spin 1.2s linear infinite;
}

@keyframes apple-spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text-apple {
  color: #2563eb;
  font-size: 1.15rem;
  font-weight: 500;
  letter-spacing: 0.2px;
}

.result-content-apple {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.result-notice {
  border-radius: 14px;
  padding: 14px 16px;
  border: 1px solid transparent;
}

.result-notice.is-preview {
  background: linear-gradient(180deg, #eef6ff 0%, #f9fbff 100%);
  border-color: #bfdcff;
}

.result-notice.is-hint {
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border-color: #d7e7f6;
}

.result-notice.is-warning {
  background: linear-gradient(180deg, #fff8ef 0%, #ffffff 100%);
  border-color: #f2d3aa;
}

.notice-title {
  margin-bottom: 6px;
  font-size: 14px;
  font-weight: 700;
  color: #21507e;
}

.notice-text {
  font-size: 13px;
  line-height: 1.6;
  color: #4c657d;
}

.result-header-apple {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 2px solid #e9eff5;
}

.result-title-apple {
  font-size: 1.5rem;
  font-weight: 600;
  color: #222;
  margin: 0;
  letter-spacing: 0.3px;
}

.download-btn-apple {
  border-radius: 12px;
  padding: 10px 20px;
  font-weight: 500;
}

.visualization-section {
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(229, 231, 235, 0.8);
  border-radius: 12px;
  padding: 16px;
}

.visualization-image {
  display: block;
  width: 100%;
  max-height: 520px;
  object-fit: contain;
  border-radius: 8px;
  background: #f8fafc;
}

.loading-data-apple {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  color: #606266;
  font-size: 1rem;
}

.loading-icon-small {
  font-size: 24px;
  color: #5e9cff;
  animation: apple-spin 1.2s linear infinite;
}

/* 统计卡片 */
.statistics-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.stat-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(60, 60, 60, 0.08);
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(60, 60, 60, 0.12);
}

.stat-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e9eff5;
}

.stat-card-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #303133;
}

.stat-card-body {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 0.85rem;
  color: #909399;
}

.stat-value {
  font-size: 1.1rem;
  font-weight: 600;
  color: #303133;
}

/* 图表区域 */
.charts-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 24px;
  margin-top: 8px;
}

.chart-container {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(60, 60, 60, 0.08);
}

.chart-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #303133;
  margin: 0 0 16px 0;
  text-align: center;
}

.chart-canvas {
  width: 100%;
  height: 350px;
}

/* 无数据提示 */
.no-data-apple {
  text-align: center;
  padding: 60px 32px;
  color: #909399;
}

.error-state-card {
  background: linear-gradient(180deg, #fff7f7 0%, #ffffff 100%);
  border: 1px solid #ffd4d4;
  border-radius: 18px;
  padding: 24px;
  box-shadow: 0 14px 30px rgba(216, 78, 78, 0.08);
}

.error-title {
  margin: 0 0 10px;
  font-size: 20px;
  color: #9f1f1f;
}

.error-message {
  margin: 0;
  font-size: 15px;
  color: #6f2c2c;
  font-weight: 600;
}

.error-details,
.error-supported,
.error-meta {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.6;
  color: #7a4a4a;
}

.no-data-apple p {
  margin: 8px 0;
  font-size: 1.1rem;
}

.hint-text {
  font-size: 0.95rem;
  color: #b0b8c9;
}

/* 数值解读样式 */
.interpretation-content {
  padding: 20px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
}

.interpretation-text {
  max-height: 400px;
  overflow-y: auto;
}

.index-interpretation {
  margin-bottom: 24px;
  padding: 16px;
  background: white;
  border-radius: 8px;
  border-left: 4px solid #1890ff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.index-interpretation:last-child {
  margin-bottom: 0;
}

.index-name {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1890ff;
  border-bottom: 1px solid #f0f0f0;
  padding-bottom: 8px;
}

.interpretation-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.interpretation-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  line-height: 1.6;
}

.item-label {
  font-weight: 600;
  color: #333;
  min-width: 80px;
  flex-shrink: 0;
}

.item-content {
  color: #666;
  flex: 1;
  text-align: justify;
}

.no-data-text {
  text-align: center;
  padding: 40px 20px;
  color: #999;
}

.no-data-text p {
  margin: 8px 0;
}

/* 响应式设计 */
@media (max-width: 900px) {
  .stats-cards {
    grid-template-columns: 1fr;
  }

  .charts-section {
    grid-template-columns: 1fr;
  }

  .chart-canvas {
    height: 300px;
  }
}
</style>
