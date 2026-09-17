param(
  [Parameter(Mandatory=$true)][ValidateSet('save-key','has-key','delete-key','save-budget','status','self-test','run-job')][string]$Action,
  [string]$InputPath,
  [string]$OutputPath,
  [switch]$DryRun
)
$ErrorActionPreference='Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$root=Join-Path $env:LOCALAPPDATA 'CorelAIVector'
$keyPath=Join-Path $root 'api_key.dpapi'
$budgetPath=Join-Path $root 'budget.json'
$usagePath=Join-Path $root 'usage.jsonl'
[IO.Directory]::CreateDirectory($root)|Out-Null

function Write-JsonFile($path,$obj){
  if([string]::IsNullOrWhiteSpace($path)){return}
  $json=$obj|ConvertTo-Json -Depth 60 -Compress
  [IO.File]::WriteAllText($path,$json,(New-Object Text.UTF8Encoding($false)))
}
function Protect-Key([string]$key){
  $b=[Text.Encoding]::UTF8.GetBytes($key)
  $p=[Security.Cryptography.ProtectedData]::Protect($b,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser)
  [IO.File]::WriteAllBytes($keyPath,$p)
}
function Read-Key(){
  if(-not(Test-Path -LiteralPath $keyPath)){throw 'Chua luu API key.'}
  $p=[IO.File]::ReadAllBytes($keyPath)
  $b=[Security.Cryptography.ProtectedData]::Unprotect($p,$null,[Security.Cryptography.DataProtectionScope]::CurrentUser)
  return [Text.Encoding]::UTF8.GetString($b)
}
function Price-For([string]$model){
  # USD per 1M tokens; centralized here so a future update can change prices without touching geometry code.
  switch($model){
    'gpt-5.6-luna'{return @{in=0.20;out=1.20}}
    'gpt-5.6-sol'{return @{in=4.00;out=20.00}}
    default{return @{in=2.00;out=12.00}}
  }
}
function Read-Budget(){
  if(-not(Test-Path -LiteralPath $budgetPath)){return 0.0}
  try{$o=Get-Content -LiteralPath $budgetPath -Raw|ConvertFrom-Json;return [Math]::Max(0.0,[double]$o.monthly_usd)}catch{return 0.0}
}
function Save-Budget([double]$value){
  $v=[Math]::Max(0.0,$value)
  Write-JsonFile $budgetPath @{monthly_usd=$v;updated_at=(Get-Date).ToString('o')}
  return $v
}
function Month-Usage(){
  if(-not(Test-Path -LiteralPath $usagePath)){return 0.0}
  $prefix=(Get-Date).ToString('yyyy-MM');$sum=0.0
  Get-Content -LiteralPath $usagePath -ErrorAction SilentlyContinue|ForEach-Object{
    try{$o=$_|ConvertFrom-Json;if($o.month -eq $prefix){$sum += [double]$o.cost_usd}}catch{}
  }
  return $sum
}
function Get-Status(){
  $budget=Read-Budget;$used=Month-Usage
  return @{ok=$true;has_key=(Test-Path -LiteralPath $keyPath);budget_usd=$budget;month_cost_usd=$used;remaining_usd=[Math]::Max(0.0,$budget-$used);appdata=$root}
}

