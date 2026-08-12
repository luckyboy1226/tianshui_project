<template>
  <div class="file-uploader">
    <input 
      type="file" 
      ref="fileInput" 
      @change="handleFileChange" 
      :accept="accept" 
      style="display: none;" 
    />
    
    <el-button 
      class="upload-btn" 
      type="primary"
      size="large"
      :loading="loading"
      @click="triggerUpload"
    >
      <el-icon v-if="!loading"><Upload /></el-icon>
      {{ loading ? '正在处理...' : buttonText }}
    </el-button>
    
    <div v-if="selectedFile" class="file-info">
      <el-icon><Document /></el-icon>
      <span>{{ selectedFile.name }}</span>
      <el-button 
        type="danger" 
        size="small" 
        circle 
        @click="clearFile"
      >
        <el-icon><Delete /></el-icon>
      </el-button>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, Document, Delete } from '@element-plus/icons-vue'

export default {
  name: 'FileUploader',
  props: {
    accept: {
      type: String,
      default: '*/*'
    },
    buttonText: {
      type: String,
      default: '上传文件'
    }
  },
  emits: ['file-selected', 'file-cleared'],
  setup(props, { emit }) {
    const fileInput = ref(null)
    const selectedFile = ref(null)
    const loading = ref(false)
    
    const triggerUpload = () => {
      console.log('触发文件上传')
      if (fileInput.value) {
        fileInput.value.click()
      }
    }
    
    const handleFileChange = (event) => {
      loading.value = true
      console.log('文件选择事件触发')
      
      try {
        const file = event.target.files[0]
        if (file) {
          console.log('选择的文件:', file.name)
          selectedFile.value = file
          emit('file-selected', file)
          ElMessage.success(`文件 ${file.name} 已选择`)
        }
      } catch (error) {
        console.error('文件处理错误:', error)
        ElMessage.error('文件处理失败')
      } finally {
        setTimeout(() => {
          loading.value = false
        }, 500)
      }
    }
    
    const clearFile = () => {
      selectedFile.value = null
      if (fileInput.value) {
        fileInput.value.value = ''
      }
      emit('file-cleared')
      ElMessage.info('文件已清除')
    }
    
    return {
      fileInput,
      selectedFile,
      loading,
      triggerUpload,
      handleFileChange,
      clearFile
    }
  }
}
</script>

<style scoped>
.file-uploader {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.upload-btn {
  width: 100%;
  height: 48px;
  background: #3b82f6 !important;
  border: none !important;
  color: white !important;
  font-weight: 600 !important;
  border-radius: 8px !important;
  transition: all 0.2s ease !important;
  position: relative !important;
  z-index: 100 !important;
  cursor: pointer !important;
  font-size: 16px !important;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important;
}

.upload-btn:hover {
  background: #2563eb !important;
  transform: translateY(-1px);
}

.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #e0f2fe;
  color: #0369a1;
  border: 1px dashed #0ea5e9;
  border-radius: 6px;
  font-size: 0.9rem;
}

.file-info span {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
