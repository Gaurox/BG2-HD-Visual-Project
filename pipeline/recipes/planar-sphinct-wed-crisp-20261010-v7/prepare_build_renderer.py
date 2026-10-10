from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
source=(ROOT/'pipeline/recipes/ar0517-sphinct-wed-smooth-20261010-v1/build_renderer.py').read_text(encoding='utf-8')
source=source.replace("HERE=ROOT/'animations/batches/ar0517-sphinct-wed-smooth-20261010-v1'","HERE=ROOT/'animations/batches/planar-sphinct-wed-crisp-20261010-v7'")
source=source.replace("BASE=ROOT/'animations/batches/bdforcew-shift-right-20261010-v3/.work/runtime-src'","BASE=ROOT/'animations/batches/ar0517-sphinct-wed-smooth-20261010-v1/.work/runtime-src'")
source=source.replace("BASE_SHA='748fe476d24ffa32007d33d34f5c6e506b56147570772ee40b810556ad317c56'","BASE_SHA='ee85fdaba70fd99d0fbf114c6dcee46cf21ccc60a93f8e650a2dbb50abaf42b0'")
source=source.replace("changed=['src/iee/core/area_occlusion_smoothing.h'","changed=['src/iee/core/planar_sphinct_world_masks.h','src/iee/core/area_occlusion_smoothing.h'")
source=source.replace("scope='SPHINCT / AR0517 / occurrence497,452 / AreaRegistry / non-dither binary transfer'","scope='AR0516 SPHINCT positions1520,1287;1529,1447;2948,1776 / AreaRegistry / full x4 spline transfer'")
source=source.replace('guard_x4=4,feather_x4=16','guard_x4=0,feather_x4=0')
source=source.replace('scoped AR0517 renderer','scoped planar renderer').replace('AR0517 renderer candidate ready','Planar renderer candidate ready')
target=Path(__file__).with_name('build_renderer.py');assert not target.exists();target.write_text(source,encoding='utf-8')
