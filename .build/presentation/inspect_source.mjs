import fs from 'node:fs/promises';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';
const p=await PresentationFile.importPptx(await FileBlob.load('C:/Users/sonpo/Downloads/Presentation (1).pptx'));
const d='C:/Users/sonpo/Desktop/Hackathon/.build/hackathon_edit';
await fs.writeFile(d+'/source-inspect.ndjson',(await p.inspect({kind:'slide,textbox,shape,image,notes,layout',maxChars:60000})).ndjson);
console.log('slides',p.slides.items.length,'masters',p.masters.items.length);
for(let i=0;i<p.slides.items.length;i++){
const s=p.slides.items[i];
await fs.writeFile(d+`/source-${i+1}.png`,new Uint8Array(await (await s.export({format:'png',scale:1})).arrayBuffer()));
await fs.writeFile(d+`/source-${i+1}.json`,await (await s.export({format:'layout'})).text());
}
