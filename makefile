command = python -m nuitka --msvc=latest --remove-output --company-name="xystudio" --copyright="Copyright 2026 xystudio" --trademarks="xystudio" --product-version="1.1.0.0" --standalone

main:
	echo Please run a build command, such as "make ft".

ft: src/ftree.py
	$(command) --file-description="FileTree" --product-name="FileTree" --windows-icon-from-ico=src/res/fticon.ico --include-data-dir=src/res/=res/ src/ftree.py --file-version="1.1.0.0"