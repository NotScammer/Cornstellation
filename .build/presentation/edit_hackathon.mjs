import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {PresentationFile,FileBlob} from '@oai/artifact-tool';

const workspaceDir='C:/Users/sonpo/Desktop/Hackathon';
const TMP=workspaceDir+'/.build/hackathon_edit';
const SKILL_DIR='C:/Users/sonpo/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations';
const PYTHON='C:/Users/sonpo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const FINAL=workspaceDir+'/deliverables/Hackathon_4min/FieldSignal_4_minute_pitch.pptx';
const {resolvePresentationFont,applyPresentationChartFont,finalizePresentation}=await import(pathToFileURL(SKILL_DIR+'/container_tools/artifact_tool_utils.mjs').href);
const font=resolvePresentationFont({fontFamily:'Arial'});
const P=await PresentationFile.importPptx(await FileBlob.load('C:/Users/sonpo/Downloads/Presentation (1).pptx'));
const navy='#073A63',green='#237047',blue='#008BCD',ink='#183847',muted='#58706F';
const blank=P.layouts.items.find(l=>l.name==='Blank');
// Retain the original eight slides, masters, dimensions and embedded source art.
// The revised pitch needs new layouts and concise editable text.
for(const s of P.slides.items){
 s.shapes.deleteAll();
 for(const im of [...s.images.items]) s.images.deleteById(im.id);
 if(blank)s.setLayout(blank);
 s.background.fill='#FFFFFF';
}
function txt(s,v,x,y,w,h,size=30,color=ink,bold=false){
 const o=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 o.text=v;o.text.style={typeface:font,fontSize:size,color,bold,autoFit:'none',verticalAlignment:'middle'};return o;
}
function head(s,v){txt(s,v,64,48,1152,110,48,navy,true);}
function foot(s,v){txt(s,v,64,640,1100,52,20,muted);}
async function pic(s,f,x,y,w,h,alt){return s.images.add({blob:new Uint8Array(await fs.readFile(TMP+'/'+f)),contentType:f.endsWith('png')?'image/png':'image/jpeg',position:{left:x,top:y,width:w,height:h},fit:'contain',alt});}
const script=[];
function notes(i,time,talk,source,extra=''){
 const text=`Timing: ${time}\n\n${talk}\n\n${extra ? extra+'\n\n':''}Sources (not spoken): ${source}`;
 P.slides.items[i].speakerNotes.textFrame.setText(text);
 script.push({slide:i+1,time,talk});
}
let s=P.slides.items[0];
txt(s,'FieldSignal',64,64,680,90,72,navy,true);
txt(s,'Morning Briefing',68,166,680,65,44,green,true);
txt(s,'Which research plots\nneed a closer look today?',68,282,675,160,46,ink);
txt(s,'Cornstellation',68,589,700,44,26,muted);
await pic(s,'image2.png',782,188,420,315,'Original FieldSignal logo');
notes(0,'0:00–0:20 (20 seconds)',
 'A scouting crew starts the morning with more research plots than it can visit. Which ones deserve a closer look? We built FieldSignal Morning Briefing to combine agronomic records and satellite observations into a suggested inspection list, with the evidence behind each choice.',
 'Presentation (1).pptx, slides 2–3. Original FieldSignal logo from the supplied deck.');

s=P.slides.items[1];
head(s,'Too many plots, limited scouting hours');
txt(s,'Crews need to choose where to go\nbefore harvest reveals the outcome.',64,211,1110,142,48,ink);
txt(s,'2,131',64,429,335,89,68,blue,true);
txt(s,'labeled research plots',68,526,335,58,27,muted);
txt(s,'5',485,429,290,89,68,blue,true);
txt(s,'trial locations',489,526,300,58,27,muted);
txt(s,'2022',905,429,300,89,68,blue,true);
txt(s,'season in this prototype',909,526,300,58,27,muted);
foot(s,'Research trials in Nebraska and Iowa');
notes(1,'0:20–0:45 (25 seconds)',
 'Our prototype covers 2,131 labeled research plots across five locations in Nebraska and Iowa. Visiting every plot is difficult when scouting time is limited. Crews need a way to focus attention before harvest. We frame this as a prioritization problem: where to inspect first, then what to check when they arrive.',
 'Presentation (1).pptx, slide 2; README.md; deliverables/IoT4Ag/tables/model_comparison.csv, Overall cohort.');

