"""Test the observed Polish INTRO15F framing against the shared 4:3 picture."""
import numpy as np
from PIL import Image
from compare import read, compare, save


def main():
    base=read('INTRO15F-default');other=read('INTRO15F-pl_PL')
    native=base['frames']
    base['frames']=np.stack([np.asarray(Image.fromarray(np.asarray(f)).crop((20,0,140,90))
        .resize((160,120),Image.Resampling.LANCZOS).crop((0,15,160,105))) for f in native])
    result=compare('INTRO15F-default-normalized-PL-framing','INTRO15F-pl_PL-normalized',base,other)
    result['spatial_transform_native']='crop x=160,y=0,w=960,h=720; resize 1280x960; center crop 1280x720'
    result['interpretation']='Visual geometry test, not exact-byte identity; title cards remain locale-specific.'
    save('INTRO15F-pl_PL-spatial-analysis.json',result)


if __name__=='__main__':main()
