import {FileBlob,PresentationFile} from '@oai/artifact-tool';
const p=await PresentationFile.importPptx(await FileBlob.load('C:/Users/sonpo/Downloads/Presentation (1).pptx'));
for (const [n,x] of [['slides',p.slides],['shapes',p.slides.items[1].shapes],['images',p.slides.items[1].images],['shape',p.slides.items[1].shapes.items[0]]]) console.log(n,Object.getOwnPropertyNames(Object.getPrototypeOf(x)));
