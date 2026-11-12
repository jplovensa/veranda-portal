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
        <div class="walk-fittings">
          <label class="walk-kicker" for="fittingSelect">DOORS &amp; STORAGE</label>
          <p>Tap a door, cabinet front or drawer in the model, or choose one below.</p>
          <select id="fittingSelect" disabled><option value="">Choose a fitting</option></select>
          <div class="walk-controls"><button id="fittingToggle" disabled>Open fitting</button><button id="fittingReset" disabled>Reset fittings</button></div>
          <p id="fittingStatus" role="status" aria-live="polite">Room doors start open for easy circulation.</p>
        </div>
        <div class="walk-clearances">
          <p class="walk-kicker">MODEL CLEARANCES</p>
          <dl id="clearances"></dl>
          <p>Model measurements. Confirm surveyed room sizes and final furniture, appliance and joinery dimensions before ordering.</p>
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

const fittings = [];
const fittingById = new Map();
const fittingRay = new THREE.Raycaster();
let activeFitting = null;

function fittingPose(item, value) {
  return {
    angle: item.kind === 'door' ? item.angle * (1 - value) : item.angle * value,
    x: item.pivot[0] + item.travel[0] * value,
    z: item.pivot[1] + item.travel[1] * value
  };
}

function fittingBlocks(item, value, x, z) {
  const pose = fittingPose(item, value);
  const c = Math.cos(pose.angle), s = Math.sin(pose.angle);
  const dx = x - pose.x, dz = z - pose.z;
  const lx = c * dx - s * dz, lz = s * dx + c * dz;
  const [a,b,e,f] = item.rect;
  return Math.hypot(Math.max(a-lx,0,lx-e), Math.max(b-lz,0,lz-f)) < radius;
}

function fittingCorners(item, value) {
  const pose = fittingPose(item, value);
  const c = Math.cos(pose.angle), s = Math.sin(pose.angle);
  const [a,b,e,f] = item.rect;
  return [[a,b],[e,b],[e,f],[a,f]].map(([x,z]) => [pose.x+c*x+s*z,pose.z-s*x+c*z]);
}

function rectanglesOverlap(points, rect) {
  const [a,b,e,f] = rect;
  const other = [[a,b],[e,b],[e,f],[a,f]];
  const axes = [[1,0],[0,1], [points[1][1]-points[0][1],points[0][0]-points[1][0]],
    [points[2][1]-points[1][1],points[1][0]-points[2][0]]];
  return axes.every(([x,z]) => {
    const first=points.map(p=>p[0]*x+p[1]*z), second=other.map(p=>p[0]*x+p[1]*z);
    return Math.min(...first)<Math.max(...second)-.0001 && Math.min(...second)<Math.max(...first)-.0001;
  });
}

function fittingHitsFurniture(item, value) {
  const points=fittingCorners(item,value);
  return item.obstacles.some(rect=>rectanglesOverlap(points,rect));
}

function applyFitting(item) {
  const pose = fittingPose(item, item.value);
  item.object.rotation.y = pose.angle;
  item.object.position.x = pose.x;
  item.object.position.z = pose.z;
  needsRender = true;
  renderer.shadowMap.needsUpdate = true;
}

function updateFittingButton() {
  const button = ui('fittingToggle');
  button.disabled = !activeFitting;
  if (!activeFitting) return;
  const opening = activeFitting.target < .5;
  button.textContent = opening ? 'Open fitting' : 'Close fitting';
  button.setAttribute('aria-expanded', String(!opening));
  button.setAttribute('aria-label', (opening ? 'Open ' : 'Close ') + activeFitting.label);
}

function chooseFitting(item) {
  activeFitting = item;
  ui('fittingSelect').value = item.id;
  ui('fittingStatus').textContent = item.label + (item.value > .98 ? ' is open.' : item.value < .02 ? ' is closed.' : ' is partly open.');
  updateFittingButton();
}

function toggleFitting(item) {
  stopTour();
  chooseFitting(item);
  item.target = item.target < .5 ? 1 : 0;
  updateFittingButton();
}

