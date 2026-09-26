"""Check pitch claims against evidence and package final deliverables."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"deliverables/IoT4Ag"
d=json.loads((ROOT/"outputs/decision_brief/claims.json").read_text())
c=json.loads((ROOT/"outputs/broad_performance/claims.json").read_text())
metrics={(r["cutoff"],r["model"]):r for r in d["overall"]}
for model,mae,hits in [("mean",55.1,7),("nitrogen",59.7,6),("agronomy",72.1,24),("combined",45.5,30)]:
    r=metrics[75,model]
    assert round(r["mae"],1)==mae and r["hits"]==hits and r["k"]==50 and r["target_n"]==428
assert round(metrics[90,"combined"]["mae"],1)==44.0 and metrics[90,"combined"]["hits"]==31
assert [r["hits"] for r in d["warning"]]==[163,141]
assert len(c["shortlist"])==5 and all(h["sites_above_median"]==5 for h in c["shortlist"])
q=pd.read_csv(OUT/"tables/scouting_queue.csv")
assert "yieldPerAcre" not in q.columns
for name in ["model_comparison","warning_evaluation","ranking_comparison","case_examples","scouting_queue"]:
    assert (OUT/f"tables/{name}.csv").read_bytes()==(ROOT/f"outputs/decision_brief/{name}.csv").read_bytes()
for name in ["forecast_hybrids","forecast_site"]:
    shutil.copy2(ROOT/f"outputs/broad_performance/{name}.csv",OUT/f"tables/{name}.csv")
(OUT/"methods").mkdir(exist_ok=True)
shutil.copy2(ROOT/"outputs/decision_brief/nitrogen_fold_audit.json",OUT/"methods/nitrogen_fold_audit.json")
shutil.copy2(ROOT/"outputs/broad_performance/ridge_fold_audit.json",OUT/"methods/ridge_fold_audit.json")
shutil.copy2(ROOT/"outputs/run_config.json",OUT/"methods/run_config.json")
shutil.copy2(ROOT/"outputs/broad_performance/claims.json",OUT/"methods/broad_performance_claims.json")
manifest={str(p.relative_to(OUT)).replace("\\","/"):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.rglob("*") if p.is_file() and p.name!="manifest.json"}
(OUT/"manifest.json").write_text(json.dumps(manifest,indent=2))
archive=ROOT/"FieldSignal_IoT4Ag_package.zip"
with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z:
    for p in OUT.rglob("*"):
        if p.is_file(): z.write(p,Path("FieldSignal_IoT4Ag")/p.relative_to(OUT))
with zipfile.ZipFile(archive) as z: assert z.testzip() is None
words=len((OUT/"talk_track.md").read_text().split())
print(f"Verified claims and archive: {archive}; {len(manifest)+1} files; talk track {words} words")
