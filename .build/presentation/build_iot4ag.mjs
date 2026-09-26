import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation, PresentationFile, FileBlob} from '@oai/artifact-tool';
const workspaceDir='C:/Users/sonpo/Desktop/Hackathon';
const SKILL_DIR='C:/Users/sonpo/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations';
const RUNTIME_PYTHON='C:/Users/sonpo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const TMP=path.join(workspaceDir,'.build/presentation/iot4ag');
const OUT=path.join(workspaceDir,'deliverables/IoT4Ag');
const FINAL=path.join(OUT,process.env.DECK_FILENAME||'FieldSignal_IoT4Ag_pitch.pptx');
await fs.mkdir(TMP,{recursive:true}); await fs.mkdir(OUT,{recursive:true});
const {resolvePresentationFont,applyPresentationChartFont,finalizePresentation}=await import(pathToFileURL(path.join(SKILL_DIR,'container_tools/artifact_tool_utils.mjs')).href);
const font=resolvePresentationFont({fontFamily:'Arial'});
const d=JSON.parse(await fs.readFile(path.join(workspaceDir,'outputs/decision_brief/claims.json'),'utf8'));
const broad=JSON.parse(await fs.readFile(path.join(workspaceDir,'outputs/broad_performance/presentation_data.json'),'utf8'));
const c=broad.claims;
const P=Presentation.create({slideSize:{width:1280,height:720}});
const green='#173E2C',cream='#F5F3E9',muted='#556358',accent='#2C744B',gold='#AD7440';
function text(s,value,x,y,w,h,size=28,color=green,bold=false){
 const o=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 o.text=value;o.text.style={typeface:font,fontSize:size,color,bold,autoFit:'none',verticalAlignment:'middle'};return o;
}
function slide(title,sub){const s=P.slides.add();s.background.fill=cream;text(s,title,64,42,1152,84,44,green,true);text(s,sub,64,132,1152,62,24,muted);return s;}
function footer(s,t){text(s,t,64,654,1152,46,17,muted);}
const talk=[];
function notes(s,t,source){s.speakerNotes.textFrame.setText(`${t}\n\nSources (not spoken): ${source}\nScope: five locations in 2022. No cross-season validation.`);talk.push(t);}
function chart(s,cfg){const o=s.charts.add('bar',cfg);applyPresentationChartFont(o,{fontFamily:font});return o;}
const base={hasLegend:false,chartFill:cream,plotAreaFill:cream,chartLine:{fill:'none',width:0},plotAreaLine:{fill:'none',width:0},
 xAxis:{textStyle:{typeface:font,fontSize:21,fill:green},line:{fill:'#C9D0C6',width:1}},
 yAxis:{textStyle:{typeface:font,fontSize:21,fill:green},majorGridlines:{fill:'#D9DDD4',width:1}},
 dataLabels:{showValue:true,position:'outEnd',textStyle:{typeface:font,fontSize:25,fill:green}}};

let s=P.slides.add();s.background.fill=green;
text(s,'CORNSTELLATION  /  FIELDSIGNAL',64,53,1120,52,29,cream,true);
text(s,'Which plots need a visit?\nWhich hybrids deserve\nthe next trial?',64,165,1140,242,60,cream,true);
text(s,'Satellite-informed forecasts for better hybrid selection\nacross environments.',68,435,1130,88,29,'#DBE8D9');
text(s,'84 hybrids     5 locations     2,131 labeled plots',68,558,1130,53,32,cream,true);
text(s,'Nebraska and Iowa, 2022  •  Historical replay, not a live alert',68,639,1130,36,22,'#DBE8D9');
notes(s,'Our crop team has two decisions: which plots deserve a visit now, and which hybrids deserve the next trial. FieldSignal connects those decisions using agronomic records and satellite observations. We studied 84 hybrids and 2,131 plots across five Nebraska and Iowa locations. This is a 2022 historical replay. Our forecasts are tested at locations withheld from training, while our hybrid shortlist is separately labeled as observed harvest evidence.','outputs/decision_brief/claims.json; outputs/broad_performance/claims.json');