function animateFittings(dt) {
  for (const item of fittings) {
    if (Math.abs(item.target - item.value) < .0001) continue;
    const delta = Math.sign(item.target - item.value) * Math.min(dt * 1.65, Math.abs(item.target - item.value));
    const next = item.value + delta;
    const occupied = mode === 'walk' && fittingBlocks(item, next, camera.position.x, camera.position.z);
    if (occupied || fittingHitsFurniture(item,next)) {
      item.target = item.value;
      ui('fittingStatus').textContent = occupied ? 'Move back to give ' + item.label + ' room to move.'
        : item.label + ' has reached the available clearance.';
      updateFittingButton();
      continue;
    }
    item.value = next;
    applyFitting(item);
    if (item === activeFitting && Math.abs(item.value - item.target) < .0001) chooseFitting(item);
  }
}

function pickFitting(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  fittingRay.setFromCamera(new THREE.Vector2((event.clientX - rect.left) / rect.width * 2 - 1,
    -(event.clientY - rect.top) / rect.height * 2 + 1), camera);
  const visible = object => {
    for (let node=object; node; node=node.parent) if (!node.visible) return false;
    return true;
  };
  const hit = fittingRay.intersectObject(model, true).find(item => visible(item.object));
  if (!hit) return;
  for (let node=hit.object; node; node=node.parent) {
    if (fittingById.has(node.name)) {
      toggleFitting(fittingById.get(node.name));
      return;
    }
  }
}

function bindFittings() {
  for (const spec of data.operable || []) {
    const object = model.getObjectByName(spec.id);
    if (!object) throw Error('Missing moving fitting ' + spec.id);
    const item = { ...spec, object, value: spec.initial, target: spec.initial };
    const starting=fittingCorners(item,item.initial);
    item.obstacles=data.solids.filter(solid=>!solid.motion && !rectanglesOverlap(starting,solid.rect)).map(solid=>solid.rect);
    fittings.push(item);
    fittingById.set(item.id, item);
    const option = document.createElement('option');
    option.value = item.id;
    option.textContent = item.label + ' · ' + fittings.length;
    ui('fittingSelect').append(option);
    applyFitting(item);
  }
  ui('fittingSelect').disabled = fittings.length === 0;
  ui('fittingSelect').addEventListener('change', event => {
    const item = fittingById.get(event.target.value);
    activeFitting = item || null;
    if (item) chooseFitting(item);
    else updateFittingButton();
  });
  ui('fittingToggle').addEventListener('click', () => { if (activeFitting) toggleFitting(activeFitting); });
  ui('fittingReset').disabled = false;
  ui('fittingReset').addEventListener('click', () => {
    stopTour();
    for (const item of fittings) item.target = item.initial;
    ui('fittingStatus').textContent = 'Returning doors and storage to their starting positions.';
    updateFittingButton();
  });
  let start = null;
  renderer.domElement.addEventListener('pointerdown', event => {
    if (event.button === 0 || event.pointerType === 'touch') start = {id:event.pointerId,x:event.clientX,y:event.clientY,moved:false};
  });
  renderer.domElement.addEventListener('pointermove', event => {
    if (start?.id === event.pointerId && Math.hypot(event.clientX-start.x,event.clientY-start.y)>7) start.moved=true;
  });
  renderer.domElement.addEventListener('pointerup', event => {
    if (start?.id === event.pointerId && !start.moved) pickFitting(event);
    start = null;
  });
  renderer.domElement.addEventListener('pointercancel', () => { start=null; });
}

function inside(x, z, [x1, z1, x2, z2]) {
  return x >= x1 && x <= x2 && z >= z1 && z <= z2;
}

function canWalk(x, z) {
  for (const [dx, dz] of [[0,0], [radius,0], [-radius,0], [0,radius], [0,-radius]]) {
    if (!data.floors.some(rect => inside(x + dx, z + dz, rect))) return false;
  }
  return !fittings.some(item => fittingBlocks(item, item.value, x, z)) && !data.solids.some(({ rect: [x1, z1, x2, z2], motion }) => {
    if (motion) return false;
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
  animateFittings(dt);
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
  for (const item of fittings) {
    if (fittingBlocks(item, item.value, x, z)) {
      item.value=item.target=item.initial;
      applyFitting(item);
    }
  }
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
    ? 'Drag to look · Tap fittings to open · Joystick or WASD to walk'
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
    const version = 'operable-layouts-1';
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
    bindFittings();
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
