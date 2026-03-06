<template>
  <div class="chat-page">
    <aside class="chat-sidebar" :class="{ 'is-open': sidebarOpen }">
      <div class="sidebar-header">
        <div class="logo-section">
          <div class="logo-icon-small">
            <svg viewBox="0 0 48 48" fill="none">
              <circle cx="24" cy="24" r="20" stroke="currentColor" stroke-width="2"/>
              <path d="M16 24C16 19.5817 19.5817 16 24 16V16C28.4183 16 32 19.5817 32 24V32H16V24Z" fill="currentColor"/>
              <circle cx="20" cy="26" r="2" fill="var(--bg-secondary)"/>
              <circle cx="28" cy="26" r="2" fill="var(--bg-secondary)"/>
            </svg>
          </div>
          <span class="logo-text">{{ t('common.appName') }}</span>
        </div>
        <button class="new-chat-btn" @click="handleNewChat">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          <span>{{ t('chat.newChat') }}</span>
        </button>
      </div>

      <div class="sidebar-content">
        <div class="history-section">
          <div class="history-header">
            <h3 class="section-title">{{ t('chat.history') }}</h3>
            <button class="clear-history-btn" @click="handleClearHistory" :title="t('chat.clearHistory') || '一键清除'">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 6h18"></path>
                <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
                <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
              </svg>
              <span>清除</span>
            </button>
          </div>
          <div v-if="chatStore.conversations.length === 0" class="no-history">
            {{ t('chat.noHistory') }}
          </div>
          <div v-else class="history-list">
            <div
              v-for="conv in chatStore.conversations"
              :key="conv.id"
              class="history-item"
              :class="{ active: conv.conversationId === chatStore.currentConversationId }"
              @click="loadConversation(conv.conversationId)"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
              <span class="history-title">{{ conv.title }}</span>
              <button class="delete-btn" @click.stop="deleteConversation(conv.conversationId)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6"/>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="sidebar-footer">
        <div class="user-section">
          <div class="user-avatar">
            {{ authStore.username.charAt(0).toUpperCase() }}
          </div>
          <span class="user-name">{{ authStore.username }}</span>
        </div>
        <div class="footer-actions">
          <LanguageSwitcher />
          <button class="settings-btn sidebar-settings-btn" @click="router.push('/manager')" :title="t('settings.title')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
            <span class="settings-btn-text">{{ t('settings.title') }}</span>
          </button>
          <button class="logout-btn" @click="handleLogout">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
          </button>
        </div>
      </div>
    </aside>

    <main class="chat-main">
      <button class="sidebar-toggle" @click="sidebarOpen = !sidebarOpen">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="3" y1="12" x2="21" y2="12"/>
          <line x1="3" y1="6" x2="21" y2="6"/>
          <line x1="3" y1="18" x2="21" y2="18"/>
        </svg>
      </button>

      <div class="chat-container">
        <div ref="messagesContainer" class="messages-container">
          <div v-if="!chatStore.hasMessages" class="welcome-section">
            <div class="welcome-icon">
              <svg viewBox="0 0 48 48" fill="none">
                <circle cx="24" cy="24" r="20" stroke="currentColor" stroke-width="2"/>
                <path d="M16 24C16 19.5817 19.5817 16 24 16V16C28.4183 16 32 19.5817 32 24V32H16V24Z" fill="currentColor"/>
                <circle cx="20" cy="26" r="2" fill="var(--bg-primary)"/>
                <circle cx="28" cy="26" r="2" fill="var(--bg-primary)"/>
              </svg>
            </div>
            <h2 class="welcome-title">{{ t('chat.title') }}</h2>
            <p class="welcome-subtitle">{{ t('chat.subtitle') }}</p>
          </div>

          <TransitionGroup name="message" tag="div" class="messages-list">
            <div
              v-for="message in chatStore.messages"
              :key="message.id"
              class="message"
              :class="message.role"
            >
              <div class="message-avatar">
                <template v-if="message.role === 'user'">
                  {{ authStore.username.charAt(0).toUpperCase() }}
                </template>
                <template v-else>
                  <svg viewBox="0 0 48 48" fill="none">
                    <circle cx="24" cy="24" r="20" stroke="currentColor" stroke-width="2"/>
                    <path d="M16 24C16 19.5817 19.5817 16 24 16V16C28.4183 16 32 19.5817 32 24V32H16V24Z" fill="currentColor"/>
                    <circle cx="20" cy="26" r="2" fill="var(--accent-primary)"/>
                    <circle cx="28" cy="26" r="2" fill="var(--accent-primary)"/>
                  </svg>
                </template>
              </div>
              <div class="message-content">
                <div v-if="message.thinking" class="message-thinking" :class="{ collapsed: !isThinkingExpanded(message) }">
                  <div class="thinking-header" @click="toggleThinking(message)">
                    <div class="thinking-title">
                      <span class="thinking-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <circle cx="12" cy="12" r="10"/>
                          <line x1="12" y1="16" x2="12" y2="12"/>
                          <line x1="12" y1="8" x2="12.01" y2="8"/>
                        </svg>
                      </span>
                      <span class="thinking-label">
                        {{ (message.role === 'assistant' && chatStore.streaming && message.id === chatStore.lastMessage?.id && !message.thinkingDuration) ? (t('chat.thinking') || 'Thinking Process...') : `已完成深度搜索(用时${Math.max(1, Math.round(message.thinkingDuration || 0))}秒)` }}
                      </span>
                    </div>
                    <span class="thinking-toggle-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="6 9 12 15 18 9"></polyline>
                      </svg>
                    </span>
                  </div>
                  <div v-show="isThinkingExpanded(message)" class="thinking-body markdown-body" v-html="formatMessage(message.thinking)"></div>
                </div>
                <div v-if="message.attachments && message.attachments.length" class="message-attachments">
                  <div
                    v-for="(att, idx) in message.attachments"
                    :key="idx"
                    class="attachment-item"
                    @click="downloadAttachment(att)"
                  >
                    <div class="attachment-icon">
                      <svg v-if="att.fileType.startsWith('image/')" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                        <circle cx="8.5" cy="8.5" r="1.5"/>
                        <polyline points="21 15 16 10 5 21"/>
                      </svg>
                      <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
                        <polyline points="13 2 13 9 20 9"/>
                      </svg>
                    </div>
                    <div class="attachment-info">
                      <span class="attachment-name">{{ att.fileName }}</span>
                      <span class="attachment-size">{{ formatSize(att.fileSize) }}</span>
                    </div>
                  </div>
                </div>
                <div class="message-text" v-html="formatMessage(message.content)"></div>
                <div v-if="message.role === 'assistant' && chatStore.streaming && message === chatStore.lastMessage" class="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
              <div class="message-actions" v-if="message.role === 'assistant' && message.content">
                <button class="action-btn" @click="copyMessage(message.content)" :title="t('chat.copy')">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                  </svg>
                </button>
              </div>
            </div>
          </TransitionGroup>
        </div>
      </div>

      <div class="input-section">
        <div class="input-container">
          <div v-if="selectedFiles.length" class="selected-files">
            <div v-for="(file, idx) in selectedFiles" :key="idx" class="selected-file-item">
              <span class="file-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
                  <polyline points="13 2 13 9 20 9"/>
                </svg>
              </span>
              <span class="file-name">{{ file.fileName }}</span>
              <span v-if="file.status === 'uploading'" class="file-status">...</span>
              <span v-else-if="file.status === 'error'" class="file-status error">!</span>
              <button class="remove-file-btn" @click="removeFile(idx)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
          </div>
          <form class="input-form" @submit.prevent="sendMessage">
            <div class="input-wrapper">
              <textarea
                ref="inputRef"
                v-model="inputText"
                class="chat-input"
                :placeholder="t('chat.placeholder')"
                rows="1"
                @keydown.enter.exact.prevent="sendMessage"
                @input="autoResize"
              ></textarea>
              <div class="input-footer">
                <div class="footer-left">
                  <div class="role-selector" v-if="roles.length > 0">
                    <select v-model="selectedRoleId" class="role-select" :title="t('role.selectRole') || '选择角色'">
                      <option :value="null">默认角色</option>
                      <option v-for="role in roles" :key="role.id" :value="role.id">
                        {{ role.name }}
                      </option>
                    </select>
                  </div>
                  <button
                    type="button"
                    class="thinking-btn"
                    :class="{ active: isThinking }"
                    @click="isThinking = !isThinking"
                    :title="isThinking ? '深度思考模式' : '普通快速模式'"
                  >
                    <svg v-if="!isThinking" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                    </svg>
                    <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 0 1-2 2H10a2 2 0 0 1-2-2v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 0 1 7-7z" />
                      <path d="M9 21h6" />
                      <path d="M12 9v4M12 17h.01" />
                    </svg>
                    <span class="thinking-text">{{ isThinking ? '深度思考' : '快速' }}</span>
                  </button>
                </div>
                <div class="footer-right">
                  <button
                    type="submit"
                    class="send-btn"
                    :disabled="(!inputText.trim() && selectedFiles.length === 0) && !chatStore.streaming"
                  >
                    <svg v-if="chatStore.streaming" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <rect x="6" y="6" width="12" height="12"/>
                    </svg>
                    <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <line x1="22" y1="2" x2="11" y2="13"/>
                      <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </form>
          <div class="disclaimer-text">
            内容由AI生成，仅供参考
          </div>
        </div>
      </div>
    </main>

    <aside class="chat-right-side" :class="{ 'is-open': rightPanelOpen }">
      <div class="right-side-header">
        <span class="right-side-title">{{ t('settings.runDetails') }}</span>
        <button type="button" class="right-side-close" :title="t('common.cancel')" @click="rightPanelOpen = false">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
      <div class="right-side-body">
        <!-- 运行详情类型选择：设备管理 / 告警管理 -->
        <div class="run-details-type-toggle">
          <button
            type="button"
            class="run-details-type-btn"
            :class="{ active: runDetailsType === 'device' }"
            @click="runDetailsType = 'device'"
          >
            <span class="run-details-type-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <rect x="4" y="5" width="16" height="12" rx="2" />
                <path d="M8 9h8M8 13h5" />
              </svg>
            </span>
            <span class="run-details-type-label">
              {{ t('settings.deviceMng') }}
            </span>
          </button>
          <button
            type="button"
            class="run-details-type-btn"
            :class="{ active: runDetailsType === 'alert' }"
            @click="runDetailsType = 'alert'"
          >
            <span class="run-details-type-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <path d="M12 3 3 19h18L12 3Z" />
                <line x1="12" y1="10" x2="12" y2="14" />
                <circle cx="12" cy="17" r="1" />
              </svg>
            </span>
            <span class="run-details-type-label">
              {{ t('settings.alertMng') }}
            </span>
          </button>
        </div>

        <!-- 设备统计，仅在设备管理 Tab 下展示 -->
        <div v-if="runDetailsType === 'device'" class="run-details-device-stats">
          <div class="run-details-stats-title">{{ t('runDetails.deviceStatsTitle') }}</div>
          <div class="run-details-device-stats-grid">
            <div class="run-details-device-stats-item">
              <div class="run-details-device-stats-label">{{ t('runDetails.deviceTotal') }}</div>
              <div class="run-details-device-stats-value">{{ deviceTotalCount }}</div>
            </div>
            <div class="run-details-device-stats-item">
              <div class="run-details-device-stats-label">{{ t('runDetails.deviceOnline') }}</div>
              <div class="run-details-device-stats-value is-online">{{ deviceOnlineCount }}</div>
            </div>
            <div class="run-details-device-stats-item">
              <div class="run-details-device-stats-label">{{ t('runDetails.deviceOffline') }}</div>
              <div class="run-details-device-stats-value is-offline">{{ deviceOfflineCount }}</div>
            </div>
          </div>
        </div>

        <!-- 告警统计，仅在告警管理 Tab 下展示 -->
        <div v-else class="run-details-alert-stats">
          <div class="run-details-stats-title">{{ t('runDetails.alertStatsTitle') }}</div>
          <div class="run-details-alert-stats-grid">
            <div class="run-details-alert-stats-item">
              <div class="run-details-alert-stats-label">{{ t('runDetails.fatalAlerts') }}</div>
              <div class="run-details-alert-stats-value fatal">{{ fatalAlertCount }}</div>
            </div>
            <div class="run-details-alert-stats-item">
              <div class="run-details-alert-stats-label">{{ t('runDetails.criticalAlerts') }}</div>
              <div class="run-details-alert-stats-value critical">{{ criticalAlertCount }}</div>
            </div>
            <div class="run-details-alert-stats-item">
              <div class="run-details-alert-stats-label">{{ t('runDetails.normalAlerts') }}</div>
              <div class="run-details-alert-stats-value normal">{{ normalAlertCount }}</div>
            </div>
            <div class="run-details-alert-stats-item">
              <div class="run-details-alert-stats-label">{{ t('runDetails.infoAlerts') }}</div>
              <div class="run-details-alert-stats-value info">{{ infoAlertCount }}</div>
            </div>
          </div>
        </div>

        <div
          class="run-details-carousel"
          :class="{ 'no-carousel': !needCarousel }"
          @mouseenter="carouselPaused = true"
          @mouseleave="carouselPaused = false"
        >
          <div
            ref="carouselWrapRef"
            class="carousel-slide-wrap"
            :style="carouselWrapStyle"
          >
            <template v-if="carouselItems.length > 0">
              <!-- 从下往上轮播：所有卡片同时向上滚动，一次展示 3 条 -->
              <div
                class="carousel-vertical-track"
                :class="`carousel-vertical-track--${runDetailsType}`"
                ref="carouselTrackRef"
                :style="carouselTrackStyle"
              >
                <div
                  v-for="item in carouselItems"
                  :key="item._loopIndex ?? item.id"
                  class="carousel-card-wrap"
                >
                  <!-- 设备卡片 -->
                  <div
                    v-if="item.type === 'device'"
                    class="carousel-card device-card"
                  >
                    <div class="carousel-card-icon">
                      <!-- 根据设备名称简单区分图标类型 -->
                      <svg
                        v-if="item.name.includes('摄像头')"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="1.5"
                      >
                        <rect x="4" y="6" width="11" height="10" rx="2" />
                        <circle cx="9.5" cy="11" r="1.8" />
                        <path d="M15 9.5 19 7v10l-4-2.5V9.5Z" />
                      </svg>
                      <svg
                        v-else-if="item.name.includes('传感器')"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="1.5"
                      >
                        <rect x="5" y="5" width="14" height="14" rx="3" />
                        <circle cx="12" cy="12" r="2.2" />
                        <path d="M9 3h6M9 21h6" />
                      </svg>
                      <svg
                        v-else
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="1.5"
                      >
                        <circle cx="12" cy="8" r="3" />
                        <path d="M5 19c0-3.3 2.8-6 7-6s7 2.7 7 6" />
                      </svg>
                    </div>
                    <div class="carousel-card-main">
                      <div class="carousel-card-name">{{ item.name }}</div>
                      <div class="carousel-card-status" :class="item.status">
                        {{ item.status === 'online' ? t('runDetails.online') : t('runDetails.offline') }}
                      </div>
                    </div>
                    <div class="carousel-card-dot" :class="item.status"></div>
                  </div>
                  <!-- 告警卡片 -->
                  <div
                    v-else
                    class="carousel-card alert-card"
                  >
                    <div class="carousel-alert-header">
                      <div class="carousel-card-name">{{ item.name }}</div>
                      <span class="carousel-alert-level" :class="item.level">
                        {{ alertLevelText(item.level) }}
                      </span>
                    </div>
                    <div class="carousel-card-time">{{ item.time }}</div>
                    <div class="carousel-card-actions">
                      <button type="button" class="carousel-btn" @click.stop="showAlertPopup = true">
                        {{ t('alert.ignore', '忽略') }}
                      </button>
                      <button type="button" class="carousel-btn" @click.stop="showAlertPopup = true">
                        {{ t('alert.view', '查看') }}
                      </button>
                      <button type="button" class="carousel-btn primary" @click.stop="showAlertPopup = true">
                        {{ t('alert.aiFix', 'AI修复') }}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </template>
            <div v-else class="carousel-empty">{{ t('common.noData') }}</div>
          </div>
        </div>

        <!-- 运行统计信息：MCP 工具 / Skills / CoT 规则 -->
        <div class="run-details-stats">
          <div class="run-details-stats-title">{{ t('runDetails.statsTitle') }}</div>
          <div class="run-details-stats-grid">
            <div class="run-details-stats-item">
              <div class="run-details-stats-top">
                <div class="run-details-stats-icon run-details-stats-icon--mcp">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                    <rect x="3" y="4" width="18" height="16" rx="3"/>
                    <path d="M7 9h10M7 13h4"/>
                  </svg>
                </div>
                <div class="run-details-stats-label">{{ t('runDetails.mcpTools') }}</div>
              </div>
              <div class="run-details-stats-value">{{ mcpToolsCount }}</div>
            </div>
            <div class="run-details-stats-item">
              <div class="run-details-stats-top">
                <div class="run-details-stats-icon run-details-stats-icon--skills">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                    <circle cx="12" cy="8" r="3"/>
                    <path d="M6 19c0-3 2.5-5 6-5s6 2 6 5"/>
                  </svg>
                </div>
                <div class="run-details-stats-label">{{ t('runDetails.skills') }}</div>
              </div>
              <div class="run-details-stats-value">{{ skillsCount }}</div>
            </div>
            <div class="run-details-stats-item">
              <div class="run-details-stats-top">
                <div class="run-details-stats-icon run-details-stats-icon--cot">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                    <path d="M5 7h14M5 12h9M5 17h6"/>
                    <circle cx="18" cy="12" r="2.2"/>
                  </svg>
                </div>
                <div class="run-details-stats-label">{{ t('runDetails.cotRules') }}</div>
              </div>
              <div class="run-details-stats-value">{{ cotRulesCount }}</div>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <Teleport to="body">
      <Transition name="popup">
        <div v-if="showDevicePopup" class="right-popup-overlay" @click.self="showDevicePopup = false">
          <div class="right-popup-box">
            <div class="right-popup-header">
              <span class="right-popup-title">{{ t('settings.deviceMng') }}</span>
              <button type="button" class="right-popup-close" @click="showDevicePopup = false">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
            <div class="right-popup-body">
              <DeviceMngView :list-mode="true" />
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
    <Teleport to="body">
      <Transition name="popup">
        <div v-if="showAlertPopup" class="right-popup-overlay" @click.self="showAlertPopup = false">
          <div class="right-popup-box">
            <div class="right-popup-header">
              <span class="right-popup-title">{{ t('settings.alertMng') }}</span>
              <button type="button" class="right-popup-close" @click="showAlertPopup = false">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
            <div class="right-popup-body">
              <WarnningView :hide-title="true" />
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <button
      class="right-panel-toggle"
      :class="{ 'is-visible': !rightPanelOpen }"
      :title="t('settings.runDetails')"
      @click="rightPanelOpen = true"
    >
      <svg class="run-details-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2"/>
        <line x1="7" y1="9" x2="17" y2="9"/>
        <line x1="7" y1="13" x2="15" y2="13"/>
        <line x1="7" y1="17" x2="13" y2="17"/>
      </svg>
    </button>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import * as echarts from 'echarts'
