/**
 * 应县木塔三维渲染引擎 - pagoda_3d.js
 * 独立封装的木塔Three.js渲染模块，可在任何前端项目中直接引用
 *
 * 功能：
 * 1. 木塔三维模型构建（5层楼阁式塔）
 * 2. LOD多细节层次自动切换
 * 3. 视锥体剔除与遮挡优化
 * 4. 模态振动动画
 * 5. 损伤标记与传感器显示
 * 6. 性能监控面板
 *
 * 用法：
 * import { Pagoda3DRenderer } from './pagoda_3d'
 * const renderer = new Pagoda3DRenderer(container, options)
 * renderer.start()
 */

import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { LOD } from 'three'

/**
 * 木材材质配置
 */
const TIMBER_MATERIALS = {
  column: new THREE.MeshStandardMaterial({
    color: 0x8B4513,
    roughness: 0.8,
    metalness: 0.1
  }),
  beam: new THREE.MeshStandardMaterial({
    color: 0xCD853F,
    roughness: 0.7,
    metalness: 0.05
  }),
  bracket: new THREE.MeshStandardMaterial({
    color: 0xD2691E,
    roughness: 0.75,
    metalness: 0.08
  }),
  roof: new THREE.MeshStandardMaterial({
    color: 0x2F4F4F,
    roughness: 0.9,
    metalness: 0.0
  }),
  base: new THREE.MeshStandardMaterial({
    color: 0x696969,
    roughness: 0.95,
    metalness: 0.0
  }),
  sensor: new THREE.MeshStandardMaterial({
    color: 0x00ff00,
    emissive: 0x00ff00,
    emissiveIntensity: 0.5
  }),
  damage: new THREE.MeshStandardMaterial({
    color: 0xff0000,
    emissive: 0xff0000,
    emissiveIntensity: 0.8
  })
}

/**
 * 楼层高度配置（米）
 */
const FLOOR_HEIGHTS = [6.59, 5.49, 4.99, 4.59, 4.09]
const COLUMN_COUNTS = { high: 24, medium: 16, low: 8 }
const BEAM_COUNTS = { high: 8, medium: 6, low: 4 }
const BRACKET_COUNTS = { high: 24, medium: 12, low: 0 }
const LOD_DISTANCES = { high: 30, medium: 60, low: 100 }
const TOTAL_HEIGHT = 25.75
const BASE_RADIUS = 12.0

/**
 * 木塔三维渲染器类
 */
export class Pagoda3DRenderer {
  /**
   * 构造函数
   * @param {HTMLElement} container - 容器DOM元素
   * @param {Object} options - 配置选项
   */
  constructor(container, options = {}) {
    this.container = container
    this.options = {
      enableLOD: true,
      enableOcclusionCulling: true,
      enablePerformancePanel: true,
      showSensors: true,
      showDamage: false,
      showLabels: false,
      backgroundColor: 0x1a1a2e,
      ...options
    }

    this.scene = null
    this.camera = null
    this.renderer = null
    this.controls = null
    this.animationId = null
    this.floorGroups = []
    this.sensorMarkers = []
    this.damageMarkers = []
    this.base = null
    this.time = 0
    this.vibrationMode = 1
    this.vibrationAmplitude = 0.5
    this.animationRunning = false
    this.performanceInfo = {
      fps: 0,
      triangles: 0,
      drawCalls: 0,
      lodLevel: 'high'
    }
    this._frameCount = 0
    this._lastFpsUpdate = 0
    this._frustum = new THREE.Frustum()
    this._projScreenMatrix = new THREE.Matrix4()
  }

  /**
   * 初始化场景
   */
  init() {
    const width = this.container.clientWidth
    const height = this.container.clientHeight

    // 场景
    this.scene = new THREE.Scene()
    this.scene.background = new THREE.Color(this.options.backgroundColor)
    this.scene.fog = new THREE.Fog(this.options.backgroundColor, 50, 150)

    // 相机
    this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000)
    this.camera.position.set(20, 15, 25)

