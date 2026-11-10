import * as THREE from './vendor/three.module.js';
import { OrbitControls } from './vendor/OrbitControls.js';
import { GLTFLoader } from './vendor/GLTFLoader.js';
import { RGBELoader } from './vendor/RGBELoader.js';
import { MeshoptDecoder } from './vendor/meshopt_decoder.module.js';
import { RoomEnvironment } from './vendor/RoomEnvironment.js';

const section = document.querySelector('[data-walkthrough-unit]');
const unit = section.dataset.walkthroughUnit;
const mount = section.querySelector('.walk-viewer');
mount.insertAdjacentHTML('afterbegin', `
    <div class="walk-grid">
      <section class="walk-viewport" aria-label="Apartment model">
        <div id="stage" class="walk-stage"></div>
        <p class="walk-status" id="status" role="status">Loading apartment model…</p>
        <div class="walk-joystick" id="joystick" hidden>
          <button id="stick" aria-label="Walk joystick. Drag to move, or use W, A, S and D." aria-describedby="hint">
            <span class="stick-tick stick-n" aria-hidden="true"></span>
            <span class="stick-tick stick-e" aria-hidden="true"></span>
            <span class="stick-tick stick-s" aria-hidden="true"></span>
            <span class="stick-tick stick-w" aria-hidden="true"></span>
            <span id="stick-thumb" class="stick-thumb" aria-hidden="true"></span>
          </button>
        </div>
        <div class="walk-hint" id="hint">Drag to orbit · Scroll or pinch to zoom</div>
      </section>
      <aside class="walk-sidebar" aria-label="Walkthrough controls">
        <div>
          <p class="walk-kicker">VIEW</p>
          <div class="walk-controls">
            <button data-mode="orbit" aria-pressed="true" disabled>Cutaway</button>
            <button data-mode="plan" aria-pressed="false" disabled>Plan</button>
            <button data-mode="walk" aria-pressed="false" disabled>Walk</button>
            <button id="tour" aria-pressed="false" disabled>Play tour</button>
          </div>
        </div>
        <div>
          <p class="walk-kicker">ROOM STOPS</p>
          <nav class="walk-rooms" id="walkRoomStops" aria-label="Room stops"></nav>
        </div>
        <div>
          <p class="walk-kicker">LIGHTING</p>
          <div class="walk-swatches" role="group" aria-label="Lighting swatches">
            <button data-light="daylight" aria-pressed="true" disabled><span class="swatch-day" aria-hidden="true"></span>Daylight</button>
            <button data-light="golden" aria-pressed="false" disabled><span class="swatch-gold" aria-hidden="true"></span>Golden hour</button>
            <button data-light="evening" aria-pressed="false" disabled><span class="swatch-night" aria-hidden="true"></span>Evening</button>
          </div>
        </div>
        <div class="walk-clearances">
          <p class="walk-kicker">KITCHEN CLEARANCE</p>
          <dl id="clearances"></dl>
          <p>Based on the model. Verify on site with the final appliance, cabinetry and furniture sizes.</p>
        </div>
      </aside>
    </div>
`);
const ui = id => section.querySelector('#' + id);
const stage = ui('stage');
const status = ui('status');
const modeButtons = [...section.querySelectorAll('[data-mode]')];
const roomButtons = [];
const keys = new Set();
const stick = ui('stick');
const motion = new THREE.Vector2();
const lightingButtons = [...section.querySelectorAll('[data-light]')];
const movementKeys = new Set(['KeyW', 'KeyA', 'KeyS', 'KeyD', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight']);
const eye = 1.62;
const radius = .19;
const lighting = {
  daylight: { outlook: 1.22, sun: '#fff2dc', height: 8, sunPower: 2.15, ambient: 1.10, window: 1, interior: .55, reflections: .68 },
  golden: { outlook: .68, sun: '#ffb66e', height: 3.7, sunPower: 2.7, ambient: .70, window: .65, interior: .85, reflections: .53 },
  evening: { outlook: .12, sun: '#8fa9e1', height: 5, sunPower: .12, ambient: .25, window: .12, interior: 2.0, reflections: .30 }
};
const scene = new THREE.Scene();
const studyBackground = new THREE.Color('#d9d0c3');
scene.background = studyBackground;
const camera = new THREE.PerspectiveCamera(60, 1, .035, 100);
camera.rotation.order = 'YXZ';

let renderer, orbit, model, data, outlook;
let mode = 'orbit', selected = -1;
let tourTimer = null, drag = null;
let lastTime = 0, needsRender = true;
let lightStyle = 'daylight', joystickPointer = null;
let hemi, key;
const fillLights = [];

function inside(x, z, [x1, z1, x2, z2]) {
  return x >= x1 && x <= x2 && z >= z1 && z <= z2;
}

function canWalk(x, z) {
  for (const [dx, dz] of [[0,0], [radius,0], [-radius,0], [0,radius], [0,-radius]]) {
    if (!data.floors.some(rect => inside(x + dx, z + dz, rect))) return false;
  }
  return !data.solids.some(({ rect: [x1, z1, x2, z2] }) => {
    const dx = Math.max(x1 - x, 0, x - x2);
    const dz = Math.max(z1 - z, 0, z - z2);
    return dx * dx + dz * dz < radius * radius;
  });
}

function walkStep(dt) {
  const straight = Number(keys.has('KeyW') || keys.has('ArrowUp')) - Number(keys.has('KeyS') || keys.has('ArrowDown')) - motion.y;
  const side = Number(keys.has('KeyD')) - Number(keys.has('KeyA')) + motion.x;
  const turn = Number(keys.has('ArrowLeft')) - Number(keys.has('ArrowRight'));
  if (straight || side || turn) needsRender = true;
  camera.rotation.y += turn * dt * 1.48;
  if (!straight && !side) return;
  const speed = 1.45 * dt / Math.max(1, Math.hypot(straight, side));
  const yaw = camera.rotation.y;
  const dx = speed * (-Math.sin(yaw) * straight + Math.cos(yaw) * side);
  const dz = speed * (-Math.cos(yaw) * straight - Math.sin(yaw) * side);
  if (canWalk(camera.position.x + dx, camera.position.z)) camera.position.x += dx;
  if (canWalk(camera.position.x, camera.position.z + dz)) camera.position.z += dz;
}

function render(time) {
  const dt = Math.min(.04, (time - lastTime) / 1000);
  lastTime = time;
  if (mode === 'walk') walkStep(dt);
  else orbit.update();
  if (needsRender) {
    renderer.render(scene, camera);
    needsRender = false;
  }
}

function fitOverview() {
  const [x, z] = data.center;
  const fit = data.span / Math.min(camera.aspect, 1.1);
  orbit.target.set(x, 0, z);
  if (mode === 'plan') camera.position.set(x, fit * 1.18, z + .001);
  else camera.position.set(x + fit * .58, fit * .77, z + fit * .69);
  orbit.update();
  needsRender = true;
}

function showRoom(index, announce = true) {
  selected = index;
  const [label, [x,z,h], [tx,tz,th]] = data.views[index];
  camera.position.set(x,h || eye,z);
  camera.lookAt(tx,th,tz);
  needsRender = true;
  roomButtons.forEach((button, i) => {
    if (i === selected) button.setAttribute('aria-current', 'location');
    else button.removeAttribute('aria-current');
  });
  if (announce) {
    status.hidden = false;
    status.textContent = label;
  }
}

function setMode(next, index = 0) {
  mode = next;
  const walking = mode === 'walk';
  const plan = mode === 'plan';
  model.getObjectByName('Upper_walls').visible = walking;
  model.getObjectByName('Glazing').visible = walking;
  model.getObjectByName('Doors').visible = walking;
  model.getObjectByName('Ceiling').visible = walking;
  scene.background = walking ? outlook : studyBackground;
  orbit.enabled = !walking;
  orbit.enableRotate = !plan;
  orbit.mouseButtons.LEFT = plan ? THREE.MOUSE.PAN : THREE.MOUSE.ROTATE;
  orbit.touches.ONE = plan ? THREE.TOUCH.PAN : THREE.TOUCH.ROTATE;
  orbit.maxPolarAngle = plan ? Math.PI / 2 : Math.PI / 2.05;
  renderer.shadowMap.needsUpdate = true;
  camera.fov = walking ? (camera.aspect < 1 ? 72 : 62) : 49;
  camera.updateProjectionMatrix();
  keys.clear();
  resetJoystick();
  modeButtons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.mode === mode)));
  ui('joystick').hidden = !walking;
  stage.parentElement.dataset.mode = mode;
  ui('hint').textContent = walking
    ? 'Drag the view to look · Use joystick or WASD to walk'
    : plan ? 'Drag to pan · Scroll or pinch to zoom' : 'Drag to orbit · Scroll or pinch to zoom';
  renderer.domElement.setAttribute('aria-label', walking
    ? 'Walkthrough. W and S move, A and D step sideways, arrow keys turn or move.'
    : 'Apartment overview. Use the room buttons to enter a room.');
  if (walking) showRoom(index);
  else {
    selected = -1;
    status.hidden = true;
    roomButtons.forEach(button => button.removeAttribute('aria-current'));
    fitOverview();
  }
}

