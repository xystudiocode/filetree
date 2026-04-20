command = python -m nuitka --msvc=latest --remove-output --company-name="xystudio" --copyright="Copyright 2026 xystudio" --trademarks="xystudio" --product-version="0.1.0" --standalone

main:
	echo Please run a build command, such as "make ft".

ft: ft_exe/main.py
	$(command) --file-description="FileTree" --product-name="FileTree" --windows-icon-from-ico=ft_exe/res/fticon.ico --include-data-dir=ft_exe/res/=res/ ft_exe/main.py --file-version="1.0.0.0"  --enable-plugin=pyside6 --windows-console-mode="disable"
	$(command) --file-description="FileTree" --product-name="FileTree" --windows-icon-from-ico=ft_exe/res/fticon.ico --include-data-dir=ft_exe/res/=res/ ft_exe/main.py --file-version="1.0.0.0"