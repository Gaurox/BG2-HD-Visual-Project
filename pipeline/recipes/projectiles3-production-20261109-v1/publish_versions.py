"""Review both spatial methods, defaulting to the faithful xBR alternative."""
import copy,json,shutil,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import effect_workflow as w
import effect_authority as authority
BASE=ROOT/'effects/batches/projectiles3-production-20261109-v1';ALT=BASE/'alternatives/xbr4x-20261109-v1';OUT=BASE/'review-versions'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 import temporal
 temporal.BATCH=ALT
 import companions
 companions.BATCH=ALT
 alt=load(ALT/'batch.json')
 for a in alt['assets']:a['variant_suffix']='xbr4x';companions.build(a)
 cards=[]
 for version,prefix,folder in [('xBR4X','xbr',ALT/'review'),('SeedVR7B','seed',BASE/'review')]:
  target=OUT/prefix;shutil.copytree(folder,target,dirs_exist_ok=True)
  for a in load(BASE/'batch.json')['assets']:
   c=load(folder/'data'/f"{a['resref']}.json");c['version']=version
   c['native']['image']=prefix+'/'+c['native']['image']
   for f in c['frames']:
    for k in ['image','neutral']:
     if k in f:f[k]=prefix+'/'+f[k]
   cards.append(c)
 template=(HERE/'board.html').read_text(encoding='utf-8')
 template=template.replace('SeedVR7B x4 + Apollo30','xBR4X / SeedVR7B + Apollo30').replace('Fumées BGLRYU/SPCL236U et fragments SPGLYPHI.','Fumées BGLRYU/SPCL236U et fragments SPGLYPHI. xBR fidèle affiché par défaut ; SeedVR7B disponible pour comparaison.')
 template=template.replace('<input id="search"', '<label>Version <select id="method"><option value="xBR4X">xBR4X fidèle</option><option value="SeedVR7B">SeedVR7B détaillé</option><option value="all">Les deux versions</option></select></label><input id="search"')
 template=template.replace('${a.resref}</h2>','${a.resref} · ${a.version}</h2>').replace('SeedVR7B x4 · Apollo30</div>','${a.version} x4 · Apollo30</div>')
 template=template.replace("$('main').append(el);","el.classList.toggle('hidden',a.version!=='xBR4X');$('main').append(el);")
 start=template.index("$('#search').oninput=");end=template.index('</script>',start)
 template=template[:start]+"function filter(){const q=$('#search').value.trim().toUpperCase(),m=$('#method').value;let n=0;cards.forEach(c=>{const show=c.a.resref.includes(q)&&(m==='all'||c.a.version===m);c.el.classList.toggle('hidden',!show);n+=show});$('#counter').textContent=n+' versions / 3 projectiles'};$('#search').oninput=filter;$('#method').onchange=filter;filter();\n"+template[end:]
 html=template.replace('__CARDS__',json.dumps(cards,ensure_ascii=False));(OUT/'index.html').write_text(html,encoding='utf-8')
 js=ROOT/'.tmp/projectiles3-20261109-v1/versions.js';js.write_text(re.search(r'<script>(.*?)</script>',html,re.S)[1],encoding='utf-8');subprocess.run(['node','--check',str(js)],check=True)
 original=load(BASE/'production.json');current=copy.deepcopy(original)
 by={a['resref']:a for a in alt['assets']}
 for a in current['assets']:
  n=a['resref'];r=load(ALT/'runtime-verification'/f'{n}.json');a.update({k:v for k,v in r.items() if k not in ('qa','passed')});a.update(spatial_run=by[n]['spatial_run'],interpolation_run=by[n]['interpolation_run'],method='XBR/xbr4X',companions=load(ALT/'runtime-verification'/f'{n}-companions.json')['companions'],seedvr_version=next(s for s in original['assets'] if s['resref']==n))
 current['summary'].update(backings=sum(a['backings'] for a in current['assets']),native_contracts_all_review_versions=4320)
 current.update(board='http://127.0.0.1:8800/',review_directory=OUT.relative_to(ROOT).as_posix(),default_version='xBR4X',seedvr_production='effects/batches/projectiles3-production-20261109-v1/production.json',decision='Technical default xBR for fidelity; manual visual acceptance remains pending. SeedVR adds invented geometric motifs in native halos, retained as alternate.')
 save(BASE/'production-current-v2.json',current);save(BASE/'current-production.json',dict(path='effects/batches/projectiles3-production-20261109-v1/production-current-v2.json',sha256=w.sha256_file(BASE/'production-current-v2.json')))
 completion=load(ROOT/'effects/index/completion.json');completion['processing_sha256']=w.sha256_file(ROOT/'effects/index/processing.csv');completion['extension']='effects/batches/projectiles3-production-20261109-v1/production-current-v2.json'
 with authority.guard(ROOT,True):authority.commit(ROOT,{'effects/index/completion.json':w.json_bytes(completion)})
 # A new sample sheet preserves the initial SeedVR comparison unchanged.
 import finalize
 finalize.BATCH=BASE
 original_contact=finalize.contact
 # contact writes a working image; preserve the existing baseline explicitly.
 before=(BASE/'comparison.png').read_bytes();original_contact({**alt,'display_method':'xBR4X'});(BASE/'comparison-xbr.png').write_bytes((BASE/'comparison.png').read_bytes());(BASE/'comparison.png').write_bytes(before)
 print('Published 3 projectiles / 6 versions; xBR faithful default; QA pending.')
if __name__=='__main__':main()
