import { mkdirSync, readFileSync, writeFileSync, copyFileSync } from 'node:fs';
mkdirSync('vendor', { recursive: true });
copyFileSync('node_modules/three/build/three.module.js', 'vendor/three.module.js');
writeFileSync('vendor/OrbitControls.js', readFileSync('node_modules/three/examples/jsm/controls/OrbitControls.js', 'utf8').replace("from 'three'", "from './three.module.js'"));
copyFileSync('node_modules/three/LICENSE', 'vendor/THREE-LICENSE.txt');
