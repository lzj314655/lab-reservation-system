<template>
  <div class="lab-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>实验室管理</h2>
    </div>

    <el-card class="box-card" shadow="never">
      <!-- 搜索栏 -->
      <el-form :inline="true" :model="queryParams" class="search-bar">
        <el-form-item>
          <el-input
            v-model="queryParams.keywords"
            placeholder="请输入名称查询"
            clearable
            style="width: 200px;"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>查询
          </el-button>
          <el-button type="success" @click="handleAdd">
            <el-icon><Plus /></el-icon>新增
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 表格区域 -->
      <el-table :data="tableData" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="名称" min-width="120" />
        
        <el-table-column prop="description" label="简介" min-width="150" show-overflow-tooltip>
          <template #default="scope">{{ scope.row.description || '-' }}</template>
        </el-table-column>

        <el-table-column label="封面" width="120" align="center">
          <template #default="scope">
            <el-image 
              v-if="scope.row.img" 
              :src="getImgUrl(scope.row.img)" 
              :preview-src-list="[getImgUrl(scope.row.img)]"
              fit="cover"
              style="width: 60px; height: 60px; border-radius: 4px; border: 1px solid #ebeef5;"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column prop="location" label="位置" min-width="120">
          <template #default="scope">{{ scope.row.location || '-' }}</template>
        </el-table-column>

        <el-table-column prop="capacity" label="容量" width="100" align="center">
          <template #default="scope">{{ scope.row.capacity }} 人</template>
        </el-table-column>

        <el-table-column label="开放时间" width="180" align="center">
          <template #default="scope">
            <span v-if="scope.row.open_time || scope.row.close_time">
              {{ scope.row.open_time || '--:--' }} - {{ scope.row.close_time || '--:--' }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="scope">
            <el-tag 
              effect="light" 
              :type="scope.row.status === 1 ? 'success' : 'info'"
            >
              {{ scope.row.status === 1 ? '开启' : '关闭' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="150" align="center">
          <template #default="scope">
            <el-button type="primary" link @click="handleEdit(scope.row)">编辑</el-button>
            <el-popconfirm title="确定要删除该实验室吗？" @confirm="handleDelete(scope.row.id)">
              <template #reference>
                <el-button type="danger" link>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页组件 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.page_size"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 新增/编辑 弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑实验室' : '新增实验室'"
      width="550px"
      @close="resetForm"
    >
      <el-form ref="formRef" :model="formData" :rules="rules" label-width="100px">
        <el-form-item label="实验室名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入实验室名称" />
        </el-form-item>

        <el-form-item label="位置" prop="location">
          <el-input v-model="formData.location" placeholder="请输入位置 (如: 实验楼A101)" />
        </el-form-item>

        <el-form-item label="容量" prop="capacity">
          <el-input-number v-model="formData.capacity" :min="0" :max="9999" placeholder="请输入容量" style="width: 100%" />
        </el-form-item>

        <el-form-item label="开放时间">
          <div style="display: flex; align-items: center; gap: 10px; width: 100%;">
            <el-time-select
              v-model="formData.open_time"
              start="00:00"
              step="00:30"
              end="23:30"
              placeholder="开始时间"
              style="flex: 1"
            />
            <span>至</span>
            <el-time-select
              v-model="formData.close_time"
              start="00:00"
              step="00:30"
              end="23:30"
              placeholder="结束时间"
              style="flex: 1"
            />
          </div>
        </el-form-item>

        <el-form-item label="封面图片" prop="img">
          <el-upload
            class="avatar-uploader"
            :show-file-list="false"
            :http-request="handleUpload"
            :before-upload="beforeUpload"
            accept="image/*"
          >
            <img v-if="formData.img" :src="getImgUrl(formData.img)" class="avatar" />
            <el-icon v-else class="avatar-uploader-icon"><Plus /></el-icon>
          </el-upload>
          <div class="upload-tip">支持 jpg、png 格式，大小不超过 2MB</div>
        </el-form-item>

        <el-form-item label="简介" prop="description">
          <el-input 
            v-model="formData.description" 
            type="textarea" 
            :rows="3" 
            placeholder="请输入实验室简介" 
          />
        </el-form-item>

        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="formData.status">
            <el-radio :label="1">开放</el-radio>
            <el-radio :label="0">关闭</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取 消</el-button>
          <el-button type="primary" :loading="submitLoading" @click="submitForm">确 定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import { uploadFileApi } from '@/api/file'

// 引入你的 API
import { getlabList, createlab, updatelab, deletelab } from '@/api/lab'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

// 列表相关状态
const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const queryParams = reactive({
  page: 1,
  page_size: 10,
  keywords: ''
})

// 弹窗相关状态
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref(null)
const currentEditId = ref(null)

// 表单数据
const formData = reactive({
  name: '',
  description: '',
  img: '',
  location: '',
  capacity: 0,
  open_time: '',
  close_time: '',
  status: 1
})

// 表单校验规则
const rules = {
  name: [{ required: true, message: '请输入实验室名称', trigger: 'blur' }],
  capacity: [{ required: true, message: '请输入容量', trigger: 'blur' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }]
}

// 拼接图片路径
const getImgUrl = (imgPath) => {
  if (!imgPath) return ''
  return imgPath.startsWith('http') ? imgPath : `${BASE_URL}${imgPath}`
}

// ================= 图片上传逻辑 =================

// 上传前的校验
const beforeUpload = (file) => {
  const isImage = file.type.startsWith('image/')
  const isLt2M = file.size / 1024 / 1024 < 2

  if (!isImage) {
    ElMessage.error('只能上传图片文件!')
    return false
  }
  if (!isLt2M) {
    ElMessage.error('图片大小不能超过 2MB!')
    return false
  }
  return true
}

// 自定义上传逻辑
const handleUpload = async (options) => {
  try {
    const res = await uploadFileApi(options.file)
    if (res.code === 200) {
      const url = typeof res.data === 'string' ? res.data : res.data.url
      formData.img = url
      ElMessage.success('图片上传成功')
    } else {
      ElMessage.error(res.message || '图片上传失败')
    }
  } catch (error) {
    console.error('上传异常:', error)
    ElMessage.error('图片上传异常，请重试')
  }
}

// ===============================================

// 获取列表
const fetchList = async () => {
  loading.value = true
  try {
    const params = { ...queryParams }
    if (!params.keywords) delete params.keywords

    const res = await getlabList(params)
    if (res.code === 200) {
      tableData.value = res.data.list || []
      total.value = res.data.total || 0
    }
  } catch (error) {
    console.error('请求异常', error)
  } finally {
    loading.value = false
  }
}

// 搜索与分页
const handleSearch = () => { queryParams.page = 1; fetchList() }
const resetSearch = () => { queryParams.keywords = ''; handleSearch() }
const handleSizeChange = (val) => { queryParams.page_size = val; queryParams.page = 1; fetchList() }
const handleCurrentChange = (val) => { queryParams.page = val; fetchList() }

// ================= 增删改逻辑 =================

// 重置表单
const resetForm = () => {
  if (formRef.value) formRef.value.resetFields()
  formData.name = ''
  formData.description = ''
  formData.img = ''
  formData.location = ''
  formData.capacity = 0
  formData.open_time = ''
  formData.close_time = ''
  formData.status = 1
  currentEditId.value = null
}

// 点击新增
const handleAdd = () => {
  isEdit.value = false
  resetForm()
  dialogVisible.value = true
}

// 点击编辑
const handleEdit = (row) => {
  isEdit.value = true
  resetForm()
  currentEditId.value = row.id
  formData.name = row.name
  formData.description = row.description || ''
  formData.img = row.img || ''
  formData.location = row.location || ''
  formData.capacity = row.capacity || 0
  formData.open_time = row.open_time || ''
  formData.close_time = row.close_time || ''
  formData.status = row.status
  dialogVisible.value = true
}

// 提交表单（新增或编辑）
const submitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitLoading.value = true
    try {
      let res
      if (isEdit.value) {
        res = await updatelab(currentEditId.value, formData)
      } else {
        res = await createlab(formData)
      }

      if (res.code === 200) {
        ElMessage.success(isEdit.value ? '更新成功' : '新增成功')
        dialogVisible.value = false
        fetchList()
      } else {
        ElMessage.error(res.message || '操作失败')
      }
    } catch (error) {
      console.error('提交异常', error)
    } finally {
      submitLoading.value = false
    }
  })
}

