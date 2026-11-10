"""Additional native timestamps: VP8 invisible packets are not displayed frames."""
from concurrent.futures import ThreadPoolExecutor
from extract import ROOT, OUT, run, save
import json, shutil

def main():
    sources=json.loads((OUT/'sources.json').read_text(encoding='utf-8'))['sources']
    def process(source):
        path=OUT/(source['name']+'.native-frame-times.json')
        assert not path.exists()
        data=json.loads(run([shutil.which('ffprobe'),'-v','error','-threads','2','-select_streams','v:0',
            '-show_frames','-show_entries','frame=best_effort_timestamp_time,pkt_duration_time,key_frame',
            '-of','json',str(ROOT/source['source'])]))
        assert len(data['frames'])==source['frames']
        save(path,data)
        print(source['name'],len(data['frames']),flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(process,sources))

if __name__=='__main__':main()
