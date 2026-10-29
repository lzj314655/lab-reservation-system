<template>
  <div class="profile-container">
    <el-card class="profile-card" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>个人中心</span>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="90px"
        
      >
      <el-form-item label="头像">
        <div class="avatar-uploader">
            <el-upload
            class="avatar-uploader-box"
            :show-file-list="false"
            :before-upload="beforeAvatarUpload"
            :http-request="handleAvatarUpload"
            accept="image/*"
            >
            <img v-if="form.avatar" :src="fullAvatarUrl" class="avatar" />
            <el-icon v-else class="avatar-uploader-icon"><Plus /></el-icon>
            </el-upload>
            <div class="avatar-tip">支持 jpg / png / gif，不超过 2MB</div>
        </div>
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" disabled placeholder="用户名不可修改" />
        </el-form-item>

        <el-form-item label="昵称" prop="name">
          <el-input v-model="form.name" placeholder="请输入昵称" maxlength="20" show-word-limit />
        </el-form-item>

        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>

        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" placeholder="请输入手机号" maxlength="11" />
        </el-form-item>

        <el-form-item label="角色">
          <el-tag>{{ roleText }}</el-tag>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            保存修改
          </el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getUserInfo, updateUserInfo } from '@/api/user'
import { uploadFileApi } from '@/api/file'
// 拼完整地址：后端返回 /uploads/xxx，需要加上 base
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
const fullAvatarUrl = computed(() => {
  if (!form.avatar) return ''
  return form.avatar.startsWith('http')
    ? form.avatar
    : API_BASE + form.avatar
})

// 上传前校验
function beforeAvatarUpload(file) {
  const isImage = file.type.startsWith('image/')
  const isLt2M = file.size / 1024 / 1024 < 2
  if (!isImage) {
    ElMessage.error('只能上传图片文件')
    return false
  }
  if (!isLt2M) {
    ElMessage.error('图片大小不能超过 2MB')
    return false
  }
  return true
}

// 自定义上传：拿到 url 后立即保存到用户信息
async function handleAvatarUpload({ file }) {
  try {
    const res = await uploadFileApi(file)
    // 你的响应结构：{ code, message, data: { url, ... } }
    const data = res?.data ?? res
    const url = data.url

    // 调 update 接口保存 avatar
    await updateUserInfo({ avatar: url })

    // 更新本地
    form.avatar = url
    originalData.avatar = url

    ElMessage.success('头像更新成功')
    window.dispatchEvent(new Event('user-info-updated'))
  } catch (err) {
    ElMessage.error(err?.message || '头像上传失败')
  }
}
const formRef = ref(null)
const loading = ref(false)
const submitting = ref(false)

// 与后端 User 模型字段保持一致
const form = reactive({
  username: '',
  name: '',
  email: '',
  phone: '',
  role: '',
  avatar: '' 
})

let originalData = {}

const roleMap = { student: '学生', teacher: '教师', admin: '管理员' }
const roleText = computed(() => roleMap[form.role] || form.role || '-')

const rules = {
  name: [
    { required: true, message: '昵称不能为空', trigger: 'blur' },
    { min: 1, max: 20, message: '长度在 1 到 20 个字符', trigger: 'blur' }
  ],
  email: [
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }
  ]
}

// 获取用户信息
async function fetchUserInfo() {
  loading.value = true
  try {
    const res = await getUserInfo()
    // 后端返回：{ code, message, data }
    // 如果 axios 拦截器已经返回 res.data（也就是整个响应体），这里取 res.data
    // 如果拦截器返回的是 data 字段本身，就直接用 res
    const data = res?.data ?? res

    Object.assign(form, {
      username: data.username ?? '',
      name: data.name ?? '',
      email: data.email ?? '',
      phone: data.phone ?? '',
      role: data.role ?? '',
      avatar: data.avatar ?? ''
    })
    originalData = { ...form }
  } catch (err) {
    ElMessage.error(err?.message || '获取用户信息失败')
  } finally {
    loading.value = false
  }
}

// 提交修改（只提交变化且非只读字段）
async function handleSubmit() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  const changed = {}
  // 只提交允许修改的字段
  const editableFields = ['name', 'email', 'phone']
  editableFields.forEach((key) => {
    if (form[key] !== originalData[key]) {
      changed[key] = form[key]
    }
  })

  if (Object.keys(changed).length === 0) {
    ElMessage.info('没有需要修改的内容')
    return
  }

  submitting.value = true
  try {
    await updateUserInfo(changed)
    ElMessage.success('修改成功')
    Object.assign(originalData, changed)
  } catch (err) {
    ElMessage.error(err?.message || '修改失败')
  } finally {
    submitting.value = false
  }
}

// 重置
function handleReset() {
  Object.assign(form, originalData)
  formRef.value?.clearValidate()
}

onMounted(fetchUserInfo)
</script>

<style scoped>
.profile-container {
  display: flex;
  justify-content: center;
  padding: 24px;
}
.profile-card {
  width: 100%;
  max-width: 560px;
}
.card-header {
  font-size: 16px;
  font-weight: 600;
}
.avatar-uploader-box {
  width: 100px;
  height: 100px;
  border: 1px dashed #d9d9d9;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  transition: border-color 0.2s;
}
.avatar-uploader-box:hover {
  border-color: #409eff;
}
.avatar {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.avatar-uploader-icon {
  font-size: 24px;
  color: #8c939d;
}
.avatar-tip {
  font-size: 12px;
  color: #999;
  margin-top: 6px;
}
</style>