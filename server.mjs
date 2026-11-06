import http from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { resolve, extname, sep } from 'node:path';
const root=resolve(process.cwd(),existsSync('dist/index.html')?'dist':'.');
const arg=(key)=>{const i=process.argv.indexOf(key);return i<0?undefined:process.argv[i+1];};
const port=Number(arg('--port') || process.env.PORT || 3000);
const host=arg('--host') || process.env.HOST || '127.0.0.1';
const mime={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.jpg':'image/jpeg','.png':'image/png','.webp':'image/webp','.mp4':'video/mp4','.ttf':'font/ttf','.txt':'text/plain; charset=utf-8'};
http.createServer(async(req,res)=>{try{
 const url=new URL(req.url,'http://localhost');
 const pathname=decodeURIComponent(url.pathname);
 if(pathname.split('/').some(p=>p.startsWith('.'))){res.writeHead(404).end();return;}
 const file=resolve(root,'.'+pathname+(pathname.endsWith('/')?'index.html':''));
 if(!file.startsWith(root+sep)){res.writeHead(403).end();return;}
 const meta=await stat(file);if(!meta.isFile()){res.writeHead(404).end();return;}
 const data=await readFile(file);res.writeHead(200,{'Content-Type':mime[extname(file)]||'application/octet-stream','Content-Length':data.length,'X-Content-Type-Options':'nosniff'});res.end(req.method==='HEAD'?undefined:data);
 }catch{res.writeHead(404).end('Not found');}
}).listen(port,host,()=>console.log(`Veranda portal: http://${host}:${port}`));
