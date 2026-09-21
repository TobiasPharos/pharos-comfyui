# assumes to be in comfyui directory
param(
    [string]$uvPath = "",
    [string]$cacheDir = "",
    [string]$pypiUrl = "",
    [string]$pythonVersion = "",
    [string[]]$plugins = @(),
    [string[]]$extraDependencies = @(),
    [string]$cudaVersion = "",
    [bool]$installSageAttention = $false
)

# Function to get dependencies from a requirements.txt file
function Get-PluginDependencies {
    param([string]$requirementsPath)
    if (Test-Path $requirementsPath) {
        $dependencies = @()
        Get-Content $requirementsPath | ForEach-Object {
            $line = $_.Trim()
            if ($line -and -not $line.StartsWith("#")) {
                # Extract package name (remove version specifiers and handle all pip requirement syntax)
                # Handle operators: ==, >=, <=, >, <, !=, ~=, ===
                # Handle extras: package[extra1,extra2]
                # Handle URLs and VCS: git+https://...
                $packageName = ""
                if ($line -match '^([a-zA-Z0-9_-]+)') {
                    $packageName = $matches[1]
                } elseif ($line -match '^git\+.*#egg=([a-zA-Z0-9_-]+)') {
                    $packageName = $matches[1]
                } else {
                    # Fallback: split on common operators and take first part
                    $packageName = ($line -split '[<>=!~\[\s]')[0]
                }
                if ($packageName) {
                    $dependencies += $packageName.Trim()
                }
            }
        }
        return $dependencies
    }
    return @()
}

# Function to collect dependencies from multiple plugins
function Get-Dependencies {
    param($fromPlugins)
    $result = @{}
    foreach ($plugin in $fromPlugins) {
        $requirementsPath = ".\custom_nodes\$plugin\requirements.txt"
        $dependencies = Get-PluginDependencies -requirementsPath $requirementsPath
        $result[$plugin] = $dependencies
    }
    return $result
}

# ensure uv is installed
$uv = "uv"
if ($uvPath) {
    Write-Output "Using uv from: $uvPath"
    $uv = $uvPath
}
if ((-not $uvPath) -and (-not (Get-Command $uv -ErrorAction SilentlyContinue))) {
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:Path += ";$env:USERPROFILE\.cargo\bin"
}

if ($cacheDir) {
    Write-Output "Setting cache directory to $cacheDir"
    $env:UV_CACHE_DIR = $cacheDir
}

# install temp venv to get protected dependencies
$tempVenv = ".venv-baseline"
Write-Output "Creating temporary venv at $PWD\$tempVenv"
& $uv venv $tempVenv --python $pythonVersion
& "$tempVenv\Scripts\activate"
& $uv pip install --pre torch torchvision torchaudio --index-url $pypiUrl
& $uv pip install -r requirements.txt
$baselineDependencies = & $uv pip list --format json | ConvertFrom-Json
$protectedDependencies = $baselineDependencies | ForEach-Object { $_.name }
deactivate
Remove-Item -Path $tempVenv -Recurse -Force

# create local venv
& $uv venv --allow-existing --python $pythonVersion
if (-not $?) {
    Write-Output "Failed to create venv. Check if Comfy server is already running."
    exit 1
}
.venv\Scripts\activate
& $uv pip install --pre torch torchvision torchaudio --index-url $pypiUrl
& $uv pip install -r requirements.txt

