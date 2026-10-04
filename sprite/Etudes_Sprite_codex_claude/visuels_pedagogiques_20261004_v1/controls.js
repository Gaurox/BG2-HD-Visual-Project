(function () {
  'use strict';
  const entry = document.currentScript, embedded = entry?.dataset.visualEmbedded === 'true';
  const assetBase = new URL('./', entry.src);
  const query = selector => document.querySelectorAll(embedded ? '[data-sprite-visual] ' + selector : selector);
  const D = window.VISUAL_DATA, S = window.SIM, $ = id => document.getElementById(id);
  let lang = 'fr', selectedWitness = 2, renderTimer;
  const t = (fr, en) => lang === 'fr' ? fr : en;
  const labels = () => lang === 'fr' ? ['Corps', 'Casque', 'Bouclier', 'Arme'] : ['Body', 'Helmet', 'Shield', 'Weapon'];
  const palettes = D.palettes.map(p => S.bytes(p.rgba));
  const images = D.gallery.map(g => {
    const im = new Image(); im.src = new URL(g.image, assetBase).href; im.onload = () => renderGallery(); return im;
  });
  const alphaImages = D.alpha.rgba.map((rgba, i) => ({w: D.alpha.frames[i].w, h: D.alpha.frames[i].h, data: S.bytes(rgba)}));
  const make = (tag, classes) => {const e = document.createElement(tag); if (classes) e.className = classes; return e;};
  function setText(element, value) {element.textContent = value;}
  function imageCanvas(image) {
    const c = make('canvas'); c.width = image.w; c.height = image.h;
    c.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(image.data), image.w, image.h), 0, 0);
    return c;
  }
  function background(canvas, kind) {
    const context = canvas.getContext('2d'), a = S.background(canvas.width, canvas.height, kind);
    context.putImageData(new ImageData(a.data, a.w, a.h), 0, 0);
    context.imageSmoothingEnabled = false;
    return context;
  }
  function card(parent, title, width, height) {
    const article = make('article', 'canvas-card'), heading = make('h3'), canvas = make('canvas'), caption = make('p', 'hint');
    heading.textContent = title; canvas.width = width; canvas.height = height;
    canvas.setAttribute('role', 'img'); canvas.setAttribute('aria-label', title + ' · ' + t('simulation hors jeu', 'offline simulation'));
    article.append(heading, canvas, caption); parent.append(article);
    return {canvas, caption, article};
  }
  function reference(context, x, y, colour) {
    context.strokeStyle = colour; context.lineWidth = 1.5;
    context.beginPath(); context.moveTo(x - 9, y); context.lineTo(x + 9, y); context.moveTo(x, y - 9); context.lineTo(x, y + 9); context.stroke();
    context.beginPath(); context.arc(x, y, 3, 0, Math.PI * 2); context.stroke();
  }
  function fillPoseOptions() {
    for (const id of ['assembly-pose', 'filter-pose']) {
      const value = $(id).value || '0'; $(id).replaceChildren();
      D.poses.forEach((p, i) => {const option = make('option'); option.value = String(i); option.textContent = p.name[lang]; $(id).append(option);});
      $(id).value = value;
    }
    const value = $('assembly-palette').value || '0'; $('assembly-palette').replaceChildren();
    D.palettes.forEach((p, i) => {const option = make('option'); option.value = String(i); option.textContent = p.name; $('assembly-palette').append(option);});
    $('assembly-palette').value = value;
  }
  function renderAssembly() {
    const pose = D.poses[Number($('assembly-pose').value)], palette = palettes[Number($('assembly-palette').value)];
    const show = $('assembly-anchors').checked, kind = $('assembly-bg').value, holder = $('assembly-cards'); holder.replaceChildren();
    const enabled = Array.from($('layer-toggles').querySelectorAll('input')).map(e => e.checked);
    const layers = pose.layers.map(layer => S.decode(layer, 2, palette));
    for (let i = 0; i < 5; i++) {
      const {canvas, caption} = card(holder, i < 4 ? labels()[i] : t('Assemblage', 'Assembly'), 300, 325);
      const ctx = background(canvas, kind), ax = 150, ay = 265, zoom = 3;
      const use = i < 4 ? [i] : [0, 1, 2, 3].filter(k => enabled[k]);
      for (const k of use) {
        const layer = layers[k], image = imageCanvas(layer), x = ax - layer.cx * zoom, y = ay - layer.cy * zoom;
        ctx.drawImage(image, x, y, image.width * zoom / 2, image.height * zoom / 2);
        if (show && i < 4) {ctx.strokeStyle = '#8fbfc3'; ctx.lineWidth = 1; ctx.strokeRect(x, y, image.width * zoom / 2, image.height * zoom / 2);}
      }
      if (show) {
        ctx.strokeStyle = kind === 'parchment' ? '#70684f' : '#59604e'; ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(15, ay); ctx.lineTo(285, ay); ctx.stroke();
        reference(ctx, ax, ay, kind === 'parchment' ? '#594311' : '#caa45b');
      }
      ctx.fillStyle = kind === 'parchment' ? '#29241b' : '#e9dfca'; ctx.font = '17px Consolas,monospace';
      ctx.fillText(i < 4 ? `C = (${layers[i].cx}, ${layers[i].cy})` : 'A = (150, 265)', 16, 310);
      caption.textContent = i < 4 ? pose.layers[i].key + ` · ${pose.layers[i].w} × ${pose.layers[i].h}` : t('Palette commune · ordre fixe', 'Shared palette · fixed order');
    }
  }
  function setupToggles() {
    const enabled = Array.from($('layer-toggles').querySelectorAll('input')).map(e => e.checked);
    $('layer-toggles').replaceChildren();
    labels().forEach((label, i) => {
      const container = make('label', 'inline'), input = make('input'), span = make('span'); input.type = 'checkbox'; input.checked = enabled[i] ?? true;
      span.textContent = label; input.addEventListener('change', renderAssembly); container.append(input, span); $('layer-toggles').append(container);
    });
  }
  function renderFilters() {
    const pose = D.poses[Number($('filter-pose').value)], scale = Number($('filter-scale').value), zoom = Number($('filter-zoom').value), phase = Number($('filter-phase').value), kind = $('filter-bg').value;
    const mode = $('filter-mode').value; $('filter-scale').disabled = mode === 'scales';
    const variants = mode === 'scales' ? [{scale: 2, method: 'BOX', title: 'x2 + BOX'}, {scale: 4, method: 'BOX', title: 'x4 + BOX'}] : ['Nearest', 'BOX', 'Mipmaps', 'Catmull-Rom'].map(method => ({scale, method, title: method}));
    const holder = $('filter-cards'); holder.replaceChildren(); holder.style.gridTemplateColumns = mode === 'scales' ? 'repeat(2,minmax(0,1fr))' : '';
    for (const variant of variants) {
      const actual = variant.method === 'Mipmaps' && variant.scale === 2 ? 'Nearest' : variant.method;
      const layers = pose.layers.map(layer => S.decode(layer, variant.scale, palettes[0]));
      const rendered = S.filtered(layers, variant.scale, zoom, actual, phase), source = imageCanvas(rendered);
      const {canvas, caption} = card(holder, variant.title, 365, 600), ctx = background(canvas, kind);
      const py = 42, px = Math.floor((canvas.width - source.width) / 2);
      ctx.drawImage(source, px, py);
      const cropX = Math.round((-15 + 40) * zoom), cropY = Math.round((-62 + 75) * zoom);
      const cropW = Math.max(8, Math.round(29 * zoom)), cropH = Math.max(8, Math.round(24 * zoom));
      ctx.strokeStyle = '#8fbfc3'; ctx.strokeRect(px + cropX, py + cropY, cropW, cropH);
      const factor = Math.max(1, Math.min(5, Math.floor(325 / cropW), Math.floor(145 / cropH)));
      ctx.fillStyle = kind === 'parchment' ? '#29241b' : '#e9dfca'; ctx.font = '17px Calibri,Arial,sans-serif';
      ctx.fillText(t('Pixels affichés, loupe', 'Displayed pixels, close-up') + ' ×' + factor, 18, 445);
      ctx.drawImage(source, cropX, cropY, cropW, cropH, Math.floor((365-cropW*factor)/2), 456, cropW*factor, cropH*factor);
      caption.textContent = actual !== variant.method ? t('Mipmaps x2 : retour réel à Nearest.', 'x2 mipmaps: actual fallback to Nearest.') : variant.method === 'BOX' ? t('BOX : moyenne de la surface couverte ; Nearest en agrandissement.', 'BOX: covered-area average; Nearest when magnifying.') : variant.method === 'Mipmaps' ? t('Pyramide RGBA8 simulée, réduction trilinéaire.', 'Simulated RGBA8 pyramid, trilinear reduction.') : variant.method === 'Catmull-Rom' ? t('Voisinage de 4 × 4 texels ; alpha prémultiplié.', '4 × 4 texel neighbourhood; premultiplied alpha.') : t('Un seul texel par pixel écran.', 'One texel per screen pixel.');
    }
    const footprint = scale/zoom;
    setText($('filter-status'), mode==='scales' ? t(`Même zoom ×${zoom} ; surface couverte par pixel : x2 → ${(2/zoom).toFixed(2)} texels de côté, x4 → ${(4/zoom).toFixed(2)}.`, `Same zoom ×${zoom}; footprint per pixel: x2 → ${(2/zoom).toFixed(2)} texels per side, x4 → ${(4/zoom).toFixed(2)}.`) : t(`Texture x${scale} ; zoom ×${zoom} ; surface couverte : ${footprint.toFixed(2)} × ${footprint.toFixed(2)} texels. Position sous-pixel ${phase}.`, `x${scale} texture; zoom ×${zoom}; footprint: ${footprint.toFixed(2)} × ${footprint.toFixed(2)} texels. Subpixel position ${phase}.`));
    let base = 0, total = 0;
    for (const layer of pose.layers) {
      let w = layer.w*4, h = layer.h*4; base += w*h*4;
      for (;;) {total += w*h*4; if (w===1 && h===1) break; w=Math.max(1,Math.floor(w/2)); h=Math.max(1,Math.floor(h/2));}
    }
    const extra = ((total/base-1)*100).toFixed(1);
    setText($('mip-storage'), t(`Pour les quatre textures x4 de cette pose : base RGBA8 ${(base/1024).toFixed(1)} Kio ; pyramide complète ${(total/1024).toFixed(1)} Kio (+${extra} %). BOX n’ajoute aucun niveau mipmap. Ce calcul exclut bordures, caches et allocations du moteur ; il ne mesure pas la mémoire GPU totale.`, `For this pose’s four x4 textures: RGBA8 base ${(base/1024).toFixed(1)} KiB; full pyramid ${(total/1024).toFixed(1)} KiB (+${extra}%). BOX adds no mipmap levels. This calculation excludes borders, caches and engine allocations; it does not measure total GPU memory.`));
  }
  function scheduleFilters() {
    clearTimeout(renderTimer); setText($('filter-status'), t('Calcul de la simulation…', 'Computing simulation…'));
    renderTimer = setTimeout(renderFilters, 30);
  }
  function renderGallery() {
    const holder = $('gallery-cards'); if (!holder) return; holder.replaceChildren();
    const kind = $('gallery-bg').value;
    D.gallery.forEach((g, i) => {
      const button = make('button'), canvas = make('canvas'), name = make('span', 'name'), profile = make('span', 'kind');
      button.type = 'button'; button.setAttribute('aria-pressed', String(selectedWitness===i));
      canvas.width = 280; canvas.height = 245; canvas.setAttribute('role','img'); canvas.setAttribute('aria-label',g.name[lang]);
      const ctx = background(canvas,kind), image = images[i];
      if (image.complete && image.naturalWidth) {
        const factor = Math.min(4,260/image.naturalWidth,224/image.naturalHeight);
        ctx.drawImage(image,(280-image.naturalWidth*factor)/2,(245-image.naturalHeight*factor)/2,image.naturalWidth*factor,image.naturalHeight*factor);
      }
      name.textContent = g.name[lang]+' · '+g.animation;
      profile.textContent = t(g.kind ? 'Rampes recolorables' : 'Palette fixe',g.kind ? 'Recolourable ramps' : 'Fixed palette');
      name.append(make('br'),profile); button.append(canvas,name);
      button.addEventListener('click',()=>{selectedWitness=i;renderGallery();renderPartners();}); holder.append(button);
    });
  }
  function renderPartners() {
    const g=D.gallery[selectedWitness], p=g.partners;
    setText($('partner-title'),g.name[lang]+' · '+t('un indice, quatre partenaires','one index, four partners'));
    setText($('partner-meta'),`${p.resref} · I=${p.index} · code=(B<<3)|F · F=0…7`);
    $('partner-rows').replaceChildren();
    for(let b=0;b<4;b++){
      const row=make('div'), title=make('span','mono'), ramp=make('div','ramp'), numbers=make('div','ramp-label');
      title.textContent=`B=${b} → J=${p.indices[b]}`;
      for(let f=0;f<8;f++){
        const swatch=make('div'), number=make('span'); const rgb=p.primary.slice(0,3).map((v,c)=>(v*(8-f)+p.colours[b][c]*f+4)>>3);
        swatch.style.backgroundColor=`rgb(${rgb.join(',')})`; swatch.title=`B=${b}, F=${f}: RGB(${rgb.join(',')})`; number.textContent=String(f); ramp.append(swatch);numbers.append(number);
      }
      row.append(title,ramp,numbers);$('partner-rows').append(row);
    }
  }
  function renderAlpha() {
    const holder=$('alpha-cards'), kind=$('alpha-bg').value, magnify=Number($('alpha-magnify').value), [x,y,size]=D.alpha.crop;
    holder.replaceChildren();
    const names=['Q3m V7 original','Spline Fit 1',t('Alpha léger','Light alpha')];
    const statuses=[t('Référence de production','Production reference'),t('Essai rejeté en jeu','Trial rejected in game'),t('Étape remplacée par le SDF','Superseded by SDF')];
    alphaImages.forEach((image,i)=>{
      const {canvas,caption}=card(holder,names[i],425,560),ctx=background(canvas,kind),source=imageCanvas(image);
      const px=Math.floor((425-source.width)/2),py=28;ctx.drawImage(source,px,py);
      ctx.strokeStyle='#8fbfc3';ctx.lineWidth=1;ctx.strokeRect(px+x,py+y,size,size);
      ctx.fillStyle=kind==='parchment'?'#29241b':'#e9dfca';ctx.font='18px Calibri,Arial,sans-serif';ctx.fillText(t('Loupe du même contour','Same contour, close-up')+' ×'+magnify,18,343);
      ctx.drawImage(source,x,y,size,size,Math.floor((425-size*magnify)/2),365,size*magnify,size*magnify);
      caption.textContent=statuses[i];
    });
  }
  function language(value) {
    lang=value;
    if (!embedded) {document.documentElement.lang=lang;document.title=t('Sprites HD · Propositions de visuels hors jeu','HD sprites · Offline visual proposals');}
    for(const element of query('[data-fr]'))element.textContent=element.dataset[lang];
    const alts=lang==='fr'?['Calques, centres et assemblage','Comparaison des filtres d’affichage','Profils V7 et partenaires','Comparaison des contours alpha']:['Layers, centres and assembly','Display filter comparison','V7 profiles and partners','Alpha contour comparison'];
    if (!embedded) query('[data-board]').forEach((im,i)=>{im.src=new URL(`assets/proposal-${im.dataset.board}-${lang}.png`,assetBase).href;im.alt=alts[i]+' · '+t('simulation hors jeu','offline simulation');});
    if (!embedded) {$('lang-fr').setAttribute('aria-pressed',String(lang==='fr'));$('lang-en').setAttribute('aria-pressed',String(lang==='en'));}
    fillPoseOptions();setupToggles();renderAssembly();renderGallery();renderPartners();renderAlpha();scheduleFilters();
  }
  for(const id of ['assembly-pose','assembly-palette','assembly-bg','assembly-anchors'])$(id).addEventListener('change',renderAssembly);
  for(const id of ['filter-mode','filter-scale','filter-zoom','filter-pose','filter-bg','filter-phase'])$(id).addEventListener('change',scheduleFilters);
  $('filter-render').addEventListener('click',scheduleFilters);$('gallery-bg').addEventListener('change',renderGallery);
  for(const id of ['alpha-bg','alpha-magnify'])$(id).addEventListener('change',renderAlpha);
  if (!embedded) {$('lang-fr').addEventListener('click',()=>language('fr'));$('lang-en').addEventListener('click',()=>language('en'));}
  language(entry?.dataset.visualLanguage || 'fr');
})();
