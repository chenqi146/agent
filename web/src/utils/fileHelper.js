/**
 * 文件处理工具类
 * 用于文件读取、校验和信息提取
 */

// 文件大小限制配置
export const FILE_SIZE_LIMITS = {
  DEFAULT: 10 * 1024 * 1024, // 10MB
  TEXT: 1 * 1024 * 1024,    // 1MB
  PDF: 50 * 1024 * 1024,     // 50MB
  WORD: 20 * 1024 * 1024,    // 20MB
  EXCEL: 20 * 1024 * 1024,   // 20MB
  IMAGE: 5 * 1024 * 1024      // 5MB
}

// 支持的文件类型
export const SUPPORTED_FILE_TYPES = {
  TEXT: ['text/plain', 'text/csv'],
  PDF: ['application/pdf'],
  WORD: [
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
  ],
  EXCEL: [
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  ],
  IMAGE: [
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp'
  ]
}

/**
 * 获取文件类型分类
 * @param {File} file - 文件对象
 * @returns {string} - 文件类型分类
 */
export function getFileTypeCategory(file) {
  const mimeType = file.type.toLowerCase()

  if (SUPPORTED_FILE_TYPES.TEXT.includes(mimeType)) return 'text'
  if (SUPPORTED_FILE_TYPES.PDF.includes(mimeType)) return 'pdf'
  if (SUPPORTED_FILE_TYPES.WORD.includes(mimeType)) return 'word'
  if (SUPPORTED_FILE_TYPES.EXCEL.includes(mimeType)) return 'excel'
  if (SUPPORTED_FILE_TYPES.IMAGE.includes(mimeType)) return 'image'

  return 'other'
}

/**
 * 校验文件大小
 * @param {File} file - 文件对象
 * @param {number} maxSize - 最大文件大小（字节）
 * @returns {Object} - 校验结果 { valid: boolean, message?: string }
 */
export function validateFileSize(file, maxSize = FILE_SIZE_LIMITS.DEFAULT) {
  if (!file) {
    return { valid: false, message: '文件不存在' }
  }

  if (file.size > maxSize) {
    const sizeMB = (maxSize / (1024 * 1024)).toFixed(2)
    return { 
      valid: false, 
      message: `文件大小超过限制，最大允许 ${sizeMB}MB` 
    }
  }

  return { valid: true }
}

/**
 * 校验文件类型
 * @param {File} file - 文件对象
 * @returns {Object} - 校验结果 { valid: boolean, message?: string }
 */
export function validateFileType(file) {
  if (!file) {
    return { valid: false, message: '文件不存在' }
  }

  const category = getFileTypeCategory(file)
  if (category === 'other') {
    return { 
      valid: false, 
      message: '不支持的文件类型' 
    }
  }

  return { valid: true }
}

/**
 * 读取文本文件内容
 * @param {File} file - 文件对象
 * @returns {Promise<string>} - 文件内容
 */
export function readTextFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()

    reader.onload = (e) => {
      resolve(e.target.result)
    }

    reader.onerror = (e) => {
      reject(new Error('文件读取失败'))
    }

    reader.readAsText(file)
  })
}

/**
 * 读取文件为ArrayBuffer
 * @param {File} file - 文件对象
 * @returns {Promise<ArrayBuffer>} - 文件内容
 */
export function readFileAsArrayBuffer(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()

    reader.onload = (e) => {
      resolve(e.target.result)
    }

    reader.onerror = (e) => {
      reject(new Error('文件读取失败'))
    }

    reader.readAsArrayBuffer(file)
  })
}

/**
 * 获取文件的字符数
 * @param {File} file - 文件对象
 * @returns {Promise<number>} - 字符数
 */
export async function getFileCharCount(file) {
  try {
    const content = await readTextFile(file)
    return content.length
  } catch (error) {
    console.error('获取文件字符数失败:', error)
    return 0
  }
}

/**
 * 格式化文件大小
 * @param {number} bytes - 文件大小（字节）
 * @returns {string} - 格式化后的文件大小
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'

  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * 获取文件信息
 * @param {File} file - 文件对象
 * @returns {Promise<Object>} - 文件信息对象
 */
export async function getFileInfo(file) {
  const fileType = getFileTypeCategory(file)
  const charCount = fileType === 'text' ? await getFileCharCount(file) : 0

  return {
    name: file.name,
    size: file.size,
    type: file.type,
    fileType: fileType,
    charCount: charCount,
    lastModified: new Date(file.lastModified),
    formattedSize: formatFileSize(file.size)
  }
}

/**
 * 批量校验文件
 * @param {File[]} files - 文件数组
 * @param {Object} options - 配置选项
 * @returns {Object} - 校验结果 { valid: boolean, validFiles: File[], invalidFiles: Array<{file: File, message: string}> }
 */
export async function validateFiles(files, options = {}) {
  const {
    maxSize = FILE_SIZE_LIMITS.DEFAULT,
    allowMultipleTypes = true,
    allowedTypes = null
  } = options

  const validFiles = []
  const invalidFiles = []

  for (const file of files) {
    // 校验文件大小
    const sizeValidation = validateFileSize(file, maxSize)
    if (!sizeValidation.valid) {
      invalidFiles.push({ file, message: sizeValidation.message })
      continue
    }

    // 校验文件类型
    const typeValidation = validateFileType(file)
    if (!typeValidation.valid) {
      invalidFiles.push({ file, message: typeValidation.message })
      continue
    }

    // 如果指定了允许的类型，进行额外校验
    if (allowedTypes && !allowMultipleTypes) {
      const fileType = getFileTypeCategory(file)
      if (!allowedTypes.includes(fileType)) {
        invalidFiles.push({ file, message: `不支持的文件类型: ${fileType}` })
        continue
      }
    }

    validFiles.push(file)
  }

  return {
    valid: invalidFiles.length === 0,
    validFiles,
    invalidFiles
  }
}
