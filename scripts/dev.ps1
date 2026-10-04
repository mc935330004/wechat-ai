param(
    [ValidateSet('run', 'test', 'package', 'resolve')]
    [string]$Action = 'run',
    [ValidatePattern('^(ai|database|rag)(,(ai|database|rag))*$')]
    [string]$MavenProfiles,
    [string]$JavaHome = 'D:\java\jdk-17'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$previousJavaHome = $env:JAVA_HOME
$previousPath = $env:Path
Push-Location -LiteralPath $projectRoot
try {
    if (-not (Test-Path -LiteralPath (Join-Path $JavaHome 'bin\javac.exe'))) {
        throw "JDK 17 not found at $JavaHome. Pass -JavaHome with your JDK 17 directory."
    }
    $compilerVersion = & (Join-Path $JavaHome 'bin\javac.exe') -version 2>&1
    if ($LASTEXITCODE -ne 0 -or "$compilerVersion" -notmatch '^javac 17\.') {
        throw "JDK 17 is required; found $compilerVersion."
    }
    $env:JAVA_HOME = $JavaHome
    $env:Path = (Join-Path $JavaHome 'bin') + ';' + $env:Path
    $mavenArguments = @('-B', '-ntp')
    if ($MavenProfiles) { $mavenArguments += '-P' + $MavenProfiles }
    switch ($Action) {
        'run' { $mavenArguments += 'spring-boot:run' }
        'test' { $mavenArguments += 'test' }
        'package' { $mavenArguments += 'package' }
        'resolve' { $mavenArguments += 'dependency:resolve' }
    }
    & (Join-Path $projectRoot 'mvnw.cmd') @mavenArguments
    if ($LASTEXITCODE -ne 0) { throw "Maven failed (exit $LASTEXITCODE)." }
} finally {
    Pop-Location
    $env:JAVA_HOME = $previousJavaHome
    $env:Path = $previousPath
}
