"""Select the visible fixed-palette material/conjuration cohort, source-only."""
from pathlib import Path
import csv,json,hashlib,sys,math
from collections import Counter
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from bam_export import decode_bam
from export_bam_frames import read_bam,cycle_metadata
OUT=ROOT/'effects/batches/lot26-material-organic-summons-proposal-20261017-v1'
GROUPS={
 'matieres-brumes-essaims':'OHBENVLP SPHEART SPINSECT SPIPLAAI SPIPLAUI SPMELBD1 TRGOOYAA TRGOOYBB TRVENTAA TRVENTBB WRITHING'.split(),
 'apparitions-conjurations':'OHRFEAR SPANISUM SPHANDAT SPPROIMG SPRAISED SPSUMGTE'.split(),
 'objets-pieges-eclats':'GLPHWRDT SKLT SPBLBBTM SPBLBTOP SPGLBBLD SPSTONES SPTRAPBB TRAPGR TRSPEART'.split(),
}
ALIASES={'SPIPLAAI':['SPIPLARI']}
def rows(n):return list(csv.DictReader((ROOT/n).open(encoding='utf-8-sig',newline='')))
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 raw=(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
 if p.exists():assert p.read_bytes()==raw,p
 else:p.write_bytes(raw)
def sha(raw):return hashlib.sha256(raw).hexdigest().upper()
def main():
 work={x['resref']:x for x in rows('effects/index/work-items.csv')}
 source={x['resref']:x for x in rows('effects/index/bam-assets.csv')}
 state={x['asset_key'].rsplit(':',1)[-1]:x for x in rows('effects/index/processing.csv')}
 consumers=rows('effects/index/consumers.csv')
 old=[work[n] for n in work if state[n]['spatial_state']!='not-started' or state[n]['qa_state'] in ('passed','native')]
 old_hashes={x['canonical_sha256'] for x in old}
 anims={p.stem.upper() for p in (ROOT/'animations/index/selections').glob('*.json')}
 selected=[]; audits=[]
 for group,names in GROUPS.items():
  for name in names:
   w=work[name];s=state[name];src=source[name]
   assert w['source_state']=='available' and w['usage']=='known'
   assert s['spatial_state']=='not-started' and not s['selected_run']
   assert name not in anims and w['canonical_sha256'] not in old_hashes
   assert 'palette' not in w['tags']
   assert sha((ROOT/src['extracted_path']).read_bytes())==src['source_sha256']
   raw=read_bam(ROOT/src['extracted_path']);assert sha(raw)==w['canonical_sha256']
   frames,palette,tr=decode_bam(raw);cycles=cycle_metadata(raw,len(frames))
   l=min(-cx for _,cx,_,_ in frames);t=min(-cy for _,_,cy,_ in frames)
   r=max(-cx+idx.shape[1] for idx,cx,_,_ in frames);b=max(-cy+idx.shape[0] for idx,_,cy,_ in frames)
   keys=[]
   for idx,cx,cy,_ in frames:
    canvas=np.zeros((b-t,r-l,4),np.uint8);x=-cx-l;y=-cy-t
    canvas[y:y+idx.shape[0],x:x+idx.shape[1],:3]=palette[idx]
    canvas[y:y+idx.shape[0],x:x+idx.shape[1],3]=(idx!=tr).astype(np.uint8)*255
    canvas[canvas[:,:,3]==0]=0;keys.append(sha(canvas.tobytes()))
   audit=[]
   for c in cycles:
    hashes=[keys[i] for i in c['frame_indices']]
    audit.append({'cycle':c['cycle'],'slots':len(hashes),'distinct_anchored_rgba':len(set(hashes)),
      'repeated_slots':len(hashes)-len(set(hashes)),
      'adjacent_duplicate_slots':[i for i in range(1,len(hashes)) if hashes[i]==hashes[i-1]],
      'constant_native_cycle':len(set(hashes))<=1})
   audits.append({'resref':name,'cycles':audit})
   aliases=ALIASES.get(name,[])
   for n in aliases:
    assert work[n]['canonical_sha256']==w['canonical_sha256']
    assert state[n]['spatial_state']=='not-started' and not state[n]['selected_run']
   owners=[c for c in consumers if c['asset_key'].rsplit(':',1)[-1] in [name]+aliases]
   selected.append({'ordinal':len(selected)+1,'asset_key':w['asset_key'],'resref':name,'group':group,
     'source':src['extracted_path'],'source_sha256':src['source_sha256'],'canonical_sha256':w['canonical_sha256'],
     'reuse_aliases':aliases,'source_frames':len(frames),'native_cycles':cycles,
     'max_frame_x1':[max(f[0].shape[1] for f in frames),max(f[0].shape[0] for f in frames)],
     'native_fps':w['native_fps'],'playback':w['playback'],'static':w['static']=='1',
     'raw_x4_bytes_at_native_records':int(w['raw_x4_bytes']),'consumers':owners,
     'production':{k:s[k] for k in ('spatial_state','interpolation_state','qa_state','installation_state')}})
 assert len(selected)==26 and len({a['canonical_sha256'] for a in selected})==26
 summary={'distinct_productions':26,'covered_resrefs':27,'source_frames':sum(a['source_frames'] for a in selected),
   'native_cycles':sum(len(a['native_cycles']) for a in selected),
   'native_cycle_slots_alternative_not_global_duration':sum(len(c['frame_indices']) for a in selected for c in a['native_cycles']),
   'raw_x4_bytes_at_native_records':sum(a['raw_x4_bytes_at_native_records'] for a in selected),
   'group_counts':{k:len(v) for k,v in GROUPS.items()},'static_assets':[a['resref'] for a in selected if a['static']],
   'assets_with_native_duplicate_slots':sum(any(c['repeated_slots'] for c in a['cycles']) for a in audits),
   'native_repeated_slots':sum(c['repeated_slots'] for a in audits for c in a['cycles']),
   'constant_native_cycles':sum(c['constant_native_cycle'] for a in audits for c in a['cycles']),
   'vvc_assets':sum(any(c['owner_route']=='vvc' for c in a['consumers']) for a in selected),
   'projectile_assets':sum(any(c['owner_route']=='projectile' for c in a['consumers']) for a in selected)}
 proposal={'schema':'bg2-effects-batch-proposal-v1','date':'2026-10-17','status':'proposed-native-preview',
   'assets_count':26,'family':'Figurative magical effects: matter, swarms, apparitions, blades and traps',
   'summary':summary,'subgroups':GROUPS,'aliases':ALIASES,
   'selection_basis':{'known_candidates_inspected':51,'other_candidates_inspected':98,
    'excluded':'current productions, accepted animation resources, canonical duplicates already produced; character animations BDETHREA/MSOLG1; native shadows/black-only masks; runtime palette-dependent projectiles; consumers not established',
    'scope':'largest retained visible fixed-palette cohort with known owners; visually related subgroups, independent native alpha/playback contracts'},
   'proposed_processing':{'spatial':'SeedVR7B x4 RGB; source silhouette, anchors, fine insect/blade details retained; contour treatment per subgroup',
    'temporal':'Apollo30 per native cycle, remove duplicate poses then redistribute over unchanged native duration; preserve constant cycles; TRAPGR static',
    'render':'straight-alpha normal consumers; premultiplied Blended consumers. SPIPLAAI/SPIPLARI share pixels but have mixed consumers.',
    'rate':'VVC field 15FPS; PRO cadence requires confirmation, no cadence measurement inferred',
    'production_started':False},'assets':selected}
 save(OUT/'batch.json',proposal);save(OUT/'native-duplicate-audit.json',{'summary':summary,'assets':audits})
 review=ROOT/'effects/batches/next-lot-inspection-20261017-v1'
 known=[w for w in json.loads((review/'candidates.json').read_text(encoding='utf-8'))['candidates'] if w['usage']=='known']
 positions={w['resref']:i for i,w in enumerate(known)}
 sheet=Image.new('RGB',(1280,64+6*178),(14,16,21));d=ImageDraw.Draw(sheet)
 font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',22)
 d.text((12,10),'Lot26 - matieres, apparitions, objets et essaims',font=font,fill='white')
 d.text((12,36),'26 productions / 27 RESREF - sources natives uniquement',font=font,fill=(155,180,210))
 for j,a in enumerate(selected):
  k=positions[a['resref']]; page=Image.open(review/f'known-{k//30+1}.png');k%=30
  tile=page.crop(((k%5)*256,(k//5)*178,(k%5+1)*256,(k//5+1)*178))
  sheet.paste(tile,((j%5)*256,64+(j//5)*178))
 (OUT/'preview').mkdir(exist_ok=True);sheet.save(OUT/'preview/native.png')
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
