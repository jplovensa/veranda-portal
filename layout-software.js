import * as THREE from './vendor/three.module.js';

// A small painter renderer keeps the same 3D model usable without WebGL.
// It shares the camera, geometry, controls, dimensions and PNG export path.
export class CompatibleRenderer {
 constructor(){this.domElement=document.createElement('canvas');this.ctx=this.domElement.getContext('2d');this.ratio=1;this.shadowMap={};this.isSoftware=true;this.cache=new WeakMap();}
 setPixelRatio(r){this.ratio=Math.min(r,1.5);}
 setSize(w,h){this.width=w;this.height=h;this.domElement.width=w*this.ratio;this.domElement.height=h*this.ratio;this.domElement.style.width=w+'px';this.domElement.style.height=h+'px';}
 render(scene,camera){
  if(!this.width)return;scene.updateMatrixWorld();camera.updateMatrixWorld();
  const ctx=this.ctx,polys=[],lines=[],sun=new THREE.Vector3(-.4,.8,.35).normalize(),cameraPosition=new THREE.Vector3();camera.getWorldPosition(cameraPosition);
  const projection=new THREE.Matrix4().multiplyMatrices(camera.projectionMatrix,camera.matrixWorldInverse);
  const toScreen=p=>{const v=p.clone().applyMatrix4(projection);return [(v.x*.5+.5)*this.width,(-v.y*.5+.5)*this.height,v.z];};
  scene.traverseVisible(o=>{
   if(o.isMesh&&o.material&&!o.material.isShadowMaterial){
    const geo=o.geometry,material=Array.isArray(o.material)?o.material[0]:o.material;if(!material.color||material.visible===false)return;
    const pos=geo.attributes.position,index=geo.index;let faces=this.cache.get(geo);
    if(!faces){faces=[];const count=index?index.count:pos.count,box=geo.type==='BoxGeometry';for(let i=0;i<count;i+=box?6:3){const ids=box?[0,1,4,2]:[0,1,2];faces.push(ids.map(n=>new THREE.Vector3().fromBufferAttribute(pos,index?index.getX(i+n):i+n)));}this.cache.set(geo,faces);}
    for(const face of faces){const world=face.map(v=>v.clone().applyMatrix4(o.matrixWorld)),normal=new THREE.Vector3().crossVectors(world[1].clone().sub(world[0]),world[2].clone().sub(world[0])).normalize(),center=world.reduce((a,p)=>a.add(p),new THREE.Vector3()).multiplyScalar(1/world.length);if(normal.dot(cameraPosition.clone().sub(center))<=0&&!material.transparent)continue;const p=world.map(toScreen);if(p.some(v=>v[2]<-1||v[2]>1))continue;if(p.every(v=>v[0]<0)||p.every(v=>v[0]>this.width)||p.every(v=>v[1]<0)||p.every(v=>v[1]>this.height))continue;
     const color=material.color.clone();if(material.map)color.set(material.roughness>.9?'#e6dfd0':'#ab9270');color.multiplyScalar(.69+Math.max(0,normal.dot(sun))*.33);polys.push({p,color:'#'+color.getHexString(THREE.SRGBColorSpace),alpha:material.transparent?material.opacity:1,depth:center.clone().applyMatrix4(camera.matrixWorldInverse).z});
    }
   }else if(o.isLine){const pos=o.geometry.attributes.position,p=[];for(let i=0;i<pos.count;i++)p.push(toScreen(new THREE.Vector3().fromBufferAttribute(pos,i).applyMatrix4(o.matrixWorld)));if(p.every(v=>v[2]>-1&&v[2]<1))lines.push({p,color:'#'+o.material.color.getHexString()});}
  });
  ctx.setTransform(this.ratio,0,0,this.ratio,0,0);ctx.clearRect(0,0,this.width,this.height);polys.sort((a,b)=>a.depth-b.depth);
  for(const f of polys){ctx.beginPath();f.p.forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.closePath();ctx.globalAlpha=f.alpha;ctx.fillStyle=f.color;ctx.fill();ctx.strokeStyle=f.color;ctx.lineWidth=.4;ctx.stroke();}ctx.globalAlpha=1;
  for(const l of lines){ctx.beginPath();l.p.forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.strokeStyle=l.color;ctx.lineWidth=.7;ctx.stroke();}
 }
}