function stopTour() {
  if (tourTimer !== null) clearInterval(tourTimer);
  tourTimer = null;
  ui('tour').textContent = 'Play tour';
  ui('tour').setAttribute('aria-pressed', 'false');
}

function playTour() {
  if (tourTimer !== null) {
    stopTour();
    return;
  }
  setMode('walk', 0);
  ui('tour').textContent = 'Pause tour';
  ui('tour').setAttribute('aria-pressed', 'true');
  tourTimer = setInterval(() => {
    if (selected === data.views.length - 1) stopTour();
    else showRoom(selected + 1);
  }, 3900);
}

function bindControls() {
  const canvas = renderer.domElement;
  modeButtons.forEach(button => {
    button.disabled = false;
    button.addEventListener('click', () => {
      stopTour();
      setMode(button.dataset.mode);
      if (mode === 'walk') canvas.focus({ preventScroll: true });
    });
  });
  ui('tour').disabled = false;
  ui('tour').addEventListener('click', playTour);
  for (const [i, [label]] of data.views.entries()) {
    const button = document.createElement('button');
    button.textContent = label;
    button.addEventListener('click', () => {
      stopTour();
      setMode('walk', i);
      canvas.focus({ preventScroll: true });
    });
    ui('walkRoomStops').append(button);
    roomButtons.push(button);
  }
  for (const check of data.checks) {
    const row = document.createElement('div');
    const name = document.createElement('dt');
    const value = document.createElement('dd');
    name.textContent = check.label;
    value.textContent = check.metres.toFixed(2) + ' m';
    row.append(name, value);
    ui('clearances').append(row);
  }
  const onMovementKey = event => {
    if (mode !== 'walk' || !movementKeys.has(event.code)) return;
    event.preventDefault();
    stopTour();
    keys.add(event.code);
  };
  canvas.addEventListener('keydown', onMovementKey);
  stick.addEventListener('keydown', onMovementKey);
  stick.addEventListener('blur', () => keys.clear());
  window.addEventListener('keyup', event => keys.delete(event.code));
  canvas.addEventListener('blur', () => keys.clear());
  window.addEventListener('blur', () => {
    keys.clear();
    resetJoystick();
  });
  canvas.addEventListener('pointerdown', event => {
    if (mode !== 'walk' || drag || (event.pointerType === 'mouse' && event.button !== 0)) return;
    stopTour();
    canvas.focus({ preventScroll: true });
    canvas.setPointerCapture(event.pointerId);
    drag = { id: event.pointerId, x: event.clientX, y: event.clientY };
  });
  canvas.addEventListener('pointermove', event => {
    if (!drag || drag.id !== event.pointerId) return;
    camera.rotation.y -= (event.clientX - drag.x) * .0045;
    camera.rotation.x = THREE.MathUtils.clamp(camera.rotation.x - (event.clientY - drag.y) * .0045, -1.32, 1.32);
    needsRender = true;
    drag.x = event.clientX;
    drag.y = event.clientY;
  });
  for (const eventType of ['pointerup', 'pointercancel', 'lostpointercapture']) {
    canvas.addEventListener(eventType, event => {
      if (drag?.id === event.pointerId) drag = null;
    });
  }
  stick.addEventListener('pointerdown', event => {
    if (joystickPointer !== null || (event.pointerType === 'mouse' && event.button !== 0)) return;
    stopTour();
    joystickPointer = event.pointerId;
    stick.setPointerCapture(event.pointerId);
    updateJoystick(event);
  });
  stick.addEventListener('pointermove', event => {
    if (event.pointerId === joystickPointer) updateJoystick(event);
  });
  for (const eventType of ['pointerup', 'pointercancel', 'lostpointercapture']) {
    stick.addEventListener(eventType, event => {
      if (event.pointerId === joystickPointer) resetJoystick();
    });
  }
  for (const button of lightingButtons) {
    button.disabled = false;
    button.addEventListener('click', () => applyLighting(button.dataset.light));
  }
}

