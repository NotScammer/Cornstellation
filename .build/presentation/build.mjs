import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation, PresentationFile, FileBlob} from '@oai/artifact-tool';

const workspaceDir = 'C:/Users/sonpo/Desktop/Hackathon';
const SKILL_DIR = 'C:/Users/sonpo/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations';
const RUNTIME_PYTHON = 'C:/Users/sonpo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const TMP = path.join(workspaceDir,'.build/presentation');
const FINAL = path.join(workspaceDir,'deliverables/FieldSignal_pitch_v2.pptx');
const {resolvePresentationFont,applyPresentationChartFont,finalizePresentation}=await import(pathToFileURL(path.join(SKILL_DIR,'container_tools/artifact_tool_utils.mjs')).href);
const font = resolvePresentationFont({fontFamily:'Arial'});
const data=JSON.parse(await fs.readFile(path.join(workspaceDir,'outputs/broad_performance/presentation_data.json'),'utf8'));
const c=data.claims;
const P=Presentation.create({slideSize:{width:1280,height:720}});
const green='#173E2C',cream='#F5F3E9',muted='#556358',accent='#2C744B',gold='#AD7440';
function text(slide,value,x,y,w,h,size=28,color=green,bold=false){
  const shape=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  shape.text=value;
  shape.text.style={typeface:font,fontSize:size,color,bold,autoFit:'none',verticalAlignment:'middle'};
  return shape;
}
function addSlide(title,subtitle){
  const s=P.slides.add();s.background.fill=cream;
  text(s,title,64,48,1152,72,46,green,true);
  if(subtitle)text(s,subtitle,64,126,1152,70,24,muted);
  return s;
}
function footer(s,value){text(s,value,64,655,1152,44,18,muted);}
function notes(s,spoken,source){s.speakerNotes.textFrame.setText(`${spoken}\n\nSources (not spoken): ${source}\nEvidence scope: five locations in 2022. No cross-season validation.`);return spoken;}
const talk=[];
function chart(s,cfg){const o=s.charts.add('bar',cfg);applyPresentationChartFont(o,{fontFamily:font});return o;}
const baseChart={hasLegend:false,chartFill:cream,plotAreaFill:cream,chartLine:{fill:'none',width:0},plotAreaLine:{fill:'none',width:0},
  xAxis:{textStyle:{typeface:font,fontSize:21,fill:green},line:{fill:'#C9D0C6',width:1}},
  yAxis:{textStyle:{typeface:font,fontSize:21,fill:green},majorGridlines:{fill:'#D9DDD4',width:1}},
  dataLabels:{showValue:true,position:'outEnd',textStyle:{typeface:font,fontSize:23,fill:green}}};

// 1. Minimal, editable cover.
let s=P.slides.add();s.background.fill=green;
text(s,'FieldSignal',64,58,900,60,34,cream,true);
text(s,'Hybrid performance\nacross environments',64,171,1120,180,68,cream,true);
text(s,'Satellite-informed forecasts for better hybrid selection\nacross environments',68,380,1100,94,30,'#DBE8D9');
text(s,`${c.hybrids} hybrids     ${c.locations} locations     ${c.labeled_plots.toLocaleString('en-US')} labeled plots`,68,546,1100,58,31,cream,true);
text(s,'Nebraska and Iowa trials, 2022',68,630,1100,40,23,'#DBE8D9');
talk.push(notes(s,'A research team needs to choose which hybrids deserve another round of trials. The highest yield at one location is only part of that decision. FieldSignal compares the same 84 hybrids across five Nebraska and Iowa locations, using 2,131 labeled plots and satellite observations. We separate two questions: which hybrids performed consistently in the completed trials, and how well imagery can forecast their performance at a location the model has never seen. Today, our evidence covers 2022.','outputs/broad_performance/claims.json; supplied 2022/README.md'));

