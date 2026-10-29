<template>
  <div class="password-container">
    <el-card class="password-card">
      <template #header>
        <div class="card-header">
          <span>修改密码</span>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
        status-icon
      >
        <el-form-item label="原密码" prop="old_password">
          <el-input
            v-model="form.old_password"
            type="password"
            placeholder="请输入原密码"
            show-password
            clearable
          />
        </el-form-item>

        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="form.new_password"
            type="password"
            placeholder="请输入新密码"
            show-password
            clearable
          />
        </el-form-item>

        <el-form-item label="确认新密码" prop="confirm_password">
          <el-input
            v-model="form.confirm_password"
            type="password"
            placeholder="请再次输入新密码"
            show-password
            clearable
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSubmit">
            确认修改
          </el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { updatePassword } from '@/api/user'
import { logout } from '@/utils/auth'

const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

// 自定义校验：新密码
const validateNewPassword = (rule, value, callback) => {
  if (!value) {
    return callback(new Error('请输入新密码'))
  }
  if (value.length < 6 || value.length > 20) {
    return callback(new Error('密码长度需在 6 到 20 位之间'))
  }
  if (value === form.old_password) {
    return callback(new Error('新密码不能与原密码相同'))
  }
  if (form.confirm_password) {
    formRef.value.validateField('confirm_password')
  }
  callback()
}

// 自定义校验：确认密码
const validateConfirmPassword = (rule, value, callback) => {
  if (!value) {
    return callback(new Error('请再次输入新密码'))
  }
  if (value !== form.new_password) {
    return callback(new Error('两次输入的密码不一致'))
  }
  callback()
}

const rules = {
  old_password: [
    { required: true, message: '请输入原密码', trigger: 'blur' }
  ],
  new_password: [
    { required: true, validator: validateNewPassword, trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
  } catch (e) {
    return
  }

  loading.value = true
  try {
    await updatePassword({
      old_password: form.old_password,
      new_password: form.new_password
    })

    ElMessage.success('密码修改成功，请重新登录')

    setTimeout(() => {
      logout()
      window.location.href = '/login'
    }, 1000)
  } catch (err) {
    const msg = err?.response?.data?.message || err?.message || '修改失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

const handleReset = () => {
  formRef.value?.resetFields()
}
</script>

<style scoped>
.password-container {
  display: flex;
  justify-content: center;
  padding: 40px 20px;
}

.password-card {
  width: 100%;
  max-width: 500px;
}

.card-header {
  font-size: 16px;
  font-weight: 600;
}
</style>