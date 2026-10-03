"""Five-page visual report; run with the Codex PDF Python dependency runtime."""
import json,hashlib
from pathlib import Path
from xml.sax.saxutils import escape
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;IMG=HERE/'images'
OUTPUT=ROOT/'output/pdf/ankheg-contour-sdf-comparatif-20261004-v1.pdf';OUTPUT.parent.mkdir(parents=True,exist_ok=True)
TRIAL=json.loads((HERE/'trial.json').read_text(encoding='utf-8'))
REFERENCE=Path('E:/Steam/userdata/5536307/760/remote/257350/screenshots/20261004001901_1_crop.jpg')
pdfmetrics.registerFont(TTFont('Segoe','C:/Windows/Fonts/segoeui.ttf'))
pdfmetrics.registerFont(TTFont('Segoe-Bold','C:/Windows/Fonts/segoeuib.ttf'))
W,H=landscape(A4);M=34;GAP=22;PW=(W-2*M-GAP)/2
INK=HexColor('#1c2731');MUTED=HexColor('#53616b');ACCENT=HexColor('#007a73')
PAPER=HexColor('#f6f4ee');LINE=HexColor('#d7ddd9');OLD=HexColor('#956444')
style=ParagraphStyle('body',fontName='Segoe',fontSize=11,leading=16,textColor=INK)
c=canvas.Canvas(str(OUTPUT),pagesize=(W,H),pageCompression=1,invariant=1)
c.setTitle('Ankheg - contour SDF reconstruit - comparatif hors jeu')
c.setAuthor('BG2 Upscale');c.setSubject('Essai offline Q3m x2, alpha actuel et silhouette SDF, zooms simulés.')

def text(x,y,value,size=11,bold=False,color=INK):
    c.setFillColor(color);c.setFont('Segoe-Bold' if bold else 'Segoe',size);c.drawString(x,y,value)

def paragraph(x,top,width,value,size=11,leading=16,color=INK,max_height=None):
    st=ParagraphStyle('p',parent=style,fontSize=size,leading=leading,textColor=color)
    p=Paragraph(value,st);w,h=p.wrap(width,H)
    if max_height is not None:assert h<=max_height,(value,h,max_height)
    p.drawOn(c,x,top-h);return h

def header(number,title,subtitle):
    c.setFillColor(PAPER);c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(ACCENT);c.roundRect(M,H-66,5,33,2,fill=1,stroke=0)
    text(M+18,H-52,title,27,True)
    text(M+18,H-76,subtitle,10.5,color=MUTED)
    c.setStrokeColor(LINE);c.line(M,H-91,W-M,H-91)
    text(W-M-92,H-48,'ESSAI HORS JEU',9,True,ACCENT)
    c.setStrokeColor(LINE);c.line(M,42,W-M,42)
    text(M,24,'BG2 UPSCALE  /  Q3m x2  /  04.10.2026',8,color=MUTED)
    text(W-M-30,24,str(number)+' / 5',8,color=MUTED)

def image(path,x,y,width,height,background=None):
    im=Image.open(path);ratio=min(width/im.width,height/im.height)
    dw,dh=im.width*ratio,im.height*ratio
    if background:
        c.setFillColor(HexColor(background));c.roundRect(x,y,width,height,4,fill=1,stroke=0)
    c.drawImage(ImageReader(im),x+(width-dw)/2,y+(height-dh)/2,dw,dh,mask='auto')

def column_titles(y):
    text(M,y,'ALPHA ACTUEL',11,True,OLD)
    text(M+PW+GAP,y,'CONTOUR RECONSTRUIT',11,True,ACCENT)

# 1: Large equal-camera comparison on a deliberately synthetic floor.
header(1,'Contour reconstruit','Ankheg - comparaison du masque alpha installé avec une reconstruction SDF.')
column_titles(H-118)
for col,label in enumerate(('actuel','sdf')):
    image(IMG/('profil-'+label+'-3p0-pierre.png'),M+col*(PW+GAP),91,PW,365,background='#e7e8e2')
text(M,73,'Même pose, même palette et même cadrage. Sol de pierre simulé.',10,color=MUTED)
text(M,55,'Zoom de simulation : 1 pixel de la texture Q3m x2 = 3 pixels écran.',10,color=MUTED)
c.showPage()

# 2: Two actual re-rendered closeups; no enlarged screenshot or nearest PNG scaling.
header(2,'Les marches du contour','Gros plans reconstitués à un grossissement de 6 pixels écran par texel Q3m x2.')
column_titles(H-116)
for name,title,top in [('dos','DOS ET CARAPACE',H-145),('patte','PATTE DIAGONALE',H-345)]:
    text(M,top,title,10,True,color=MUTED)
    for col,label in enumerate(('actuel','sdf')):
        image(IMG/('detail-'+name+'-'+label+'.png'),M+col*(PW+GAP),top-167,PW,152,background='#777a7b')
text(M,56,'Le bord peut avancer ou reculer localement ; l’intérieur reste la texture Q3m.',10,color=MUTED)
c.showPage()

