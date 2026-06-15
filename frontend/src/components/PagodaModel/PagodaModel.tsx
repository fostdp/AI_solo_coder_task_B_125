import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { LOD } from 'three'
import type { DamageResult } from '@/types'
import './PagodaModel.scss'

interface PagodaModelProps {
  showSensors?: boolean
  showDamage?: boolean
  vibrationMode?: number
  vibrationAmplitude?: number
  damageResults?: DamageResult[]
  selectedFloor?: number
  onFloorSelect?: (floor: number) => void
  enableLOD?: boolean
  enableOcclusionCulling?: boolean
  lodDistances?: { high: number; medium: number; low: number }
  height?: number
}

type DetailLevel = 'high' | 'medium' | 'low'

const FLOOR_HEIGHTS = [0, 6.59, 5.49, 4.99, 4.59, 4.09]
const FLOOR_DIAMETERS = [0, 30.27, 22.65, 18.46, 15.28, 12.10]
const COLUMN_COUNT = 24
const BEAM_COUNT = 8
const TOTAL_HEIGHT = FLOOR_HEIGHTS.reduce((a, b) => a + b, 0)

const WOOD_COLORS = {
  column: 0x8B4513,
  beam: 0xA0522D,
  bracket: 0xCD853F,
  roof: 0x8B0000,
  base: 0x696969,
  sensor: 0x00FF00,
  damage: 0xFF0000
}

const LOD_DISTANCES = {
  high: 30,
  medium: 60,
  low: 100
}

const GEOMETRY_DETAIL = {
  high: { segments: 8, bracketSegments: 3 },
  medium: { segments: 6, bracketSegments: 2 },
  low: { segments: 4, bracketSegments: 1 }
}

