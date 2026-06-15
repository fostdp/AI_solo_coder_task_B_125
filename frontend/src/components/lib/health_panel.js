/**
 * 木塔健康状态面板 - health_panel.js
 * 独立封装的健康状态展示组件，显示结构健康度、损伤情况、告警信息
 *
 * 功能：
 * 1. 结构健康度总览（环形进度条）
 * 2. 各楼层健康状态列表
 * 3. 模态参数变化曲线
 * 4. 损伤标记与说明
 * 5. 告警列表与统计
 *
 * 用法：
 * import { HealthPanel } from './health_panel'
 * const panel = new HealthPanel(container, options)
 * panel.updateData(data)
 */

/**
 * 健康等级配置
 */
const HEALTH_LEVELS = [
  { level: 'excellent', name: '优秀', minScore: 90, color: '#00ff88' },
  { level: 'good', name: '良好', minScore: 75, color: '#88ff00' },
  { level: 'fair', name: '一般', minScore: 60, color: '#ffcc00' },
  { level: 'poor', name: '较差', minScore: 40, color: '#ff6600' },
  { level: 'critical', name: '危险', minScore: 0, color: '#ff0000' }
]

/**
 * 健康面板类
 */
export class HealthPanel {
  /**
   * 构造函数
   * @param {HTMLElement} container - 容器DOM元素
   * @param {Object} options - 配置选项
   */
  constructor(container, options = {}) {
    this.container = container
    this.options = {
      theme: 'dark',
      showChart: true,
      showAlerts: true,
      maxAlertCount: 5,
      ...options
    }

    this.healthScore = 85
    this.floorHealth = [
      { floor: 1, score: 92, status: 'excellent' },
      { floor: 2, score: 88, status: 'good' },
      { floor: 3, score: 85, status: 'good' },
      { floor: 4, score: 82, status: 'good' },
      { floor: 5, score: 78, status: 'good' }
    ]
    this.naturalFrequencies = [1.2, 2.8, 4.5, 6.2, 8.1]
    this.frequencyHistory = []
    this.alerts = []

    this._render()
    this._setupStyles()
  }