function resize() {
  camera.aspect = stage.clientWidth / Math.max(1, stage.clientHeight);
  camera.fov = mode === 'walk' ? (camera.aspect < 1 ? 72 : 62) : 49;
  camera.updateProjectionMatrix();
  renderer.setSize(stage.clientWidth, stage.clientHeight, false);
  needsRender = true;
  if (model && mode !== 'walk') fitOverview();
}

function updateJoystick(event) {
  const rect = stick.getBoundingClientRect();
  const travel = rect.width * .30;
  motion.set((event.clientX - rect.left - rect.width/2) / travel,
             (event.clientY - rect.top - rect.height/2) / travel);
  if (motion.lengthSq() > 1) motion.normalize();
  if (motion.lengthSq() < .012) motion.set(0, 0);
  stick.style.setProperty('--stick-x', motion.x * travel + 'px');
  stick.style.setProperty('--stick-y', motion.y * travel + 'px');
}

function resetJoystick() {
  joystickPointer = null;
  motion.set(0, 0);
  stick.style.setProperty('--stick-x', '0px');
  stick.style.setProperty('--stick-y', '0px');
}

function applyLighting(name) {
  lightStyle = name;
  const preset = lighting[name];
  const side = unit === '2br' ? -1 : 1;
  key.color.set(preset.sun);
  key.intensity = preset.sunPower;
  key.position.set(data.center[0] + side*9, preset.height, data.center[1] - 2.2);
  hemi.intensity = preset.ambient;
  scene.backgroundIntensity = preset.outlook;
  for (const { light, kind, power } of fillLights) {
    light.intensity = power * preset[kind];
    light.color.set(kind === 'interior' ? '#ffd8a8' : name === 'golden' ? '#ffd2a2' : '#e4efff');
  }
  model.traverse(object => {
    if (object.isMesh) object.material.envMapIntensity = preset.reflections;
  });
  renderer.shadowMap.needsUpdate = true;
  needsRender = true;
  for (const button of lightingButtons) {
    button.setAttribute('aria-pressed', String(button.dataset.light === name));
  }
}

