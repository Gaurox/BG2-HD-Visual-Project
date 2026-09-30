from pathlib import Path
import csv,hashlib,json
import numpy as np

HERE=Path(__file__).resolve().parent
CLAUDE=Path('C:/Users/Adrien/Desktop/ClaudeCode_Guide_HD_0x6110_Femme_Humaine_Guerriere')
given=json.loads((CLAUDE/'donnees_v2/e3b_results.json').read_text())
repro=json.loads((HERE/'reproduction_e3b/e3_results.json').read_text())
checks=json.loads((HERE/'reproduction_e3b/codex_recheck.json').read_text())
methods=['Q0_used_nodither','Q2_bayer4','Q6_idx_multipal','Q3_frac_ref','Q3m_frac_multipal','Q8_frac_multipal_boundary','Q7_errdiff']
temporal=[]
for scale in (2,4):
 for method in methods:
  result={'scale':scale,'method':method}
  for name,field in [('original','original_flicker'),('corrected','corrected_flicker')]:
   values=[v for k,v in checks[field].items() if f'|x{scale}|{method}|' in k]
   result[name+'_mean_all_percent']=100*np.mean([v['flicker_ratio'] for v in values if v['flicker_ratio'] is not None])
   result[name+'_weighted_all_percent']=100*sum(v['flicker_ratio']*v['static_px'] for v in values if v['static_px'])/sum(v['static_px'] for v in values)
   for pn in ['REF','B']:
    v=checks[field][f'body|x{scale}|{method}|{pn}']
    result[name+'_body_'+pn+'_percent']=100*v['flicker_ratio']
    result[name+'_body_'+pn+'_support']=v['static_px']
  temporal.append(result)
precision=[]
for scale in (2,4):
 for pn in given['palettes']:
  entries=[r for r in checks['q8_three_bit_records'] if r['scale']==scale and r['palette']==pn]
  pixels=sum(e['pixels'] for e in entries)
  precision.append({'scale':scale,'palette':pn,'q8_original_4bit_mean':repro['summary'][f'x{scale}|Q8_frac_multipal_boundary|{pn}']['de_mean'],
                    'q8_3bit_mean':sum(e['de_mean']*e['pixels'] for e in entries)/pixels,
                    'changed_rgb_fraction':sum(e['changed_rgb_fraction']*e['pixels'] for e in entries)/pixels})
def aligned_error(sign):
 world=np.arange(10);a=world[2:8];b=world[1:9];ca=3;cb=4
 ox=sign*(cb-ca);lo=max(0,ox);hi=min(len(a),len(b)+ox)
 return {'compared':hi-lo,'mismatch_count':int(np.sum(a[lo:hi]!=b[lo-ox:hi-ox]))}
summary={'original_files_sha256':{},
         'reproduced_max_abs_de_delta':max(abs(v['de_mean']-repro['summary'][k]['de_mean']) for k,v in given['summary'].items()),
         'reproduced_max_abs_flicker_delta':max(abs(v['flicker_ratio']-checks['original_flicker'][k]['flicker_ratio']) for k,v in given['flicker'].items() if v['flicker_ratio'] is not None),
         'synthetic_same_world_different_crop':{'claude_alignment':aligned_error(1),'correct_alignment':aligned_error(-1)},
         'temporal':temporal,'precision':precision,'boundary_channel_support':checks['boundary_channel_support']}
for name in ['GUIDE_ClaudeCode_HD_0x6110_palettes_dynamiques.md','PRESENTATION_ClaudeCode_0x6110.html','outils/e3b_experiment.py','donnees_v2/e3b_results.json']:
 summary['original_files_sha256'][name]=hashlib.sha256((CLAUDE/name).read_bytes()).hexdigest()
(HERE/'verification_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
for name,rows in [('temporal_corrected.csv',temporal),('precision_3bits.csv',precision)]:
 with (HERE/name).open('w',newline='',encoding='utf-8-sig') as f:
  writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
print(json.dumps(summary,indent=2))