// 删除实验室
const handleDelete = async (id) => {
  try {
    const res = await deletelab(id)
    if (res.code === 200) {
      ElMessage.success('删除成功')
      if (tableData.value.length === 1 && queryParams.page > 1) {
        queryParams.page--
      }
      fetchList()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (error) {
    console.error('删除异常', error)
  }
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
/* 页面整体背景与留白 */
.lab-container { padding: 2px 2px 12px; }

/* 页面标题样式 */
.page-header {
  margin-bottom: 20px;
}
.page-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
  font-weight: 600;
}

/* 卡片样式 */
.box-card { 
  border-radius: 8px; 
}
.box-card :deep(.el-card__body) {
  padding: 20px;
}

/* 搜索栏样式 */
.search-bar {
  margin-bottom: 20px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.search-bar .el-form-item {
  margin-bottom: 0;
}

/* 表格表头背景色调整 */
:deep(.el-table th.el-table__cell) {
  background-color: #f8f9fa;
  color: #606266;
  font-weight: 500;
}

/* 分页容器 */
.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

/* 上传组件样式美化 */
.avatar-uploader {
  border: 1px dashed #d9d9d9;
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: all 0.3s;
  width: 120px;
  height: 120px;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #fafafa;
}
.avatar-uploader:hover {
  border-color: #409eff;
}
.avatar-uploader-icon {
  font-size: 28px;
  color: #8c939d;
  width: 120px;
  height: 120px;
  text-align: center;
  line-height: 120px;
}
.avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.upload-tip {
  font-size: 12px;
  color: #999;
  margin-top: 5px;
  line-height: 1.5;
}
</style>