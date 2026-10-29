import request from '@/utils/request'
/**
 * 获取当前登录用户
 */
export function getlabInfo() {
  return request({
    url: '/api/lab/info',
    method: 'get'
  })
}

/**
 * 修改当前登录用户的个人信息
 */
export function updatelabInfo(data) {
  return request({
    url: '/api/lab/update',
    method: 'put',
    data
  })
}
/**
 * 修改密码
*/
export function updatePassword(data) {
  return request({
    url: '/api/lab/password',
    method: 'put',
    data
  })
}


// 获取用户列表
export function getlabList(params) {
  return request({
    url: '/api/lab/list', // 结合你之前的截图，完整路径应该是这个
    method: 'get',
    params // GET 请求必须使用 params，Axios 会将其拼接为 ?page=1&page_size=10&labname=xxx
  })
}

export function createlab(data) {
  return request({
    url: '/api/lab',
    method: 'post',
    data
  })
}

// 更新用户
export function updatelab(id, data) {
  return request({
    url: `/api/lab/${id}`,
    method: 'put',
    data
  })
}

// 删除用户
export function deletelab(id) {
  return request({
    url: `/api/lab/${id}`,
    method: 'delete'
  })
}

/**
 * 根据ID查询实验室详情
 * @param {Number} lab_id
 * @returns
 */
export function getLab(lab_id) {
  return request({
    url: `/api/lab/${lab_id}`,
    method: 'get'
  })
}