import { useAuthStore } from '@/store/auth'
import { useChatStore } from '@/store/chat'
import LanguageSwitcher from '@/components/LanguageSwitcher.vue'
import DeviceMngView from '@/views/DeviceMngView.vue'
import WarnningView from '@/views/WarnningView.vue'

import { roleApi } from '@/api/applicationRole'
import { chatApi } from '@/api/chat'

const router = useRouter()
const { t } = useI18n()
const authStore = useAuthStore()
const chatStore = useChatStore()
const isThinking = ref(false)
const thinkingExpandedState = ref({})
const roles = ref([])
const selectedRoleId = ref(null)

async function loadRoles() {
  try {
    const res = await roleApi.list({ page: 1, size: 100 })
    if (res.data && res.data.code === 0 && res.data.data) {
      roles.value = res.data.data.items || []
      // Default select first enabled role if available
      const enabledRoles = roles.value.filter(r => r.enabled)
      if (enabledRoles.length > 0) {
        selectedRoleId.value = enabledRoles[0].id
      }
    }
  } catch (e) {
    console.error('Failed to load roles', e)
  }
}

function toggleThinking(message) {
  if (!message.id) return
  // If undefined, default to true (expanded) so we set to false (collapsed)
  // Or if we want default collapsed for old messages?
  // Let's assume default is expanded.
  if (thinkingExpandedState.value[message.id] === undefined) {
    thinkingExpandedState.value[message.id] = false
  } else {
    thinkingExpandedState.value[message.id] = !thinkingExpandedState.value[message.id]
  }
}

