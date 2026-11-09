"""Materialize optional normal-alpha halo packs; canonical production retained."""
import copy,subprocess
from temporal import ROOT,BATCH,load,save,rel,digest
from compose_effect_runtime_packs import validate_pack
from build_effect_runtime_pack import write_pack
from runtime_profiles import PROBE

def build(a):
 name=a['resref'];base=validate_pack(ROOT/a['final_pack'])
 run=ROOT/'effects/ressources'/name/'runs'/a['interpolation_run'];stage=run/'02-interpolation'
 m=load(stage/'manifest.json');s=load(ROOT/m['parent']['spatial_manifest'])
 by={(f['raw_rgba_x4_sha256'],tuple(f['physical_size_x4'])):f for f in m['frames']}
 result=[]
 for kind,field in [('normal','straight_raw_rgba_x4'),('neutral','neutral_raw_rgba_x4')]:
  suffix=a.get('variant_suffix','x4')
  output=ROOT/'effects/ressources'/name/'packs'/f'{name.lower()}-{suffix}-apollo30-{kind}-20261109-v1'
  if not (output/'manifest.json').exists():
   assets=[]
   for f in base.frames:
    src=by[(f['sha256'],tuple(f['physical_size_x4']))];payload=(stage/src[field]).read_bytes()
    row={k:v for k,v in f.items() if k not in ('resref','resource_frame')}
    row.update(source=rel(stage/src[field]),sha256=digest(payload),bytes=len(payload),_payload=payload)
    assets.append(row)
   manifest=write_pack(output,(base.root/base.manifest['registry']).read_bytes(),assets,
     load(ROOT/'effects/ressources'/name/'runs'/a['spatial_run']/'run.json'),load(ROOT/s['source']['frame_manifest']),s,
     registry_version=3,timeline=copy.deepcopy(base.manifest['timeline']),interpolation_descriptor=load(run/'run.json'))
   manifest.update(rgb_encoding='straight',companion_kind=kind,canonical_parent=rel(base.root/'manifest.json'),
     alpha_policy='native palette alpha; linear native-slot interpolation' if kind=='normal' else 'luminous energy preserved within 1/255; black neutral alpha; optional normal consumer')
   save(output/'manifest.json',manifest)
  checked=validate_pack(output)
  log=BATCH/'runtime-verification'/f'{name}-{kind}.log'
  with log.open('w',encoding='utf-8') as f:subprocess.run([str(PROBE),'--catalogue-only',str(output),str(BATCH/'contracts'/f'{name}.tsv')],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
  result.append(dict(kind=kind,pack=rel(output),manifest_sha256=checked.manifest_sha256,encoding='straight',native_probe=rel(log),installed=False))
 save(BATCH/'runtime-verification'/f'{name}-companions.json',dict(resref=name,passed=True,companions=result))
 return result
if __name__=='__main__':
 for a in load(BATCH/'batch.json')['assets']:print(a['resref'],build(a))
