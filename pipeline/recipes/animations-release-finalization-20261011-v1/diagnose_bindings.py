"""Compare the frozen runtime contracts with current accepted per-resource packs."""
from prepare import *

def main():
    differences=[]
    for leaf in sorted(PACK.iterdir()):
        if not leaf.is_dir():continue
        area=leaf.name;rr=resources(leaf)
        for ref in sorted({r['resref'] for r in rr}):
            matches=[]
            for selection_path in (ROOT/'animations/index/selections').glob('*.json'):
                sel=load(selection_path)
                if sel.get('runtime_resref',sel['resref'])!=ref:continue
                record=next((x for x in sel['source_pack']['areas'] if x['area']==area),None)
                if record:matches.append((sel,record))
            if not matches:
                differences.append(dict(area=area,resref=ref,reason='no current area selection'));continue
            sel,record=matches[0];old=resources(path(record['path']),ref)
            if release.equivalent_resource_groups(old,rr,ref):continue
            new=[r for r in rr if r['resref']==ref]
            keys=sorted({k for r in old+new for k in r})
            differing=[k for k in keys if [r.get(k) for r in old]!=[r.get(k) for r in new]]
            differences.append(dict(area=area,resref=ref,tracked_resref=sel['resref'],qa=sel['qa_decision'],
                old_pack=record['path'],differences=differing,old=[{k:r.get(k) for k in differing} for r in old],
                new=[{k:r.get(k) for k in differing} for r in new]))
    write(HERE/'binding-differences.json',differences)
    for item in differences:print(item['area'],item['resref'],item.get('differences',item.get('reason')),flush=True)
    print('DIFFERENCES',len(differences),flush=True)

if __name__=='__main__':main()
