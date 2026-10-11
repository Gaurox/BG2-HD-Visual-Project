from prepare import *
cached_validators();checked=set();errors=[]
for selection_path in (ROOT/'animations/index/selections').glob('*.json'):
    selection=load(selection_path)
    for record in selection['source_pack']['areas']:
        pack=record['path'];key=(record['area'],pack)
        if key in checked:continue
        checked.add(key)
        try:release.validate_pack(*key,qa_evidence=True)
        except Exception as error:
            errors.append(dict(area=key[0],pack=pack,error=str(error)))
            print('QA PACK ERROR',key[0],str(error),flush=True)
write(HERE/'qa-pack-compatibility.json',dict(checked=len(checked),errors=errors))
print('QA PACKS',len(checked),'ERRORS',len(errors),flush=True)
