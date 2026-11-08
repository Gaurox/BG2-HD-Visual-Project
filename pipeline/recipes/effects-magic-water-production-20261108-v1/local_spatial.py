"""Seven small-source xBR productions; own palette, native geometry, recorded algorithms."""
import sys,json,copy,shutil
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_effect_spatial as sp
from run_creature_sprite_x2 import run_xbr,direct_upscale_contract,XBR_ADAPTER
from run_animation_small_subject_xbr2 import run_xbr2x,nearest_x2
from workspace_paths import get_path
from upscale_animation_frames import make_contact_sheet
from export_bam_frames import read_bam
from bam_export import decode_bam,native_palette_alpha
BATCH=ROOT/'effects/batches/lot50-magic-water-production-20261108-v1'
load=sp.load_json;save=sp.write_json
def produce(a):
 n=a['resref'];p=sp.build_plan(ROOT,n,a['spatial_run'],'xbr-small-source-x4',Path('pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json'),server='http://127.0.0.1:8188',pad=0,poll_seconds=.2,timeout_seconds=1800,upload_folder='unused',color_correction_method='lab')
 if p.descriptor_path.exists() and load(p.descriptor_path).get('result',{}).get('sealed'):return
 if not p.run_root.exists():sp.reserve_plan(p)
 source=sp._ensure_source(p);fm=sp.export_frames(p,source,p.frame_root.exists());cw,ch=fm['aligned_canvas_size']
 arrays=[np.array(Image.open(p.frame_root/'rgba'/f['file']).convert('RGBA')) for f in fm['frames']]
 scalepix=get_path('mmpx_scalepix',required=True)
 bubble=n=='BUBLES';body=n=='WTRBODY2'
 if bubble or body:
  # Same algorithm as accepted AMOH7300, using this source's own palette.
  arrays4=[nearest_x2(x) for x in run_xbr2x(arrays,scalepix,'node',bubble)]
 else:
  inputs=[]
  for f in fm['frames']:
   rgb=np.array(Image.open(p.frame_root/'rgb'/f['file']).convert('RGB'));rgba=np.dstack((rgb,np.full(rgb.shape[:2],255,np.uint8)))
   inputs.append(SimpleNamespace(width=cw,height=ch,rgba=rgba.tobytes()))
  outputs=run_xbr(inputs,scalepix,'node',direct_upscale_contract(4));arrays4=[np.frombuffer(b,np.uint8).reshape(h,w,4).copy() for w,h,b in outputs]
  for rgba,f in zip(arrays4,fm['frames']):rgba[:,:,3]=np.array(Image.open(p.frame_root/'alpha'/f['file'])).repeat(4,0).repeat(4,1)
 stage=p.spatial_root;stage.mkdir(parents=True,exist_ok=True);records=[];images=[]
 for f,rgba in zip(fm['frames'],arrays4):
  ox,oy=f['canvas_offset'];sw,sh=f['source_size'];box=[ox*4,oy*4,(ox+sw)*4,(oy+sh)*4]
  # Restrict processed alpha to native rectangle; no runtime geometry enlargement.
  keep=np.zeros(rgba.shape[:2],bool);keep[box[1]:box[3],box[0]:box[2]]=True;rgba[~keep,3]=0;rgba[rgba[:,:,3]==0]=0
  aligned=Image.fromarray(rgba);crop=aligned.crop(tuple(box));name=f['file']
  row=dict(frame=f['frame'],source_rgb=name,source_rgb_sha256=f['rgb_sha256'],source_alpha=name,source_alpha_sha256=f['alpha_sha256'],aligned_size_x1=[cw,ch],logical_size_x1=[sw,sh],physical_size_xn=[sw*4,sh*4],centre_x1=f['centre'],canvas_offset_x1=[ox,oy],runtime_crop_box_xn=box)
  for key,folder,im in [('aligned_rgba_xn','aligned_rgba',aligned),('rgba_xn','rgba',crop),('rgb_xn','rgb',crop.convert('RGB')),('alpha_xn','alpha',crop.getchannel('A'))]:
   target=stage/folder/name;target.parent.mkdir(exist_ok=True);im.save(target);row[key]=folder+'/'+name;row[key+'_sha256']=sp.workflow.sha256_file(target)
  raw=stage/'raw_rgba'/Path(name).with_suffix('.rgba');raw.parent.mkdir(exist_ok=True);raw.write_bytes(crop.tobytes());row.update(raw_rgba_xn='raw_rgba/'+raw.name,raw_rgba_xn_sha256=sp.workflow.sha256_file(raw));records.append(row);images.append(stage/row['rgba_xn'])
 preview=stage/'preview/contact.png';make_contact_sheet(images,preview)
 model='XBR/xbr2blend-nearest2' if bubble else 'XBR/xbr2-nearest2' if body else 'XBR/xbr4X'
 m=dict(schema=sp.SPATIAL_SCHEMA,status='completed',scale=4,geometry_mode='per-frame',aligned_canvas_size_x1=[cw,ch],source=dict(frame_manifest=sp.workflow.relative_path(ROOT,p.frame_root/'manifest.json'),frame_manifest_sha256=sp.workflow.sha256_file(p.frame_root/'manifest.json')),parameters=dict(model=model,color_correction_method='native',scale=4,blend_colors=bubble),alpha_policy='source RGBA xBR2blend then nearest2 clipped to native rectangle' if bubble else 'native alpha nearest4',frames=records,preview='preview/contact.png',preview_sha256=sp.workflow.sha256_file(preview),created_utc=sp.workflow.utc_now())
 recipe=dict(schema=sp.RECIPE_SCHEMA,pipeline_id=sp.PIPELINE_ID,recipe_id=model,scale=4,algorithm=model,blend_colors=bubble,tools=[sp.file_evidence(ROOT,'producer',Path(__file__)),sp.file_evidence(ROOT,'adapter',XBR_ADAPTER)],alpha_policy=m['alpha_policy'])
 save(p.recipe_path,recipe);save(stage/'manifest.json',m);sp.validate_frame_stage(ROOT,p.frame_root,source);sp.validate_spatial_stage(ROOT,stage,fm)
 outputs=[sp.file_evidence(ROOT,'frames-manifest',p.frame_root/'manifest.json'),sp.file_evidence(ROOT,'spatial-manifest',stage/'manifest.json'),sp.file_evidence(ROOT,'spatial-preview',preview)]
 save(p.descriptor_path,sp.build_descriptor(p,recipe,source,status='completed',sealed=True,created_at_utc=sp.workflow.utc_now(),outputs=outputs))
 sp.workflow.register_run(ROOT,n,'spatial',a['spatial_run'],write=True);print(n,model,'spatial complete',flush=True)
