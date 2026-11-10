"""Summarize native-source analysis without changing production/QA/release states."""
import csv,json
import numpy as np
from extract import ROOT,OUT,save,sha


def main():
    assert not (OUT/'summary.json').exists(), 'Use a new final analysis version'
    sources=json.loads((OUT/'sources.json').read_text())['sources']
    comparisons=json.loads((OUT/'comparisons.json').read_text())
    pairs=[]
    for name,cut in [('INTRO-de_DE',7),('INTRO-pl_PL',7),('INTRO15F-de_DE',18),('INTRO15F-it_IT',18),('INTRO15F-pl_PL-fitted',18)]:
        rows=list(csv.DictReader((OUT/(name+'-to-default.csv')).open()))
        main=[r for r in rows if float(r['locale_pts_s'])>=cut]
        errors=[float(r['luma_mae_160x90']) for r in main]
        differences=[r for r in main if r['exact_yuv_sha256']!='True']
        pairs.append(dict(other=name,post_title_from_s=cut,frames=len(main),exact_yuv_matches=sum(r['exact_yuv_sha256']=='True' for r in main),
            luma_mae_160x90_percentiles=dict(zip(['p50','p90','p99','max'],np.percentile(errors,[50,90,99,100]).tolist())),
            last_nonexact_locale_pts_s=float(differences[-1]['locale_pts_s']) if differences else None))
    total=sum(s['frames'] for s in sources)
    masters=sum(s['frames'] for s in sources if s['name'].endswith('-default'))
    # Conservative planning windows include title fades and transition context.
    extra_title_budget=210+105+3*270
    summary=dict(status='analysis-complete',scope='7 native INTRO/INTRO15F sources present in this installation',
        sources=[dict(name=s['name'],source=s['source'],sha256=s['source_sha256'],frames=s['frames'],
            fps=s['video']['avg_frame_rate'],container_duration_s=float(s['format_duration']),
            audio_codec=s['audio']['codec_name'],audio_sample_rate=s['audio']['sample_rate'],audio_channels=s['audio']['channels']) for s in sources],
        native_hashes_verified=True,total_decoded_frames=total,
        audio_pcm_streams_all_distinct=len({s['audio_pcm_hash'] for s in sources})==len(sources),
        identical_video_sequences=False,comparisons=comparisons,post_title_comparisons=pairs,
        findings=dict(localized_title_cards=True,INTRO_title_window_plan_s=[0,7],INTRO15F_title_window_plan_s=[0,18],
            INTRO_main='German exact after 7s; Polish visually aligned, separately encoded at ~15fps instead of ~30fps.',
            INTRO15F_main='Default/German/Italian common picture; exact hashes match after ~32.8s, earlier shared film differs slightly through encoding.',
            INTRO15F_polish='Same scenes; central 960x720 picture enlarged ~4/3 and vertically center cropped to 1280x720; separately encoded.',
            geometry_precision='Observed native RGB previews + full-film thumbnail registration; approximate geometry, not exact pixel equality.',
            additional_translated_video_text='No additional localized title/card segment identified after opening; Polish equivalence remains visual, not byte-certified.',
            missing_locales='No separate French INTRO/INTRO15F file in this installation; locale-movies.json records directory inventory.'),
        feasibility=dict(shared_masters=2,distinct_films=['INTRO','INTRO15F'],
            plan='Upscale/interpolate common picture once per film; process opening cards separately; derive locale framing/timeline; remux corresponding native audio.',
            required='Preserve real native frame PTS and trailing holds/audio; do not substitute duration/rate metadata for decoded frame timing.',
            seedvr='Shared inference with temporal context; handle title transitions with overlap/black-boundary joins; do not infer common content independently per locale.',
            audio='Preserve native encoded Vorbis streams where runtime permits; retain start/hold/trim offsets; no audio stretching inferred.',
            polish_framing_choice='Preserve native crop or choose common uncropped 4:3 framing explicitly before production.'),
        inference_work_estimate=dict(method='Source-frame counts, not measured GPU time; conservative 7s/18s localized title windows.',
            independent_frames=total,two_master_frames=masters,extra_localized_title_frames_budget=extra_title_budget,
            estimated_frames_with_separate_title_upscale=masters+extra_title_budget,
            estimated_frame_reduction_percent=100*(1-(masters+extra_title_budget)/total),
            master_only_reduction_percent=100*(1-masters/total),
            limits='Temporal overlaps, output cadence and framing requirements may add work. This saves inference work, not necessarily installed video size.'),
        source_files_modified=False,game_modified=False,upscale_started=False,QA_changed=False,release_modified=False,
        visual_review=['INTRO-title.jpg','INTRO15F-title.jpg','INTRO15F-composition.jpg','INTRO15F-polish-review-1.jpg','INTRO15F-polish-review-2.jpg'],
        evidence={p.name:sha(p) for p in [OUT/'sources.json',OUT/'comparisons.json',OUT/'INTRO15F-pl_PL-fitted-geometry-analysis.json']})
    save(OUT/'summary.json',summary)
    print(json.dumps(dict(status=summary['status'],total_frames=total,masters_frames=masters,inference_estimate=summary['inference_work_estimate']),indent=2))


if __name__=='__main__':main()
