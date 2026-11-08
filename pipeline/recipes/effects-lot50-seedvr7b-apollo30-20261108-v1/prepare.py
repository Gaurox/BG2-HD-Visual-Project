import copy
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
BATCH=ROOT/'effects/batches/lot50-seedvr7b-apollo30-20261108-v1'

def main():
    source=ROOT/'effects/batches/lot50-fire-smoke-proposal-20261028-v1/batch.json'
    proposal=json.loads(source.read_text(encoding='utf-8'))
    analysis=json.loads((ROOT/'effects/research/lot50-recipe-analysis-20261108-v1/analysis.json').read_text(encoding='utf-8'))
    recommendations={a['resref']:a for a in analysis['assets']}
    assets=copy.deepcopy(proposal['assets'])
    for a in assets:
        n=a['resref'];r=recommendations[n]
        a.update(native_fps=[],profile=r['profile'],sigma_x4=r['recipe']['rgb_gauss_sigma_x4'],inner_feather_x4=r['recipe']['inner_feather_x4'],
                 spatial_run=f'{n.lower()}-seedvr7b-x4-20261108-v1',
                 interpolation_run=f'{n.lower()}-apollo30-native-anchors-20261108-v1',
                 pack=f'effects/ressources/{n}/packs/{n.lower()}-7b-x4-apollo30-native-20261108-v1',
                 green_index={'FLLGBLUE':47,'FLMDBLU':39,'FLSM1PUR':245}.get(n),
                 native_rate_basis='15 FPS compatibility; not instrumented',
                 mask_review='pending-user-review')
    BATCH.mkdir(parents=True,exist_ok=True)
    path=BATCH/'batch.json';assert not path.exists()
    path.write_text(json.dumps(dict(schema='bg2-effects-production-batch-v1',date='2026-11-08',assets_count=50,
                                   authorization='User authorized treatment of complete50 after recipe analysis; ComfyUI running.',
                                   proposal=source.relative_to(ROOT).as_posix(),spatial_batch=BATCH.relative_to(ROOT).as_posix(),assets=assets),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Prepared50; new runs only.')

if __name__=='__main__':main()