# 3: Four static poses, paired individually without normalizing one variant differently.
header(3,'Quatre poses de contrôle','Même recette - zoom simulé : 1,5 pixel écran par texel Q3m x2.')
items=[('face','Face','MAKHG1 / frame 11'),('profil','Profil','MAKHG1 / frame 25'),
    ('attaque','Attaque','MAKHG3 / frame 20'),('miroir','Direction opposée','MAKHG1E / frame 25')]
for idx,(name,title,ref) in enumerate(items):
    x=M+(idx%2)*(PW+GAP);y=276 if idx<2 else 70
    # Fixed two-by-two cards; paired source rasters share every drawing parameter.
    c.setFillColor(HexColor('#eceee8'));c.roundRect(x,y,PW,192,5,fill=1,stroke=0)
    text(x+12,y+172,title,12,True)
    text(x+12,y+157,ref,8,color=MUTED)
    cell=(PW-32)/2
    for col,label in enumerate(('actuel','sdf')):
        image(IMG/(name+'-'+label+'-1p5-gris.png'),x+12+col*(cell+8),y+29,cell,121)
        text(x+12+col*(cell+8),y+13,'Actuel' if col==0 else 'SDF',9,True,OLD if col==0 else ACCENT)
c.showPage()

# 4: Opacity, including original shadows, without colour texture distracting the eye.
header(4,'La transparence reconstruite','Blanc = opaque ; gris = partiellement transparent ; noir = transparent.')
column_titles(H-118)
for col,label in enumerate(('actuel','sdf')):
    image(IMG/('profil-'+label+'-alpha.png'),M+col*(PW+GAP),132,PW,316,background='#111111')
paragraph(M,110,W-2*M,
    'Le nouveau masque couvre les deux côtés du contour. Les couleurs de bord proviennent des pixels Q3m voisins, '
    'ce qui évite de mélanger le contour avec du noir. Les ombres gardent leur masque source et leur filtrage Catmull-Rom.',
    size=10,leading=14,max_height=45)
c.showPage()

# 5: User capture is explicitly a reference, not a claimed post-treatment screenshot.
header(5,'Portée du test','Référence ingame fournie et paramètres de la simulation présentée dans ce PDF.')
left_width=310;rx=M+left_width+30;rw=W-M-rx
text(M,H-119,'CAPTURE INGAME FOURNIE',10,True,OLD)
image(REFERENCE,M,176,left_width,286)
paragraph(M,158,left_width,
    'Image de référence avant ce test. Les simulations utilisent une palette verte de référence et des poses décodées du sprite ; '
    'elles ne reproduisent pas exactement cet instant du jeu.',size=9,leading=13,max_height=66)
top=H-116
for title,value in [
    ('Reconstruction','Champ de distance lissé, sigma 2 pixels x2 ; modification du champ bornée à 1 pixel x2. Protection des parties fines et des composantes du masque.'),
    ('Anti-crénelage','Couverture intégrée sur 8 × 8 sous-pixels écran. RGB filtré en Catmull-Rom, avec extension des couleurs Q3m au bord.'),
    ('Contrôles','12 frames issues de 4 poses et de leurs voisines. Composantes et trous conservés au centre des texels, y compris les fragments préexistants. Variation de surface opaque inférieure à 0,5 %.'),
    ('Ce qui reste à vérifier','Précision GPU, flou natif, sélection, teintes et éclairage du jeu. Le rendu SDF proposé demande une intégration runtime et une validation ingame.'),
    ('État','Essai offline uniquement. Aucun fichier du jeu modifié et aucune nouvelle validation ingame déduite.')]:
    text(rx,top,title,11,True,ACCENT)
    h=paragraph(rx,top-10,rw,value,size=10,leading=14,max_height=65)
    top-=h+32
assert top>58,top
paragraph(M,82,W-2*M,'Principe SDF : Chris Green / Valve, SIGGRAPH 2007. Recette et données du test : '
    'q3m-ankheg-sdf-offline-x2-20261004-v1.',size=8.5,leading=12,color=MUTED,max_height=25)
c.linkURL('https://steamcdn-a.akamaihd.net/apps/valve/2007/SIGGRAPH2007_AlphaTestedMagnification.pdf',(M,68,M+300,84),relative=0,thickness=0)
c.showPage();c.save()
reader=PdfReader(OUTPUT)
assert len(reader.pages)==5 and all(p.extract_text().strip() for p in reader.pages)
assert not reader.get_fields()
proof=dict(pdf=OUTPUT.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
    bytes=OUTPUT.stat().st_size,pages=len(reader.pages),source_trial_sha256=hashlib.sha256((HERE/'trial.json').read_bytes()).hexdigest(),
    reference_image=dict(path=str(REFERENCE),sha256=hashlib.sha256(REFERENCE.read_bytes()).hexdigest()),
    semantic_checks_passed=True,visual_review='pending')
(HERE/'pdf.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(proof,ensure_ascii=False))