  /**
   * 注入样式
   */
  _setupStyles() {
    if (document.getElementById('health-panel-styles')) return

    const style = document.createElement('style')
    style.id = 'health-panel-styles'
    style.textContent = `
      .health-panel {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        color: #fff;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        backdrop-filter: blur(10px);
      }

      .health-panel-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        padding-bottom: 12px;
        border-bottom: 1px solid rgba(255,255,255,0.1);
      }

      .health-panel-title {
        font-size: 18px;
        font-weight: 600;
        margin: 0;
      }

      .health-panel-status {
        font-size: 12px;
        padding: 4px 10px;
        border-radius: 12px;
        background: rgba(0, 255, 136, 0.15);
        color: #00ff88;
      }

      .health-score-section {
        display: flex;
        gap: 20px;
        margin-bottom: 20px;
      }

      .health-gauge-container {
        flex: 0 0 140px;
        display: flex;
        flex-direction: column;
        align-items: center;
      }

      .health-gauge {
        position: relative;
        width: 120px;
        height: 120px;
      }

      .health-gauge svg {
        transform: rotate(-90deg);
      }

      .health-gauge-bg {
        fill: none;
        stroke: rgba(255,255,255,0.1);
        stroke-width: 10;
      }

      .health-gauge-fill {
        fill: none;
        stroke-width: 10;
        stroke-linecap: round;
        transition: stroke-dashoffset 0.5s ease, stroke 0.5s ease;
      }

      .health-score-value {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 32px;
        font-weight: 700;
      }

      .health-score-label {
        font-size: 12px;
        color: #aaa;
        margin-top: 8px;
      }

      .health-stats {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 12px;
      }

      .stat-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .stat-label {
        font-size: 13px;
        color: #aaa;
      }

      .stat-value {
        font-size: 14px;
        font-weight: 600;
      }

      .stat-bar {
        height: 6px;
        background: rgba(255,255,255,0.1);
        border-radius: 3px;
        overflow: hidden;
        margin-top: 4px;
      }

      .stat-bar-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.5s ease;
      }

      .floor-health-section {
        margin-bottom: 20px;
      }

      .section-title {
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 12px;
        color: #ddd;
      }

      .floor-health-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .floor-health-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 12px;
        background: rgba(255,255,255,0.05);
        border-radius: 8px;
        transition: background 0.2s;
      }

      .floor-health-item:hover {
        background: rgba(255,255,255,0.08);
      }

      .floor-number {
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(255,255,255,0.1);
        border-radius: 50%;
        font-size: 14px;
        font-weight: 600;
        flex-shrink: 0;
      }

      .floor-info {
        flex: 1;
      }

      .floor-info-top {
        display: flex;
        justify-content: space-between;
        margin-bottom: 4px;
      }

      .floor-name {
        font-size: 13px;
        font-weight: 500;
      }

      .floor-score {
        font-size: 13px;
        font-weight: 600;
      }

      .floor-bar {
        height: 4px;
        background: rgba(255,255,255,0.1);
        border-radius: 2px;
        overflow: hidden;
      }

      .floor-bar-fill {
        height: 100%;
        border-radius: 2px;
        transition: width 0.5s ease;
      }

      .alerts-section {
        margin-top: 20px;
      }

      .alert-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .alert-item {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        padding: 10px 12px;
        background: rgba(255,0,0,0.08);
        border-left: 3px solid #ff4444;
        border-radius: 6px;
        font-size: 12px;
      }

      .alert-item.warning {
        background: rgba(255,170,0,0.08);
        border-left-color: #ffaa00;
      }

      .alert-item.info {
        background: rgba(0,150,255,0.08);
        border-left-color: #0096ff;
      }

      .alert-icon {
        width: 20px;
        height: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(255,68,68,0.2);
        border-radius: 50%;
        font-size: 12px;
        flex-shrink: 0;
      }

      .alert-item.warning .alert-icon {
        background: rgba(255,170,0,0.2);
      }

      .alert-content {
        flex: 1;
      }

      .alert-title {
        font-weight: 600;
        margin-bottom: 2px;
      }

      .alert-time {
        font-size: 11px;
        color: #888;
      }

      .empty-alerts {
        text-align: center;
        padding: 20px;
        color: #666;
        font-size: 13px;
      }

      .frequency-chart {
        width: 100%;
        height: 80px;
        margin-top: 10px;
      }
    `
    document.head.appendChild(style)
  }

  /**
   * 渲染面板
   */
  _render() {
    this.container.innerHTML = ''

    const panel = document.createElement('div')
    panel.className = 'health-panel'

    const level = this._getHealthLevel(this.healthScore)

    panel.innerHTML = `
      <div class="health-panel-header">
        <h3 class="health-panel-title">结构健康状态</h3>
        <span class="health-panel-status" style="background: ${level.color}22; color: ${level.color}">
          ${level.name}
        </span>
      </div>

      <div class="health-score-section">
        <div class="health-gauge-container">
          <div class="health-gauge">
            <svg width="120" height="120" viewBox="0 0 120 120">
              <circle class="health-gauge-bg" cx="60" cy="60" r="50" />
              <circle class="health-gauge-fill" 
                      cx="60" cy="60" r="50" 
                      stroke="${level.color}"
                      stroke-dasharray="314"
                      stroke-dashoffset="${314 * (1 - this.healthScore / 100)}" />
            </svg>
            <div class="health-score-value" style="color: ${level.color}">
              ${Math.round(this.healthScore)}
            </div>
          </div>
          <span class="health-score-label">健康指数</span>
        </div>

        <div class="health-stats">
          <div>
            <div class="stat-row">
              <span class="stat-label">一阶频率</span>
              <span class="stat-value">${this.naturalFrequencies[0].toFixed(2)} Hz</span>
            </div>
            <div class="stat-bar">
              <div class="stat-bar-fill" style="width: 85%; background: #00ff88;"></div>
            </div>
          </div>
          <div>
            <div class="stat-row">
              <span class="stat-label">最大层间位移</span>
              <span class="stat-value">1/850</span>
            </div>
            <div class="stat-bar">
              <div class="stat-bar-fill" style="width: 60%; background: #ffcc00;"></div>
            </div>
          </div>
          <div>
            <div class="stat-row">
              <span class="stat-label">木材含水率</span>
              <span class="stat-value">12.5%</span>
            </div>
            <div class="stat-bar">
              <div class="stat-bar-fill" style="width: 45%; background: #88ff00;"></div>
            </div>
          </div>
        </div>
      </div>

      <div class="floor-health-section">
        <div class="section-title">各楼层健康状态</div>
        <div class="floor-health-list">
          ${this.floorHealth.map(floor => {
            const floorLevel = this._getHealthLevel(floor.score)
            return `
              <div class="floor-health-item">
                <div class="floor-number" style="background: ${floorLevel.color}22; color: ${floorLevel.color}">
                  ${floor.floor}
                </div>
                <div class="floor-info">
                  <div class="floor-info-top">
                    <span class="floor-name">第${floor.floor}层</span>
                    <span class="floor-score" style="color: ${floorLevel.color}">${floor.score}%</span>
                  </div>
                  <div class="floor-bar">
                    <div class="floor-bar-fill" 
                         style="width: ${floor.score}%; background: ${floorLevel.color};"></div>
                  </div>
                </div>
              </div>
            `
          }).join('')}
        </div>
      </div>

      <div class="alerts-section">
        <div class="section-title">最近告警</div>
        <div class="alert-list" id="alert-list">
          ${this._renderAlerts()}
        </div>
      </div>
    `

    this.container.appendChild(panel)
    this._panelElement = panel
    this._alertListEl = panel.querySelector('#alert-list')
  }

