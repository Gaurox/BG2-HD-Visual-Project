"""Re-evaluate Claude E3b in a NEW Codex folder; never modify original study.
Only reviewed E3b code is executed. Uses the same inference and encodings, then
measures both temporal alignment signs and the proposed 3-bit Q8 payload.
"""
from pathlib import Path
import hashlib,json,sys
import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent
SOURCE=Path('C:/Users/Adrien/Desktop/ClaudeCode_Guide_HD_0x6110_Femme_Humaine_Guerriere/outils/e3b_experiment.py')
RUN=HERE/'reproduction_e3b'
RUN.mkdir(exist_ok=True)
ramps=np.array(Image.open(HERE.parent/'palette/MPALETTE.bmp').convert('RGB'))
np.save(HERE/'mpalette.npy',ramps)
text=SOURCE.read_text(encoding='utf-8')
start=text.index('    # temporal flicker on idle cycle')
end=text.index('    json.dump(',start)
original_loop=text[start:end]
correct_loop=original_loop.replace('(fb.center_x - fa.center_x)', '(fa.center_x - fb.center_x)').replace('(fb.center_y - fa.center_y)', '(fa.center_y - fb.center_y)')
correct_loop=correct_loop.replace('flicker = {}','flicker_corrected = {}').replace('flicker[f"','flicker_corrected[f"')
extra='''
    # Compare the measured 4-bit Q8 with its proposed 3-bit implementation.
    precision=[]
    supports={"weighted_boundary_pixels":0,"more_than_two_channels":0,"pure_secondary_pixels":0}
    def channels(c):
        name=CLASS_NAMES[int(c)]
        if name in SPECIAL:return set()
        if name.startswith('mix_'):return set(name[4:-5].split('_'))
        return {name}
    for lname, items in data.items():
        for it in items:
            for scale in (2,4):
                c,t,c2,t2,w=it[f'enc{scale}']['Q8_frac_multipal_boundary'][1]
                q=(c,np.round(t*8)/8,c2,np.round(t2*8)/8,w)
                mask=it[f'g{scale}']!=0
                weighted=(c2>=0)&(w>0)&(w<1)&mask
                supports['weighted_boundary_pixels']+=int(weighted.sum())
                supports['pure_secondary_pixels']+=int(((c2>=0)&(w==0)&mask).sum())
                for ca,cb in np.unique(np.stack((c[weighted],c2[weighted]),axis=-1),axis=0):
                    if len(channels(ca)|channels(cb))>2:
                        supports['more_than_two_channels']+=int((weighted&(c==ca)&(c2==cb)).sum())
                si=0 if scale==4 else 1
                for pn in PALETTES:
                    rec=frac2_render(q,PAL[pn])
                    mu,_=de(rec,it['gt'][pn][si],mask)
                    old=recon_store[(lname,it['cycle'],it['pos'],scale,'Q8_frac_multipal_boundary',pn)]
                    difference=float(np.mean(np.any(rec[mask]!=old[mask],axis=-1)))
                    precision.append(dict(layer=lname,cycle=it['cycle'],pos=it['pos'],scale=scale,palette=pn,de_mean=mu,pixels=int(mask.sum()),changed_rgb_fraction=difference))
    report={"source_sha256":SOURCE_SHA256,"original_flicker":flicker,
            "corrected_flicker":flicker_corrected,"q8_three_bit_records":precision,
            "boundary_channel_support":supports,"frac_bits_measured_by_original":FRAC_BITS,
            "idle_positions":IDLE_POSITIONS}
    (OUT/'codex_recheck.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    log('CODEX independent checks saved; skip duplicate visuals')
    return
'''
replacement='    log("metrics written")\n'+correct_loop+extra
assert text.count('    log("metrics written")')==1
modified=text.replace('    log("metrics written")',replacement)
sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
(HERE/'e3b_instrumented_codex.py').write_text(modified,encoding='utf-8')
sys.argv=[str(SOURCE),str(RUN),str(HERE/'mpalette.npy')]
exec(compile(modified,str(HERE/'e3b_instrumented_codex.py'),'exec'),{'__name__':'__main__','__file__':str(SOURCE),'SOURCE_SHA256':sha})
