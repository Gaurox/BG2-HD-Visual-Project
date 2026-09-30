// Offline document renderer. No game files or installed assets are modified.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { marked } from 'file:///C:/Users/Adrien/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/marked/lib/marked.esm.js';

const root=path.dirname(fileURLToPath(import.meta.url));
const stem='GUIDE_CODEX_BG2EE_FEMME_GUERRIERE';
let content=marked.parse(fs.readFileSync(path.join(root,stem+'.md'),'utf8'));
const headings=[];let ordinal=0;
content=content.replace(/<h([23])>([\s\S]*?)<\/h\1>/g,(_,level,title)=>{
  const id=`part-${++ordinal}`;headings.push({level,title,id});return `<h${level} id="${id}">${title}</h${level}>`;
});
content=content.replace(/<table>/g,'<div class="table-scroll"><table>').replace(/<\/table>/g,'</table></div>');
content=content.replace(/<img src="([^"]+)"([^>]*?)>/g,'<a class="figure" href="$1" target="_blank"><img loading="lazy" src="$1"$2></a>');
// Companion notes remain available as Markdown and gain HTML for easy reading.
for(const note of ['engine_research','inventory_research','upscale_research']) {
  const md=path.join(root,note+'.md');
  if(fs.existsSync(md)) {
    const body=marked.parse(fs.readFileSync(md,'utf8'));
    fs.writeFileSync(path.join(root,note+'.html'),`<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Codex — ${note}</title><style>body{font:16px/1.6 system-ui,sans-serif;max-width:1150px;margin:30px auto;padding:20px;color:#1c2938}table{border-collapse:collapse;font-size:14px}td,th{padding:8px;border:1px solid #ccc}pre{overflow:auto;padding:14px;background:#f0f3f7}a{color:#195aa7}</style><a href="${stem}.html">← Guide Codex</a>${body}</html>`);
    content=content.replaceAll(`href="${note}.md"`,`href="${note}.html"`);
  }
}
const nav=headings.filter(x=>x.level==='2').map(x=>`<a href="#${x.id}">${x.title}</a>`).join('');
const html=`<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CODEX — BG2EE : femme humaine guerrière HD</title>
<style>
:root{color-scheme:light;--ink:#1d2939;--muted:#586677;--line:#d8e1ec;--blue:#125caf}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}
body{margin:0;background:#edf1f6;color:var(--ink);font:16px/1.66 system-ui,-apple-system,"Segoe UI",sans-serif}
aside{position:fixed;inset:0 auto 0 0;width:255px;padding:30px 20px;background:#142437;color:#eff6ff;overflow:auto}
.brand{font-size:26px;font-weight:800;letter-spacing:.14em}.tag{color:#b8c9dd;font-size:13px;margin:8px 0 28px}
nav a{display:block;color:#d6e5f6;text-decoration:none;font-size:13px;line-height:1.45;padding:10px 0;border-bottom:1px solid #34465b}
nav a:hover{color:white}aside .download{display:block;font-size:13px;color:#a2d3ff;margin-top:18px}
main{max-width:1260px;margin:32px 32px 60px 285px;background:white;padding:42px 48px;border-radius:14px;box-shadow:0 6px 24px #24364e0c}
h1{font-size:34px;line-height:1.18;letter-spacing:-.03em;margin-top:0}h2{font-size:26px;line-height:1.28;border-top:2px solid #c5d7ea;padding-top:32px;margin-top:56px}h3{font-size:20px;line-height:1.4;margin-top:32px}
a{color:var(--blue);text-underline-offset:3px}strong{font-weight:700}p,li{max-width:100%}li{margin:5px 0}li::marker{color:var(--blue)}
code{font-family:Consolas,monospace;font-size:.91em;background:#f0f4f8;border-radius:3px;padding:1px 4px}pre{padding:18px;background:#142437;color:#e8f2ff;border-radius:8px;overflow:auto;line-height:1.5}pre code{background:transparent;padding:0}
.table-scroll{overflow-x:auto;border:1px solid var(--line);border-radius:7px;margin:22px 0}table{width:100%;border-collapse:collapse;font-size:14px;line-height:1.5}th{background:#edf3fa;text-align:left;font-weight:700}th,td{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}tr:last-child td{border-bottom:0}tr:nth-child(even) td{background:#fafcff}
.figure{display:block;text-align:center;background:#17202c;padding:8px;border-radius:8px;margin:24px 0}.figure img{max-width:100%;max-height:800px;object-fit:contain;vertical-align:middle}.hint{font-size:12px;color:var(--muted);margin-top:-15px}
@media(max-width:1080px){aside{width:215px;padding:24px 15px}main{margin-left:235px;padding:30px; margin-right:20px}h1{font-size:29px}}
@media(max-width:760px){aside{position:relative;width:auto}nav{display:grid;grid-template-columns:1fr 1fr;gap:0 15px}.tag{margin-bottom:12px}main{margin:16px;padding:24px}h1{font-size:26px}h2{font-size:23px}}
@media print{aside{display:none}body{background:white}main{margin:0;padding:0;max-width:none;box-shadow:none}h2{break-before:auto}table{font-size:11px}.figure img{max-height:650px}a{color:inherit}pre{white-space:pre-wrap}.table-scroll{overflow:visible}tr{break-inside:avoid}}
</style></head><body><aside><div class="brand">CODEX</div><div class="tag">BG2EE · Recherche indépendante<br>29 septembre 2026<br>Avatar 0x6110</div><nav>${nav}</nav><a class="download" href="${stem}.md">Version Markdown</a><a class="download" href="assets_inventory.csv">Inventaire des 774 BAM</a><a class="download" href="CODEX_inventory_annexes.zip">Annexes d’inventaire</a></aside><main>${content}</main></body></html>`;
fs.writeFileSync(path.join(root,stem+'.html'),html,'utf8');
console.log(JSON.stringify({html:path.join(root,stem+'.html'),sections:headings.length,bytes:Buffer.byteLength(html)}));