function roomLighting() {
  hemi = new THREE.HemisphereLight('#e9eeff', '#958371');
  key = new THREE.DirectionalLight();
  key.target.position.set(data.center[0], 0, data.center[1]);
  key.castShadow = true;
  key.shadow.mapSize.set(1536, 1536);
  Object.assign(key.shadow.camera, { left: -10, right: 10, top: 10, bottom: -10, near: .5, far: 34 });
  key.shadow.camera.updateProjectionMatrix();
  key.shadow.bias = -.0004;
  key.shadow.normalBias = .017;
  scene.add(hemi, key, key.target);
  for (const { position, power, kind } of data.lights) {
    const light = new THREE.PointLight('#fff0d9', 0, 4.6);
    light.position.set(...position);
    scene.add(light);
    fillLights.push({ light, power, kind });
  }
  applyLighting(lightStyle);
}

async function load() {
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 1.65));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.04;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.autoUpdate = false;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.domElement.tabIndex = 0;
    stage.append(renderer.domElement);
    renderer.domElement.addEventListener('webglcontextlost', () => {
      renderer.setAnimationLoop(null);
      stopTour();
      status.hidden = false;
      status.textContent = 'The graphics connection was interrupted. Reload to reopen the walkthrough.';
    });
    orbit = new OrbitControls(camera, renderer.domElement);
    orbit.enableDamping = true;
    orbit.addEventListener('change', () => { needsRender = true; });
    orbit.minDistance = 3;
    orbit.maxDistance = 45;
    orbit.maxPolarAngle = Math.PI / 2.05;
    orbit.mouseButtons.LEFT = THREE.MOUSE.ROTATE;
    orbit.touches.ONE = THREE.TOUCH.ROTATE;
    const path = `assets/walkthrough/${unit}`;
    const version = unit === '3br' ? 'resort-1' : 'bathrooms-1';
    const [gltf, settings, garden] = await Promise.all([
      new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).loadAsync(`${path}.glb?v=${version}`),
      fetch(`${path}.json?v=${version}`).then(response => {
        if (!response.ok) throw Error('Apartment settings unavailable');
        return response.json();
      }),
      new RGBELoader().loadAsync('assets/walkthrough/studio-garden.hdr')
    ]);
    data = settings;
    outlook = garden;
    outlook.mapping = THREE.EquirectangularReflectionMapping;
    model = gltf.scene;
    model.traverse(object => {
      if (!object.isMesh) return;
      object.castShadow = !object.material.transparent && !['Ceiling', 'Floors'].includes(object.parent.name);
      object.receiveShadow = true;
    });
    scene.add(model);
    const pmrem = new THREE.PMREMGenerator(renderer);
    const environment = new RoomEnvironment();
    scene.environment = pmrem.fromScene(environment, .04).texture;
    environment.dispose();
    pmrem.dispose();
    roomLighting();
    new ResizeObserver(resize).observe(stage);
    resize();
    bindControls();
    setMode('orbit');
    renderer.setAnimationLoop(render);
  } catch (error) {
    console.error(error);
    status.hidden = false;
    status.textContent = 'The 3D walkthrough could not load. Reload to try again. The proposal and room previews are still available on this page.';
  }
}
// Keep the proposal lightweight until the walkthrough is near the viewport.
if ('IntersectionObserver' in window) {
  const observer = new IntersectionObserver(([entry]) => {
    if (!entry.isIntersecting) return;
    observer.disconnect();
    load();
  }, { rootMargin: '300px' });
  observer.observe(mount);
} else {
  load();
}
