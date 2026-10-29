<template>
  <el-dialog
    v-model="visible"
    :title="title"
    width="500px"
    @close="handleClose"
  >
    <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
      <el-form-item label="预约对象">
        <span class="target-name">{{ targetName }}</span>
      </el-form-item>
      
      <el-form-item label="预约日期" prop="date">
        <el-date-picker
          v-model="form.date"
          type="date"
          placeholder="请选择日期"
          value-format="YYYY-MM-DD"
          style="width: 100%"
          :disabled-date="disabledDate"
        />
      </el-form-item>

      <el-form-item label="开始时间" prop="start_time">
        <el-time-picker
          v-model="form.start_time"
          placeholder="请选择开始时间"
          value-format="HH:mm"
          format="HH:mm"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item label="结束时间" prop="end_time">
        <el-time-picker
          v-model="form.end_time"
          placeholder="请选择结束时间"
          value-format="HH:mm"
          format="HH:mm"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item label="备注" prop="remark">
        <el-input
          v-model="form.remark"
          type="textarea"
          placeholder="请输入备注（选填）"
          :rows="3"
          maxlength="255"
          show-word-limit
        />
      </el-form-item>
    </el-form>
    
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="loading" @click="handleSubmit">
          确认预约
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { createReservationApi } from '@/api/reservation'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  labId: {
    type: [Number, String],
    required: true
  },
  equipmentId: {
    type: [Number, String],
    default: null
  },
  labName: {
    type: String,
    default: ''
  },
  equipmentName: {
    type: String,
    default: ''
  },
  // 日历页带入的预设时段
  presetDate: { type: String, default: '' },
  presetStart: { type: String, default: '' },
  presetEnd: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue', 'success'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const title = computed(() => {
  return props.equipmentId ? '预约设备' : '预约实验室'
})

const targetName = computed(() => {
  if (props.equipmentId) {
    return `${props.labName || '实验室'} - ${props.equipmentName || '设备'}`
  }
  return props.labName || '当前实验室'
})

const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  date: '',
  start_time: '',
  end_time: '',
  remark: ''
})

const rules = {
  date: [{ required: true, message: '请选择预约日期', trigger: 'change' }],
  start_time: [{ required: true, message: '请选择开始时间', trigger: 'change' }],
  end_time: [
    { required: true, message: '请选择结束时间', trigger: 'change' },
    {
      validator: (rule, value, callback) => {
        if (form.start_time && value <= form.start_time) {
          callback(new Error('结束时间必须大于开始时间'))
        } else {
          callback()
        }
      },
      trigger: 'change'
    }
  ]
}

// 禁用过去的日期
const disabledDate = (time) => {
  return time.getTime() < Date.now() - 8.64e7
}

// 重置表单
const resetForm = () => {
  form.date = ''
  form.start_time = ''
  form.end_time = ''
  form.remark = ''
  if (formRef.value) {
    formRef.value.clearValidate()
  }
}

// 监听弹窗打开，重置表单并应用日历带入的预设时段
watch(() => props.modelValue, (val) => {
  if (val) {
    resetForm()
    if (props.presetDate) form.date = props.presetDate
    if (props.presetStart) form.start_time = props.presetStart
    if (props.presetEnd) form.end_time = props.presetEnd
  }
})

const handleClose = () => {
  resetForm()
}

const handleSubmit = () => {
  formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const payload = {
          lab_id: Number(props.labId),
          equipment_id: props.equipmentId ? Number(props.equipmentId) : null,
          date: form.date,
          start_time: form.start_time,
          end_time: form.end_time,
          remark: form.remark
        }
        
        const res = await createReservationApi(payload)
        // 这里根据你的 response 拦截器判断，如果直接返回 data，可能不需要 res.code
        if (res.code === 200) {
          ElMessage.success('预约申请提交成功，请等待审核')
          visible.value = false
          emit('success')
        } else {
          ElMessage.error(res.message || '预约失败')
        }
      } catch (error) {
        console.error('预约请求异常:', error)
        ElMessage.error(error.response?.data?.message || error.message || '预约请求失败')
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.target-name {
  font-weight: bold;
  color: #409eff;
}
</style>