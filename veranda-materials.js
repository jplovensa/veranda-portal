import * as THREE from './vendor/three.module.js';
// Small deterministic material studies; no remote textures or simulated product claims.
function canvasTexture(draw,size=256){const c=document.createElement('canvas');c.width=c.height=size;draw(c.getContext('2d'),size);const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.colorSpace=THREE.SRGBColorSpace;return t;}
function random(seed){return()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;};}
export function resortMaterials(){
 const wood=canvasTexture((g,n)=>{const r=random(61);g.fillStyle='#72543b';g.fillRect(0,0,n,n);for(let i=0;i<650;i++){const x=r()*n;g.strokeStyle=`rgba(${r()>.5?'32,20,12':'202,168,120'},${.04+r()*.12})`;g.lineWidth=.3+r();g.beginPath();g.moveTo(x,0);g.bezierCurveTo(x+Math.sin(x)*7,n*.33,x+Math.cos(x)*8,n*.66,x,n);g.stroke();}});
 const stone=canvasTexture((g,n)=>{const r=random(97);g.fillStyle='#e4ddcd';g.fillRect(0,0,n,n);for(let i=0;i<2100;i++){g.fillStyle=r()>.5?'#fff8ec15':'#a69b8612';g.fillRect(r()*n,r()*n,1+r()*3,1+r()*2);}for(let i=0;i<8;i++){const y=r()*n;g.strokeStyle='#95867430';g.lineWidth=.35+r();g.beginPath();g.moveTo(0,y);g.bezierCurveTo(n*.3,y-25,n*.6,y+35,n,y+12);g.stroke();}g.strokeStyle='#a79c8828';g.lineWidth=1;g.strokeRect(.5,.5,n-1,n-1);});
 const granite=canvasTexture((g,n)=>{
  const rand=random(147);
  g.fillStyle='#74716c';
  g.fillRect(0,0,n,n);
  for(let i=0;i<10500;i++){
   g.fillStyle=rand()>.55?'#c9c3b92a':'#302c2930';
   g.fillRect(rand()*n,rand()*n,1+rand()*1.6,1+rand()*1.4);
  }
  g.strokeStyle='#57534e55';
  g.strokeRect(.5,.5,n-1,n-1);
 });
 const fabric=canvasTexture((g,n)=>{g.fillStyle='#e9e1d2';g.fillRect(0,0,n,n);for(let i=0;i<n;i+=3){g.strokeStyle=i%2?'#ffffff5a':'#8d80622a';g.lineWidth=.6;g.beginPath();g.moveTo(i,0);g.lineTo(i,n);g.moveTo(0,i);g.lineTo(n,i);g.stroke();}});
 const rug=canvasTexture((g,n)=>{g.fillStyle='#bfb19a';g.fillRect(0,0,n,n);for(let i=0;i<n;i+=4){g.strokeStyle='#e7ddc7';g.lineWidth=1.3;g.beginPath();g.moveTo(i,0);g.lineTo(i,n);g.stroke();g.strokeStyle='#8f806633';g.beginPath();g.moveTo(0,i);g.lineTo(n,i);g.stroke();}});
 const plaster=canvasTexture((g,n)=>{const r=random(31);g.fillStyle='#eee8dc';g.fillRect(0,0,n,n);for(let i=0;i<3500;i++){g.fillStyle=r()>.5?'#fffdf312':'#a3957b0e';g.fillRect(r()*n,r()*n,2,2);}});
 fabric.repeat.set(3,3);rug.repeat.set(2,2);
 const make=(name,color,roughness,map=null,metalness=0)=>{const m=new THREE.MeshStandardMaterial({color,roughness,metalness,map});m.name=name;return m;};
 return {wall:make('Warm ivory mineral finish','#ffffff',.9,plaster),ivory:make('Ivory painted joinery','#eee7d8',.7),wood:make('Walnut grain finish','#ffffff',.6,wood),floor:make('Gray granite flooring','#ffffff',.52,granite),woodFloor:make('Wood-look SPC bedroom flooring','#ffffff',.65,wood),fabric:make('Ivory woven upholstery','#ffffff',.96,fabric),linen:make('Natural linen textile','#e1d8c4',.98,fabric),rug:make('Woven neutral rug','#ffffff',1,rug),stone:make('Pale stone-look surface','#ffffff',.3,stone),espresso:make('Espresso upholstery','#49372d',.8),bronze:make('Brushed champagne finish','#a48b58',.4,null,.65),black:make('Dark bronze frame','#302d26',.45,null,.25),grey:make('Existing provision grey','#c6c3bb',.65),tile:make('Existing pale tile','#dedbd2',.45),white:make('Warm white','#f4f0e7',.6),olive:make('Deep garden green','#435d42',.9),soil:make('Planter soil','#4b3d2d',1),glow:new THREE.MeshStandardMaterial({color:'#fff0d0',emissive:'#ffdba0',emissiveIntensity:.65,roughness:.5})};
}
