import request from '@/utils/request'

export function loginApi(data){
    return request({
        url: '/api/auth/login',
        method: 'post',
        data
    })
}
export function registerApi(data) {
  return request({
    url: '/api/auth/register', // 👈 注意：这里需替换为你后端的真实注册接口地址
    method: 'post',
    data
  })
}