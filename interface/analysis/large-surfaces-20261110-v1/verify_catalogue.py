import sys,json,csv,zlib,struct,re
from pathlib import Path
sys.path.insert(0,'pipeline/scripts')
from bg2lib import load_key,resolve_resource,GAME_DIR
p=Path('interface/analysis/large-surfaces-20261110-v1');g=Path(GAME_DIR);b,e=load_key();idx={(n.upper(),k):l for n,k,l in e};known={r['resref'] for r in json.loads((p/'inventory.json').read_text(encoding='utf-8'))['resources']}
def read(n,k,ext):
 f=g/'override'/f'{n}.{ext}'
 return (f.read_bytes(),'override') if f.exists() else resolve_resource(b,idx[n,k])
mos=[];bam=[]
for n,k in sorted(idx):
 if k!=1004:continue
 raw,src=read(n,k,'mos');raw=zlib.decompress(raw[12:]) if raw[:4]==b'MOSC' else raw
 if raw[:8]==b'MOS V1  ':w,h=struct.unpack_from('<HH',raw,8)
 elif raw[:8]==b'MOS V2  ':w,h=struct.unpack_from('<II',raw,8)
 else:continue
 if n not in known:mos.append(dict(resref=n,width=w,height=h,source=src))
rows=list(csv.DictReader(open('interface/index/resources.csv',encoding='utf-8-sig')))
for row in rows:
 n=row['resref']
 if row['format']!='BAM' or n in known:continue
 raw,src=read(n,1000,'bam');raw=zlib.decompress(raw[12:]) if raw[:4]==b'BAMC' else raw
 if raw[:8]==b'BAM V1  ':count=struct.unpack_from('<H',raw,8)[0];off=struct.unpack_from('<I',raw,12)[0]
 elif raw[:8]==b'BAM V2  ':count,_,_,off=struct.unpack_from('<4I',raw,8)
 else:continue
 dims=[struct.unpack_from('<HH',raw,off+i*12) for i in range(count)]
 w,h=max(dims,key=lambda x:x[0]*x[1]) if dims else (0,0)
 if w*h>=10000:bam.append(dict(resref=n,width=w,height=h,frames=count,source=src))
texts={}
for n,k in idx:
 if k==1032:texts[n+'.menu']=read(n,k,'menu')[0].decode('utf-8-sig',errors='replace')
for f in (g/'override').iterdir():
 if f.suffix.lower() in ('.lua','.menu'):texts[f.name]=f.read_text(encoding='utf-8-sig',errors='replace')
hits=[]
for file,s in texts.items():
 for line,t in enumerate(s.splitlines(),1):
  if re.search(r'GUIBG|GUINOTE',t,re.I):hits.append(dict(file=file,line=line,text=t))
report=dict(mos_not_in_catalogue=mos,large_bam_not_in_catalogue=bam,unresolved_reference_context=hits,text_sources=list(texts))
(p/'verification-pass.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('MOS missing',len(mos));print('BAM candidates',bam);print('unresolved',hits);print('MOS nonmap', [r for r in mos if not re.match(r'^(AR|OH|BD|BP|BG|MP)',r['resref'])]);print('text sources',list(texts))