    // 渲染器
    this.renderer = new THREE.WebGLRenderer({ antialias: true })
    this.renderer.setSize(width, height)
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.shadowMap.enabled = true
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap
    this.container.appendChild(this.renderer.domElement)

    // 控制器
    this.controls = new OrbitControls(this.camera, this.renderer.domElement)
    this.controls.enableDamping = true
    this.controls.dampingFactor = 0.05
    this.controls.target.set(0, TOTAL_HEIGHT / 2, 0)
    this.controls.minDistance = 5
    this.controls.maxDistance = 100
    this.controls.maxPolarAngle = Math.PI / 2.1

    // 光照
    this._setupLights()

    // 台基
    this._createBase()

    // 楼层
    this._createAllFloors()

    // 传感器标记
    if (this.options.showSensors) {
      this._createSensorMarkers()
    }

    // 损伤标记
    if (this.options.showDamage) {
      this._createDamageMarkers()
    }

    // 性能面板
    if (this.options.enablePerformancePanel) {
      this._createPerformancePanel()
    }

    // 窗口大小变化
    window.addEventListener('resize', () => this._onResize())

    return this
  }

  /**
   * 设置光照
   */
  _setupLights() {
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4)
    this.scene.add(ambientLight)

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
    directionalLight.position.set(20, 30, 15)
    directionalLight.castShadow = true
    directionalLight.shadow.mapSize.width = 2048
    directionalLight.shadow.mapSize.height = 2048
    directionalLight.shadow.camera.near = 0.5
    directionalLight.shadow.camera.far = 100
    directionalLight.shadow.camera.left = -20
    directionalLight.shadow.camera.right = 20
    directionalLight.shadow.camera.top = 20
    directionalLight.shadow.camera.bottom = -20
    this.scene.add(directionalLight)

    const fillLight = new THREE.DirectionalLight(0x87ceeb, 0.3)
    fillLight.position.set(-15, 10, -10)
    this.scene.add(fillLight)

    const pointLight = new THREE.PointLight(0xffd700, 0.5, 50)
    pointLight.position.set(0, TOTAL_HEIGHT + 2, 0)
    this.scene.add(pointLight)
  }

  /**
   * 创建台基
   */
  _createBase() {
    const baseGroup = new THREE.Group()

    const baseGeo = new THREE.CylinderGeometry(BASE_RADIUS, BASE_RADIUS + 1, 2.0, 32)
    const baseMesh = new THREE.Mesh(baseGeo, TIMBER_MATERIALS.base)
    baseMesh.position.y = 1.0
    baseMesh.receiveShadow = true
    baseGroup.add(baseMesh)

    const platformGeo = new THREE.CylinderGeometry(BASE_RADIUS - 0.5, BASE_RADIUS, 0.5, 32)
    const platformMesh = new THREE.Mesh(platformGeo, TIMBER_MATERIALS.base)
    platformMesh.position.y = 2.25
    baseGroup.add(platformMesh)

    this.scene.add(baseGroup)
    this.base = baseGroup
  }

  /**
   * 创建所有楼层
   */
  _createAllFloors() {
    let cumulativeHeight = 2.5

    for (let i = 0; i < 5; i++) {
      const floorHeight = FLOOR_HEIGHTS[i]
      const floorRadius = BASE_RADIUS - i * 0.8

      if (this.options.enableLOD) {
        const lod = this._createFloorLOD(i + 1, floorHeight, floorRadius, cumulativeHeight)
        lod.position.y = cumulativeHeight
        this.scene.add(lod)
        this.floorGroups.push(lod)
      } else {
        const floorGroup = this._createFloor(i + 1, 'high', floorHeight, floorRadius)
        floorGroup.position.y = cumulativeHeight
        this.scene.add(floorGroup)
        this.floorGroups.push(floorGroup)
      }

      cumulativeHeight += floorHeight
    }
  }

  /**
   * 创建单层LOD
   */
  _createFloorLOD(floor, height, radius, baseHeight) {
    const lod = new LOD()

    lod.addLevel(
      this._createFloor(floor, 'high', height, radius),
      0
    )
    lod.addLevel(
      this._createFloor(floor, 'medium', height, radius),
      LOD_DISTANCES.high
    )
    lod.addLevel(
      this._createFloor(floor, 'low', height, radius),
      LOD_DISTANCES.medium
    )

    lod.userData.floor = floor
    lod.userData.height = height
    lod.userData.baseHeight = baseHeight

    return lod
  }

  /**
   * 创建单层模型
   */
  _createFloor(floor, detailLevel, height, radius) {
    const group = new THREE.Group()
    group.userData.detailLevel = detailLevel
    group.userData.floor = floor

    const columnCount = COLUMN_COUNTS[detailLevel]
    const beamCount = BEAM_COUNTS[detailLevel]
    const bracketCount = BRACKET_COUNTS[detailLevel]
    const segments = detailLevel === 'high' ? 8 : detailLevel === 'medium' ? 6 : 4

    const columnRadius = 0.3 - (floor - 1) * 0.02

    for (let i = 0; i < columnCount; i++) {
      const angle = (i / columnCount) * Math.PI * 2
      const x = Math.cos(angle) * (radius - 0.5)
      const z = Math.sin(angle) * (radius - 0.5)

      const columnGeo = new THREE.CylinderGeometry(
        columnRadius * 0.9, columnRadius, height, segments
      )
      const column = new THREE.Mesh(columnGeo, TIMBER_MATERIALS.column)
      column.position.set(x, height / 2, z)
      column.castShadow = true
      column.receiveShadow = true
      group.add(column)
    }

    for (let i = 0; i < beamCount; i++) {
      const angle = (i / beamCount) * Math.PI
      const beamLength = (radius - 1) * 2
      const beamGeo = new THREE.BoxGeometry(beamLength, 0.4, 0.3)

      const topBeam = new THREE.Mesh(beamGeo, TIMBER_MATERIALS.beam)
      topBeam.position.y = height - 0.5
      topBeam.rotation.y = angle
      topBeam.castShadow = true
      group.add(topBeam)

      const midBeam = new THREE.Mesh(beamGeo, TIMBER_MATERIALS.beam)
      midBeam.position.y = height / 2
      midBeam.rotation.y = angle + Math.PI / beamCount / 2
      midBeam.scale.set(0.8, 1, 1)
      midBeam.castShadow = true
      group.add(midBeam)
    }

    if (bracketCount > 0) {
      for (let i = 0; i < bracketCount; i++) {
        const angle = (i / bracketCount) * Math.PI * 2
        const bracketGroup = this._createBracket(detailLevel)
        bracketGroup.position.set(
          Math.cos(angle) * (radius - 1.2),
          height - 0.3,
          Math.sin(angle) * (radius - 1.2)
        )
        bracketGroup.rotation.y = angle + Math.PI / 2
        group.add(bracketGroup)
      }
    }

    const roofHeight = 1.5 + floor * 0.1
    const roofGeo = new THREE.ConeGeometry(radius + 0.5, roofHeight, 32)
    const roof = new THREE.Mesh(roofGeo, TIMBER_MATERIALS.roof)
    roof.position.y = height + roofHeight / 2 - 0.5
    roof.castShadow = true
    group.add(roof)

    const floorPlateGeo = new THREE.CylinderGeometry(radius, radius, 0.2, 32)
    const floorPlate = new THREE.Mesh(floorPlateGeo, TIMBER_MATERIALS.beam)
    floorPlate.position.y = -0.1
    floorPlate.receiveShadow = true
    group.add(floorPlate)

    if (detailLevel !== 'low') {
      const railingCount = detailLevel === 'high' ? 32 : 16
      for (let i = 0; i < railingCount; i++) {
        const angle = (i / railingCount) * Math.PI * 2
        const r = radius - 0.8

        const railPostGeo = new THREE.CylinderGeometry(0.05, 0.05, 1.0, 4)
        const railPost = new THREE.Mesh(railPostGeo, TIMBER_MATERIALS.bracket)
        railPost.position.set(Math.cos(angle) * r, 0.5, Math.sin(angle) * r)
        group.add(railPost)
      }
    }

    return group
  }

  /**
   * 创建斗拱组件
   */
  _createBracket(detailLevel) {
    const group = new THREE.Group()
    const scale = detailLevel === 'high' ? 1.0 : 0.9

    const armGeo = new THREE.BoxGeometry(0.8, 0.15, 0.25)
    const arm1 = new THREE.Mesh(armGeo, TIMBER_MATERIALS.bracket)
    arm1.position.y = 0.1
    group.add(arm1)

    const arm2 = new THREE.Mesh(armGeo, TIMBER_MATERIALS.bracket)
    arm2.rotation.y = Math.PI / 2
    arm2.position.y = 0.25
    group.add(arm2)

    const blockGeo = new THREE.BoxGeometry(0.3, 0.3, 0.3)
    const block = new THREE.Mesh(blockGeo, TIMBER_MATERIALS.bracket)
    block.position.y = -0.1
    group.add(block)

    group.scale.setScalar(scale)
    return group
  }

  /**
   * 创建传感器标记
   */
  _createSensorMarkers() {
    for (let floor = 1; floor <= 5; floor++) {
      const floorY = FLOOR_HEIGHTS.slice(0, floor - 1).reduce((a, b) => a + b, 0) + 2.5
      const floorHeight = FLOOR_HEIGHTS[floor - 1]

      const sensorPositions = [
        { angle: 0, y: floorHeight * 0.3 },
        { angle: Math.PI / 2, y: floorHeight * 0.5 },
        { angle: Math.PI, y: floorHeight * 0.7 },
        { angle: Math.PI * 1.5, y: floorHeight * 0.5 }
      ]

      sensorPositions.forEach((pos, idx) => {
        const radius = BASE_RADIUS - (floor - 1) * 0.8 - 0.5
        const sensorGeo = new THREE.SphereGeometry(0.15, 12, 12)
        const sensor = new THREE.Mesh(sensorGeo, TIMBER_MATERIALS.sensor)
        sensor.position.set(
          Math.cos(pos.angle) * radius,
          floorY + pos.y,
          Math.sin(pos.angle) * radius
        )
        sensor.userData.floor = floor
        sensor.userData.sensorIndex = idx
        sensor.userData.baseY = floorY + pos.y

        this.scene.add(sensor)
        this.sensorMarkers.push(sensor)
      })
    }
  }

  /**
   * 创建损伤标记
   */
  _createDamageMarkers() {
    for (let floor = 1; floor <= 5; floor++) {
      const floorY = FLOOR_HEIGHTS.slice(0, floor - 1).reduce((a, b) => a + b, 0) + 2.5
      const radius = BASE_RADIUS - (floor - 1) * 0.8 - 1

      const damageGeo = new THREE.SphereGeometry(0.3, 16, 16)
      const damage = new THREE.Mesh(damageGeo, TIMBER_MATERIALS.damage)
      damage.position.set(radius * 0.5, floorY + FLOOR_HEIGHTS[floor - 1] / 2, 0)
      damage.visible = false
      damage.userData.floor = floor
      damage.userData.baseScale = 1

      const pulseGeo = new THREE.RingGeometry(0.3, 0.5, 32)
      const pulseMat = new THREE.MeshBasicMaterial({
        color: 0xff0000,
        transparent: true,
        opacity: 0.5,
        side: THREE.DoubleSide
      })
      const pulse = new THREE.Mesh(pulseGeo, pulseMat)
      pulse.rotation.x = -Math.PI / 2
      pulse.position.copy(damage.position)
      pulse.visible = false
      pulse.userData.floor = floor

      this.scene.add(damage)
      this.scene.add(pulse)
      this.damageMarkers.push({ marker: damage, pulse })
    }
  }

  /**
   * 创建性能面板
   */
  _createPerformancePanel() {
    const panel = document.createElement('div')
    panel.className = 'pagoda3d-perf-panel'
    panel.style.cssText = `
      position: absolute;
      top: 16px;
      right: 16px;
      background: rgba(0,0,0,0.6);
      backdrop-filter: blur(10px);
      border-radius: 8px;
      padding: 12px 16px;
      z-index: 10;
      min-width: 160px;
      font-family: monospace;
      font-size: 12px;
      color: #fff;
    `
    panel.innerHTML = `
      <div style="font-weight:600;margin-bottom:8px;border-bottom:1px solid rgba(255,255,255,0.2);padding-bottom:6px;">
        性能监控
      </div>
      <div><span style="color:#aaa">FPS:</span> <span id="perf-fps" style="color:#0f0;font-weight:600">60</span></div>
      <div><span style="color:#aaa">三角形:</span> <span id="perf-tris">0</span></div>
      <div><span style="color:#aaa">绘制调用:</span> <span id="perf-draw">0</span></div>
      <div><span style="color:#aaa">LOD级别:</span> <span id="perf-lod" style="color:#0ff">高细节</span></div>
    `
    this.container.appendChild(panel)
    this._perfPanel = panel
    this._perfFpsEl = panel.querySelector('#perf-fps')
    this._perfTrisEl = panel.querySelector('#perf-tris')
    this._perfDrawEl = panel.querySelector('#perf-draw')
    this._perfLodEl = panel.querySelector('#perf-lod')
  }

  /**
   * 更新视锥体剔除
   */
  _updateOcclusionCulling() {
    if (!this.options.enableOcclusionCulling) return

    this._projScreenMatrix.multiplyMatrices(
      this.camera.projectionMatrix,
      this.camera.matrixWorldInverse
    )
    this._frustum.setFromProjectionMatrix(this._projScreenMatrix)

    this.floorGroups.forEach(floorObj => {
      if (floorObj.isLOD) {
        const sphere = new THREE.Sphere(floorObj.position, 20)
        floorObj.visible = this._frustum.intersectsSphere(sphere)
      }
    })
  }

  /**
   * 更新性能指标
   */
  _updatePerformance() {
    const info = this.renderer.info
    const now = performance.now()

    this._frameCount++
    if (now - this._lastFpsUpdate >= 1000) {
      this.performanceInfo.fps = Math.round(
        (this._frameCount * 1000) / (now - this._lastFpsUpdate)
      )
      this._frameCount = 0
      this._lastFpsUpdate = now

      if (this._perfFpsEl) {
        this._perfFpsEl.textContent = this.performanceInfo.fps
        this._perfFpsEl.style.color =
          this.performanceInfo.fps >= 50 ? '#0f0' :
          this.performanceInfo.fps >= 30 ? '#fa0' : '#f44'
      }
      if (this._perfTrisEl) {
        this._perfTrisEl.textContent = info.render.triangles.toLocaleString()
      }
      if (this._perfDrawEl) {
        this._perfDrawEl.textContent = info.render.calls
      }
    }

    const distance = this.camera.position.distanceTo(
      new THREE.Vector3(0, TOTAL_HEIGHT / 2, 0)
    )
    this.performanceInfo.lodLevel =
      distance < LOD_DISTANCES.high ? 'high' :
      distance < LOD_DISTANCES.medium ? 'medium' : 'low'

    if (this._perfLodEl) {
      const names = { high: '高细节', medium: '中细节', low: '低细节' }
      const colors = { high: '#0ff', medium: '#fa0', low: '#f60' }
      this._perfLodEl.textContent = names[this.performanceInfo.lodLevel]
      this._perfLodEl.style.color = colors[this.performanceInfo.lodLevel]
    }
  }

  /**
   * 更新振动动画
   */
  _updateVibration() {
    if (!this.animationRunning) return

    const omega = this.vibrationMode * 0.5 * Math.PI * 2
    const amp = this.vibrationAmplitude * 0.1

    this.floorGroups.forEach((floorObj, index) => {
      const floor = index + 1
      let group = floorObj

      if (floorObj.isLOD) {
        floorObj.levels.forEach(level => {
          level.object.position.x = Math.sin(omega * this.time + floor * 0.5) * amp * floor
          level.object.position.z = Math.cos(omega * this.time + floor * 0.3) * amp * floor * 0.5
          level.object.rotation.y = Math.sin(omega * 0.7 * this.time) * 0.02 * floor
        })
      } else {
        group.position.x = Math.sin(omega * this.time + floor * 0.5) * amp * floor
        group.position.z = Math.cos(omega * this.time + floor * 0.3) * amp * floor * 0.5
        group.rotation.y = Math.sin(omega * 0.7 * this.time) * 0.02 * floor
      }
    })

    this.sensorMarkers.forEach(sensor => {
      const scale = 1 + Math.sin(this.time * 4 + sensor.userData.sensorIndex) * 0.2
      sensor.scale.setScalar(scale)
    })

    this.damageMarkers.forEach(({ marker, pulse }) => {
      if (marker.visible) {
        const scale = 1 + Math.sin(this.time * 3) * 0.3
        marker.scale.setScalar(scale * marker.userData.baseScale)
        pulse.scale.setScalar(1 + Math.sin(this.time * 2) * 0.5)
        pulse.material.opacity = 0.3 + Math.sin(this.time * 2) * 0.2
      }
    })
  }

  /**
   * 动画循环
   */
  _animate() {
    this.animationId = requestAnimationFrame(() => this._animate())

    this.time += 0.016

    this._updateVibration()
    this._updateOcclusionCulling()
    this._updatePerformance()

    this.controls.update()
    this.renderer.render(this.scene, this.camera)
  }

  /**
   * 开始渲染
   */
  start() {
    if (!this.scene) {
      this.init()
    }
    this.animationRunning = true
    this._animate()
    return this
  }

  /**
   * 停止渲染
   */
  stop() {
    this.animationRunning = false
    if (this.animationId) {
      cancelAnimationFrame(this.animationId)
      this.animationId = null
    }
    return this
  }

  /**
   * 播放/暂停振动
   */
  toggleAnimation() {
    this.animationRunning = !this.animationRunning
    return this
  }

  /**
   * 设置振动模式
   * @param {number} mode - 模态阶数 (1-5)
   */
  setVibrationMode(mode) {
    this.vibrationMode = Math.max(1, Math.min(5, mode))
    return this
  }

  /**
   * 设置振动幅度
   * @param {number} amp - 幅度 (0-1)
   */
  setVibrationAmplitude(amp) {
    this.vibrationAmplitude = Math.max(0, Math.min(1, amp))
    return this
  }

  /**
   * 设置指定楼层损伤状态
   * @param {number} floor - 楼层
   * @param {boolean} hasDamage - 是否有损伤
   * @param {number} severity - 损伤程度 (0-1)
   */
  setFloorDamage(floor, hasDamage, severity = 0.5) {
    const idx = floor - 1
    if (this.damageMarkers[idx]) {
      const { marker, pulse } = this.damageMarkers[idx]
      marker.visible = hasDamage
      pulse.visible = hasDamage
      marker.userData.baseScale = 0.8 + severity * 0.6
      marker.material.emissiveIntensity = 0.5 + severity * 0.5
    }
    return this
  }

  /**
   * 显示/隐藏传感器
   */
  toggleSensors(show) {
    this.sensorMarkers.forEach(s => { s.visible = show })
    return this
  }

  /**
   * 相机对准指定楼层
   */
  focusFloor(floor) {
    const floorY = FLOOR_HEIGHTS.slice(0, floor - 1).reduce((a, b) => a + b, 0) +
      FLOOR_HEIGHTS[floor - 1] / 2 + 2.5
    this.controls.target.set(0, floorY, 0)
    return this
  }

  /**
   * 窗口大小变化处理
   */
  _onResize() {
    const width = this.container.clientWidth
    const height = this.container.clientHeight
    this.camera.aspect = width / height
    this.camera.updateProjectionMatrix()
    this.renderer.setSize(width, height)
  }

  /**
   * 销毁
   */
  dispose() {
    this.stop()
    this.renderer.dispose()
    if (this._perfPanel) {
      this._perfPanel.remove()
    }
    window.removeEventListener('resize', () => this._onResize())
  }

  /**
   * 获取性能信息
   */
  getPerformanceInfo() {
    return { ...this.performanceInfo }
  }
}

export default Pagoda3DRenderer
