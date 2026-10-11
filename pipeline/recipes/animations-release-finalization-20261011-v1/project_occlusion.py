"""Materialize the acquired AR0516 WED contract before candidate promotions."""
from prepare import *

def main():
    with release.workflow_lock():
        candidates=release.load_json(release.CANDIDATES)['candidates']
        release.validate_occlusion_contracts(candidates)
        content=release.load_json(release.CONTENT);added=[]
        for candidate in candidates:
            c=candidate.get('occlusion_contract')
            if not c:continue
            existing=[e for e in content['entries'] if e['destination']==c['destination']]
            if existing:continue
            entry=dict(component_id=c['map_component_id'],component_label=c['map_component_label'],
                payload_group=c['map_payload_group'],kind='map',area=candidate['area'],source=c['source'],
                source_run=Path(c['source']).parent.as_posix(),destination=c['destination'],bytes=c['bytes'],
                sha256=c['sha256'],qa_status='validated',scale=4,model='WED-Native-Occlusion-v1',
                install_order=c['map_component_id'],replaces_component_output=False)
            content['entries'].append(entry);added.append(entry)
        release.validate_occlusion_contracts(candidates,validate_release_mapping=True,content_document=content)
        content['entries'].sort(key=lambda e:(e['component_id'],e['install_order'],e['destination'],e['source']))
        if added:release.write_atomic(release.CONTENT,release.json_bytes(content))
        write(HERE/'occlusion-projection.json',dict(added=added,purpose='existing acquired WED contract; prerequisite of promotion before full compilation',game_mutation=False))
        print('WED PROJECTED',len(added))

if __name__=='__main__':main()