  /**
   * 渲染告警列表
   */
  _renderAlerts() {
    if (!this.alerts || this.alerts.length === 0) {
      return '<div class="empty-alerts">暂无告警信息</div>'
    }

    return this.alerts.slice(0, this.options.maxAlertCount).map(alert => `
      <div class="alert-item ${alert.severity}">
        <div class="alert-icon">
          ${alert.severity === 'critical' ? '!' : alert.severity === 'warning' ? '⚠' : 'ℹ'}
        </div>
        <div class="alert-content">
          <div class="alert-title">${alert.title}</div>
          <div style="font-size: 11px; color: #aaa; margin-bottom: 2px;">
            第${alert.floor}层 · ${alert.type}
          </div>
          <div class="alert-time">${alert.time}</div>
        </div>
      </div>
    `).join('')
  }

  /**
   * 根据分数获取健康等级
   */
  _getHealthLevel(score) {
    for (const level of HEALTH_LEVELS) {
      if (score >= level.minScore) {
        return level
      }
    }
    return HEALTH_LEVELS[HEALTH_LEVELS.length - 1]
  }

  /**
   * 更新健康分数
   * @param {number} score - 健康分数 0-100
   */
  setHealthScore(score) {
    this.healthScore = Math.max(0, Math.min(100, score))
    this._render()
    return this
  }

  /**
   * 更新楼层健康状态
   * @param {Array} floorData - 楼层健康数据
   */
  setFloorHealth(floorData) {
    if (Array.isArray(floorData) && floorData.length > 0) {
      this.floorHealth = floorData.map((d, i) => ({
        floor: d.floor || i + 1,
        score: d.score || d.healthScore || 80,
        status: d.status || this._getHealthLevel(d.score || d.healthScore || 80).level
      }))
      this._render()
    }
    return this
  }

  /**
   * 更新固有频率
   * @param {Array} frequencies - 频率数组
   */
  setFrequencies(frequencies) {
    if (Array.isArray(frequencies)) {
      this.naturalFrequencies = frequencies
      this._render()
    }
    return this
  }

  /**
   * 添加告警
   * @param {Object} alert - 告警数据
   */
  addAlert(alert) {
    this.alerts.unshift({
      id: Date.now(),
      title: alert.title || alert.alert_type || '告警',
      floor: alert.floor || 1,
      type: alert.type || alert.alert_type || 'unknown',
      severity: alert.severity || 'warning',
      time: alert.time || alert.timestamp || new Date().toLocaleTimeString(),
      ...alert
    })

    if (this.alerts.length > 20) {
      this.alerts = this.alerts.slice(0, 20)
    }

    if (this._alertListEl) {
      this._alertListEl.innerHTML = this._renderAlerts()
    }
    return this
  }