s=P.slides.items[2];
head(s,'The morning briefing');
txt(s,'A suggested site order and a plot list sized to the crew’s capacity',64,165,1152,65,30,muted);
await pic(s,'image1.png',64,282,1152,202,'Original workflow: evaluate data, identify sites, identify plots, generate scouting brief');
txt(s,'Each plot includes a forecast, recent imagery context\nand a reason to inspect.',64,529,1152,92,31,green,true);
notes(2,'0:45–1:10 (25 seconds)',
 'FieldSignal organizes the decision into a morning briefing. It combines the available data, suggests a site order, and identifies plots within each site. The crew sets how many plots it can visit. The output includes the forecast, recent satellite context and a reason to inspect, plus a downloadable list for use in the field.',
 'Presentation (1).pptx, slides 3, 5–6; README.md, Scouting plan description. Original workflow artwork from the supplied deck.');

s=P.slides.items[3];
head(s,'How FieldSignal builds the list');
txt(s,'Forecast inputs',64,200,510,60,33,green,true);
txt(s,'Planting date, hybrid,\nnitrogen and irrigation\n\nSatellite bands and vegetation\nindices available by the cutoff',64,277,542,261,29,ink);
txt(s,'Scouting logic',690,200,510,60,33,green,true);
txt(s,'Compare forecasts within each site\n\nFlag low forecasts that fall below\nthe agronomy-only ranking\n\nOrder sites by their flagged share',690,277,526,278,29,ink);
foot(s,'Prototype screening rule. A flag calls for field inspection; it does not diagnose crop stress.');
notes(3,'1:10–1:40 (30 seconds)',
 'The model uses planting date, hybrid and management records, together with satellite observations available by the selected cutoff. In the scouting-plan view, a candidate flag combines a bottom-twenty-percent yield forecast with a drop of at least twenty within-site percentile points compared with the agronomy-only model. Sites rank by the share flagged. This rule is a prototype, and scouts still need to confirm what is happening.',
 'README.md, Scouting plan and Scientific interpretation; scouting_plan.py.',
 'For questions: CatBoost predicts yield. Agronomy inputs are planting day-of-year, nitrogen, irrigation and genotype. Satellite inputs include spectral summaries, NDVI/NDRE, recent changes and observation age. The site-priority and anomaly ordering has not been evaluated.');

s=P.slides.items[4];
head(s,'Demo: the suggested first stop');
txt(s,'Crawfordsville',64,177,655,66,44,green,true);
txt(s,'88 plots flagged',746,181,450,58,38,navy,true);
await pic(s,'image5.jpeg',64,285,1152,300,'Source dashboard screenshot: Crawfordsville, 88 flags, 18.0 percent of site');
foot(s,'Historical replay. The suggested order uses the flagged share, not the total number of plots.');
notes(4,'1:40–2:10 (30 seconds)',
 'Here is the briefing in action. In this historical replay, Crawfordsville is the suggested first stop, with 88 plots flagged, or eighteen percent of that site. Using a share prevents a large site from automatically taking first place. The crew can open the site to see the first three plot summaries and download an inspection list that fits its capacity.',
 'Presentation (1).pptx, slide 6, original embedded dashboard screenshot image5.jpeg.',
 'This screenshot is an illustrative historical replay, not a live alert. Its site-ordering rule has not been validated.');

s=P.slides.items[5];
head(s,'Demo: a plot and a reason to inspect');
await pic(s,'image4.jpeg',64,192,1152,349,'Source dashboard screenshot of first Crawfordsville plot, experiment 4351, range 12, row 20');
txt(s,'Crew action: inspect crop condition and record the findings',64,556,1152,65,32,green,true);
foot(s,'Forecasts guide inspection. The prototype does not identify a cause or prescribe a treatment.');
notes(5,'2:10–2:45 (35 seconds)',
 'The first summary identifies the exact plot: experiment 4351, range twelve, row twenty, with hybrid WF9 by H95. Its predicted yield is 118.9 bushels per acre, and the recent vegetation index has declined. Those signals tell the crew why this plot deserves attention. The image is five days old, so timing is visible too. A scout can now inspect crop condition and record findings. The forecast alone cannot tell us the cause or the right treatment.',
 'Presentation (1).pptx, slide 6, original embedded dashboard screenshot image4.jpeg.',
 'Shown replay date: July 25, 2022. NDVI change is −0.031. The dashboard identifies this as one of the lowest predicted yields at the site.');

