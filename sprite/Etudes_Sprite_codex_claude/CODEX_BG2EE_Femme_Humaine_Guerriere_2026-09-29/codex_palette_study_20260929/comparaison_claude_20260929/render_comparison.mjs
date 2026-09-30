// Creates only the new comparison HTML; preserves both original studies.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {marked} from 'file:///C:/Users/Adrien/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/marked/lib/marked.esm.js';

const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const stem='COMPARAISON_CODEX_CLAUDE_0x6110';
let body=marked.parse(fs.readFileSync(path.join(root,stem+'.md'),'utf8'));
const sections=[];
body=body.replace(/<h2>([\s\S]*?)<\/h2>/g,(_,title)=>{
  const id='section-'+(sections.length+1);
  sections.push({id,title});
  return `<h2 id="${id}">${title}</h2>`;
});
body=body.replace(/href="([A-Za-z]:\/[^\"]*)"/g,'href="file:///$1"');
for(const note of ['GUIDE_CODEX_BG2EE_FEMME_GUERRIERE','inventory_research']) {
  body=body.replaceAll(`href="${note}.md"`,`href="${note}.html"`);
}
body=body.replaceAll('<table>','<div class="table-scroll"><table>').replaceAll('</table>','</table></div>');
body=body.replace(/<img src="([^\"]+)"([^>]*?)>/g,'<a class="figure" href="$1"><img loading="lazy" src="$1"$2></a>');
const nav=sections.map(s=>`<a href="#${s.id}">${s.title}</a>`).join('\n');
const html=`<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CODEX — Comparaison critique de l'étude Claude, BG2EE 0x6110</title>
<style>
:root{color-scheme:light;--ink:#1e2e3b;--line:#d9e3e7;--accent:#006d77}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}
body{margin:0;background:#edf2f3;color:var(--ink);font:16px/1.65 system-ui,"Segoe UI",sans-serif}
aside{position:fixed;inset:0 auto 0 0;width:255px;padding:28px 22px;background:#173940;color:#e9f7f6;overflow:auto}
.brand{font-size:26px;font-weight:800;letter-spacing:.13em}.meta{font-size:13px;color:#b7d8d9;margin:8px 0 25px}
nav a{display:block;color:#d7eeef;text-decoration:none;font-size:13px;line-height:1.5;padding:11px 0;border-bottom:1px solid #426066}
aside .download{display:block;color:#ade5df;font-size:13px;margin-top:20px}
main{max-width:1300px;margin:30px 30px 70px 285px;padding:42px 48px;background:white;border-radius:12px}
h1{font-size:33px;line-height:1.2;letter-spacing:-.025em;margin-top:0}h2{font-size:25px;line-height:1.3;margin-top:48px;padding-top:28px;border-top:2px solid #c1dadd}h3{font-size:20px;line-height:1.4;margin-top:30px}
a{color:var(--accent);text-underline-offset:3px}li{margin:6px 0}li::marker{color:var(--accent)}
code{font: .9em Consolas,monospace;background:#eff4f5;border-radius:3px;padding:1px 4px}
pre{overflow:auto;background:#173940;color:#e6f4f5;padding:18px;border-radius:7px;line-height:1.5}pre code{background:none;padding:0}
.table-scroll{overflow-x:auto;margin:22px 0;border:1px solid var(--line);border-radius:7px}table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.5}th,td{text-align:left;vertical-align:top;padding:10px 12px;border-bottom:1px solid var(--line)}th{background:#e9f3f3}tr:nth-child(even) td{background:#f8fbfb}tr:last-child td{border-bottom:0}
.figure{display:block;margin:24px 0;padding:10px;background:#172027;text-align:center;border-radius:7px}.figure img{max-width:100%;height:auto;vertical-align:middle}
@media(max-width:1000px){aside{width:215px;padding:24px 16px}main{margin-left:235px;margin-right:20px;padding:30px}h1{font-size:29px}}
@media(max-width:740px){aside{position:relative;width:auto}nav{display:grid;grid-template-columns:1fr 1fr;gap:0 14px}main{margin:16px;padding:23px}h1{font-size:25px}}
@media print{aside{display:none}body{background:white}main{margin:0;padding:0;max-width:none}table{font-size:11px}tr{break-inside:avoid}pre{white-space:pre-wrap}.table-scroll{overflow:visible}a{color:inherit}}
</style></head><body><aside><div class="brand">CODEX</div>
<div class="meta">Comparaison après lecture de Claude<br>BG2EE · Avatar 0x6110<br>29 septembre 2026</div>
<nav>${nav}</nav><a class="download" href="${stem}.md">Document Markdown</a>
<a class="download" href="comparaison_claude_20260929/verification_summary.json">Résultats de vérification</a>
</aside><main>${body}</main></body></html>`;
const output=path.join(root,stem+'.html');
fs.writeFileSync(output,html,'utf8');
console.log(JSON.stringify({output,sections:sections.length,bytes:Buffer.byteLength(html)}));
