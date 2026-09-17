(function(root){
'use strict';
var C={};
C.CDR_PNG=802; C.CDR_SELECTION=2; C.CDR_RGB=4; C.CDR_NORMAL_AA=1;
var _app=null;
function app(){if(_app)return _app;_app=window.external.Application;return _app;}
function fso(){return new ActiveXObject('Scripting.FileSystemObject');}
function shell(){return new ActiveXObject('WScript.Shell');}
function q(s){return '"'+String(s).replace(/"/g,'\\"')+'"';}
C.app=app;
C.localRoot=function(){var p=shell().ExpandEnvironmentStrings('%LOCALAPPDATA%')+'\\CorelAIVector';if(!fso().FolderExists(p))fso().CreateFolder(p);return p;};
C.addonDir=function(){var u=decodeURIComponent(window.location.pathname||'').replace(/^\//,'').replace(/\//g,'\\');return fso().GetParentFolderName(u);};
C.writeText=function(path,text){var ts=fso().CreateTextFile(path,true,true);ts.Write(String(text));ts.Close();};
C.readText=function(path){var ts=fso().OpenTextFile(path,1,false,-1);var t=ts.ReadAll();ts.Close();return t;};
C.exists=function(path){return fso().FileExists(path);};
C.makeJobDir=function(){var base=C.localRoot()+'\\jobs';if(!fso().FolderExists(base))fso().CreateFolder(base);var id='job_'+(new Date().getTime())+'_'+Math.floor(Math.random()*1000000);var p=base+'\\'+id;fso().CreateFolder(p);return p;};
C.bridgeCommand=function(action,inputPath,outputPath,extra){var ps=C.addonDir()+'\\CorelAIVectorBridge.ps1';var cmd='powershell.exe -NoProfile -ExecutionPolicy Bypass -File '+q(ps)+' -Action '+q(action);if(inputPath)cmd+=' -InputPath '+q(inputPath);if(outputPath)cmd+=' -OutputPath '+q(outputPath);if(extra&&extra.dryRun)cmd+=' -DryRun';return cmd;};
C.runBridgeAsync=function(action,inputPath,outputPath,callback,extra){try{if(C.exists(outputPath))fso().DeleteFile(outputPath,true);shell().Run(C.bridgeCommand(action,inputPath,outputPath,extra),0,false);var started=new Date().getTime();var timer=setInterval(function(){if(C.exists(outputPath)){clearInterval(timer);try{callback(null,JSON.parse(C.readText(outputPath)));}catch(e){callback(e);}}else if(new Date().getTime()-started>120000){clearInterval(timer);callback(new Error('Bridge timeout'));}},250);}catch(e){callback(e);}};
C.saveApiKey=function(key,callback){var d=C.makeJobDir(),inp=d+'\\key.txt',out=d+'\\result.json';C.writeText(inp,key);C.runBridgeAsync('save-key',inp,out,callback);};
C.bridgeSelfTest=function(callback){var d=C.makeJobDir(),out=d+'\\result.json';C.runBridgeAsync('self-test','',out,callback);};
C.saveBudget=function(value,callback){var d=C.makeJobDir(),inp=d+'\\budget.json',out=d+'\\result.json';C.writeText(inp,JSON.stringify({monthly_usd:Math.max(0,Number(value)||0)}));C.runBridgeAsync('save-budget',inp,out,callback);};
C.getStatus=function(callback){var d=C.makeJobDir(),out=d+'\\result.json';C.runBridgeAsync('status','',out,callback);};
C.estimateMaxCost=function(model){var price={'gpt-5.6-luna':[0.20,1.20],'gpt-5.6-terra':[2.00,12.00],'gpt-5.6-sol':[4.00,20.00]}[model]||[2.00,12.00];return 20000/1000000*price[0]+6000/1000000*price[1];};
C.getSelectionMeta=function(){var a=app(),d=a.ActiveDocument;if(!d)throw new Error('Chua mo tai lieu CorelDRAW.');var sr=a.ActiveSelectionRange;if(!sr||sr.Count!==1)throw new Error('Hay chon dung 1 doi tuong/bitmap.');return {range:sr,left:sr.LeftX,bottom:sr.BottomY,docWidth:sr.SizeWidth,docHeight:sr.SizeHeight};};
C.exportSelectionPng=function(path,maxPx){var a=app(),d=a.ActiveDocument,m=C.getSelectionMeta(),ratio=m.docWidth/m.docHeight,w,h;if(ratio>=1){w=maxPx;h=Math.max(1,Math.round(maxPx/ratio));}else{h=maxPx;w=Math.max(1,Math.round(maxPx*ratio));}var ef=d.ExportBitmap(path,C.CDR_PNG,C.CDR_SELECTION,C.CDR_RGB,w,h,300,300,C.CDR_NORMAL_AA,false,true,true,false,0);if(ef&&ef.Finish)ef.Finish();m.path=path;m.width=w;m.height=h;return m;};
C.makeFixturePlan=function(){return {version:1,glyphs:[{id:'fixture_oval',label:'TEST',confidence:1,paths:[{role:'outer',closed:true,regions:[
{kind:'smooth_curve',start:[0.5,0.05],end:[0.95,0.5],start_tangent_deg:0,end_tangent_deg:90,out_handle_ratio:0.390524,in_handle_ratio:0.390524,continuity_to_next:'g1',allow_intermediate_anchor:false},
{kind:'smooth_curve',start:[0.95,0.5],end:[0.5,0.95],start_tangent_deg:90,end_tangent_deg:180,out_handle_ratio:0.390524,in_handle_ratio:0.390524,continuity_to_next:'g1',allow_intermediate_anchor:false},
{kind:'smooth_curve',start:[0.5,0.95],end:[0.05,0.5],start_tangent_deg:180,end_tangent_deg:270,out_handle_ratio:0.390524,in_handle_ratio:0.390524,continuity_to_next:'g1',allow_intermediate_anchor:false},
{kind:'smooth_curve',start:[0.05,0.5],end:[0.5,0.05],start_tangent_deg:270,end_tangent_deg:360,out_handle_ratio:0.390524,in_handle_ratio:0.390524,continuity_to_next:'g1',allow_intermediate_anchor:false}
]}]}]};};
C.buildCurveFromPlan=function(plan,meta){var a=app(),d=a.ActiveDocument;if(!d)throw new Error('Chua mo tai lieu CorelDRAW.');plan=CAIVG.normalizePlan(plan);var shapes=[],gi,pi,ri,g,p,segs,first,sp,crv,s,seg,P0,P1,C1,C2;d.BeginCommandGroup('Corel AI Vector');try{a.Optimization=true;for(gi=0;gi<plan.glyphs.length;gi++){g=plan.glyphs[gi];crv=a.CreateCurve(d);for(pi=0;pi<g.paths.length;pi++){p=g.paths[pi];segs=CAIVG.makePathSegments(p);if(!segs.length)continue;first=CAIVG.toDoc(segs[0].p0,meta);sp=crv.CreateSubPath(first.x,first.y);for(ri=0;ri<segs.length;ri++){seg=segs[ri];P1=CAIVG.toDoc(seg.p1,meta);if(seg.type==='line')sp.AppendLineSegment(P1.x,P1.y,false);else{C1=CAIVG.toDoc(seg.c1,meta);C2=CAIVG.toDoc(seg.c2,meta);sp.AppendCurveSegment2(P1.x,P1.y,C1.x,C1.y,C2.x,C2.y,false);}}sp.Closed=!!p.closed;}s=d.ActiveLayer.CreateCurve(crv);try{s.Name='CAIV_'+g.id;}catch(ignore){}try{s.Fill.ApplyUniformFill(a.CreateRGBColor(0,0,0));s.Outline.SetNoOutline();}catch(styleErr){}shapes.push(s);}a.Optimization=false;d.EndCommandGroup();try{a.ActiveWindow.Refresh();}catch(refreshErr){}return shapes;}catch(e){try{a.Optimization=false;}catch(oe){}try{d.EndCommandGroup();}catch(ce){}throw e;}};
C.drawFixture=function(){var m=C.getSelectionMeta();var gap=m.docWidth*0.15;var meta={left:m.left+m.docWidth+gap,bottom:m.bottom,docWidth:m.docWidth*0.55,docHeight:m.docHeight*0.55};return C.buildCurveFromPlan(C.makeFixturePlan(),meta);};
C.snapPlanWithPng=function(plan,pngPath,callback){
  try{
    var img=new Image();
    img.onload=function(){
      try{var cv=document.createElement('canvas');cv.width=img.naturalWidth||img.width;cv.height=img.naturalHeight||img.height;var ctx=cv.getContext('2d');ctx.drawImage(img,0,0);var data=ctx.getImageData(0,0,cv.width,cv.height);callback(null,CAIVG.snapPlanToImageData(plan,data,8,18));}catch(e){callback(null,plan);}
    };
    img.onerror=function(){callback(null,plan);};
    img.src='file:///'+String(pngPath).replace(/\\/g,'/');
  }catch(e){callback(null,plan);}
};
C.runAi=function(model,callback){
  try{
    var d=C.makeJobDir(),png=d+'\\source.png',meta=C.exportSelectionPng(png,1600);
    var job={image_path:png,prompt_path:C.addonDir()+'\\geometry_prompt.txt',schema_path:C.addonDir()+'\\geometry_schema.json',model:model||'gpt-5.6-terra',max_output_tokens:6000,estimated_input_tokens:20000,pass_type:'geometry_plan'};
    var inp=d+'\\job.json',out=d+'\\result.json';C.writeText(inp,JSON.stringify(job));
    C.runBridgeAsync('run-job',inp,out,function(err,r){
      if(err)return callback(err);if(!r||!r.ok)return callback(new Error((r&&r.error)||'AI bridge failed'));
      C.snapPlanWithPng(r.plan,png,function(snapErr,snapped){
        try{var plan=snapped||r.plan;var shapes=C.buildCurveFromPlan(plan,meta);callback(null,{result:r,plan:plan,shapes:shapes,source:meta});}catch(e){callback(e);}
      });
    });
  }catch(e){callback(e);}
};
root.CAIV=C;
})(this);
