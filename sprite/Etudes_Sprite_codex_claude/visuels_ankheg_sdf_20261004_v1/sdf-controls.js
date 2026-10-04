(function(){
 'use strict';
 const entry=document.currentScript,lang=entry.dataset.sdfLanguage||'fr',D=window.ANKHEG_SDF_DATA,S=window.ANKHEG_SDF_SIM,$=id=>document.getElementById(id);
 const t=(fr,en)=>lang==='fr'?fr:en;
 const poses=D.poses.map(S.prepare),details=$('ankheg-sdf-details');let timer;
 function imageCanvas(image){const c=document.createElement('canvas');c.width=image.w;c.height=image.h;c.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(image.data),image.w,image.h),0,0);return c;}
 function background(canvas,kind){const ctx=canvas.getContext('2d'),b=window.SIM.background(canvas.width,canvas.height,kind);ctx.putImageData(new ImageData(b.data,b.w,b.h),0,0);ctx.imageSmoothingEnabled=false;return ctx;}
 function render(){
  const pose=poses[Number($('ankheg-sdf-pose').value)],nativeZoom=Number($('ankheg-sdf-zoom').value),zoom=nativeZoom/2,kind=$('ankheg-sdf-bg').value;
  const output=[S.render(pose,zoom,false),S.render(pose,zoom,true)],names=[t('Avant · alpha léger','Before · light alpha'),t('Après · SDF V9 retenu','After · selected V9 SDF')];
  const root=$('ankheg-sdf-cards');root.replaceChildren();
  const ratio=zoom/1.5,size=Math.max(8,Math.round(pose.crop[2]*ratio)),cx=Math.round(pose.crop[0]*ratio),cy=Math.round(pose.crop[1]*ratio);
  for(let i=0;i<2;i++){
   const article=document.createElement('article'),heading=document.createElement('h4'),canvas=document.createElement('canvas'),caption=document.createElement('p');
   article.className='canvas-card';heading.textContent=names[i];canvas.width=Math.max(600,output[i].w+40);canvas.height=Math.max(350,output[i].h+35)+235;
   canvas.setAttribute('role','img');canvas.setAttribute('aria-label',names[i]+' · '+t('simulation hors jeu','offline simulation'));
   const ctx=background(canvas,kind),source=imageCanvas(output[i]),px=Math.floor((canvas.width-source.width)/2),py=15;ctx.drawImage(source,px,py);
   ctx.strokeStyle='#8fbfc3';ctx.lineWidth=1;ctx.strokeRect(px+cx,py+cy,size,size);
   const factor=Math.max(1,Math.min(6,Math.floor(195/size))),start=Math.max(350,output[i].h+35);
   ctx.fillStyle=kind==='parchment'?'#29241b':'#e9dfca';ctx.font='20px Calibri,Arial,sans-serif';ctx.fillText(t('Même contour · loupe','Same contour · close-up')+' ×'+factor,20,start+25);
   ctx.drawImage(source,cx,cy,size,size,Math.floor((canvas.width-size*factor)/2),start+40,size*factor,size*factor);
   caption.className='hint';caption.textContent=i===0?t('Ancien essai V8 : adoucissement de l’opacité du bord.','Previous V8 trial: softening of edge opacity.'):t('V9 : mêmes couleurs sources Q3m, contour SDF et ombre séparée.','V9: the same Q3m source colours, SDF contour and separate shadow.');
   article.append(heading,canvas,caption);root.append(article);
  }
  $('ankheg-sdf-status').textContent=t(`${pose.resref} #${pose.frame} · zoom natif ×${nativeZoom} · 1 texel x2 = ${zoom} pixels simulés. Mêmes couleurs sources Q3m et filtre Catmull-Rom ; contour et prolongement du matériau différents.`,`${pose.resref} #${pose.frame} · native zoom ×${nativeZoom} · 1 x2 texel = ${zoom} simulated pixels. The same Q3m source colours and Catmull-Rom filter are used; contour coverage and material extension differ.`);
 }
 function schedule(){clearTimeout(timer);if(!details.open)return;$('ankheg-sdf-status').textContent=t('Calcul du contour SDF…','Computing SDF contour…');timer=setTimeout(render,30);}
 for(const node of document.querySelectorAll('[data-sprite-sdf] [data-fr]'))node.textContent=node.dataset[lang];
 const select=$('ankheg-sdf-pose');D.poses.forEach((p,i)=>{const option=document.createElement('option');option.value=String(i);option.textContent=p.name[lang];select.append(option);});select.value='1';
 for(const id of ['ankheg-sdf-pose','ankheg-sdf-zoom','ankheg-sdf-bg'])$(id).addEventListener('change',schedule);
 details.addEventListener('toggle',schedule);$('ankheg-sdf-recalculate').addEventListener('click',schedule);schedule();
})();
