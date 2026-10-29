<template>
  <div class="notfound-container">
    <div class="notfound-card fade-up">
      <div class="code font-num">404</div>
      <div class="title">页面不存在</div>
      <div class="desc">你访问的页面可能已被移除、改名或暂时不可用</div>
      <div class="actions">
        <el-button @click="$router.push('/manager/home')">返回首页</el-button>
        <el-button type="primary" @click="$router.back()">返回上一页</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
</script>

<style scoped>
.notfound-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(900px 500px at 80% -10%, rgba(14, 116, 144, 0.35), transparent 55%),
    linear-gradient(160deg, #0b1a26 0%, #0c2736 100%);
  padding: 24px;
}

.notfound-card {
  text-align: center;
  color: #e8f1f5;
}

.code {
  font-size: 120px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: 0.04em;
  background: linear-gradient(135deg, #5ecbe5, #0e7490 60%, #f59e0b);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  margin-bottom: 12px;
}

.title {
  font-size: 24px;
  font-weight: 800;
  margin-bottom: 10px;
}

.desc {
  font-size: 14px;
  color: rgba(157, 178, 194, 0.9);
  margin-bottom: 30px;
}

.actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}
</style>