try{
  if($Action -eq 'save-key'){
    if(-not(Test-Path -LiteralPath $InputPath)){throw 'Khong tim thay file key tam.'}
    $key=[IO.File]::ReadAllText($InputPath).Trim()
    if($key.Length -lt 20){throw 'API key khong hop le.'}
    Protect-Key $key
    Remove-Item -LiteralPath $InputPath -Force -ErrorAction SilentlyContinue
    Write-JsonFile $OutputPath @{ok=$true;has_key=$true};exit 0
  }
  if($Action -eq 'has-key'){Write-JsonFile $OutputPath @{ok=$true;has_key=(Test-Path -LiteralPath $keyPath)};exit 0}
  if($Action -eq 'delete-key'){Remove-Item -LiteralPath $keyPath -Force -ErrorAction SilentlyContinue;Write-JsonFile $OutputPath @{ok=$true;has_key=$false};exit 0}
  if($Action -eq 'save-budget'){
    if(-not(Test-Path -LiteralPath $InputPath)){throw 'Khong tim thay budget input.'}
    $o=Get-Content -LiteralPath $InputPath -Raw|ConvertFrom-Json
    $v=Save-Budget ([double]$o.monthly_usd)
    Write-JsonFile $OutputPath @{ok=$true;budget_usd=$v;month_cost_usd=(Month-Usage)};exit 0
  }
  if($Action -eq 'status'){Write-JsonFile $OutputPath (Get-Status);exit 0}
  if($Action -eq 'self-test'){
    $s=Get-Status;$s.powershell=$PSVersionTable.PSVersion.ToString();$s.tls12=$true
    Write-JsonFile $OutputPath $s;exit 0
  }
  if($Action -eq 'run-job'){
    if(-not(Test-Path -LiteralPath $InputPath)){throw 'Khong tim thay job.json.'}
    $job=Get-Content -LiteralPath $InputPath -Raw|ConvertFrom-Json
    $budget=Read-Budget
    if($budget -le 0){throw 'Ngan sach API dang bang 0. Hay luu ngan sach duong truoc khi goi AI.'}
    $used=Month-Usage
    if($used -ge $budget){throw ('Da cham gioi han ngan sach thang: $'+$used.ToString('0.0000'))}
    $model=if($job.model){[string]$job.model}else{'gpt-5.6-terra'}
    $maxOut=if($job.max_output_tokens){[int]$job.max_output_tokens}else{6000}
    $estimateIn=if($job.estimated_input_tokens){[double]$job.estimated_input_tokens}else{20000.0}
    $pr=Price-For $model
    $worst=($estimateIn/1000000.0)*$pr.in+($maxOut/1000000.0)*$pr.out
    if(($used+$worst) -gt $budget){throw ('Du toan toi da $'+$worst.ToString('0.0000')+' se vuot ngan sach con lai $'+([Math]::Max(0,$budget-$used)).ToString('0.0000'))}

    if(-not(Test-Path -LiteralPath $job.image_path)){throw 'Khong tim thay anh input.'}
    $prompt=[IO.File]::ReadAllText($job.prompt_path)
    $schema=Get-Content -LiteralPath $job.schema_path -Raw|ConvertFrom-Json
    $bytes=[IO.File]::ReadAllBytes($job.image_path);$b64=[Convert]::ToBase64String($bytes);$dataUrl='data:image/png;base64,'+$b64
    $body=@{
      model=$model
      store=$false
      reasoning=@{effort='medium'}
      max_output_tokens=$maxOut
      input=@(@{role='user';content=@(
        @{type='input_text';text=$prompt},
        @{type='input_image';image_url=$dataUrl;detail='high'}
      )})
      text=@{format=@{type='json_schema';name='corel_ai_vector_geometry_plan';strict=$true;schema=$schema}}
    }
    $bodyJson=$body|ConvertTo-Json -Depth 60 -Compress
    if($DryRun){Write-JsonFile $OutputPath @{ok=$true;dry_run=$true;budget_usd=$budget;used_usd=$used;worst_case_usd=$worst;request=($bodyJson|ConvertFrom-Json)};exit 0}

    $key=Read-Key
    $headers=@{Authorization=('Bearer '+$key);'Content-Type'='application/json'}
    $resp=Invoke-RestMethod -Uri 'https://api.openai.com/v1/responses' -Method Post -Headers $headers -Body ([Text.Encoding]::UTF8.GetBytes($bodyJson)) -TimeoutSec 110
    $text=$null
    foreach($item in $resp.output){
      if($item.type -eq 'message'){
        foreach($c in $item.content){if($c.type -eq 'output_text'){$text=$c.text;break}}
      }
      if($text){break}
    }
    if([string]::IsNullOrWhiteSpace($text)){throw 'API khong tra structured output text.'}
    $plan=$text|ConvertFrom-Json
    $inTok=[double]$resp.usage.input_tokens;$outTok=[double]$resp.usage.output_tokens
    $cost=($inTok/1000000.0)*$pr.in+($outTok/1000000.0)*$pr.out
    $entry=@{month=(Get-Date).ToString('yyyy-MM');at=(Get-Date).ToString('o');model=$model;input_tokens=$inTok;output_tokens=$outTok;cost_usd=$cost}
    Add-Content -LiteralPath $usagePath -Value ($entry|ConvertTo-Json -Compress) -Encoding UTF8
    Write-JsonFile $OutputPath @{ok=$true;plan=$plan;usage=$entry;month_cost_usd=(Month-Usage);budget_usd=$budget};exit 0
  }
}catch{
  try{Write-JsonFile $OutputPath @{ok=$false;error=$_.Exception.Message}}catch{}
  exit 1
}
