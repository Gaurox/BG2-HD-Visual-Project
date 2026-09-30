"""Does RGB inference/requantization depend on the player's chosen color profile?"""
from run_upscale_study import *

def run():
    descriptor,_=load_model(get_path('reboutcx_model'),device='cuda:0',fp16=True)
    classes=character_chmb1_classes(); rows=[]
    for key in ['CHFB1A1_0045','CHFF4A1_0045','WQNJ6A1_0006']:
        d=np.load(OUT/'samples'/key/'data.npz'); idx=d['source_indices']; guide=d['guide_x4']; visible=guide>1
        for profile in ['contrast','pale']:
            pal=character_chmb1_palette_rgb(d['ramps'][PROFILES[profile]])
            rgb=pal[idx]; nearest=distance_transform_edt(idx==0,return_distances=False,return_indices=True); filled=rgb[tuple(nearest)]
            target4,_=infer_x4_box_x2(descriptor,filled,fp16=True)
            q,_=quantize_classed_oklab(target4,guide,pal,np.arange(256),classes,transparent_index=0)
            ref=d['quant_full_x4']; dl=srgb_u8_to_oklab(pal[q])-srgb_u8_to_oklab(pal[ref])
            rows.append({'sample':key,'profile':profile,'changed_index_pct_visible':100*float(np.mean(ref[visible]!=q[visible])),'mean_oklab_render_difference':float(np.linalg.norm(dl[visible],axis=1).mean())})
            np.savez_compressed(OUT/'samples'/key/f'sensitivity_{profile}.npz',target_rgb_x4=target4,quant_full_x4=q,palette=pal)
            panel([(rgba(guide,pal),4),(rgba(ref,pal),4),(rgba(q,pal),4)],['XBR x4','Indices ref recolores','Inference autre profil'],key+' | profile '+profile+' | dependance chromatique; meme classe/alpha',OUT/'samples'/key/f'sensitivity_{profile}.png',8)
    (OUT/'palette_sensitivity.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps(rows,indent=2))
if __name__=='__main__':run()
