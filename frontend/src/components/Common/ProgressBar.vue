<template>
  <div class="progress-bar-container" :class="{ 'progress-compact': compact }">
    <!-- 进度条标题 -->
    <div v-if="title" class="progress-header">
      <span class="progress-title">{{ title }}</span>
      <span v-if="showPercentage" class="progress-percentage">{{ Math.round(percentage) }}%</span>
    </div>
    
    <!-- 进度条 -->
    <div class="progress-bar" :class="[`progress-${type}`, { 'progress-animated': animated }]">
      <div 
        class="progress-fill" 
        :style="{ 
          width: `${percentage}%`,
          backgroundColor: customColor || getDefaultColor(percentage)
        }"
        :data-progress="percentage"
      ></div>
      
      <!-- 调试信息 -->
      <!-- <div style="position: absolute; top: -20px; left: 0; font-size: 10px; color: red;">
        调试: {{ percentage }}% (内部值: {{ internalValue }})
      </div> -->
      
      <!-- 进度条标签 -->
      <div v-if="showLabel" class="progress-label">
        <span v-if="label" class="label-text">{{ label }}</span>
        <span v-if="showPercentage" class="label-percentage">{{ Math.round(percentage) }}%</span>
      </div>
    </div>
    
    <!-- 进度信息 -->
    <div v-if="showInfo" class="progress-info">
      <div v-if="current" class="info-item">
        <span class="info-label">当前:</span>
        <span class="info-value">{{ current }}</span>
      </div>
      <div v-if="total" class="info-item">
        <span class="info-label">总计:</span>
        <span class="info-value">{{ total }}</span>
      </div>
      <div v-if="speed" class="info-item">
        <span class="info-label">速度:</span>
        <span class="info-value">{{ speed }}</span>
      </div>
      <div v-if="eta" class="info-item">
        <span class="info-label">预计剩余:</span>
        <span class="info-value">{{ eta }}</span>
      </div>
    </div>
    
    <!-- 操作按钮 -->
    <div v-if="showActions" class="progress-actions">
      <el-button 
        v-if="canPause" 
        size="small" 
        @click="togglePause"
        :type="isPaused ? 'success' : 'warning'"
      >
        <i :class="isPaused ? 'el-icon-video-play' : 'el-icon-video-pause'"></i>
        {{ isPaused ? '继续' : '暂停' }}
      </el-button>
      
      <el-button 
        v-if="canCancel" 
        size="small" 
        type="danger" 
        @click="cancel"
      >
        <i class="el-icon-close"></i>
        取消
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  // 进度值 (0-100)
  value: {
    type: Number,
    default: 0
  },
  // 进度条标题
  title: {
    type: String,
    default: ''
  },
  // 进度条类型
  type: {
    type: String,
    default: 'primary', // primary, success, warning, danger, info
    validator: (value) => ['primary', 'success', 'warning', 'danger', 'info'].includes(value)
  },
  // 是否显示百分比
  showPercentage: {
    type: Boolean,
    default: true
  },
  // 是否显示标签
  showLabel: {
    type: Boolean,
    default: false
  },
  // 标签文本
  label: {
    type: String,
    default: ''
  },
  // 是否显示详细信息
  showInfo: {
    type: Boolean,
    default: false
  },
  // 当前值
  current: {
    type: [String, Number],
    default: ''
  },
  // 总值
  total: {
    type: [String, Number],
    default: ''
  },
  // 速度
  speed: {
    type: String,
    default: ''
  },
  // 预计剩余时间
  eta: {
    type: String,
    default: ''
  },
  // 是否显示操作按钮
  showActions: {
    type: Boolean,
    default: false
  },
  // 是否可以暂停
  canPause: {
    type: Boolean,
    default: false
  },
  // 是否可以取消
  canCancel: {
    type: Boolean,
    default: false
  },
  // 是否紧凑模式
  compact: {
    type: Boolean,
    default: false
  },
  // 是否动画
  animated: {
    type: Boolean,
    default: true
  },
  // 自定义颜色
  customColor: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['pause', 'resume', 'cancel', 'update:value'])

// 内部状态
const isPaused = ref(false)
const internalValue = ref(props.value)

// 计算百分比
const percentage = computed(() => {
  const value = Math.max(0, Math.min(100, internalValue.value))
  // console.log(`ProgressBar - 内部值: ${internalValue.value}, 计算百分比: ${value}%`)
  return value
})

// 监听外部值变化
watch(() => props.value, (newValue) => {
  internalValue.value = newValue
}, { immediate: true })

// 获取默认颜色
function getDefaultColor(percent) {
  if (percent < 30) return '#67c23a' // 绿色
  if (percent < 70) return '#e6a23c' // 橙色
  return '#f56c6c' // 红色
}

// 切换暂停状态
function togglePause() {
  isPaused.value = !isPaused.value
  if (isPaused.value) {
    emit('pause')
  } else {
    emit('resume')
  }
}

// 取消操作
function cancel() {
  emit('cancel')
}

// 更新进度值
function updateProgress(value) {
  internalValue.value = value
  emit('update:value', value)
}

// 暴露方法给父组件
defineExpose({
  updateProgress,
  setPaused: (paused) => { isPaused.value = paused },
  reset: () => { internalValue.value = 0 }
})
</script>

<style scoped>
.progress-bar-container {
  width: 100%;
  margin: 16px 0;
}

.progress-compact {
  margin: 8px 0;
}

/* 进度条标题 */
.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.progress-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.progress-percentage {
  font-size: 12px;
  color: #909399;
  font-weight: 500;
}

/* 进度条 */
.progress-bar {
  position: relative;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
  border: 1px solid #ddd; /* 添加边框以便调试 */
}

.progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease, background-color 0.3s ease;
  position: relative;
  min-width: 0%; /* 确保最小宽度为0 */
  max-width: 100%; /* 确保最大宽度不超过100% */
  background-color: #409eff !important; /* 强制显示颜色 */
}

/* 进度条类型样式 */
.progress-primary .progress-fill {
  background: linear-gradient(90deg, #409eff, #67c23a);
}

.progress-success .progress-fill {
  background: linear-gradient(90deg, #67c23a, #85ce61);
}

.progress-warning .progress-fill {
  background: linear-gradient(90deg, #e6a23c, #ebb563);
}

.progress-danger .progress-fill {
  background: linear-gradient(90deg, #f56c6c, #f78989);
}

.progress-info .progress-fill {
  background: linear-gradient(90deg, #909399, #c0c4cc);
}

/* 动画效果 */
.progress-animated .progress-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.3),
    transparent
  );
  animation: progress-shine 2s infinite;
}

@keyframes progress-shine {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

/* 进度条标签 */
.progress-label {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #606266;
  font-weight: 500;
}

.label-text {
  white-space: nowrap;
}

.label-percentage {
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 10px;
}

/* 进度信息 */
.progress-info {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 12px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.info-label {
  font-size: 12px;
  color: #909399;
}

.info-value {
  font-size: 12px;
  color: #606266;
  font-weight: 500;
}

/* 操作按钮 */
.progress-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .progress-info {
    flex-direction: column;
    gap: 8px;
  }
  
  .progress-actions {
    justify-content: center;
  }
  
  .progress-actions .el-button {
    flex: 1;
    max-width: 120px;
  }
}

/* 紧凑模式 */
.progress-compact .progress-bar {
  height: 6px;
}

.progress-compact .progress-header {
  margin-bottom: 4px;
}

.progress-compact .progress-info {
  margin-bottom: 8px;
}

.progress-compact .progress-actions {
  margin-top: 4px;
}
</style>
