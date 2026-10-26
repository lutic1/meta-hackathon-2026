import { Color, PerspectiveCamera, Scene, WebGLRenderer } from 'three'

const CANVAS = '#14100C' // DESIGN.md colors.canvas

/** Renders an empty scene into a canvas under `root` and keeps it sized to `root`. */
export function mountScene(root: HTMLElement): void {
  const renderer = new WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(window.devicePixelRatio)
  const scene = new Scene()
  scene.background = new Color(CANVAS)
  const camera = new PerspectiveCamera(50, 1, 0.1, 100)
  camera.position.z = 5

  const render = (): void => {
    const { clientWidth: width, clientHeight: height } = root
    camera.aspect = width / height
    camera.updateProjectionMatrix()
    renderer.setSize(width, height)
    renderer.render(scene, camera)
  }
  root.append(renderer.domElement)
  window.addEventListener('resize', render)
  render()
}