s=slide('Imagery found 6 more low-yield plots','Day 75: 10 inspections per site, 50 total; identical held-out plots and CatBoost settings');
const rows=d.overall.filter(r=>r.cutoff===75);
const mods=['nitrogen','agronomy','combined'];
chart(s,{...base,position:{left:64,top:223,width:765,height:334},categories:['Nitrogen only','Agronomic records','Agronomy + satellite'],
 series:[{name:'Low-yield plots found',values:mods.map(m=>rows.find(r=>r.model===m).hits),fill:accent,valuesFormatCode:'0',points:[{idx:0,fill:'#B5BEAF'},{idx:1,fill:'#A3BC94'},{idx:2,fill:accent}]}],
 barOptions:{direction:'column',grouping:'clustered',gapWidth:105},yAxis:{...base.yAxis,min:0,max:40,majorUnit:10,title:{text:'Low-yield plots found / 50 visits',textStyle:{typeface:font,fontSize:20}}}});
text(s,'60% precision',884,225,326,67,40,green,true);
text(s,'30 of 50 visits reached\na bottom-20% yield plot.',888,304,316,86,26,green);
text(s,'7% recall',884,424,326,57,35,gold,true);
text(s,'30 of all 428 low-yield\nplots were reached.',888,487,316,76,24,muted);
text(s,'MAE (bu/ac): 59.7 nitrogen  |  72.1 agronomy  |  45.5 combined  |  55.1 mean',64,584,1152,44,23,green,true);
footer(s,'Target: actual bottom 20% within each site. Nitrogen-only predictions tie by rate; selection then depends on plot ID.');
notes(s,'What does imagery add? We held the plots, site folds and model settings constant. At day 75, agronomic records found 24 low-yield plots in 50 visits. Adding imagery found 30: six additional useful inspections. That is 60 percent precision, but only seven percent recall of all 428 low-yield plots. Nitrogen alone found six, although tied predictions make that comparison sensitive to plot ordering. Combined yield error was 45.5 bushels per acre, compared with 55.1 for the training mean.','outputs/decision_brief/model_comparison.csv; cutoff75, locationOverall. Nitrogen/mean top-K uses deterministic plot-ID tie-break.');

s=slide('Day 75: flag, rank, then inspect','Candidate rule: flag the lowest predicted 20% within a site; visit in order up to capacity');
text(s,'38% of low-yield plots captured',64,225,680,54,35,green,true);
text(s,'The 20% screen found 163 of 428.\nIt is a screening rule, not a stress diagnosis.',68,291,674,89,27,green);
const cases=d.cases;
text(s,'Ames: success and a capacity miss',64,411,704,49,29,green,true);
text(s,`Priority 1: forecast ${cases[0].predicted_yield.toFixed(0)}, harvest ${cases[0].yieldPerAcre.toFixed(0)} bu/ac\nPriority 13: forecast ${cases[1].predicted_yield.toFixed(0)}, harvest ${cases[1].yieldPerAcre.toFixed(0)} bu/ac`,68,472,704,90,27,green);
text(s,'Both flagged. Only priority 1 fits 10 visits.',68,576,704,42,22,muted);
chart(s,{...base,position:{left:824,top:224,width:386,height:340},categories:['Day 75','Day 90'],series:[{name:'Screen recall (%)',values:d.warning.map(r=>Number((100*r.recall).toFixed(1))),fill:gold,valuesFormatCode:'0.0'}],barOptions:{direction:'column',grouping:'clustered',gapWidth:110},yAxis:{...base.yAxis,min:0,max:50,majorUnit:10,title:{text:'20% screen recall (%)',textStyle:{typeface:font,fontSize:20}}}});
footer(s,'Threshold is site-relative. Image age and NDVI change are context. Harvest labels appear only in this retrospective evaluation.');
notes(s,'The candidate warning rule is explicit. Starting at day 75, flag the lowest predicted fifth within each site, then inspect in priority order up to capacity. The screen found 163 of 428 eventual low-yield plots. In Ames, priority one was correctly reached. A very low-yield plot ranked thirteenth: it was flagged, but ten visits would miss it. Day 90 reduced yield error, yet screen recall fell. Scouts must establish the cause; the model does not diagnose stress or prescribe treatment.','outputs/decision_brief/warning_evaluation.csv; case_examples.csv. Both examples are actual-bottom20 and warning_flag true; the second is a capacity miss, not a screening miss.');

