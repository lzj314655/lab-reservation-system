import request from '@/utils/request'
/**
 * 获取当前登录用户
 */
export function getlequipmentInfo() {
  return request({
    url: '/api/equipment/info',
    method: 'get'
  })
}

/**
 * 修改当前登录用户的个人信息
 */
export function updateequipmentInfo(data) {
  return request({
    url: '/api/equipment/update',
    method: 'put',
    data
  })
}
/**
 * 修改密码
*/
export function updatePassword(data) {
  return request({
    url: '/api/equipment/password',
    method: 'put',
    data
  })
}


// 获取用户列表
export function getequipmentList(params) {
  return request({
    url: '/api/equipment/list', // 结合你之前的截图，完整路径应该是这个
    method: 'get',
    params // GET 请求必须使用 params，Axios 会将其拼接为 ?page=1&page_size=10&equipmentname=xxx
  })
}

export function createequipment(data) {
  return request({
    url: '/api/equipment',
    method: 'post',
    data
  })
}

// 更新用户
export function updateequipment(id, data) {
  return request({
    url: `/api/equipment/${id}`,
    method: 'put',
    data
  })
}

// 删除用户
export function deleteequipment(id) {
  return request({
    url: `/api/equipment/${id}`,
    method: 'delete'
  })
}