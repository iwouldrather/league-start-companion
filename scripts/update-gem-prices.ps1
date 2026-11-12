param([switch]$Refresh)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$cache=Join-Path $root '.cache/gem-prices'
New-Item -ItemType Directory -Path $cache -Force | Out-Null
$snapshot=Get-Content -LiteralPath (Join-Path $root 'source/gem-acquisition.json') -Raw | ConvertFrom-Json
$requests=@($snapshot.gems.PSObject.Properties | Where-Object { @($_.Value.routes | Where-Object { $_.act -le 3 -and $_.kind -in @('vendor','reward','starter') }).Count } | ForEach-Object { [pscustomobject]@{name=$_.Name;url=$_.Value.source} })
$results=$requests | ForEach-Object -ThrottleLimit 4 -Parallel {
 $request=$_
 $hash=[Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($request.url)))
 $path=Join-Path $using:cache ($hash+'.json')
 if((Test-Path -LiteralPath $path) -and -not $using:Refresh){Get-Content -LiteralPath $path -Raw | ConvertFrom-Json;return}
 for($attempt=0;$attempt -lt 3;$attempt++){
  try{
   $page=(Invoke-WebRequest -Uri $request.url -TimeoutSec 30).Content
   $row=[regex]::Match($page,'(?si)<tr[^>]*>\s*<t[dh][^>]*>Cost</t[dh]>\s*<td[^>]*>(.*?)</td>')
   if(-not $row.Success){$row=[regex]::Match($page,'(?si)<div class="name">Cost</div>\s*<div class="value">(.*?)</div>')}
   $text=[Net.WebUtility]::HtmlDecode([regex]::Replace($row.Groups[1].Value,'<[^>]*>',''))
   $cost=[regex]::Match($text,'Normal:\s*(\d+)x\s*(Scroll of Wisdom|Orb of Transmutation|Orb of Alteration|Orb of Chance|Orb of Alchemy)')
   if(-not $cost.Success){throw 'Normal level-1 gem price not found'}
   $result=[pscustomobject]@{name=$request.name;amount=[int]$cost.Groups[1].Value;currency=$cost.Groups[2].Value;source=$request.url;checkedAt=(Get-Date).ToUniversalTime().ToString('o')}
   $result | ConvertTo-Json -Compress | Set-Content -LiteralPath $path
   $result;return
  }catch{if($attempt -lt 2){Start-Sleep -Seconds (1+$attempt)}}
 }
 [pscustomobject]@{name=$request.name;source=$request.url;error='Price unavailable'}
}
$gems=@{};foreach($result in $results){$gems[$result.name]=$result}
@{checkedAt=(Get-Date).ToUniversalTime().ToString('o');gems=$gems} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $root 'source/gem-costs.json')
Write-Output ('Saved prices: '+@($results | Where-Object amount).Count+'/'+$results.Count)
