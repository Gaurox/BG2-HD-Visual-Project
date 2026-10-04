/* Quantized V9 shader model, offline only; native Q3m upload bytes are cached. */
(function(global){
 'use strict';
 const clamp=(v,lo,hi)=>Math.max(lo,Math.min(hi,v));
 const weights=t=>[-.5*t**3+t*t-.5*t,1.5*t**3-2.5*t*t+1,-1.5*t**3+2*t*t+.5*t,.5*t**3-.5*t*t];
 function prepare(pose){
  const texture=window.SIM.bytes(pose.texture),data=window.SIM.bytes(pose.before),n=pose.w*pose.h;
  const field=new Float64Array(n),shadow=new Float64Array(n);
  for(let i=0;i<n;i++){field[i]=((texture[i*4+3]&127)-64)/16;shadow[i]=(texture[i*4+3]>>7)*127/255;}
  return{...pose,texture,field,shadow,before:window.SIM.prepare({w:pose.w,h:pose.h,data},'Catmull-Rom')};
 }
 function distance(p,x,y){
  const bx=Math.floor(x),by=Math.floor(y),fx=x-bx,fy=y-by;
  const a=p.field[clamp(by,0,p.h-1)*p.w+clamp(bx,0,p.w-1)],b=p.field[clamp(by,0,p.h-1)*p.w+clamp(bx+1,0,p.w-1)];
  const c=p.field[clamp(by+1,0,p.h-1)*p.w+clamp(bx,0,p.w-1)],d=p.field[clamp(by+1,0,p.h-1)*p.w+clamp(bx+1,0,p.w-1)];
  return(a*(1-fx)+b*fx)*(1-fy)+(c*(1-fx)+d*fx)*fy;
 }
 function coverage(p,qx,qy,footprint){
  if(footprint>2){const t=clamp((distance(p,qx,qy)+footprint/2)/footprint,0,1);return t*t*(3-2*t);}
  let count=0;
  for(let j=0;j<8;j++)for(let i=0;i<8;i++)if(distance(p,qx+((i+.5)/8-.5)*footprint,qy+((j+.5)/8-.5)*footprint)>0)count++;
  return count/64;
 }
 function sample(p,x,y,footprint){
  const qx=x-.5,qy=y-.5,bx=Math.floor(qx),by=Math.floor(qy),wx=weights(qx-bx),wy=weights(qy-by);
  let r=0,g=0,b=0,shadow=0;
  for(let j=0;j<4;j++)for(let i=0;i<4;i++){
   const k=clamp(by+j-1,0,p.h-1)*p.w+clamp(bx+i-1,0,p.w-1),weight=wx[i]*wy[j];
   r+=p.texture[k*4]*weight/255;g+=p.texture[k*4+1]*weight/255;b+=p.texture[k*4+2]*weight/255;shadow+=p.shadow[k]*weight;
  }
  const a=coverage(p,qx,qy,footprint),total=a+clamp(shadow,0,1)*(1-a);
  return total<=1e-6?[0,0,0,total]:[clamp(r,0,1)*a/total,clamp(g,0,1)*a/total,clamp(b,0,1)*a/total,total];
 }
 function render(p,zoom,sdf){
  const w=Math.ceil(p.w*zoom),h=Math.ceil(p.h*zoom),data=new Uint8ClampedArray(w*h*4),footprint=1/zoom;
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){
   const px=(x+.5)/zoom,py=(y+.5)/zoom,rgba=sdf?sample(p,px,py,footprint):window.SIM.sample(p.before,px,py,footprint,'Catmull-Rom');
   const k=(y*w+x)*4;for(let c=0;c<4;c++)data[k+c]=Math.round(clamp(rgba[c],0,1)*255);
  }
  return{w,h,data};
 }
 global.ANKHEG_SDF_SIM={prepare,distance,coverage,sample,render};
})(window);