if ($installSageAttention) {
    # Install Triton
    Write-Output "::: Installing Triton :::"
    $maxTorchVersion = "2.10"
    $torchVersion = & $uv run python -c "import torch; print(torch.__version__.split(chr(43))[0].rsplit(chr(46),1)[0])"
    if ([version]$torchVersion -gt [version]$maxTorchVersion) {
        Write-Output "Detected torch version $torchVersion is greater than max supported version $maxTorchVersion. Using $maxTorchVersion for Triton installation."
        $torchVersion = $maxTorchVersion
    }
    $pipArgs = @(
    #    "--no-cache"
    )

    Write-Output "Uninstalling any existing triton-windows installation"
    & $uv pip uninstall triton-windows -y *> $null
    $tritonConstraint = switch ($torchVersion) {
        "2.7" { "triton-windows<3.4" }
        "2.8" { "triton-windows<3.5" }
        "2.9" { "triton-windows<3.6" }
        "2.10" { "triton-windows<3.7" }
        default { $null }
    }

    if ($tritonConstraint) {
        Write-Output "Installing $tritonConstraint for torch version $torchVersion"
        Write-Output "Running: $uv pip install $tritonConstraint $($pipArgs -join ' ')"
        & $uv pip install $tritonConstraint $pipArgs
        if ($?) {
            $tritonInstalled = & $uv run python -c "import triton; print(triton.__version__)"
            if (-not $?) {
                Write-Output "Failed to verify triton-windows installation for torch version $torchVersion"
                exit 1
            }
            Write-Output "Successfully installed triton-windows for torch version $torchVersion\: $tritonInstalled"
        } else {
            $tritonInstalled = $null
            Write-Output "Failed to install triton-windows for torch version $torchVersion"
        }
    } else {
        Write-Output "Skipping triton-windows install for unsupported torch version: $torchVersion"
    }

    if ($tritonInstalled) {
        # Install SageAttention 2.2.0 and SageAttention 3
        Write-Output "::: Installing SageAttention 2.2.0 :::"

        $sage2Wheel = switch ("$torchVersion|$cudaVersion") {
            "2.7|12.8" { "v2.2.0-windows.post3/sageattention-2.2.0+cu128torch2.7.1.post3-cp39-abi3-win_amd64.whl" }
            "2.8|12.8" { "v2.2.0-windows.post3/sageattention-2.2.0+cu128torch2.8.0.post3-cp39-abi3-win_amd64.whl" }
            "2.9|13.0" { "v2.2.0-windows.post5/sageattention-2.2.0+cu130torch2.9.1.post5-cp310-abi3-win_amd64.whl" }
            "2.10|13.0" { "v2.2.0-windows.post5/sageattention-2.2.0+cu130torch2.10.0andhigher.post5-cp310-abi3-win_amd64.whl" }
            default { $null }
        }

        Write-Output "Uninstalling any existing SageAttention installation"
        & $uv pip uninstall sageattention -y *> $null
        if ($sage2Wheel) {
            Write-Output "Installing SageAttention 2.2.0 from $sage2Wheel"
            $sage2Url = "https://github.com/woct0rdho/SageAttention/releases/download/"
            Write-Output "Running: $uv pip install $sage2Url$sage2Wheel $($pipArgs -join ' ')"
            & $uv pip install $sage2Url$sage2Wheel $pipArgs
            if (-not $?) {
                Write-Output "Failed to install SageAttention 2.2.0 from $sage2Url$sage2Wheel"
                exit 1
            } else {
                Write-Output "Successfully installed SageAttention 2.2.0"
            }
        } else {
            Write-Output "No matching SageAttention 2.2.0 version found for torch=$torchVersion and cuda=$cudaVersion"
        }

        Write-Output "::: Installing SageAttention 3 :::"

        $sage3Wheel = switch ("$torchVersion|$cudaVersion") {
            "2.7|12.8" { "https://github.com/mengqin/SageAttention/releases/download/20251229/sageattn3-1.0.0+cu128torch271-cp312-cp312-win_amd64.whl" }
            "2.8|12.8" { "https://github.com/mengqin/SageAttention/releases/download/20251229/sageattn3-1.0.0+cu128torch280-cp312-cp312-win_amd64.whl" }
            "2.9|13.0" { "https://github.com/mengqin/SageAttention/releases/download/20251229/sageattn3-1.0.0+cu130torch291-cp312-cp312-win_amd64.whl" }
            "2.10|13.0" { "https://huggingface.co/ussoewwin/Sage-Attention-for-Windows/resolve/main/sageattn3-1.0.0+cu130torch2.10.0-cp312-cp312-win_amd64.whl" }
            default { $null }
        }

        Write-Output "Uninstalling any existing SageAttention 3 installation"
        & $uv pip uninstall sageattn3 -y *> $null
        if ($sage3Wheel) {
            Write-Output "Installing SageAttention 3 from $sage3Wheel"
            Write-Output "Running: $uv pip install $sage3Wheel $($pipArgs -join ' ')"
            & $uv pip install $sage3Wheel $pipArgs
            if (-not $?) {
                Write-Output "Failed to install SageAttention 3 from $sage3Wheel"
                exit 1
            } else {
                Write-Output "Successfully installed SageAttention 3"
            }
        } else {
            Write-Output "No matching SageAttention 3 version found for torch=$torchVersion and cuda=$cudaVersion"
        }
    }
}

# Get existing plugins in custom_nodes directory
Write-Output "Checking existing plugins in custom_nodes directory..."
$customNodesPath = ".\custom_nodes"
$existingPlugins = @()
if (Test-Path $customNodesPath) {
    $existingPlugins = Get-ChildItem -Path $customNodesPath -Directory | ForEach-Object { $_.Name }
}

# Find plugins to remove (existing but not in plugins list)
Write-Output "Checking for plugins to remove, which are not in the provided plugins list..."
$pluginsToRemove = $existingPlugins | Where-Object { $_ -notin $plugins }
$pluginsToKeep = $existingPlugins | Where-Object { $_ -in $plugins }

# Build dependency maps using the refactored function
$allPluginDependencies = Get-Dependencies $pluginsToKeep
$removedPluginDependencies = Get-Dependencies $pluginsToRemove

# Remove unwanted plugins
foreach ($plugin in $pluginsToRemove) {
    $pluginPath = ".\custom_nodes\$plugin"
    Write-Output "Removing plugin: $plugin"
    if (Test-Path $pluginPath) {
        Remove-Item -Path $pluginPath -Recurse -Force
    }
}

# Find dependencies that were used by removed plugins
# Use the captured protected dependencies (includes all transitive deps) instead of just requirements.txt
Write-Output "Checking for dependencies to remove that are no longer needed..."
$dependenciesToRemove = ($removedPluginDependencies.Values | ForEach-Object { $_ }) | Where-Object { 
    $_ -notin ($allPluginDependencies.Values | ForEach-Object { $_ }) -and $_ -notin $protectedDependencies 
} | Sort-Object -Unique
if ($dependenciesToRemove.Count -gt 0) {
    Write-Output "Found $($dependenciesToRemove.Count) dependencies to remove: $($dependenciesToRemove -join ', ')"
    foreach ($dependency in $dependenciesToRemove) {
        & $uv pip uninstall $dependency -y
    }
}

# install plugins dependencies
foreach ($plugin in $plugins) {
    $plugin_requirements = ".\custom_nodes\$plugin\requirements.txt"
    if (Test-Path $plugin_requirements) {
        Write-Output "Installing $plugin dependencies"
        & $uv pip install -r $plugin_requirements
    }
}

# install extra plugin dependencies
if ($extraDependencies) {
    Write-Output "Installing extra dependencies $($extraDependencies -join ', ')"
    & $uv pip install $extraDependencies
}