function isThinkingExpanded(message) {
  // Default to expanded if streaming, or if not set
  if (thinkingExpandedState.value[message.id] === undefined) {
    return true
  }
  return thinkingExpandedState.value[message.id]
}

const sidebarOpen = ref(false)
const rightPanelOpen = ref(false)
// 运行详情类型：device / alert
const runDetailsType = ref('device')
// 运行详情右侧轮播容器和轨道
const carouselWrapRef = ref(null)
const carouselTrackRef = ref(null)
const showDevicePopup = ref(false)
const showAlertPopup = ref(false)
const inputText = ref('')
const inputRef = ref(null)
const fileInputRef = ref(null)
const selectedFiles = ref([])
const messagesContainer = ref(null)

// 轮播：设备 / 告警数据（用于运行详情侧栏）
const carouselDevices = [
  { id: 1, name: '边缘智能体', status: 'online' },
  { id: 2, name: '环境传感器', status: 'online' },
  { id: 3, name: '摄像头', status: 'offline' },
  { id: 4, name: '气体传感器', status: 'online' },
  { id: 5, name: '门磁传感器', status: 'online' },
  { id: 6, name: '红外传感器', status: 'offline' },
  { id: 7, name: '户外摄像头', status: 'online' },
  { id: 8, name: '室内摄像头', status: 'online' }
]
const carouselAlerts = [
  { id: 1, name: '温度传感器异常', level: 'fatal', time: '2024-01-22 14:30:25', description: '温度传感器读数超出正常范围，当前温度95°C，可能导致设备损坏' },
  { id: 2, name: '湿度传感器异常', level: 'normal', time: '2024-01-22 14:28:10', description: '湿度传感器读数偏低，当前湿度35%' },
  { id: 3, name: '压力传感器异常', level: 'critical', time: '2024-01-22 14:25:30', description: '压力传感器读数过高，当前压力2.5MPa' },
  { id: 4, name: '气体传感器异常', level: 'info', time: '2024-01-22 14:20:15', description: '气体传感器检测到轻微泄漏' },
  { id: 5, name: '光敏传感器异常', level: 'critical', time: '2024-01-22 14:15:00', description: '光敏传感器读数异常，光照强度过低' },
  { id: 6, name: '网络连接异常', level: 'warning', time: '2024-01-22 14:10:00', description: '边缘节点与平台之间网络波动，存在短暂丢包' },
  { id: 7, name: '电压传感器异常', level: 'critical', time: '2024-01-22 14:05:00', description: '电压传感器读数异常，电压波动频繁' }
]
// 根据当前选择的运行详情类型，决定轮播数据源（基础列表）
const baseCarouselItems = computed(() => {
  if (runDetailsType.value === 'device') {
    return carouselDevices.map((d) => ({ type: 'device', ...d }))
  }
  return carouselAlerts.map((a) => ({ type: 'alert', ...a }))
})
// 每次可见条数：设备 6 条，告警 4 条
const carouselVisibleCount = computed(() => (runDetailsType.value === 'device' ? 7 : 4))

