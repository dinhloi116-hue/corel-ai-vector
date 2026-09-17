(function(root,factory){
  var api=factory();
  if(typeof module==='object'&&module.exports){module.exports=api;}else{root.CAIVG=api;}
})(this,function(){
  'use strict';
  var G={};
  function num(v,d){v=Number(v);return isFinite(v)?v:(d===undefined?0:d);}
  function clamp(v,a,b){return Math.max(a,Math.min(b,v));}
  function rad(deg){return num(deg)*Math.PI/180;}
  function normDeg(deg){deg=num(deg)%360;if(deg<0)deg+=360;return deg;}
  function avgAngle(a,b){
    var ar=rad(a),br=rad(b),x=Math.cos(ar)+Math.cos(br),y=Math.sin(ar)+Math.sin(br);
    if(Math.abs(x)+Math.abs(y)<1e-9)return normDeg(a);
    return normDeg(Math.atan2(y,x)*180/Math.PI);
  }
  function point(p){return {x:num(p&&p.x),y:num(p&&p.y)};}
  function arrPoint(a){return {x:clamp(num(a&&a[0]),0,1),y:clamp(num(a&&a[1]),0,1)};}
  function dist(a,b){var dx=b.x-a.x,dy=b.y-a.y;return Math.sqrt(dx*dx+dy*dy);}
  function clone(obj){return JSON.parse(JSON.stringify(obj));}

  // Tangent angles describe the FORWARD direction of the path at each endpoint.
  // The incoming control point is therefore endpoint - forwardTangent * handleLength.
  G.solveSegment=function(p0,p1,t0Deg,t1Deg,outRatio,inRatio){
    p0=point(p0);p1=point(p1);var d=dist(p0,p1);if(d<1e-9)d=1e-9;
    var r0=clamp(num(outRatio,0.333333),0.02,0.8),r1=clamp(num(inRatio,0.333333),0.02,0.8);
    var a0=rad(t0Deg),a1=rad(t1Deg);
    return {
      c1:{x:p0.x+Math.cos(a0)*d*r0,y:p0.y+Math.sin(a0)*d*r0},
      c2:{x:p1.x-Math.cos(a1)*d*r1,y:p1.y-Math.sin(a1)*d*r1}
    };
  };

  function enforceContinuity(regions,closed){
    var i,next,a;
    for(i=0;i<regions.length;i++){
      next=(i+1<regions.length)?regions[i+1]:(closed?regions[0]:null);
      if(!next)continue;
      if(Math.abs(regions[i].end.x-next.start.x)<0.02 && Math.abs(regions[i].end.y-next.start.y)<0.02){
        a={x:(regions[i].end.x+next.start.x)/2,y:(regions[i].end.y+next.start.y)/2};
        regions[i].end=a; next.start={x:a.x,y:a.y};
      }
      if(regions[i].continuity_to_next==='g1'||regions[i].continuity_to_next==='g2'){
        a=avgAngle(regions[i].end_tangent_deg,next.start_tangent_deg);
        regions[i].end_tangent_deg=a; next.start_tangent_deg=a;
      }
    }
  }

  G.normalizePlan=function(plan){
    if(!plan||!plan.glyphs||!plan.glyphs.length)throw new Error('Geometry plan khong co glyph.');
    var out={version:Number(plan.version)||1,glyphs:[]},gi,pi,ri,g,p,r,regions,start,end;
    for(gi=0;gi<plan.glyphs.length;gi++){
      g=plan.glyphs[gi];var ng={id:String(g.id||('glyph_'+gi)),label:String(g.label||''),confidence:clamp(num(g.confidence,0.5),0,1),paths:[]};
      if(!g.paths||!g.paths.length)continue;
      for(pi=0;pi<g.paths.length;pi++){
        p=g.paths[pi];regions=[];
        for(ri=0;ri<(p.regions||[]).length;ri++){
          r=p.regions[ri];start=arrPoint(r.start);end=arrPoint(r.end);
          if(ri>0){var prev=regions[regions.length-1].end;if(Math.abs(prev.x-start.x)<0.02&&Math.abs(prev.y-start.y)<0.02)start={x:prev.x,y:prev.y};}
          regions.push({
            kind:String(r.kind||'smooth_curve'),start:start,end:end,
            start_tangent_deg:normDeg(r.start_tangent_deg),end_tangent_deg:normDeg(r.end_tangent_deg),
            out_handle_ratio:clamp(num(r.out_handle_ratio,0.333333),0.02,0.8),
            in_handle_ratio:clamp(num(r.in_handle_ratio,0.333333),0.02,0.8),
            continuity_to_next:String(r.continuity_to_next||'none'),
            allow_intermediate_anchor:!!r.allow_intermediate_anchor
          });
        }
        if(regions.length){enforceContinuity(regions,p.closed!==false);ng.paths.push({role:String(p.role||'outer'),closed:p.closed!==false,regions:regions});}
      }
      if(ng.paths.length)out.glyphs.push(ng);
    }
    if(!out.glyphs.length)throw new Error('Geometry plan khong co path hop le.');
    return out;
  };

  G.makePathSegments=function(path){
    var segs=[],regions=path.regions||[],i,r,s;
    for(i=0;i<regions.length;i++){
      r=regions[i];
      if(r.kind==='line'||r.kind==='sharp_corner')segs.push({type:'line',p0:r.start,p1:r.end});
      else{s=G.solveSegment(r.start,r.end,r.start_tangent_deg,r.end_tangent_deg,r.out_handle_ratio,r.in_handle_ratio);segs.push({type:'cubic',p0:r.start,c1:s.c1,c2:s.c2,p1:r.end});}
    }
    return segs;
  };

  function lum(data,w,x,y){var i=(y*w+x)*4;return data[i]*0.299+data[i+1]*0.587+data[i+2]*0.114;}
  function grad(data,w,h,x,y){
    if(x<1||y<1||x>=w-1||y>=h-1)return 0;
    var gx=lum(data,w,x+1,y)-lum(data,w,x-1,y),gy=lum(data,w,x,y+1)-lum(data,w,x,y-1);
    return Math.sqrt(gx*gx+gy*gy);
  }
  function snapPoint(p,imageData,radius,minGradient){
    var w=imageData.width,h=imageData.height,data=imageData.data;
    var cx=Math.round(clamp(p.x,0,1)*(w-1)),cy=Math.round(clamp(p.y,0,1)*(h-1));
    var bestX=cx,bestY=cy,best=-1,x,y,g,dx,dy,score;
    radius=Math.max(1,Math.round(radius||7));minGradient=num(minGradient,18);
    for(y=Math.max(1,cy-radius);y<=Math.min(h-2,cy+radius);y++)for(x=Math.max(1,cx-radius);x<=Math.min(w-2,cx+radius);x++){
      g=grad(data,w,h,x,y);dx=x-cx;dy=y-cy;
      // Strong edge wins, but do not jump to unrelated interior detail unless much stronger.
      score=g-Math.sqrt(dx*dx+dy*dy)*3.0;
      if(score>best){best=score;bestX=x;bestY=y;}
    }
    if(best<minGradient)return {x:p.x,y:p.y,snapped:false,score:best};
    return {x:bestX/(w-1),y:bestY/(h-1),snapped:true,score:best};
  }
  G.snapPlanToImageData=function(plan,imageData,radius,minGradient){
    plan=G.normalizePlan(clone(plan));
    var cache={},gi,pi,ri,r,j,s,e;
    function key(p){return Math.round(p.x*10000)+','+Math.round(p.y*10000);}
    function one(p){k=key(p);if(!cache[k])cache[k]=snapPoint(p,imageData,radius,minGradient);return {x:cache[k].x,y:cache[k].y};}
    for(gi=0;gi<plan.glyphs.length;gi++)for(pi=0;pi<plan.glyphs[gi].paths.length;pi++){
      var path=plan.glyphs[gi].paths[pi];
      for(ri=0;ri<path.regions.length;ri++){r=path.regions[ri];r.start=one(r.start);r.end=one(r.end);}
      enforceContinuity(path.regions,path.closed);
    }
    return plan;
  };

  G.toDoc=function(p,meta){return {x:meta.left+p.x*meta.docWidth,y:meta.bottom+(1-p.y)*meta.docHeight};};
  G._avgAngle=avgAngle;
  return G;
});
