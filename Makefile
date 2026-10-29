# Optional shortcuts. Without make, run scripts\*.ps1 directly.
# Override the host if you use PowerShell 7: make PS=pwsh check
PS ?= powershell

.PHONY: bootstrap dev check

bootstrap:
	$(PS) -NoProfile -ExecutionPolicy Bypass -File scripts/bootstrap.ps1

dev:
	$(PS) -NoProfile -ExecutionPolicy Bypass -File scripts/dev.ps1

check:
	$(PS) -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1