def reuse_diagnosis():
 result=[]
 for n,other in [('TRBLOBA','TRGOOYAA'),('TRBLOBB','TRGOOYBB')]:
  def dec(name):
   raw=read_bam(ROOT/'effects/ressources'/name/'source.bam');f,p,t=decode_bam(raw);return f,p,native_palette_alpha(raw,t)
  fs,p,al=dec(n);gs,q,bl=dec(other);shape=alpha=centres=0;pairs={};total=equal=0
  for f,g in zip(fs,gs):
   i,cx,cy,_=f;j,dx,dy,_=g;centres+=int((cx,cy)==(dx,dy))
   if i.shape!=j.shape:continue
   shape+=1;alpha+=int(np.array_equal(al[i],bl[j]));mask=(al[i]>0)&(bl[j]>0)
   total+=int(mask.sum());equal+=int(np.all(p[i][mask]==q[j][mask],axis=1).sum())
  result.append(dict(resref=n,parent=other,frames=len(fs),identical_size_frames=shape,identical_alpha_frames=alpha,identical_centres=centres,exact_visible_rgb_fraction=equal/total if total else None,decision='new-seedvr-spatial-own-source',reason='No exact RGBA pose reuse; distinct target contour/RGB and owner geometry. Whole spatial copy cannot reproduce target without new color/contour authoring; use authorized SeedVR fallback, preserve accepted parent.'))
 save(BATCH/'blob-reuse-decision.json',dict(assets=result))
def main():
 # Existing audit already establishes non-equality; retain compact source evidence.
 reuse_diagnosis()
 for a in load(BATCH/'batch.json')['assets']:
  if a['recipe_profile'] in {'X-TINY','A-BUBBLE'}:produce(a)
if __name__=='__main__':main()