// 实际渲染用的列表：在基础列表末尾追加前 N 条，做收尾相连
const carouselItems = computed(() => {
  const list = baseCarouselItems.value
  const visibleCount = carouselVisibleCount.value
  if (list.length <= visibleCount) return list
  const extra = list.slice(0, visibleCount)
  return list
    .map((item, index) => ({ ...item, _loopIndex: index }))
    .concat(
      extra.map((item, index) => ({
        ...item,
        _loopIndex: list.length + index
      }))
    )
})

const carouselIndex = ref(0)
const carouselPaused = ref(false)
let carouselTimer = null
// 单条卡片向上滚动的步长（卡片高度 + 间距），单位 px
// 设备 / 告警使用不同的步长，但可见区域高度保持一致：
// 设备：卡片高约 68px + 间距 8px ≈ 76
// 告警：卡片高约 120px + 间距 8px = 128
const CAROUSEL_STEP_DEVICE = 76
const CAROUSEL_STEP_ALERT = 128
// 控制是否需要过渡动画，用于收尾衔接时瞬间复位
const carouselAnimated = ref(true)
// 当前是否需要轮播（内容高度超过可视区域时才轮播）
const needCarousel = ref(false)
// 运行统计：MCP 工具 / Skills / CoT 规则（此处先使用占位数量，后续可接入真实配置）
const mcpToolsCount = ref(0)
const skillsCount = ref(0)
const cotRulesCount = ref(0)
// 设备统计：总数 / 在线 / 离线
const deviceTotalCount = computed(() => carouselDevices.length)
const deviceOnlineCount = computed(() =>
  carouselDevices.filter((d) => d.status === 'online').length
)
const deviceOfflineCount = computed(() =>
  carouselDevices.filter((d) => d.status === 'offline').length
)
// 告警统计：致命 / 严重 / 一般 / 提示（将 warning 也归到 info）
const fatalAlertCount = computed(() => carouselAlerts.filter((a) => a.level === 'fatal').length)
const criticalAlertCount = computed(() =>
  carouselAlerts.filter((a) => a.level === 'critical').length
)
const normalAlertCount = computed(() =>
  carouselAlerts.filter((a) => a.level === 'normal').length
)
const infoAlertCount = computed(() =>
  carouselAlerts.filter((a) => a.level === 'info' || a.level === 'warning').length
)
// 整个轨道的位移样式：所有卡片一起向上平移
const carouselTrackStyle = computed(() => {
  const step = runDetailsType.value === 'device' ? CAROUSEL_STEP_DEVICE : CAROUSEL_STEP_ALERT
  const offset = carouselIndex.value * step
  return {
    transform: `translateY(-${offset}px)`,
    transition: carouselAnimated.value ? 'transform 0.35s ease-out' : 'none'
  }
})

// 轮播视口高度：只有在需要轮播时才固定为「可见条数 * 步长」，否则自适应内容高度
const carouselWrapStyle = computed(() => {
  if (!needCarousel.value) return {}
  const step = runDetailsType.value === 'device' ? CAROUSEL_STEP_DEVICE : CAROUSEL_STEP_ALERT
  const height = carouselVisibleCount.value * step
  return {
    height: `${height}px`
  }
})

// 根据实际高度判断是否需要轮播
function updateCarouselNeed() {
  nextTick(() => {
    const wrap = carouselWrapRef.value
    const track = carouselTrackRef.value
    if (!wrap || !track) return
    const wrapHeight = wrap.clientHeight
    const trackHeight = track.scrollHeight
    // 留一点余量，避免浮点误差
    needCarousel.value = trackHeight - wrapHeight > 4

    if (!needCarousel.value) {
      // 不需要轮播时，重置位置并停止计时器
      carouselAnimated.value = false
      carouselIndex.value = 0
      stopCarousel()
      // 下一帧恢复动画配置，避免后续再次需要轮播时没有过渡
      requestAnimationFrame(() => {
        carouselAnimated.value = true
      })
    } else if (rightPanelOpen.value) {
      // 需要轮播且右侧面板已打开时，启动轮播
      startCarousel()
    }
  })
}

function startCarousel() {
  if (carouselTimer) return
  if (!needCarousel.value) return
  carouselTimer = setInterval(() => {
    if (carouselPaused.value) return
    const maxIndex = Math.max(0, carouselItems.value.length - carouselVisibleCount.value)
    if (carouselIndex.value >= maxIndex) {
      // 先播放到最后一个窗口，然后瞬间复位到顶部，避免出现下面空白
      carouselAnimated.value = false
      carouselIndex.value = 0
      // 下一帧重新开启过渡，从头继续向上滚动，形成收尾相连的效果
      requestAnimationFrame(() => {
        carouselAnimated.value = true
      })
    } else {
      carouselAnimated.value = true
      carouselIndex.value += 1
    }
  }, 4000)
}
function stopCarousel() {
  if (carouselTimer) {
    clearInterval(carouselTimer)
    carouselTimer = null
  }
}
function alertLevelText(level) {
  const map = { fatal: '致命告警', critical: '严重告警', normal: '一般告警', info: '提示告警', warning: '提示告警' }
  return map[level] || level
}

// 切换设备 / 告警时，重置轮播起始位置并重新判断是否需要轮播
watch(runDetailsType, () => {
  carouselIndex.value = 0
  updateCarouselNeed()
})

// 右侧面板开关时，根据内容高度决定是否轮播
watch(rightPanelOpen, (open) => {
  if (open) {
    updateCarouselNeed()
  } else {
    stopCarousel()
  }
})

onMounted(() => {
  loadRoles()
  chatStore.loadHistory()
  // 初始挂载后，如果右侧面板是打开的（比如刷新在设置状态），也判断一次
  if (rightPanelOpen.value) {
    updateCarouselNeed()
  }
  initCharts()
})
onUnmounted(stopCarousel)

watch(() => chatStore.messages.length, () => {
  nextTick(() => {
    scrollToBottom()
    initCharts()
  })
})

watch(() => chatStore.lastMessage?.content, () => {
  nextTick(() => {
    scrollToBottom()
    initCharts()
  })
})

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

function autoResize() {
  if (inputRef.value) {
    inputRef.value.style.height = 'auto'
    inputRef.value.style.height = Math.min(inputRef.value.scrollHeight, 200) + 'px'
  }
}

function triggerFileUpload() {
  fileInputRef.value?.click()
}

async function handleFileSelect(event) {
  const file = event.target.files[0]
  if (!file) return

  const fileObj = {
    file,
    fileName: file.name,
    fileType: file.type,
    fileSize: file.size,
    status: 'uploading',
    progress: 0
  }
  selectedFiles.value.push(fileObj)
  
  // Clear input
  event.target.value = ''

  try {
    const res = await chatApi.uploadFile(file)
    if (res.data && res.data.code === 0 && res.data.data) {
      Object.assign(fileObj, {
        status: 'uploaded',
        ...res.data.data
      })
    } else {
      fileObj.status = 'error'
    }
  } catch (e) {
    fileObj.status = 'error'
    console.error(e)
  }
}

