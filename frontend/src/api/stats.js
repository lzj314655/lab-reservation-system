import request from '@/utils/request'

// 首页统计卡数据（管理员/学生返回不同字段）
export function getStatsOverview() {
  return request({ url: '/api/stats/overview', method: 'get' })
}

// 近 N 天预约趋势
export function getStatsTrend(days = 30) {
  return request({ url: '/api/stats/trend', method: 'get', params: { days } })
}

// 实验室预约量排行（管理员）
export function getLabUsage(limit = 8) {
  return request({ url: '/api/stats/lab-usage', method: 'get', params: { limit } })
}

// 我的预约状态分布（学生）
export function getMyReservationStatus() {
  return request({ url: '/api/stats/my-status', method: 'get' })
}
