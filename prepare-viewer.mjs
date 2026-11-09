import { mkdirSync, readFileSync, writeFileSync, copyFileSync } from 'node:fs';
mkdirSync('vendor', { recursive: true });
copyFileSync('node_modules/three/build/three.module.js', 'vendor/three.module.js');
writeFileSync('vendor/OrbitControls.js', readFileSync('node_modules/three/examples/jsm/controls/OrbitControls.js', 'utf8').replace("from 'three'", "from './three.module.js'"));
copyFileSync('node_modules/three/LICENSE', 'vendor/THREE-LICENSE.txt');
for (const [source,target] of [['exporters/GLTFExporter.js','GLTFExporter.js'],['utils/TextureUtils.js','TextureUtils.js']]) {
 const sourceText=readFileSync('node_modules/three/examples/jsm/'+source,'utf8').replaceAll("from 'three'","from './three.module.js'").replace("from './../utils/TextureUtils.js'","from './TextureUtils.js'");
 writeFileSync('vendor/'+target,sourceText);
}
for (const file of ['loaders/GLTFLoader.js', 'loaders/RGBELoader.js', 'utils/BufferGeometryUtils.js', 'environments/RoomEnvironment.js', 'libs/meshopt_decoder.module.js']) {
 const source = readFileSync('node_modules/three/examples/jsm/' + file, 'utf8')
   .replaceAll("from 'three'", "from './three.module.js'")
   .replace("from '../utils/BufferGeometryUtils.js'", "from './BufferGeometryUtils.js'");
 writeFileSync('vendor/' + file.split('/').at(-1), source);
}