// 2. Native site-yield chart.
const sy=[...c.site_yields].sort((a,b)=>a.balanced_yield-b.balanced_yield);
s=addSlide(`Site means span ${Math.round(sy[0].balanced_yield)} to ${Math.round(sy.at(-1).balanced_yield)} bu/ac`,'Site context matters when comparing the same hybrid across trials');
chart(s,{...baseChart,position:{left:64,top:224,width:800,height:372},categories:sy.map(r=>r.location==='MOValley'?'Missouri V.':r.location),
  series:[{name:'Balanced site mean',values:sy.map(r=>Number(r.balanced_yield.toFixed(1))),fill:accent,valuesFormatCode:'0.0'}],
  barOptions:{direction:'column',grouping:'clustered',gapWidth:95},yAxis:{...baseChart.yAxis,min:0,max:180,majorUnit:60,title:{text:'Grain yield (bu/ac)',textStyle:{typeface:font,fontSize:22}}}});
text(s,'A fair comparison',916,230,290,50,28,green,true);
text(s,'Average replicates within each treatment.\n\nRank hybrids within that environment.\n\nGive each site equal weight.',916,294,290,292,25,green);
footer(s,'Observed harvest. Site means weight hybrids and nitrogen treatments equally; grain moisture standardized to 15.5%.');
talk.push(notes(s,`The environment changes the yield picture dramatically. Balanced site means range from about ${Math.round(sy[0].balanced_yield)} to ${Math.round(sy.at(-1).balanced_yield)} bushels per acre. We therefore avoid ranking hybrids using pooled plot averages. First, we average their replicates inside each treatment. Then we compare hybrids with peers in the same environment, average treatment percentiles within a site, and give each site equal weight. This prevents a favorable location or a frequently repeated control hybrid from dominating the shortlist. It describes relative trial performance, not a causal genetic effect.`,'outputs/broad_performance/site_yields.csv; observed_environment.csv; maize/insights.py::hybrid_tables'));

// 3. Editable heatmap table, not a chart screenshot.
s=addSlide('Five hybrids exceed the median at every site','Observed harvest shortlist for the next replicated trials');
const sites=['Ames','Crawfordsville','Lincoln','MOValley','Scottsbluff'];
const headers=['Hybrid','Ames','Crawfordsv.','Lincoln','Missouri V.','Scottsbluff'];
const values=[headers,...c.shortlist.map(h=>[h.genotype,...sites.map(site=>Number(data.observed_sites.find(r=>r.genotype===h.genotype&&r.location===site).site_percentile.toFixed(0)))])];
const table=s.tables.add({rows:6,columns:6,left:64,top:220,width:1152,height:302,columnWidths:[452,135,145,135,140,145],values});
table.borders.assign({style:'solid',fill:cream,width:2});
table.cells.block({row:0,column:0,rowCount:6,columnCount:6}).assign({textStyle:{typeface:font,fontSize:22,color:green},margins:{left:12,right:12,top:10,bottom:10},anchor:'center'});
for(let r=0;r<6;r++)for(let col=0;col<6;col++){
  const cell=table.getCell(r,col);
  if(r===0){cell.fill=green;cell.text.style={typeface:font,fontSize:20,color:cream,bold:true};}
  else if(col===0){cell.fill='#E8ECE1';cell.text.style={typeface:font,fontSize:22,color:green,bold:false};}
  else {const v=values[r][col];cell.fill=v>=85?'#285F3B':v>=70?'#AFCBA2':'#E1E9B8';cell.text.style={typeface:font,fontSize:28,color:v>=85?cream:green,bold:true};}
}
text(s,`Leader: ${c.shortlist[0].average_percentile.toFixed(1)} average percentile; ${c.shortlist[0].worst_site_percentile.toFixed(1)} at its weakest site`,64,551,1152,53,29,green,true);
footer(s,'Within-site treatment-balanced percentiles. Observed evidence, not a forecast. Some treatment cells have one replicate.');
talk.push(notes(s,`This is the observed shortlist, not a model-generated claim. All five candidates are above the median at every site. HOEGEMEYER 8065RR leads with an average percentile of ${c.shortlist[0].average_percentile.toFixed(1)} and a weakest-site percentile of ${c.shortlist[0].worst_site_percentile.toFixed(1)}. The table makes the trade-off visible: a high average does not necessarily mean uniform performance. Our rule requires above-median results at at least four sites, then ranks by the equal-site average. We retain replicate counts because some treatment cells have only one plot. These candidates warrant further replicated trials, not a claim of proven adaptation across seasons.`,'outputs/broad_performance/observed_hybrids.csv; observed_site.csv. Crawfordsv. denotes Crawfordsville; Missouri V. denotes Missouri Valley.'));

