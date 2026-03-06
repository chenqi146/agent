import request from './request'
import routesConfig from '@/router/routes.json'
import { appTag } from './constants'

const apiRoutes = routesConfig.api.auth

export const authApi = {
  /**
   * User login
   * @param {Object} credentials - { username, password }
   * @returns {Promise} - { token, user }
   */
  login(credentials) {
       /**调试，先登录成功**/
      return request.post(apiRoutes.login, {
         tag: appTag,
         timestamp: Date.now(),
         data: {
          username: credentials.username,
          password: credentials.password,
          captcha: credentials.captcha,
          captchaId: credentials.captchaId
        }
      })
  },

  /**
   * User logout
   * @param {string} token - 用户token
   * @returns {Promise}
   */
  logout(token) {
    return request.post(apiRoutes.logout, {
        tag: appTag,
        timestamp: Date.now(),
        data:{
            token: token
        }
    })
  },
  /**
   * Get current user info
   * @returns {Promise} - { user }
   */
  getCurrentUser() {
    return request.get(apiRoutes.me)
  },

  /**
   * Refresh token
   * @returns {Promise} - { token }
   */
  refreshToken() {
    return request.post(apiRoutes.refresh)
  },

  /**
   * Get captcha image
   * @returns {Promise} - { image, captchaId }
   */
  getCaptcha() {
    return request.post(apiRoutes.captcha,{
      tag: appTag,
      timestamp: Date.now(),
      data: {
      }
    })
  }
}