s=slide('Five candidates for the next replicated trials','Observed harvest shortlist: all five exceed the median at every site');
const headers=['Hybrid','Average percentile','Weakest site','Plots'];
const values=[headers,...c.shortlist.map(h=>[h.genotype,h.average_percentile.toFixed(1),h.worst_site_percentile.toFixed(1),String(h.replicates)])];
const t=s.tables.add({rows:6,columns:4,left:64,top:220,width:1152,height:283,columnWidths:[540,244,224,144],values});
t.borders.assign({style:'solid',fill:cream,width:2});
t.cells.block({row:0,column:0,rowCount:6,columnCount:4}).assign({textStyle:{typeface:font,fontSize:23,color:green},margins:{left:12,right:12,top:8,bottom:8},anchor:'center'});
for(let r=0;r<6;r++)for(let col=0;col<4;col++){const cell=t.getCell(r,col);cell.fill=r===0?green:r%2?'#E6EDDF':'#F0F1E6';cell.text.style={typeface:font,fontSize:r===0?21:23,color:r===0?cream:green,bold:r===0};}
text(s,'Nitrogen response varies by site',64,529,1152,43,28,green,true);
text(s,'150 − 75 lb N/ac: Ames −23.6  |  Crawfordsville +15.4  |  Lincoln +10.9  |  Scottsbluff +29.2 bu/ac',64,581,1152,49,21,green);
footer(s,'Sites equally weighted. Some cells have one replicate. N contrasts match 84 hybrids/site; descriptive, not fertilizer advice.');
notes(s,'For the next trials, we keep observed findings separate from forecasts. We average replicates within treatments and weight sites equally. These five candidates exceed the median at every site; the weakest-site column prevents a strong average from hiding poor performance. They are promising in the observed environments, not proven across seasons. Management also varies: matched nitrogen contrasts range from minus 23.6 to plus 29.2 bushels per acre across four sites. Field placement may contribute, so these are not fertilizer recommendations.','outputs/broad_performance/observed_hybrids.csv; nitrogen_sites.csv; nitrogen_pairs.csv. Shortlist rule >=4 sites above median, complete5sitecoverage; all5listed have5.');

s=slide('Prioritize the next trials. Validate the next season.','A usable research decision today, with a clear test before broader deployment');
text(s,'44.0 bu/ac',64,232,520,82,58,green,true);
text(s,'Day-90 CatBoost MAE\nversus 55.1 training mean',68,330,520,87,28,green);
text(s,'4.6 / 10',696,232,520,82,58,green,true);
text(s,'Observed top-10 hybrids recovered\nper held-out site, on average',700,330,512,87,27,green);
text(s,'Next: replicated trials of the shortlist + untouched 2023 evaluation',64,473,1152,80,33,green,true);
text(s,'Freeze the pipeline. Record scouting outcomes. Test transfer across seasons.',68,567,1144,59,26,muted);
footer(s,'2022 spatial transfer only. Exploratory Ridge: 39.4 bu/ac MAE, 5.0/10 overlap. Site bias and ranking failures remain.');
notes(s,'At day 90, combined CatBoost reaches 44 bushels per acre error, about twenty percent below the training mean, and recovers 4.6 of the observed top ten hybrids per site. Exploratory Ridge improves those figures, but site bias and ranking failures remain. We have demonstrated spatial transfer in 2022, not cross-season reliability or guaranteed yield gains. Our proposal is concrete: use the shortlist to prioritize replicated trials, record what scouts find, freeze the pipeline, and test it on untouched 2023 data.','outputs/broad_performance/yield_metrics.csv; ranking_metrics.csv. CatBoostcombined90 hybridSpearman0.451. Ridgecombined90MAE39.4349,overlap5,Spearman0.477; RidgeagronomySpearman0.527.');

await fs.writeFile(path.join(OUT,'talk_track.md'),'# Three-minute talk track\n\n'+talk.map((v,i)=>`## Slide ${i+1}\n\n${v}`).join('\n\n'));
const candidate=path.join(TMP,'candidate.pptx');
await(await PresentationFile.exportPptx(P)).save(candidate);
await finalizePresentation({workspaceDir,candidatePath:candidate,finalPath:FINAL,pythonExecutable:RUNTIME_PYTHON,
 integrityValidatorPath:path.join(SKILL_DIR,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL_DIR,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','4'],explicitTotalSlideCount:5,requiredNativeTableOwnerSlides:[4],requiredNativeChartOwnerSlides:[2,3],materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,receiptPath:path.join(TMP,'validation.json')});
const checked=await PresentationFile.importPptx(await FileBlob.load(FINAL));
for(let i=0;i<5;i++){const png=await checked.export({slide:checked.slides.getItem(i),format:'png',scale:1});await fs.writeFile(path.join(TMP,`final-slide-${i+1}.png`),new Uint8Array(await png.arrayBuffer()));}
console.log(FINAL);