  /**
   * 批量设置告警
   * @param {Array} alerts - 告警列表
   */
  setAlerts(alerts) {
    this.alerts = Array.isArray(alerts) ? alerts : []
    if (this._alertListEl) {
      this._alertListEl.innerHTML = this._renderAlerts()
    }
    return this
  }

  /**
   * 更新所有数据
   * @param {Object} data - 完整数据
   */
  updateData(data) {
    if (data.healthScore !== undefined) {
      this.healthScore = data.healthScore
    }
    if (data.floorHealth) {
      this.floorHealth = data.floorHealth
    }
    if (data.frequencies) {
      this.naturalFrequencies = data.frequencies
    }
    if (data.alerts) {
      this.alerts = data.alerts
    }
    this._render()
    return this
  }

  /**
   * 获取当前数据
   */
  getData() {
    return {
      healthScore: this.healthScore,
      floorHealth: [...this.floorHealth],
      frequencies: [...this.naturalFrequencies],
      alerts: [...this.alerts]
    }
  }

  /**
   * 销毁面板
   */
  destroy() {
    if (this._panelElement) {
      this._panelElement.remove()
      this._panelElement = null
    }
  }
}

/**
 * 简化的结构健康评估器
 */
export class StructuralHealthAssessor {
  constructor() {
    this.baselineFrequencies = [1.2, 2.8, 4.5, 6.2, 8.1]
    this.thresholds = {
      frequencyDropWarning: 0.03,
      frequencyDropCritical: 0.05,
      driftWarning: 1 / 500,
      driftCritical: 1 / 250,
      moistureWarning: 18,
      moistureCritical: 25
    }
  }

  /**
   * 计算整体健康分数
   */
  calculateHealthScore(monitoringData) {
    let score = 100
    const deductions = []

    if (monitoringData.frequencies) {
      const freqChanges = monitoringData.frequencies.map((f, i) =>
        Math.abs(f - this.baselineFrequencies[i]) / this.baselineFrequencies[i]
      )
      const maxFreqChange = Math.max(...freqChanges)

      if (maxFreqChange > this.thresholds.frequencyDropCritical) {
        deductions.push({ score: 30, reason: '频率异常下降' })
      } else if (maxFreqChange > this.thresholds.frequencyDropWarning) {
        deductions.push({ score: 10, reason: '频率轻微下降' })
      }
    }

    if (monitoringData.maxDriftRatio) {
      if (monitoringData.maxDriftRatio > this.thresholds.driftCritical) {
        deductions.push({ score: 25, reason: '层间位移角超限' })
      } else if (monitoringData.maxDriftRatio > this.thresholds.driftWarning) {
        deductions.push({ score: 8, reason: '层间位移角偏大' })
      }
    }

    if (monitoringData.maxMoisture) {
      if (monitoringData.maxMoisture > this.thresholds.moistureCritical) {
        deductions.push({ score: 15, reason: '含水率过高' })
      } else if (monitoringData.maxMoisture > this.thresholds.moistureWarning) {
        deductions.push({ score: 5, reason: '含水率偏高' })
      }
    }

    const totalDeduction = Math.min(deductions.reduce((sum, d) => sum + d.score, 0), 80)
    score = Math.max(20, 100 - totalDeduction)

    return {
      score,
      level: score >= 90 ? 'excellent' : score >= 75 ? 'good' : score >= 60 ? 'fair' : score >= 40 ? 'poor' : 'critical',
      deductions
    }
  }

  /**
   * 计算各楼层健康分数
   */
  calculateFloorHealth(floorData) {
    return floorData.map(floor => {
      let score = 95

      if (floor.driftRatio && floor.driftRatio > this.thresholds.driftWarning) {
        const excess = (floor.driftRatio - this.thresholds.driftWarning) /
          (this.thresholds.driftCritical - this.thresholds.driftWarning)
        score -= Math.min(30, excess * 30)
      }

      if (floor.acceleration && floor.acceleration > 0.05) {
        score -= (floor.acceleration - 0.05) * 200
      }

      score = Math.max(20, Math.min(100, score))

      return {
        floor: floor.floor,
        score: Math.round(score),
        driftRatio: floor.driftRatio,
        acceleration: floor.acceleration
      }
    })
  }
}

export default HealthPanel