function removeFile(index) {
  selectedFiles.value.splice(index, 1)
}

function formatSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function downloadAttachment(att) {
  if (att.fileUrl) {
    // Use API helper if available or construct full URL
    // Backend returns relative path like /v1/agent/chat/files/xxx
    const url = `/api${att.fileUrl}`
    window.open(url, '_blank')
  }
}

async function sendMessage() {
  if (chatStore.streaming) {
    chatStore.stopGeneration()
    return
  }
  if ((!inputText.value.trim() && selectedFiles.value.length === 0)) return
  
  const message = inputText.value.trim()
  const attachments = selectedFiles.value
    .filter(f => f.status === 'uploaded')
    .map(f => ({
      fileName: f.fileName,
      fileType: f.fileType,
      fileSize: f.fileSize,
      fileUrl: f.fileUrl,
      storageType: f.storageType || 'local',
      thumbnailUrl: f.thumbnailUrl
    }))

  inputText.value = ''
  selectedFiles.value = []
  if (inputRef.value) {
    inputRef.value.style.height = 'auto'
  }
  
  await chatStore.sendMessage(message, attachments, isThinking.value, selectedRoleId.value)
}

function handleNewChat() {
  chatStore.createNewChat()
  sidebarOpen.value = false
}

function loadConversation(id) {
  chatStore.loadConversation(id)
  sidebarOpen.value = false
}

function deleteConversation(id) {
  if (confirm(t('chat.deleteChat'))) {
    chatStore.deleteConversation(id)
  }
}

function handleClearHistory() {
  if (confirm('确定要清除所有历史记录吗？此操作不可恢复。')) {
    chatStore.clearHistory()
  }
}

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}

function copyMessage(content) {
  navigator.clipboard.writeText(content)
}

function initCharts() {
  nextTick(() => {
    const charts = document.querySelectorAll('.echarts-chart')
    charts.forEach(el => {
      if (el.getAttribute('data-initialized') === 'true') return
      
      const raw = el.getAttribute('data-option')
      if (!raw) return
      
      try {
        let jsonStr = raw
        try {
          jsonStr = decodeURIComponent(raw)
        } catch (_) {
          jsonStr = raw
        }
        let option
        try {
          option = JSON.parse(jsonStr)
        } catch (_) {
          option = JSON.parse(raw)
        }
        if (option && option.toolbox) {
          delete option.toolbox
        }
        try {
          if (!option.textStyle) option.textStyle = {}
          option.textStyle.color = '#ffffff'
          const titles = Array.isArray(option.title) ? option.title : [option.title].filter(Boolean)
          titles.forEach(t => {
            if (!t.textStyle) t.textStyle = {}
            t.textStyle.color = '#ffffff'
          })
          const legends = Array.isArray(option.legend) ? option.legend : [option.legend].filter(Boolean)
          legends.forEach(l => {
            if (!l.textStyle) l.textStyle = {}
            l.textStyle.color = '#ffffff'
          })
          const xAxes = Array.isArray(option.xAxis) ? option.xAxis : [option.xAxis].filter(Boolean)
          const yAxes = Array.isArray(option.yAxis) ? option.yAxis : [option.yAxis].filter(Boolean)
          ;[...xAxes, ...yAxes].forEach(ax => {
            if (!ax.axisLabel) ax.axisLabel = {}
            ax.axisLabel.color = '#ffffff'
          })
          const seriesArr = Array.isArray(option.series) ? option.series : []
          seriesArr.forEach(s => {
            if (!s.label) s.label = {}
            s.label.color = '#ffffff'
          })
          if (!option.tooltip) option.tooltip = {}
          if (!option.tooltip.textStyle) option.tooltip.textStyle = {}
          option.tooltip.textStyle.color = '#ffffff'
        } catch (_) {}
        const chart = echarts.init(el)
        chart.setOption(option)
        el.setAttribute('data-initialized', 'true')
        new ResizeObserver(() => chart.resize()).observe(el)
      } catch (e) {
        console.error('Failed to init chart', e)
      }
    })
  })
}

function escapeHtml(raw) {
  return String(raw).replace(/[&<>"']/g, (ch) => {
    if (ch === '&') return '&amp;'
    if (ch === '<') return '&lt;'
    if (ch === '>') return '&gt;'
    if (ch === '"') return '&quot;'
    return '&#39;'
  })
}

function tryParseEChartsOptionJson(raw) {
  if (!raw) return null
  const trimmed = String(raw).trim()
  if (!trimmed) return null
  try {
    const parsed = JSON.parse(trimmed)
    if (parsed && typeof parsed === 'object' && parsed.echarts_option) {
      return { option: parsed.echarts_option, raw: trimmed }
    }
  } catch (_) {
    return null
  }
  return null
}

function renderEChartsBlock(option, rawJson) {
  const optionEncoded = encodeURIComponent(JSON.stringify(option ?? {}))
  const rawEscaped = escapeHtml(rawJson)
  const title = option && option.title && option.title.text ? String(option.title.text) : '图表'
  const firstSeries = Array.isArray(option?.series) ? option.series[0] : null
  const dataItems = Array.isArray(firstSeries?.data) ? firstSeries.data : []
  const total = dataItems.reduce((acc, it) => acc + (Number(it?.value) || 0), 0)
  const summaryLines = dataItems.slice(0, 12).map((it) => {
    const name = escapeHtml(it?.name ?? '')
    const valNum = Number(it?.value) || 0
    const pct = total > 0 ? ((valNum / total) * 100).toFixed(2) : '0.00'
    const value = escapeHtml(String(valNum))
    return name ? `<div class="line">${name}: ${value}（${pct}%）</div>` : `<div class="line">${value}（${pct}%）</div>`
  }).join('')
  const totalLine = `<div class="line">总计：${escapeHtml(String(total))}</div>`

  const chartSrcDoc = `<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
html,body{height:100%;margin:0;background:#0f172a;color:#fff;font-family:system-ui;}
#chart{width:100%;height:100%}
</style>
<scr` + `ipt src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></scr` + `ipt>
</head><body>
<div id="chart"></div>
<scr` + `ipt>
(function(){
  try{
    var j='${optionEncoded}';
    var option = JSON.parse(decodeURIComponent(j));
    if(option.toolbox){delete option.toolbox;}
    option.textStyle = option.textStyle || {}; option.textStyle.color = '#ffffff';
    var titles = Array.isArray(option.title) ? option.title : (option.title ? [option.title] : []);
    titles.forEach(function(t){ t.textStyle = t.textStyle || {}; t.textStyle.color = '#ffffff'; });
    var legends = Array.isArray(option.legend) ? option.legend : (option.legend ? [option.legend] : []);
    legends.forEach(function(l){ l.textStyle = l.textStyle || {}; l.textStyle.color = '#ffffff'; });
    var xAxes = Array.isArray(option.xAxis) ? option.xAxis : (option.xAxis ? [option.xAxis] : []);
    var yAxes = Array.isArray(option.yAxis) ? option.yAxis : (option.yAxis ? [option.yAxis] : []);
    [].concat(xAxes, yAxes).forEach(function(ax){ ax.axisLabel = ax.axisLabel || {}; ax.axisLabel.color = '#ffffff'; });
    var seriesArr = Array.isArray(option.series) ? option.series : [];
    seriesArr.forEach(function(s){ s.label = s.label || {}; s.label.color = '#ffffff'; });
    option.tooltip = option.tooltip || {}; option.tooltip.textStyle = option.tooltip.textStyle || {}; option.tooltip.textStyle.color = '#ffffff';
    var chart = echarts.init(document.getElementById('chart'));
    chart.setOption(option);
    window.addEventListener('resize', function(){ chart.resize(); });
  }catch(e){ console.error(e); }
})();
</scr` + `ipt>
</body></html>`

  const descSrcDoc = `<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
html,body{height:100%;margin:0;background:transparent;color:#ffffff;font-family:system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;}
.wrap{box-sizing:border-box;padding:8px 10px;line-height:1.7;font-size:14px;}
.title{margin:0 0 6px 0;font-size:14px;font-weight:600;}
.line{margin:2px 0;}
</style>
</head><body>
<div class="wrap">
  <div class="title">${escapeHtml(title)}</div>
  ${summaryLines}${totalLine}
</div>
</body></html>`

  return `
  <div class="echarts-block echarts-block--iframes">
    <div class="echarts-iframe-container echarts-iframe-container--column">
      <iframe class="echarts-iframe echarts-iframe--desc" srcdoc="${descSrcDoc.replace(/"/g, '&quot;')}" scrolling="no"></iframe>
      <iframe class="echarts-iframe echarts-iframe--chart" srcdoc="${chartSrcDoc.replace(/"/g, '&quot;')}"></iframe>
    </div>
    <details class="echarts-details"><summary>配置</summary><pre><code>${rawEscaped}</code></pre></details>
  </div>`
}

