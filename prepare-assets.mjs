import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { inflateRawSync } from 'node:zlib';
import { createHash } from 'node:crypto';
import { resolve, dirname, sep } from 'node:path';
const archive=readFileSync(new URL('./veranda-assets.zip',import.meta.url));
const expected='61f8f56af4cbbf3827cb0e8c992af82ba5b0aa065335ec6bd3e5eb725c9b59fa';
if(createHash('sha256').update(archive).digest('hex')!==expected)throw Error('Asset archive checksum mismatch');
const root=resolve('.');let offset=0,count=0;
while(offset+30<=archive.length && archive.readUInt32LE(offset)===0x04034b50){
 const flags=archive.readUInt16LE(offset+6),method=archive.readUInt16LE(offset+8),size=archive.readUInt32LE(offset+18),rawSize=archive.readUInt32LE(offset+22),nameLength=archive.readUInt16LE(offset+26),extraLength=archive.readUInt16LE(offset+28);
 if(flags&9)throw Error('Unsupported ZIP flags');
 const name=archive.toString('utf8',offset+30,offset+30+nameLength),start=offset+30+nameLength+extraLength,end=start+size;
 if(!name.startsWith('assets/')||name.includes('..')||name.includes('\\')||end>archive.length)throw Error('Invalid asset path');
 const target=resolve(root,name);if(!target.startsWith(root+sep+'assets'+sep))throw Error('Invalid asset destination');
 const packed=archive.subarray(start,end);const bytes=method===0?packed:method===8?inflateRawSync(packed):null;
 if(!bytes||bytes.length!==rawSize)throw Error('Unsupported or corrupt asset data');
 mkdirSync(dirname(target),{recursive:true});writeFileSync(target,bytes);count++;offset=end;
}
if(count!==26)throw Error('Asset file count mismatch: '+count);
console.log(`Prepared ${count} verified Veranda assets.`);