export default function PagodaModel({
  showSensors = true,
  showDamage = true,
  vibrationMode = 0,
  vibrationAmplitude = 0,
  damageResults = [],
  selectedFloor,
  onFloorSelect,
  enableLOD = true,
  enableOcclusionCulling = true,
  lodDistances = LOD_DISTANCES,
  height
}: PagodaModelProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const controlsRef = useRef<OrbitControls | null>(null)
  const animationIdRef = useRef<number>(0)
  const floorGroupsRef = useRef<THREE.Group[]>([])
  const floorLODsRef = useRef<LOD[]>([])
  const sensorMarkersRef = useRef<THREE.Mesh[]>([])
  const damageMarkersRef = useRef<THREE.Mesh[]>([])
  const timeRef = useRef(0)
  const frustumRef = useRef<THREE.Frustum>(new THREE.Frustum())
  const projScreenMatrixRef = useRef<THREE.Matrix4>(new THREE.Matrix4())

  const [isLoaded, setIsLoaded] = useState(false)
  const [performanceInfo, setPerformanceInfo] = useState<{
    triangles: number
    drawCalls: number
    fps: number
    lodLevel: DetailLevel
  }>({ triangles: 0, drawCalls: 0, fps: 60, lodLevel: 'high' })
  const frameCountRef = useRef(0)
  const lastTimeRef = useRef(performance.now())
  const currentLODRef = useRef<DetailLevel>('high')

  const createColumn = useCallback((height: number, position: THREE.Vector3, detailLevel: DetailLevel = 'high') => {
    const detail = GEOMETRY_DETAIL[detailLevel]
    const geometry = new THREE.CylinderGeometry(0.25, 0.3, height, detail.segments)
    const material = new THREE.MeshPhongMaterial({
      color: WOOD_COLORS.column,
      shininess: 30
    })
    const column = new THREE.Mesh(geometry, material)
    column.position.copy(position)
    column.position.y += height / 2
    column.castShadow = detailLevel !== 'low'
    column.receiveShadow = true
    column.frustumCulled = enableOcclusionCulling
    column.userData.detailLevel = detailLevel
    return column
  }, [enableOcclusionCulling])

  const createBeam = useCallback((length: number, position: THREE.Vector3, rotation: number, detailLevel: DetailLevel = 'high') => {
    const detail = GEOMETRY_DETAIL[detailLevel]
    const width = detailLevel === 'low' ? 0.4 : 0.3
    const height = detailLevel === 'low' ? 0.5 : 0.4
    const geometry = new THREE.BoxGeometry(width, height, length, detail.segments, detail.segments, detail.segments)
    const material = new THREE.MeshPhongMaterial({
      color: WOOD_COLORS.beam,
      shininess: 30
    })
    const beam = new THREE.Mesh(geometry, material)
    beam.position.copy(position)
    beam.rotation.y = rotation
    beam.castShadow = detailLevel !== 'low'
    beam.receiveShadow = true
    beam.frustumCulled = enableOcclusionCulling
    beam.userData.detailLevel = detailLevel
    return beam
  }, [enableOcclusionCulling])

  const createBracketSet = useCallback((position: THREE.Vector3, scale: number = 1, detailLevel: DetailLevel = 'high') => {
    const group = new THREE.Group()
    
    if (detailLevel === 'low') {
      const simpleBracket = new THREE.Mesh(
        new THREE.BoxGeometry(0.8 * scale, 0.4 * scale, 0.4 * scale),
        new THREE.MeshPhongMaterial({ color: WOOD_COLORS.bracket, shininess: 30 })
      )
      simpleBracket.position.copy(position)
      simpleBracket.frustumCulled = enableOcclusionCulling
      simpleBracket.userData.detailLevel = detailLevel
      group.add(simpleBracket)
      return group
    }
    
    const detail = GEOMETRY_DETAIL[detailLevel]
    const bracketGeo = new THREE.BoxGeometry(0.8 * scale, 0.3 * scale, 0.4 * scale)
    const bracketMat = new THREE.MeshPhongMaterial({
      color: WOOD_COLORS.bracket,
      shininess: 50
    })
    
    for (let i = 0; i < detail.bracketSegments; i++) {
      const bracket = new THREE.Mesh(bracketGeo, bracketMat)
      bracket.position.set(
        i * 0.3 * scale,
        i * 0.15 * scale,
        0
      )
      bracket.castShadow = detailLevel === 'high'
      bracket.frustumCulled = enableOcclusionCulling
      bracket.userData.detailLevel = detailLevel
      group.add(bracket)
    }
    
    group.position.copy(position)
    return group
  }, [enableOcclusionCulling])

  const createRoof = useCallback((diameter: number, floor: number, detailLevel: DetailLevel = 'high') => {
    const group = new THREE.Group()
    
    const roofHeight = diameter * 0.25
    const detail = GEOMETRY_DETAIL[detailLevel]
    const latheSegments = detailLevel === 'low' ? 16 : detailLevel === 'medium' ? 24 : 32
    const eaveCount = detailLevel === 'low' ? 4 : BEAM_COUNT
    
    if (detailLevel === 'low') {
      const simpleRoofGeo = new THREE.ConeGeometry(diameter / 2, roofHeight, latheSegments)
      const roofMat = new THREE.MeshPhongMaterial({
        color: WOOD_COLORS.roof,
        shininess: 50
      })
      const roof = new THREE.Mesh(simpleRoofGeo, roofMat)
      roof.position.y = roofHeight / 2
      roof.frustumCulled = enableOcclusionCulling
      roof.userData.detailLevel = detailLevel
      group.add(roof)
      
      if (floor === 5) {
        const spireGeo = new THREE.ConeGeometry(0.5, 3, 6)
        const spireMat = new THREE.MeshPhongMaterial({ color: 0xFFD700, shininess: 80 })
        const spire = new THREE.Mesh(spireGeo, spireMat)
        spire.position.y = roofHeight + 1.5
        spire.frustumCulled = enableOcclusionCulling
        group.add(spire)
      }
      return group
    }
    
    const points: THREE.Vector2[] = []
    const segments = detailLevel === 'medium' ? 15 : 20
    for (let i = 0; i <= segments; i++) {
      const t = i / segments
      const r = diameter / 2 * (1 - t * 0.3)
      const y = t * roofHeight
      points.push(new THREE.Vector2(r, y))
    }
    
    const roofGeo = new THREE.LatheGeometry(points, latheSegments)
    const roofMat = new THREE.MeshPhongMaterial({
      color: WOOD_COLORS.roof,
      shininess: 80,
      side: THREE.DoubleSide
    })
    const roof = new THREE.Mesh(roofGeo, roofMat)
    roof.castShadow = true
    roof.receiveShadow = true
    roof.frustumCulled = enableOcclusionCulling
    roof.userData.detailLevel = detailLevel
    group.add(roof)
    
    const eaveLength = diameter * 0.15
    for (let i = 0; i < eaveCount; i++) {
      const angle = (i / eaveCount) * Math.PI * 2
      const eaveGeo = new THREE.BoxGeometry(0.15, 0.08, eaveLength)
      const eaveMat = new THREE.MeshPhongMaterial({
        color: 0x4A2511,
        shininess: 100
      })
      const eave = new THREE.Mesh(eaveGeo, eaveMat)
      eave.position.set(
        Math.cos(angle) * diameter / 2,
        0.05,
        Math.sin(angle) * diameter / 2
      )
      eave.rotation.y = angle + Math.PI / 2
      eave.rotation.z = 0.15
      eave.castShadow = detailLevel === 'high'
      eave.frustumCulled = enableOcclusionCulling
      eave.userData.detailLevel = detailLevel
      group.add(eave)
    }
    
    if (floor === 5) {
      const spireGeo = new THREE.ConeGeometry(0.5, 3, detail.segments)
      const spireMat = new THREE.MeshPhongMaterial({
        color: 0xFFD700,
        shininess: 100
      })
      const spire = new THREE.Mesh(spireGeo, spireMat)
      spire.position.y = roofHeight + 1.5
      spire.castShadow = true
      spire.frustumCulled = enableOcclusionCulling
      group.add(spire)
    }
    
    return group
  }, [enableOcclusionCulling])

  const createFloor = useCallback((floor: number, detailLevel: DetailLevel = 'high') => {
    const group = new THREE.Group()
    group.name = `floor_${floor}`
    group.userData.floorNumber = floor
    group.userData.detailLevel = detailLevel
    
    const baseY = FLOOR_HEIGHTS.slice(0, floor + 1).reduce((a, b) => a + b, 0) - FLOOR_HEIGHTS[floor]
    const height = FLOOR_HEIGHTS[floor]
    const diameter = FLOOR_DIAMETERS[floor]
    const radius = diameter / 2
    
    const platformSegments = detailLevel === 'low' ? 16 : 32
    const platformGeo = new THREE.CylinderGeometry(radius + 0.5, radius + 0.8, 0.4, platformSegments)
    const platformMat = new THREE.MeshPhongMaterial({
      color: 0x5D4037,
      shininess: 20
    })
    const platform = new THREE.Mesh(platformGeo, platformMat)
    platform.position.y = baseY
    platform.receiveShadow = true
    platform.frustumCulled = enableOcclusionCulling
    platform.userData.detailLevel = detailLevel
    group.add(platform)
    
    const colCount = detailLevel === 'low' ? 8 : detailLevel === 'medium' ? 16 : COLUMN_COUNT
    for (let i = 0; i < colCount; i++) {
      const angle = (i / colCount) * Math.PI * 2
      const colRadius = radius * 0.85
      const position = new THREE.Vector3(
        Math.cos(angle) * colRadius,
        baseY + 0.2,
        Math.sin(angle) * colRadius
      )
      const column = createColumn(height - 1, position, detailLevel)
      group.add(column)
    }
    
    const beamCount = detailLevel === 'low' ? 4 : detailLevel === 'medium' ? 6 : BEAM_COUNT
    for (let i = 0; i < beamCount; i++) {
      const angle = (i / beamCount) * Math.PI * 2
      const beamLength = diameter * 0.9
      const position = new THREE.Vector3(
        Math.cos(angle) * radius * 0.3,
        baseY + height * 0.5,
        Math.sin(angle) * radius * 0.3
      )
      const beam = createBeam(beamLength, position, angle, detailLevel)
      group.add(beam)
    }
    
    if (detailLevel !== 'low') {
      const bracketCount = detailLevel === 'medium' ? 12 : COLUMN_COUNT
      for (let i = 0; i < bracketCount; i++) {
        const angle = (i / bracketCount) * Math.PI * 2
        const colRadius = radius * 0.85
        const bracketPos = new THREE.Vector3(
          Math.cos(angle) * colRadius,
          baseY + height * 0.8,
          Math.sin(angle) * colRadius
        )
        const bracket = createBracketSet(bracketPos, 0.6 + floor * 0.05, detailLevel)
        bracket.rotation.y = angle + Math.PI / 2
        group.add(bracket)
      }
    }
    
    const roof = createRoof(diameter, floor, detailLevel)
    roof.position.y = baseY + height * 0.9
    group.add(roof)
    
    if (detailLevel !== 'low') {
      const railingHeight = 1.2
      const postCount = detailLevel === 'medium' ? 16 : 32
      for (let i = 0; i < postCount; i++) {
        const angle = (i / postCount) * Math.PI * 2
        const postGeo = new THREE.CylinderGeometry(0.05, 0.05, railingHeight, 6)
        const postMat = new THREE.MeshPhongMaterial({ color: 0x3E2723 })
        const post = new THREE.Mesh(postGeo, postMat)
        post.position.set(
          Math.cos(angle) * (radius + 0.3),
          baseY + 0.4 + railingHeight / 2,
          Math.sin(angle) * (radius + 0.3)
        )
        post.castShadow = detailLevel === 'high'
        post.frustumCulled = enableOcclusionCulling
        group.add(post)
      }
    }
    
    group.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        child.userData.floorNumber = floor
        child.userData.detailLevel = detailLevel
      }
    })
    
    return group
  }, [createColumn, createBeam, createBracketSet, createRoof, enableOcclusionCulling])

  const createFloorLOD = useCallback((floor: number) => {
    const lod = new LOD()
    
    const highDetail = createFloor(floor, 'high')
    const mediumDetail = createFloor(floor, 'medium')
    const lowDetail = createFloor(floor, 'low')
    
    lod.addLevel(highDetail, lodDistances.high)
    lod.addLevel(mediumDetail, lodDistances.medium)
    lod.addLevel(lowDetail, lodDistances.low)
    
    lod.userData.floorNumber = floor
    lod.userData.basePosition = highDetail.position.clone()
    
    return lod
  }, [createFloor, lodDistances])

  const updateOcclusionCulling = useCallback(() => {
    if (!enableOcclusionCulling || !cameraRef.current || !sceneRef.current) return
    
    const camera = cameraRef.current
    sceneRef.current.updateMatrixWorld()
    
    projScreenMatrixRef.current.multiplyMatrices(
      camera.projectionMatrix,
      camera.matrixWorldInverse
    )
    frustumRef.current.setFromProjectionMatrix(projScreenMatrixRef.current)
    
    floorLODsRef.current.forEach((lod) => {
      lod.visible = true
      
      const boundingSphere = lod.getObjectByProperty('userData', { detailLevel: 'high' })?.geometry?.boundingSphere
      if (boundingSphere) {
        const center = boundingSphere.center.clone()
        lod.localToWorld(center)
        lod.visible = frustumRef.current.intersectsSphere(
          new THREE.Sphere(center, boundingSphere.radius * 1.2)
        )
      }
    })
  }, [enableOcclusionCulling])

  const getCurrentLODLevel = useCallback((cameraPosition: THREE.Vector3, targetPosition: THREE.Vector3): DetailLevel => {
    const distance = cameraPosition.distanceTo(targetPosition)
    if (distance < lodDistances.high) return 'high'
    if (distance < lodDistances.medium) return 'medium'
    return 'low'
  }, [lodDistances])

  const computePerformanceMetrics = useCallback(() => {
    if (!rendererRef.current || !sceneRef.current) return
    
    const info = rendererRef.current.info
    const triangles = info.render.triangles
    const drawCalls = info.render.calls
    
    frameCountRef.current++
    const now = performance.now()
    if (now - lastTimeRef.current >= 1000) {
      const fps = Math.round((frameCountRef.current * 1000) / (now - lastTimeRef.current))
      
      const center = new THREE.Vector3(0, TOTAL_HEIGHT / 2, 0)
      const lodLevel = cameraRef.current 
        ? getCurrentLODLevel(cameraRef.current.position, center)
        : 'high'
      
      currentLODRef.current = lodLevel
      setPerformanceInfo({ triangles, drawCalls, fps, lodLevel })
      
      frameCountRef.current = 0
      lastTimeRef.current = now
    }
  }, [getCurrentLODLevel])

  const createBase = useCallback(() => {
    const group = new THREE.Group()
    
    const baseGeo = new THREE.CylinderGeometry(18, 22, 2, 32)
    const baseMat = new THREE.MeshPhongMaterial({
      color: WOOD_COLORS.base,
      shininess: 10
    })
    const base = new THREE.Mesh(baseGeo, baseMat)
    base.position.y = -1
    base.receiveShadow = true
    group.add(base)
    
    const stepGeo = new THREE.BoxGeometry(3, 0.3, 12)
    const stepMat = new THREE.MeshPhongMaterial({
      color: 0x808080,
      shininess: 10
    })
    
    for (let i = 0; i < 4; i++) {
      const step = new THREE.Mesh(stepGeo, stepMat)
      step.position.set(
        i === 1 ? -18 : i === 3 ? 18 : 0,
        -0.4,
        i === 0 ? -18 : i === 2 ? 18 : 0
      )
      step.rotation.y = i % 2 === 0 ? 0 : Math.PI / 2
      step.receiveShadow = true
      group.add(step)
    }
    
    return group
  }, [])

  const createSensorMarker = useCallback((position: THREE.Vector3, sensorType: string) => {
    const geometry = new THREE.SphereGeometry(0.15, 16, 16)
    const material = new THREE.MeshBasicMaterial({
      color: WOOD_COLORS.sensor,
      transparent: true,
      opacity: 0.8
    })
    const marker = new THREE.Mesh(geometry, material)
    marker.position.copy(position)
    marker.userData.sensorType = sensorType
    
    const glowGeo = new THREE.SphereGeometry(0.25, 16, 16)
    const glowMat = new THREE.MeshBasicMaterial({
      color: 0x00FF00,
      transparent: true,
      opacity: 0.3
    })
    const glow = new THREE.Mesh(glowGeo, glowMat)
    marker.add(glow)
    
    return marker
  }, [])

  const createDamageMarker = useCallback((position: THREE.Vector3, damageIndex: number) => {
    const size = 0.2 + damageIndex * 0.5
    const geometry = new THREE.SphereGeometry(size, 16, 16)
    const material = new THREE.MeshBasicMaterial({
      color: WOOD_COLORS.damage,
      transparent: true,
      opacity: 0.6 + damageIndex * 0.4
    })
    const marker = new THREE.Mesh(geometry, material)
    marker.position.copy(position)
    
    const pulseGeo = new THREE.RingGeometry(size * 0.8, size * 1.5, 32)
    const pulseMat = new THREE.MeshBasicMaterial({
      color: 0xFF0000,
      transparent: true,
      opacity: 0.5,
      side: THREE.DoubleSide
    })
    const pulse = new THREE.Mesh(pulseGeo, pulseMat)
    pulse.lookAt(new THREE.Vector3(0, 1, 0))
    marker.add(pulse)
    
    return marker
  }, [])

  const updateSensors = useCallback(() => {
    if (!sceneRef.current) return
    
    sensorMarkersRef.current.forEach(marker => {
      sceneRef.current?.remove(marker)
    })
    sensorMarkersRef.current = []
    
    if (!showSensors) return
    
    const sensorTypes = [
      'displacement_x', 'displacement_y',
      'acceleration_x', 'acceleration_y',
      'temperature', 'humidity',
      'moisture', 'inclination'
    ]
    
    for (let floor = 1; floor <= 5; floor++) {
      const baseY = FLOOR_HEIGHTS.slice(0, floor + 1).reduce((a, b) => a + b, 0) - FLOOR_HEIGHTS[floor] / 2
      const radius = FLOOR_DIAMETERS[floor] / 2 * 0.6
      
      for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2
        const position = new THREE.Vector3(
          Math.cos(angle) * radius,
          baseY + i * 0.1,
          Math.sin(angle) * radius
        )
        const marker = createSensorMarker(position, sensorTypes[i])
        sceneRef.current.add(marker)
        sensorMarkersRef.current.push(marker)
      }
    }
  }, [showSensors, createSensorMarker])

  const updateDamageMarkers = useCallback(() => {
    if (!sceneRef.current) return
    
    damageMarkersRef.current.forEach(marker => {
      sceneRef.current?.remove(marker)
    })
    damageMarkersRef.current = []
    
    if (!showDamage || !damageResults.length) return
    
    damageResults.forEach(damage => {
      if (damage.damage_index > 0.05) {
        const floor = damage.floor_number
        const baseY = FLOOR_HEIGHTS.slice(0, floor + 1).reduce((a, b) => a + b, 0) - FLOOR_HEIGHTS[floor] / 2
        const radius = FLOOR_DIAMETERS[floor] / 2 * 0.6
        
        const elementAngle = (damage.element_id / 24) * Math.PI * 2
        const position = new THREE.Vector3(
          Math.cos(elementAngle) * radius,
          baseY + (damage.element_id % 4) * 0.3,
          Math.sin(elementAngle) * radius
        )
        
        const marker = createDamageMarker(position, damage.damage_index)
        sceneRef.current.add(marker)
        damageMarkersRef.current.push(marker)
      }
    })
  }, [showDamage, damageResults, createDamageMarker])

  const updateVibration = useCallback((time: number) => {
    const targetObjects = enableLOD ? floorLODsRef.current : floorGroupsRef.current
    
    targetObjects.forEach((group, index) => {
      const floor = index + 1
      const basePosition = group.userData.basePosition?.clone() || new THREE.Vector3()
      
      if (vibrationAmplitude > 0 && vibrationMode > 0) {
        const frequency = vibrationMode * 0.5
        const amplitude = vibrationAmplitude * 0.1 * floor
        
        let displacement = new THREE.Vector3()
        
        if (vibrationMode === 1) {
          displacement.x = Math.sin(time * frequency + floor * 0.5) * amplitude
          displacement.z = Math.cos(time * frequency + floor * 0.3) * amplitude * 0.5
        } else if (vibrationMode === 2) {
          displacement.x = Math.sin(time * frequency) * amplitude * Math.sin(floor * Math.PI / 6)
          displacement.z = Math.cos(time * frequency) * amplitude * Math.cos(floor * Math.PI / 6)
        } else if (vibrationMode === 3) {
          displacement.x = Math.sin(time * frequency + floor) * amplitude
          displacement.y = Math.sin(time * frequency * 1.5 + floor) * amplitude * 0.3
          displacement.z = Math.cos(time * frequency + floor * 0.8) * amplitude * 0.7
        } else {
          displacement.x = Math.sin(time * frequency + floor * 0.5) * amplitude * (Math.random() - 0.5)
          displacement.z = Math.cos(time * frequency + floor * 0.3) * amplitude * (Math.random() - 0.5)
        }
        
        group.position.copy(basePosition).add(displacement)
        group.rotation.y = Math.sin(time * frequency * 0.7) * 0.02 * floor
      } else {
        group.position.copy(basePosition)
        group.rotation.set(0, 0, 0)
      }
    })
    
    sensorMarkersRef.current.forEach((marker, i) => {
      const scale = 1 + Math.sin(time * 3 + i * 0.5) * 0.2
      marker.scale.setScalar(scale)
    })
    
    damageMarkersRef.current.forEach((marker, i) => {
      const pulse = marker.children[0] as THREE.Mesh
      if (pulse) {
        const scale = 1 + Math.sin(time * 5 + i) * 0.3
        pulse.scale.setScalar(scale)
        const mat = pulse.material as THREE.MeshBasicMaterial
        mat.opacity = 0.3 + Math.sin(time * 5 + i) * 0.2
      }
    })
    
    if (enableLOD) {
      floorLODsRef.current.forEach(lod => {
        if (cameraRef.current) {
          lod.update(cameraRef.current)
        }
      })
    }
  }, [vibrationMode, vibrationAmplitude, enableLOD])

  const initScene = useCallback(() => {
    if (!containerRef.current) return
    
    const container = containerRef.current
    const width = container.clientWidth
    const height = container.clientHeight
    
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x1a1a2e)
    scene.fog = new THREE.Fog(0x1a1a2e, 50, 150)
    sceneRef.current = scene
    
    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000)
    camera.position.set(40, 30, 40)
    cameraRef.current = camera
    
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(window.devicePixelRatio)
    renderer.shadowMap.enabled = true
    renderer.shadowMap.type = THREE.PCFSoftShadowMap
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.2
    container.appendChild(renderer.domElement)
    rendererRef.current = renderer
    
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.05
    controls.minDistance = 15
    controls.maxDistance = 100
    controls.maxPolarAngle = Math.PI / 2.1
    controls.target.set(0, TOTAL_HEIGHT / 3, 0)
    controlsRef.current = controls
    
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4)
    scene.add(ambientLight)
    
    const mainLight = new THREE.DirectionalLight(0xffffff, 0.8)
    mainLight.position.set(30, 50, 30)
    mainLight.castShadow = true
    mainLight.shadow.mapSize.width = 2048
    mainLight.shadow.mapSize.height = 2048
    mainLight.shadow.camera.near = 0.5
    mainLight.shadow.camera.far = 150
    mainLight.shadow.camera.left = -50
    mainLight.shadow.camera.right = 50
    mainLight.shadow.camera.top = 50
    mainLight.shadow.camera.bottom = -50
    scene.add(mainLight)
    
    const fillLight = new THREE.DirectionalLight(0x87CEEB, 0.3)
    fillLight.position.set(-30, 20, -30)
    scene.add(fillLight)
    
    const warmLight = new THREE.PointLight(0xFFD700, 0.5, 100)
    warmLight.position.set(0, TOTAL_HEIGHT, 0)
    scene.add(warmLight)
    
    const base = createBase()
    scene.add(base)
    
    if (enableLOD) {
      floorLODsRef.current = []
      for (let floor = 1; floor <= 5; floor++) {
        const floorLOD = createFloorLOD(floor)
        floorLOD.userData.basePosition = new THREE.Vector3()
        scene.add(floorLOD)
        floorLODsRef.current.push(floorLOD)
      }
    } else {
      floorGroupsRef.current = []
      for (let floor = 1; floor <= 5; floor++) {
        const floorGroup = createFloor(floor, 'high')
        floorGroup.userData.basePosition = floorGroup.position.clone()
        scene.add(floorGroup)
        floorGroupsRef.current.push(floorGroup)
      }
    }
    
    const groundGeo = new THREE.PlaneGeometry(200, 200)
    const groundMat = new THREE.MeshPhongMaterial({
      color: 0x2d4a3e,
      shininess: 5
    })
    const ground = new THREE.Mesh(groundGeo, groundMat)
    ground.rotation.x = -Math.PI / 2
    ground.position.y = -2
    ground.receiveShadow = true
    scene.add(ground)
    
    const gridHelper = new THREE.GridHelper(100, 50, 0x444444, 0x222222)
    gridHelper.position.y = -1.99
    scene.add(gridHelper)
    
    const raycaster = new THREE.Raycaster()
    const mouse = new THREE.Vector2()
    
    const onMouseClick = (event: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect()
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
      
      raycaster.setFromCamera(mouse, camera)
      const intersects = raycaster.intersectObjects(scene.children, true)
      
      for (const intersect of intersects) {
        let obj: THREE.Object3D | null = intersect.object
        while (obj) {
          if (obj.name.startsWith('floor_')) {
            const floor = obj.userData.floorNumber
            onFloorSelect?.(floor)
            break
          }
          obj = obj.parent
        }
      }
    }
    
    renderer.domElement.addEventListener('click', onMouseClick)
    
    setIsLoaded(true)
    updateSensors()
    updateDamageMarkers()
    
    const animate = () => {
      animationIdRef.current = requestAnimationFrame(animate)
      
      timeRef.current += 0.016
      updateVibration(timeRef.current)
      
      if (enableOcclusionCulling) {
        updateOcclusionCulling()
      }
      computePerformanceMetrics()
      
      controls.update()
      renderer.render(scene, camera)
    }
    animate()
    
    const handleResize = () => {
      if (!containerRef.current) return
      const w = containerRef.current.clientWidth
      const h = containerRef.current.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', handleResize)
    
    return () => {
      window.removeEventListener('resize', handleResize)
      renderer.domElement.removeEventListener('click', onMouseClick)
      cancelAnimationFrame(animationIdRef.current)
      renderer.dispose()
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [createBase, createFloor, updateSensors, updateDamageMarkers, updateVibration, onFloorSelect, updateOcclusionCulling, computePerformanceMetrics, enableOcclusionCulling])

  useEffect(() => {
    const cleanup = initScene()
    return cleanup
  }, [initScene])

  useEffect(() => {
    if (isLoaded) {
      updateSensors()
    }
  }, [isLoaded, showSensors, updateSensors])

  useEffect(() => {
    if (isLoaded) {
      updateDamageMarkers()
    }
  }, [isLoaded, showDamage, damageResults, updateDamageMarkers])

  useEffect(() => {
    if (isLoaded && selectedFloor !== undefined) {
      floorGroupsRef.current.forEach((group, index) => {
        const isSelected = index + 1 === selectedFloor
        group.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            const mat = child.material as THREE.MeshPhongMaterial
            if (mat.emissive) {
              mat.emissive.setHex(isSelected ? 0x333300 : 0x000000)
            }
          }
        })
      })
    }
  }, [isLoaded, selectedFloor])

  return (
    <div className="pagoda-model-container" ref={containerRef}>
      {!isLoaded && (
        <div className="loading-overlay">
          <div className="loading-spinner"></div>
          <span>正在加载木塔模型...</span>
        </div>
      )}
      <div className="model-legend">
        <div className="legend-item">
          <span className="legend-dot" style={{ backgroundColor: '#00FF00' }}></span>
          <span>传感器</span>
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ backgroundColor: '#FF0000' }}></span>
          <span>损伤位置</span>
        </div>
      </div>
      <div className="model-info">
        <div className="info-item">
          <span className="label">塔高:</span>
          <span className="value">{TOTAL_HEIGHT.toFixed(2)}m</span>
        </div>
        <div className="info-item">
          <span className="label">层数:</span>
          <span className="value">5层</span>
        </div>
        <div className="info-item">
          <span className="label">立柱:</span>
          <span className="value">{COLUMN_COUNT * 5}根</span>
        </div>
      </div>
      {performanceInfo && (
        <div className="performance-panel">
          <div className="perf-title">性能监控</div>
          <div className="perf-item">
            <span className="perf-label">FPS:</span>
            <span className={`perf-value ${performanceInfo.fps >= 50 ? 'good' : performanceInfo.fps >= 30 ? 'warn' : 'bad'}`}>
              {performanceInfo.fps}
            </span>
          </div>
          <div className="perf-item">
            <span className="perf-label">三角形:</span>
            <span className="perf-value">{performanceInfo.triangles.toLocaleString()}</span>
          </div>
          <div className="perf-item">
            <span className="perf-label">绘制调用:</span>
            <span className="perf-value">{performanceInfo.drawCalls}</span>
          </div>
          <div className="perf-item">
            <span className="perf-label">LOD级别:</span>
            <span className={`perf-value lod-${performanceInfo.lodLevel}`}>
              {performanceInfo.lodLevel === 'high' ? '高细节' : performanceInfo.lodLevel === 'medium' ? '中细节' : '低细节'}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
