"""Compare horizontal 4:3 -> 16:9 stretch, distinct from a crop/zoom hypothesis."""
import numpy as np
from PIL import Image
from compare import read, compare, save

def main():
    base=read('INTRO15F-default');other=read('INTRO15F-pl_PL')
    base['frames']=np.stack([np.asarray(Image.fromarray(np.asarray(f)).crop((20,0,140,90))
        .resize((160,90),Image.Resampling.LANCZOS)) for f in base['frames']])
    result=compare('INTRO15F-default-horizontal-stretch','INTRO15F-pl_PL-stretch',base,other)
    result['spatial_transform_native']='crop x=160,y=0,w=960,h=720; horizontal resize 1280x720 (4/3); vertical scale 1'
    result['interpretation']='Visual geometry test, not exact-byte identity; title cards remain locale-specific.'
    save('INTRO15F-pl_PL-stretch-analysis.json',result)

if __name__=='__main__':main()