// 4. Native matched-nitrogen contrast chart.
const ns=[...c.nitrogen_sites].sort((a,b)=>a.mean_difference-b.mean_difference);
s=addSlide('Nitrogen contrasts change with the site','Same hybrid, same site: observed yield at 150 minus 75 lb nitrogen/acre');
chart(s,{...baseChart,position:{left:64,top:226,width:835,height:363},categories:ns.map(r=>r.location),
  series:[{name:'Observed yield difference',values:ns.map(r=>Number(r.mean_difference.toFixed(1))),fill:accent,valuesFormatCode:'+0.0;-0.0;0.0',points:ns.map((r,idx)=>({idx,fill:r.mean_difference<0?gold:accent}))}],
  barOptions:{direction:'column',grouping:'clustered',gapWidth:100},xAxis:{...baseChart.xAxis,tickLabelPosition:'low'},yAxis:{...baseChart.yAxis,min:-30,max:40,majorUnit:10,title:{text:'Yield difference (bu/ac)',textStyle:{typeface:font,fontSize:22}}}});
text(s,`${c.nitrogen_matched_pairs}`,960,241,250,91,64,green,true);
text(s,'matched hybrid-site\ncomparisons',962,334,240,74,25,green);
text(s,`${c.nitrogen_equal_site_difference>=0?'+':''}${c.nitrogen_equal_site_difference.toFixed(1)} bu/ac`,960,454,260,58,38,green,true);
text(s,'equal-site mean',962,516,250,45,24,muted);
footer(s,'Descriptive contrasts. Field placement can contribute to differences. No optimal-rate or isolated irrigation claim.');
talk.push(notes(s,`Management responses also depend on the environment. We matched 84 hybrids at two nitrogen rates within each of four locations, giving ${c.nitrogen_matched_pairs} hybrid-site comparisons. The observed difference ranges from ${ns[0].mean_difference.toFixed(1)} bushels per acre at ${ns[0].location} to plus ${ns.at(-1).mean_difference.toFixed(1)} at ${ns.at(-1).location}. The equal-site mean is plus ${c.nitrogen_equal_site_difference.toFixed(1)}, but that single number hides the variation. Because treatments can occupy separate experiments, these are descriptive contrasts rather than fertilizer prescriptions. Missouri Valley has only one rate, and irrigation is site-associated, so neither supports an independent dose or irrigation effect.`,'outputs/broad_performance/nitrogen_pairs.csv; nitrogen_sites.csv; comparison is 150 minus 75 lb N/acre; 84 matched hybrids at each of four sites.'));

// 5. Honest forecast evidence, all baselines retained.
const metrics=data.overall_yield_metrics.filter(r=>r.cutoff===90);
const models=['mean','agronomy','combined','ridge_agronomy','ridge_combined'];
const labels=['Training mean','CatBoost agronomy','CatBoost combined','Ridge agronomy','Ridge combined'];
const ridgeRank=c.ranking_by_model_cutoff.find(r=>r.model==='ridge_combined'&&r.cutoff===90);
const catRank=c.ranking_by_model_cutoff.find(r=>r.model==='combined'&&r.cutoff===90);
s=addSlide('Satellite forecasts tested at unseen locations','Day 90: five held-out-site folds, with separate tests of yield and hybrid ranking');
chart(s,{...baseChart,position:{left:64,top:225,width:744,height:333},categories:labels,
  series:[{name:'MAE',values:models.map(m=>Number(metrics.find(r=>r.model===m).mae.toFixed(1))),fill:accent,valuesFormatCode:'0.0',points:models.map((m,idx)=>({idx,fill:m==='mean'?'#92988F':m.includes('combined')?accent:'#B4BCAC'}))}],
  barOptions:{direction:'bar',grouping:'clustered',gapWidth:65},xAxis:{...baseChart.xAxis,textStyle:{typeface:font,fontSize:20,fill:green}},
  yAxis:{...baseChart.yAxis,min:0,max:80,majorUnit:20,title:{text:'MAE (bu/ac), lower is better',textStyle:{typeface:font,fontSize:20}}}});