function formatMessage(content) {
  if (!content) return ''
  const trimmed = String(content).trim()
  const wholeJson = tryParseEChartsOptionJson(trimmed)
  if (wholeJson) {
    return renderEChartsBlock(wholeJson.option, wholeJson.raw)
  }

  const replaced = String(content).replace(/```([\s\S]*?)```/g, (match, code) => {
    const lines = String(code).split('\n')
    const firstLine = (lines[0] || '').trim()
    const maybeBody = ['json', 'javascript', 'js', 'text'].includes(firstLine.toLowerCase())
      ? lines.slice(1).join('\n')
      : String(code)
    const parsed = tryParseEChartsOptionJson(maybeBody)
    if (parsed) return renderEChartsBlock(parsed.option, parsed.raw)
    return `<pre><code>${code}</code></pre>`
  })

  return replaced
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}
</script>

<style lang="scss" scoped>
.chat-page {
  display: flex;
  height: 100vh;
  width: 100%;
  overflow: hidden;
  background: var(--bg-primary);
}

.chat-sidebar {
  width: 280px;
  height: 100%;
  flex-shrink: 0;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
  transition: transform 0.3s ease;

  @media (max-width: 768px) {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 100;
    transform: translateX(-100%);

    &.is-open {
      transform: translateX(0);
    }
  }
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid var(--border-primary);
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.logo-icon-small {
  width: 36px;
  height: 36px;
  color: var(--accent-primary);
}

.logo-text {
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.new-chat-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  font-family: var(--font-primary);
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-primary);
  background: var(--bg-tertiary);
  border: 1px dashed var(--border-secondary);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;

  svg {
    width: 18px;
    height: 18px;
  }

  &:hover {
    background: var(--bg-hover);
    border-style: solid;
    border-color: var(--accent-primary);
    color: var(--accent-primary);
  }
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.section-title {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.clear-history-btn {
  background: none;
  border: none;
  color: var(--text-primary);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.9;
  gap: 5px;
  font-size: 0.8rem;
}

.clear-history-btn:hover {
  opacity: 1;
  color: var(--error-text, #ff4d4f);
  background: rgba(0,0,0,0.05);
}

.clear-history-btn svg {
  width: 16px;
  height: 16px;
}

.no-history {
  text-align: center;
  color: var(--text-muted);
  font-size: 0.875rem;
  padding: 20px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;

  svg {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
    color: var(--text-muted);
  }

  .history-title {
    flex: 1;
    font-size: 0.875rem;
    color: var(--text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .delete-btn {
    opacity: 0;
    padding: 4px;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--text-muted);
    transition: all 0.2s ease;

    &:hover {
      color: var(--error-text);
    }
  }

  &:hover {
    background: var(--bg-hover);

    .delete-btn {
      opacity: 1;
    }
  }

  &.active {
    background: var(--bg-active);

    .history-title {
      color: var(--text-primary);
    }
  }
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-section {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--accent-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.875rem;
  color: var(--button-text);
}

.user-name {
  flex: 1;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
}

.footer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logout-btn {
  padding: 8px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  border-radius: 6px;
  transition: all 0.2s ease;

  svg {
    width: 18px;
    height: 18px;
  }

  &:hover {
    background: var(--bg-hover);
    color: var(--error-text);
  }
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  min-width: 0;
  height: 100%;
  overflow: hidden;
}

.chat-right-side {
  width: 380px;
  flex-shrink: 0;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
  transition: width 0.25s ease, margin 0.25s ease;

  @media (max-width: 1024px) {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    z-index: 90;
    width: 380px;
    max-width: 90vw;
    margin-right: 0;
    box-shadow: -4px 0 20px rgba(0, 0, 0, 0.15);

    &:not(.is-open) {
      width: 0;
      overflow: hidden;
      margin-right: -380px;
      border-left: none;
    }
  }
}

@media (min-width: 1025px) {
  .chat-right-side:not(.is-open) {
    width: 0;
    overflow: hidden;
    border-left: none;
  }
}

.right-side-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-primary);
  flex-shrink: 0;
}

.right-side-title {
  font-size: 1.3rem;
  font-weight: 600;
  color: var(--text-primary);
}

.right-side-close {
  padding: 6px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  border-radius: 6px;
  transition: all 0.2s ease;

  svg {
    width: 18px;
    height: 18px;
  }

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
}

.right-side-body {
  flex: 1;
  overflow: auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.run-details-type-toggle {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.run-details-type-btn {
  flex: 1;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;

  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  &.active {
    background: var(--accent-gradient);
    border-color: transparent;
    color: var(--button-text);
  }
}

.run-details-type-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.run-details-type-icon svg {
  width: 18px;
  height: 18px;
}

.run-details-type-label {
  display: inline-block;
}

.run-details-carousel {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.run-details-stats {
  margin-top: auto;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
}

.run-details-stats-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 10px;
}

/* 设备 / 告警统计信息区域，放在轮播上方，紧凑展示 */
.run-details-device-stats,
.run-details-alert-stats {
  margin-top: 8px;
  margin-bottom: 8px;
}

.run-details-device-stats-grid,
.run-details-alert-stats-grid {
  display: flex;
  gap: 8px;
}

.run-details-device-stats-item,
.run-details-alert-stats-item {
  flex: 1;
  text-align: center;
}

.run-details-device-stats-label,
.run-details-alert-stats-label {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.run-details-device-stats-value,
.run-details-alert-stats-value {
  margin-top: 2px;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.run-details-device-stats-value.is-online {
  color: var(--success-text, #34d399);
}

.run-details-device-stats-value.is-offline {
  color: var(--error-text, #ef4444);
}

.run-details-alert-stats-value.fatal,
.run-details-alert-stats-value.critical {
  color: #ef4444;
}

.run-details-alert-stats-value.normal {
  color: #f59e0b;
}

.run-details-alert-stats-value.info {
  color: #3b82f6;
}

.run-details-stats-grid {
  display: flex;
  gap: 10px;
}

.run-details-stats-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.run-details-stats-top {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.run-details-stats-icon {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at 30% 20%, rgba(56, 189, 248, 0.35), transparent 60%),
    linear-gradient(135deg, rgba(56, 189, 248, 0.18), rgba(129, 140, 248, 0.22));
  color: var(--accent-primary);

  svg {
    width: 16px;
    height: 16px;
  }
}

.run-details-stats-icon--skills {
  background: radial-gradient(circle at 30% 20%, rgba(16, 185, 129, 0.4), transparent 60%),
    linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(45, 212, 191, 0.22));
}

.run-details-stats-icon--cot {
  background: radial-gradient(circle at 30% 20%, rgba(244, 114, 182, 0.4), transparent 60%),
    linear-gradient(135deg, rgba(236, 72, 153, 0.25), rgba(129, 140, 248, 0.24));
}

.run-details-stats-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.run-details-stats-label {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-secondary);
  text-align: center;
}

.run-details-stats-value {
  margin-top: 0;
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--text-primary);
  text-align: center;
}

.carousel-slide-wrap {
  flex: 0 0 auto;
  position: relative;
  overflow: hidden;
}

.carousel-vertical-track {
  display: flex;
  flex-direction: column;
  gap: 8px;
  
  height: 100%;
  min-height: 320px;
}

.carousel-card-wrap {
  flex: 0 0 auto;
}

.carousel-card-wrap .carousel-card {
  height: 100%;
  min-height: 0;
}

/* 运行详情设备模式下，设备卡片整体再压缩并保留少量间距
   设备：高度约 68px，间距 8px，对应步长约 76px */
.carousel-vertical-track--device .carousel-card-wrap {
  height: 68px;
  min-height: 68px;
}

/* 告警模式下保持相对更高的卡片高度，保证文案和按钮不挤压 */
.carousel-vertical-track--alert .carousel-card-wrap {
  height: 120px;
  min-height: 120px;
}

.carousel-empty {
  padding: 40px 20px;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.9rem;
}

.carousel-card {
  padding: 16px;
  border-radius: 12px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  position: relative;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;

  &.device-card {
    border-left: 4px solid var(--success-text, #34d399);
    flex-direction: row;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
  }

  &.device-card .carousel-card-icon {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    flex-shrink: 0;

    svg {
      width: 26px;
      height: 26px;
    }
  }

  &.device-card .carousel-card-main {
    flex: 1;
    min-width: 0;
  }

  &.device-card .carousel-card-label {
    font-size: 0.7rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    width: 100%;
    margin-bottom: -4px;
  }

  &.device-card .carousel-card-name {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  &.device-card .carousel-card-status {
    font-size: 0.8rem;
    font-weight: 500;

    &.online {
      color: var(--success-text, #34d399);
    }
    &.offline {
      color: var(--error-text, #ef4444);
    }
  }

  &.device-card .carousel-card-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;

    &.online {
      background: var(--success-text, #34d399);
    }
    &.offline {
      background: var(--error-text, #ef4444);
    }
  }

  &.alert-card .carousel-card-label {
    font-size: 0.7rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  &.alert-card .carousel-card-name {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  &.alert-card .carousel-alert-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  &.alert-card .carousel-alert-level {
    font-size: 0.75rem;
    padding: 2px 8px;
    border-radius: 4px;
    flex-shrink: 0;

    &.fatal, &.critical {
      background: rgba(239, 68, 68, 0.15);
      color: #ef4444;
    }
    &.normal {
      background: rgba(245, 158, 11, 0.15);
      color: #f59e0b;
    }
    &.info, &.warning {
      background: rgba(59, 130, 246, 0.15);
      color: #3b82f6;
    }
  }

  &.alert-card .carousel-card-desc {
    font-size: 0.8rem;
    color: var(--text-secondary);
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  &.alert-card .carousel-card-time {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-top: 4px;
  }

  &.alert-card .carousel-card-actions {
    display: flex;
    gap: 8px;
    margin-top: 0;
  }
}

.carousel-btn {
  padding: 6px 12px;
  font-size: 0.8rem;
  border-radius: 6px;
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  /* 告警卡片底部三个按钮等宽铺满 */
  .alert-card & {
    flex: 1;
    text-align: center;
  }

  &.primary {
    background: var(--accent-gradient);
    border-color: transparent;
    color: var(--button-text);

    &:hover {
      filter: brightness(1.08);
    }
  }
}

.carousel-card-menu {
  position: absolute;
  top: 10px;
  right: 10px;
  padding: 6px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  border-radius: 6px;
  transition: all 0.2s ease;

  svg {
    width: 16px;
    height: 16px;
  }

  &:hover {
    background: var(--bg-hover);
    color: var(--accent-primary);
  }
}

.carousel-dots {
  display: flex;
  justify-content: center;
  gap: 6px;
  padding: 14px 0 0;
  flex-shrink: 0;
}

.carousel-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  padding: 0;
  border: none;
  background: var(--border-primary);
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: var(--text-muted);
  }

  &.active {
    background: var(--accent-primary);
    transform: scale(1.2);
  }
}

.right-side-block {
  flex-shrink: 0;
  border-bottom: 1px solid var(--border-primary);

  &:last-child {
    border-bottom: none;
  }
}

.right-block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border-primary);
  background: rgba(0, 0, 0, 0.15);
}

.right-block-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
}

.right-block-menu-btn {
  padding: 6px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  border-radius: 6px;
  transition: all 0.2s ease;

  svg {
    width: 18px;
    height: 18px;
  }

  &:hover {
    background: var(--bg-hover);
    color: var(--accent-primary);
  }
}

.right-side-body .device-page,
.right-side-body .warning-page {
  padding: 16px;
  min-height: auto;
}

.right-side-body .device-header,
.right-side-body .warning-page .page-title {
  margin-bottom: 12px;
}

.right-side-body .page-title {
  font-size: 1rem;
}

.right-popup-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;
}

.right-popup-box {
  width: 100%;
  max-width: 900px;
  max-height: 90vh;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 16px;
  box-shadow: var(--shadow-xl);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.right-popup-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-primary);
  flex-shrink: 0;
}

.right-popup-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.right-popup-close {
  padding: 8px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  border-radius: 8px;
  transition: all 0.2s ease;

  svg {
    width: 20px;
    height: 20px;
  }

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
}

.right-popup-body {
  flex: 1;
  overflow: auto;
  min-height: 0;
  padding: 16px;
}

.right-popup-body .device-page,
.right-popup-body .warning-page {
  padding: 0;
}

.popup-enter-active,
.popup-leave-active {
  transition: opacity 0.25s ease;
}
.popup-enter-from,
.popup-leave-to {
  opacity: 0;
}
.popup-enter-active .right-popup-box,
.popup-leave-active .right-popup-box {
  transition: transform 0.25s ease;
}
.popup-enter-from .right-popup-box,
.popup-leave-to .right-popup-box {
  transform: scale(0.96);
}

.right-panel-toggle {
  position: fixed;
  top: 50%;
  right: 0;
  transform: translateY(-50%);
  z-index: 85;
  display: none;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 48px;
  padding: 0;
  color: var(--text-muted);
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-right: none;
  border-radius: 8px 0 0 8px;
  cursor: pointer;
  transition: all 0.2s ease;

  .run-details-icon {
    width: 22px;
    height: 22px;
  }

  &:hover,
  &.is-visible {
    color: var(--accent-primary);
    border-color: var(--accent-primary);
  }

  &.is-visible {
    display: flex;
  }

  @media (max-width: 1024px) {
    &.is-visible {
      display: flex;
    }
  }
}

.chat-header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 20px;
  z-index: 5;
  pointer-events: none;

  .chat-header-placeholder {
    flex: 1;
  }
}

.settings-btn {
  pointer-events: auto;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-family: var(--font-primary);
  font-size: 0.875rem;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;

  svg {
    width: 18px;
    height: 18px;
  }

  &:hover {
    background: var(--bg-hover);
    color: var(--accent-primary);
    border-color: var(--accent-primary);
  }
}

.settings-btn-text {
  @media (max-width: 480px) {
    display: none;
  }
}

.sidebar-toggle {
  display: none;
  position: absolute;
  top: 16px;
  left: 16px;
  z-index: 10;
  padding: 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-primary);

  svg {
    width: 20px;
    height: 20px;
  }

  @media (max-width: 768px) {
    display: block;
  }
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  width: 100%;
  min-height: 0;
  overflow: hidden;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px 0;
  width: 100%;
}

.welcome-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  animation: fadeIn 0.6s ease;
  max-width: 900px;
  width: 100%;
  margin: 0 auto;
  padding: 0 20px;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.welcome-icon {
  width: 80px;
  height: 80px;
  color: var(--accent-primary);
  margin-bottom: 24px;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.welcome-title {
  font-family: var(--font-display);
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.welcome-subtitle {
  font-size: 1rem;
  color: var(--text-secondary);
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 900px;
  width: 100%;
  margin: 0 auto;
  padding: 0 20px;
}

.message {
  display: flex;
  gap: 16px;
  animation: slideIn 0.3s ease;

  &.user {
    .message-avatar {
      background: var(--accent-gradient);
      color: var(--button-text);
    }

    .message-content {
      background: var(--user-message-bg);
    }
  }

  &.assistant {
    .message-avatar {
      background: var(--bg-tertiary);
      color: var(--accent-primary);
    }

    .message-content {
      background: var(--assistant-message-bg);
    }
  }
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-weight: 600;
  font-size: 0.875rem;

  svg {
    width: 24px;
    height: 24px;
  }
}

.message-content {
  flex: 1;
  padding: 16px 20px;
  border-radius: 16px;
  border-top-left-radius: 4px;
}

.message-text {
  font-size: 0.95rem;
  line-height: 1.7;
  color: var(--text-primary);

  :deep(.echarts-block) {
    margin: 12px 0;
    padding: 12px;
    border-radius: 10px;
    border: 1px solid var(--border-primary);
    background: var(--bg-tertiary);
  }

  :deep(.echarts-summary) {
    margin-bottom: 8px;
    font-size: 0.95rem;
    color: var(--text-secondary);
  }

  :deep(.echarts-chart) {
    width: 100%;
    height: 280px;
  }

  :deep(.echarts-details) {
    margin-top: 10px;
  }

  :deep(.echarts-details summary) {
    cursor: pointer;
    user-select: none;
    color: var(--text-secondary);
    font-size: 0.9rem;
  }

  :deep(pre) {
    margin: 12px 0;
    padding: 16px;
    background: var(--code-bg);
    border-radius: 8px;
    overflow-x: auto;

    code {
      background: none;
      padding: 0;
      font-size: 0.85rem;
    }
  }

  :deep(code) {
    font-family: var(--font-mono);
    background: var(--code-inline-bg);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.9em;
  }

  :deep(strong) {
    font-weight: 600;
  }
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding-top: 8px;

  span {
    width: 6px;
    height: 6px;
    background: var(--accent-primary);
    border-radius: 50%;
    animation: bounce 1.4s infinite ease-in-out;

    &:nth-child(1) { animation-delay: -0.32s; }
    &:nth-child(2) { animation-delay: -0.16s; }
  }
}

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.message-actions {
  display: flex;
  align-items: flex-start;
  padding-top: 8px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.message:hover .message-actions {
  opacity: 1;
}

.action-btn {
  padding: 6px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  border-radius: 6px;
  transition: all 0.2s ease;

  svg {
    width: 16px;
    height: 16px;
  }

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
}

.input-section {
  flex-shrink: 0;
  width: 100%;
  background: var(--bg-primary);
}

.input-container {
  max-width: 900px;
  width: 100%;
  margin: 0 auto;
  padding: 20px 20px 24px;
}


.thinking-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s ease;
  height: 32px;
  flex-shrink: 0;
  font-size: 0.85rem;

  svg {
    width: 16px;
    height: 16px;
    transition: all 0.2s ease;
  }

  .thinking-text {
    font-size: 0.85rem;
    font-weight: 500;
    transition: all 0.2s ease;
  }

  &:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border-color: var(--accent-primary);
  }

  &.active {
    background: #4d6bfe;
    color: white;
    border-color: #4d6bfe;
    box-shadow: 0 2px 6px rgba(77, 107, 254, 0.25);

    svg {
      fill: currentColor;
      stroke: currentColor;
    }

    .thinking-text {
      font-weight: 600;
    }
  }
}

.input-form {
  display: flex;
}

.input-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  background: var(--input-bg);
  border: 1px solid var(--input-border);
  border-radius: 24px;
  transition: all 0.2s ease;

  &:focus-within {
    border-color: var(--accent-primary);
    box-shadow: 0 0 0 3px var(--accent-glow);
  }
}

.chat-input {
  width: 100%;
  padding: 0;
  font-family: var(--font-primary);
  font-size: 1rem;
  color: var(--text-primary);
  background: transparent;
  border: none;
  outline: none;
  resize: none;
  min-height: 40px;
  max-height: 200px;
  line-height: 1.5;

  &::placeholder {
    color: var(--text-muted);
  }
}

.input-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.role-selector {
  position: relative;
  display: flex;
  align-items: center;
}

.role-select {
  appearance: none;
  -webkit-appearance: none;
  background-color: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid transparent;
  border-radius: 16px;
  padding: 0 28px 0 12px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  height: 32px;
  font-family: inherit;
  line-height: 32px;
  
  /* Custom arrow */
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23888' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 6px center;
  background-size: 14px;
}

.role-select:hover {
  background-color: var(--bg-hover);
  color: var(--text-primary);
}

.role-select:focus {
  outline: none;
  background-color: var(--bg-hover);
  border-color: var(--accent-primary);
}

.role-select option {
  background-color: var(--bg-secondary);
  color: var(--text-primary);
}

.footer-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 8px;
  background: var(--accent-gradient);
  border: none;
  border-radius: 50%;
  cursor: pointer;
  color: var(--button-text);
  transition: all 0.2s ease;

  svg {
    width: 18px;
    height: 18px;
  }

  &:hover:not(:disabled) {
    transform: scale(1.05);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.message-enter-active,
.message-leave-active {
  transition: all 0.3s ease;
}

.message-thinking {
  margin-bottom: 12px;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--border-color, rgba(0,0,0,0.05));
}

.thinking-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  cursor: pointer;
  background: rgba(0, 0, 0, 0.02);
  transition: background 0.2s;
  user-select: none;
}

.thinking-header:hover {
  background: rgba(0, 0, 0, 0.05);
}

.thinking-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9em;
  font-weight: 500;
  color: var(--text-secondary);
}

.thinking-icon svg {
  width: 16px;
  height: 16px;
  color: var(--accent-primary);
}

.thinking-toggle-icon svg {
  width: 16px;
  height: 16px;
  transition: transform 0.3s ease;
  color: var(--text-muted);
}

.message-thinking.collapsed .thinking-toggle-icon svg {
  transform: rotate(-90deg);
}

.thinking-body {
  padding: 12px 14px;
  font-size: 0.9em;
  color: var(--text-secondary);
  border-top: 1px solid var(--border-color, rgba(0,0,0,0.05));
  background: rgba(0, 0, 0, 0.02);
}

.message-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.message-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

.disclaimer-text {
  text-align: center;
  font-size: 0.75rem;
  color: var(--text-muted);
  opacity: 0.8;
  margin-top: 8px;
}

.echarts-block--iframes {
  margin: 8px 0;
}
.echarts-iframe-container {
  display: flex;
  flex-direction: row;
  gap: 12px;
  align-items: stretch;
}
.echarts-iframe-container--column{
  flex-direction: column;
}
.echarts-iframe {
  width: 100%;
  height: 280px;
  border: none;
  border-radius: 6px;
  background: transparent;
}
/* 上方描述更紧凑一些 */
.echarts-iframe--desc{
  height: 160px;
}
@media (max-width: 768px) {
  .echarts-iframe-container {
    flex-direction: column;
  }
  .echarts-iframe {
    height: 240px;
  }
  .echarts-iframe--desc{
    height: 140px;
  }
}
</style>