s=P.slides.items[6];
head(s,'Imagery found 6 more low-yield plots');
txt(s,'Retrospective test at day 75: 10 visits per site, 50 visits total',64,166,1152,59,29,muted);
const chart=s.charts.add('bar',{
 position:{left:64,top:257,width:746,height:301},
 categories:['Agronomy only','Agronomy + satellite'],
 series:[{name:'Low-yield plots found',values:[24,30],fill:blue,points:[{idx:0,fill:'#809B9A'},{idx:1,fill:green}]}],
 barOptions:{direction:'bar',grouping:'clustered',gapWidth:100},hasLegend:false,
 chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF',chartLine:{fill:'none',width:0},plotAreaLine:{fill:'none',width:0},
 dataLabels:{showValue:true,position:'outEnd',textStyle:{typeface:font,fontSize:30,fill:navy}},
 xAxis:{textStyle:{typeface:font,fontSize:25,fill:ink},line:{fill:'none',width:0}},
 yAxis:{min:0,max:50,majorUnit:10,textStyle:{typeface:font,fontSize:22,fill:muted},majorGridlines:{fill:'#DFE7E5',width:1}}
});
applyPresentationChartFont(chart,{fontFamily:font});
txt(s,'30 / 50',896,273,314,90,62,green,true);
txt(s,'visits found a plot in\nthe actual bottom 20%',900,370,306,100,27,ink);
txt(s,'7% of all low-yield plots',900,496,306,63,24,muted);
txt(s,'Low-yield plots found in the inspection list',290,568,555,40,23,muted);
foot(s,'Five held-out sites in 2022. This test uses lowest forecast first, a different ordering from the demo.');
notes(6,'2:45–3:30 (45 seconds)',
 'We also tested a simpler inspection rule: visit the ten lowest yield forecasts at each site. Each test location was excluded from model training. At day seventy-five, agronomic records alone found 24 plots that later finished in their site’s bottom twenty percent. Adding satellite observations found thirty, using the same fifty visits. That is six additional low-yield plots and sixty percent precision. It still finds only seven percent of all low-yield plots. This result supports prioritization in these trials. It does not validate the demo’s newer anomaly ordering, prove a stress diagnosis, or establish performance in another season.',
 'deliverables/IoT4Ag/tables/model_comparison.csv, cutoff=75, location=Overall, agronomy and combined. Hits 24 and 30, k=50, target_n=428, n=2131. README.md distinguishes the unvalidated Scouting plan ordering from the evaluated lowest-yield-first list.',
 'Low yield is the actual within-site bottom 20% at harvest. Five leave-one-location-out folds use the same cohort. Combined precision is 30/50 = 60%; recall is 30/428 = 7.0%. Harvest labels enter evaluation only.');

s=P.slides.items[7];
head(s,'A focused start to the scouting day');
txt(s,'A site to visit.\nA plot list.\nEvidence to guide the inspection.',64,195,1130,235,48,navy,true);
txt(s,'Next: test the briefing with a scouting crew\nand validate forecasts on another season.',64,478,1140,103,32,green,true);
foot(s,'FieldSignal Morning Briefing');
notes(7,'3:30–4:00 (30 seconds)',
 'FieldSignal gives the crew a focused starting point: a site to visit, a plot list and evidence to guide inspection. The prototype also keeps hybrid performance available for longer-term trial decisions. Our next step is to test the briefing with a scouting crew, record what they find, and validate the forecasts on another season. The goal is to make limited scouting time more useful, while keeping field judgment central.',
 'Presentation (1).pptx, slides 7–8; README.md; deliverables/IoT4Ag/FieldSignal_scope_and_demo.md.');

const candidate=TMP+'/candidate.pptx';
await (await PresentationFile.exportPptx(P)).save(candidate);
for(let i=0;i<8;i++){
 await fs.writeFile(TMP+`/draft-${i+1}.png`,new Uint8Array(await (await P.slides.items[i].export({format:'png',scale:1})).arrayBuffer()));
}
console.log('Talk-track words:',script.map(x=>x.talk).join(' ').split(/\s+/).length);
await fs.writeFile(TMP+'/talk_track.json',JSON.stringify(script,null,2));
const result=await finalizePresentation({workspaceDir,candidatePath:candidate,finalPath:FINAL,pythonExecutable:PYTHON,
 integrityValidatorPath:SKILL_DIR+'/container_tools/inspect_presentation_package_integrity.py',
 layoutValidatorPath:SKILL_DIR+'/container_tools/inspect_presentation_layout_geometry.py',
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],
 explicitTotalSlideCount:8,requiredNativeChartOwnerSlides:[7],requiredNativeTableOwnerSlides:[],
 materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,
 receiptPath:TMP+'/validation.json'});
console.log(JSON.stringify(result));
const checked=await PresentationFile.importPptx(await FileBlob.load(FINAL));
for(let i=0;i<8;i++){
 await fs.writeFile(TMP+`/final-${i+1}.png`,new Uint8Array(await (await checked.slides.items[i].export({format:'png',scale:1})).arrayBuffer()));
}