text(s,`${ridgeRank.top10_overlap.toFixed(1)} / 10`,883,237,320,74,53,green,true);
text(s,'Observed top-10 hybrids\nrecovered by Ridge, on average',887,323,315,89,25,green);
text(s,`CatBoost: ${catRank.top10_overlap.toFixed(1)} of 10\nRandom: ${(100/84).toFixed(1)} of 10`,887,436,315,84,24,muted);
text(s,'Mean absolute error (bu/ac), lower is better',268,548,546,34,21,muted);
text(s,'Next: advance the shortlist to replicated trials and validate on 2023',64,585,1152,54,29,green,true);
footer(s,'Ridge is exploratory development on 2022, with nested tuning. Forecasts remain imperfect; no cross-season claim.');
talk.push(notes(s,`We tested forecasting by withholding each location entirely. At day 90, the training-mean baseline has an error of ${c.day90_mean_mae.toFixed(1)} bushels per acre. CatBoost with imagery reaches ${c.day90_combined_mae.toFixed(1)}, and our exploratory Ridge comparison reaches ${c.day90_ridge_combined_mae.toFixed(1)}. Yield error alone is insufficient for hybrid selection. Ridge recovers ${ridgeRank.top10_overlap.toFixed(1)} of the observed top ten hybrids per site on average, compared with ${catRank.top10_overlap.toFixed(1)} for CatBoost and about ${(100/84).toFixed(1)} expected at random. This is useful but imperfect evidence. Our proposal is to advance the observed shortlist into replicated trials and validate the frozen forecasting pipeline on 2023 before claiming cross-season reliability.`,'outputs/broad_performance/yield_metrics.csv; ranking_metrics.csv; ridge_fold_audit.json. Ridge alpha selected from 1,10,100 using inner site folds; additional comparisons are exploratory after initial 2022 inspection.'));

await fs.writeFile(path.join(workspaceDir,'deliverables/FieldSignal_talk_track.md'),talk.map((x,i)=>`## Slide ${i+1}\n\n${x}`).join('\n\n'),'utf8');
const candidate=path.join(TMP,'candidate.pptx');
await (await PresentationFile.exportPptx(P)).save(candidate);
for(let i=0;i<5;i++){
 const slide=P.slides.getItem(i);
 const png=await P.export({slide,format:'png',scale:1});
 await fs.writeFile(path.join(TMP,`slide-${i+1}.png`),new Uint8Array(await png.arrayBuffer()));
 const layout=await slide.export({format:'layout'});
 await fs.writeFile(path.join(TMP,`slide-${i+1}.layout.json`),await layout.text());
}
const result=await finalizePresentation({workspaceDir,candidatePath:candidate,finalPath:FINAL,pythonExecutable:RUNTIME_PYTHON,
 integrityValidatorPath:path.join(SKILL_DIR,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(SKILL_DIR,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','3'],
 explicitTotalSlideCount:5,requiredNativeTableOwnerSlides:[3],requiredNativeChartOwnerSlides:[2,4,5],
 materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,
 receiptPath:path.join(TMP,'validation-v2.json')});
console.log(JSON.stringify(result));
const checked=await PresentationFile.importPptx(await FileBlob.load(FINAL));
for(let i=0;i<5;i++){
 const png=await checked.export({slide:checked.slides.getItem(i),format:'png',scale:1});
 await fs.writeFile(path.join(TMP,`final-slide-${i+1}.png`),new Uint8Array(await png.arrayBuffer()));
}
