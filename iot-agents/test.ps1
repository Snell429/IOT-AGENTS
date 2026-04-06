param(
    [switch]$SkipComposeUp,
    [switch]$DownWhenDone,
    [int]$TimeoutSeconds = 90
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Test-DockerAvailable {
    try {
        docker version | Out-Null
    }
    catch {
        throw "Docker n'est pas accessible. Ouvre Docker Desktop puis relance le script."
    }
}

function Wait-Endpoint {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][int]$TimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $response = Invoke-RestMethod -Uri $Url -Method Get
            if ($null -ne $response) {
                return $response
            }
        }
        catch {
            Start-Sleep -Seconds 2
        }
    } while ((Get-Date) -lt $deadline)

    throw "Timeout en attendant l'endpoint $Url"
}

function Invoke-JsonPost {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][hashtable]$Body
    )

    return Invoke-RestMethod -Uri $Url -Method Post -ContentType "application/json" -Body ($Body | ConvertTo-Json -Compress)
}

function Assert-Equal {
    param(
        [Parameter(Mandatory = $true)]$Actual,
        [Parameter(Mandatory = $true)]$Expected,
        [Parameter(Mandatory = $true)][string]$Label
    )

    if ($Actual -ne $Expected) {
        throw "$Label attendu '$Expected' mais obtenu '$Actual'."
    }
}

$uiUrl = "http://localhost:8010"
$coordinatorUrl = "http://localhost:8020"
$lampUrl = "http://localhost:8031"
$plugUrl = "http://localhost:8032"
$thermostatUrl = "http://localhost:8033"

$results = New-Object System.Collections.Generic.List[object]

try {
    Write-Step "Verification de Docker"
    Test-DockerAvailable

    if (-not $SkipComposeUp) {
        Write-Step "Demarrage des conteneurs"
        docker compose up --build -d
    }

    Write-Step "Attente des services"
    $healthChecks = @(
        @{ Name = "ui-agent"; Url = "$uiUrl/healthz" },
        @{ Name = "coordinator"; Url = "$coordinatorUrl/healthz" },
        @{ Name = "lamp-agent"; Url = "$lampUrl/healthz" },
        @{ Name = "plug-agent"; Url = "$plugUrl/healthz" },
        @{ Name = "thermostat-agent"; Url = "$thermostatUrl/healthz" }
    )

    foreach ($service in $healthChecks) {
        $health = Wait-Endpoint -Url $service.Url -TimeoutSeconds $TimeoutSeconds
        $results.Add([pscustomobject]@{
            Test = "health:$($service.Name)"
            Status = "OK"
            Detail = ($health | ConvertTo-Json -Compress)
        })
    }

    Write-Step "Scenario 1: allumer la lampe"
    $lampCommand = Invoke-JsonPost -Url "$uiUrl/command" -Body @{ text = "allume la lampe du salon" }
    $lampState = Invoke-RestMethod -Uri "$lampUrl/state" -Method Get
    Assert-Equal -Actual $lampState.state.power -Expected "on" -Label "Etat de la lampe"
    $results.Add([pscustomobject]@{
        Test = "lamp-on"
        Status = "OK"
        Detail = ($lampCommand.response.result.message)
    })

    Write-Step "Scenario 2: eteindre la prise"
    $plugCommand = Invoke-JsonPost -Url "$uiUrl/command" -Body @{ text = "eteins la prise" }
    $plugState = Invoke-RestMethod -Uri "$plugUrl/state" -Method Get
    Assert-Equal -Actual $plugState.state.power -Expected "off" -Label "Etat de la prise"
    $results.Add([pscustomobject]@{
        Test = "plug-off"
        Status = "OK"
        Detail = ($plugCommand.response.result.message)
    })

    Write-Step "Scenario 3: lire l'etat du thermostat"
    $thermostatRead = Invoke-JsonPost -Url "$uiUrl/command" -Body @{ text = "donne-moi l'etat du thermostat" }
    $thermostatState = Invoke-RestMethod -Uri "$thermostatUrl/state" -Method Get
    $results.Add([pscustomobject]@{
        Test = "thermostat-state"
        Status = "OK"
        Detail = "current=$($thermostatState.state.current_temperature), target=$($thermostatState.state.target_temperature)"
    })

    Write-Step "Scenario 4: regler le thermostat a 23 degres"
    $thermostatSet = Invoke-JsonPost -Url "$uiUrl/command" -Body @{ text = "regle le thermostat a 23 degres" }
    $thermostatUpdated = Invoke-RestMethod -Uri "$thermostatUrl/state" -Method Get
    Assert-Equal -Actual $thermostatUpdated.state.target_temperature -Expected 23 -Label "Temperature cible du thermostat"
    $results.Add([pscustomobject]@{
        Test = "thermostat-set"
        Status = "OK"
        Detail = ($thermostatSet.response.result.message)
    })

    Write-Step "Resume"
    $results | Format-Table -AutoSize
    Write-Host ""
    Write-Host "Tous les tests sont passes." -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "Echec des tests: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    if ($DownWhenDone) {
        Write-Step "Arret des conteneurs"
        docker compose down
    }
}
