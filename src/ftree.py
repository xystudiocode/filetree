import sys
import argparse
import json
import os
import base64
from uuid import uuid4
from tempfile import gettempdir
import shutil
import colorama
import subprocess
import winreg
import ctypes

__version__ = '1.1.0'

colorama.init(autoreset=True)

def get_dir_size_for_reg(path):
    '''
    获取文件大小，用于注册表
    '''
    size = 0
    for root, dirs, files in os.walk(path):
        for file in files:
            try:
                size += os.path.getsize(os.path.join(root, file))
            except:
                pass
    return size // 1024

def copy_multiple_sources(sources: list[str], destination: str) -> None:
    '''
    将多个文件或文件夹复制到目标文件夹中。

    Args:
        sources: 源路径列表（文件或文件夹）
        destination: 目标文件夹路径
        overwrite: 如果目标已存在同名文件/文件夹，是否覆盖（默认覆盖）

    Raises:
        FileNotFoundError: 某个源路径不存在
        NotADirectoryError: 目标路径存在但不是一个文件夹
        PermissionError: 权限不足
    '''
    # 确保目标文件夹存在
    shutil.rmtree(destination, ignore_errors=True)
    os.makedirs(destination, exist_ok=True)

    for src in sources:
        endwith_star = False
        if src.endswith('*') and os.path.isdir(src[:-1]):
            src = src[:-1]
            endwith_star = True
        
        if not os.path.exists(src):
            raise FileNotFoundError(f"Source not found: {src}")

        # 目标路径（直接使用源路径的 base name）
        base_name = os.path.basename(src)
        dst_path = os.path.join(destination, base_name)

        if os.path.isfile(src):
            # 处理文件
            shutil.copy2(src, dst_path)  # copy2 保留元数据
        elif os.path.isdir(src):
            # 处理文件夹
            if os.path.exists(dst_path):
                shutil.rmtree(dst_path)
            # 复制整个目录树
            print(f'Copying {src} to', base_name)
            if endwith_star: # 复制整个目录树到根目录
                shutil.copytree(src, dst_path)
            else: # 复制整个目录树到目标文件夹
                shutil.copytree(src, os.path.join(dst_path, src))

def main():
    parser = argparse.ArgumentParser(description="FileTree")
    subparsers = parser.add_subparsers(dest='command', required=True)

    # open 子命令：输出文件内容
    parser_open = subparsers.add_parser('open')
    parser_open.add_argument('file_path', help='File path you want to open')

    # new 子命令：创建文件，可选是否打开
    parser_new = subparsers.add_parser('new')
    parser_new.add_argument('file_path', help='File path you want to create')
    group = parser_new.add_mutually_exclusive_group()
    group.add_argument('--open', '-o', action='store_true', help='Create and open file(default)')
    group.add_argument('--no-open', action='store_true', help='Only create file,')
    group_files = parser_new.add_mutually_exclusive_group()
    group_files.add_argument('--dir', '-d', default='', type=str, help='Create a new file with directory structure')
    group_files.add_argument('-s', '--scattered', default='', type=str, nargs='+', help='Create a new file with some files scattered in the directory structure.\nIf a directory is not ends with "*", it will be treated as a directory and all files will be copied to the root directory of the new file.')
    
    # reg子命令：注册右键菜单
    parser_reg = subparsers.add_parser('reg')
    reg_group = parser_reg.add_mutually_exclusive_group()
    reg_group.add_argument('--unregister', '-u', action='store_true', help='Unregister, and you can uninstall filetree.')
    reg_group.add_argument('--register', '-r', action='store_true', help='Register, and you can use filetree tools.')
    
    # 无参数，显示文档退出
    if len(sys.argv) == 1 or sys.argv[1] in ['-h', '--help']:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if args.command == 'open':
        controller(args.file_path)

    elif args.command == 'new':
        path = args.file_path if args.file_path.endswith('.ft') else args.file_path + '.ft'
        # 创建文件（若已存在则清空）
        try:
            with open(path, 'x') as f:
                f.write(json.dumps({path[:-3]: {"type": "dir", "content": {}}}))
        except FileExistsError:
            print(f'{colorama.Fore.RED}Error: file "{path}" already exists.')
            input(f'{colorama.Fore.YELLOW}Press Enter to exit.')
            sys.exit(1)

        # 决定是否打开：未指定 --no-open 时均打开（包括默认和 --open）
        print(f'{colorama.Fore.GREEN}File "{path}" created successfully.')
        if args.dir:
            save_file(args.dir, path)
        elif args.scattered:
            dir = os.path.join(gettempdir(), 'fileTree', path[:-3])
            try:
                copy_multiple_sources(args.scattered, dir)
                save_file(dir, path)
                shutil.rmtree(dir)
            except Exception as e:
                print(f'{colorama.Fore.RED}Error: {e}')
                os.remove(path)
                input(f'{colorama.Fore.YELLOW}Press Enter to exit.')
                sys.exit(1)
            return
        if not args.no_open:
            controller(path)
        
    elif args.command =='reg':
        if not is_admin():
            run_as_admin('ftree.py', 'ftree.exe', sys.argv[1:])
            sys.exit(0)
        if args.unregister:
            # 注销右键菜单
            unreg()
            input(f'{colorama.Fore.YELLOW}Unregister successfully.Now you can uninstall filetree tools.Path:{os.path.dirname(__file__)}')
        elif args.register:
            # 注册右键菜单
            writekey()
            with open('Initialized', 'w') as f:
                pass
            input(f'{colorama.Fore.YELLOW}Register successfully.Now you can use filetree tools.')
                
def parse_file(data, subpath=''):
    '''
    递归解析json数据映射到文件
    
    如果是目录，则创建目录并在添加新的subpath递归解析
    如果是文件，那么在subpath下创建文件并写入内容
    对于二进制文件，使用base64解码
    
    :params data: json数据
    :params subpath: 子路径(默认为空)
    '''
    
    for k, v in data.items():
        path = os.path.join(temp_path, subpath, k)
        if v['type'] == 'dir':
            # 创建文件夹
            os.mkdir(path)
            # 递归解析
            parse_file(v['content'], subpath=path)
        elif v['type'] == 'file':
            data = base64.b64decode(v['content']) # 解析文件
            with open(path, 'wb') as f: # 写入文件
                f.write(data)

def save_file(dir_path, output_path):
    '''
    保存文件到json的Tree数据
    '''
    if not os.path.exists(dir_path):
        print(f'{colorama.Fore.RED}Error: directory "{dir_path}" does not exist.')
        input(f'{colorama.Fore.YELLOW}Press Enter to exit.')
        return
    if not os.path.isdir(dir_path):
        print(f'{colorama.Fore.RED}Error: "{dir_path}" is not a directory.')
        input(f'{colorama.Fore.YELLOW}Press Enter to exit.')
        return
    
    root_name = os.path.basename(os.path.abspath(dir_path))

    def _build_node(path):
        """递归构建节点（文件夹或文件）"""
        if os.path.isfile(path):
            with open(path, 'rb') as f:
                content_b64 = base64.b64encode(f.read()).decode('utf-8')
            return {
                "type": "file",
                "content": content_b64
            }
        elif os.path.isdir(path):
            children = {}
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                children[item] = _build_node(item_path)
            return {
                "type": "dir",
                "content": children
            }
        else:
            # 忽略链接或其他特殊文件
            return None

    root_node = {
        root_name: _build_node(dir_path)
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(root_node, f)
                
def controller(file_path):
    global temp_path
    
    id = uuid4().hex
    temp_path = os.path.join(gettempdir(), 'fileTree', id)
    os.makedirs(temp_path, exist_ok=True)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        parse_file(data)
    except Exception as e:
        print(f'{colorama.Fore.RED}Error:', e)
        input(f'{colorama.Fore.YELLOW}Press Enter to exit.')
        return
    
    ft_path = os.path.join(temp_path, list(data.keys())[0])
    
    print(f'{colorama.Fore.YELLOW}Filetree{colorama.Fore.RESET} - {colorama.Fore.GREEN}1.0.0')
    print(f'{colorama.Fore.CYAN}File path is at: {colorama.Fore.YELLOW}{ft_path}')
    print(f'{colorama.Fore.GREEN}Press Ctrl+C to exit.')
    
    def main_range():
        try:
            while True:
                pass
        except (KeyboardInterrupt, EOFError):
            # 保存文件
            try:
                save_file(ft_path, file_path)
                try:
                    shutil.rmtree(ft_path)
                except Exception as e:
                    print(f'{colorama.Fore.RED}Error: {e}')
                    print(f'{colorama.Fore.RED}File saved successfully but temporary directory could not be removed completely.Please close all applications and manually remove the directory "{ft_path}"')
                print(f'{colorama.Fore.GREEN}Exit.')
                sys.exit(0)
            except Exception as e:
                print(f'{colorama.Fore.RED}Error:', e)
                print(f'{colorama.Fore.RED}Failed to save file. Please close all applications try again.')
                main_range()
            
    main_range()
    
def writekey():
    try:
        subprocess.run(
            f'setx /M PATH "{os.path.dirname(__file__)};%PATH%"',
            shell=True,
            capture_output=True,
            text=True
        )

        # HKEY_CLASSES_ROOT\*\shell\FileTreeCommand
        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r'*\shell\FileTreeCommand')
        winreg.SetValueEx(key, 'MUIVerb', 0, winreg.REG_SZ, 'FileTree')
        winreg.SetValueEx(key, 'Icon', 0, winreg.REG_SZ, os.path.join(os.path.dirname(__file__), 'res', 'fticon.ico'))
        winreg.SetValueEx(key, 'SubCommands', 0, winreg.REG_SZ, 'FileTreeOpen')

        # HKEY_CLASSES_ROOT\Directory\shell\FileTreeCommand
        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r'Directory\shell\FileTreeCommand')
        winreg.SetValueEx(key, 'MUIVerb', 0, winreg.REG_SZ, 'FileTree')
        winreg.SetValueEx(key, 'Icon', 0, winreg.REG_SZ, os.path.join(os.path.dirname(__file__), 'res', 'fticon.ico'))
        winreg.SetValueEx(key, 'SubCommands', 0, winreg.REG_SZ, 'FileTreeMake')

        # HKEY_CLASSES_ROOT\AllFilesystemObjects\shell\
        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r'AllFilesystemObjects\shell\FileTreeCommand')
        winreg.SetValueEx(key, 'MUIVerb', 0, winreg.REG_SZ, 'FileTree')
        winreg.SetValueEx(key, 'Icon', 0, winreg.REG_SZ, os.path.join(os.path.dirname(__file__), 'res', 'fticon.ico'))
        winreg.SetValueEx(key, 'SubCommands', 0, winreg.REG_SZ, 'FileTreeScattered')

        # HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell\FileTreeOpen
        key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell\FileTreeOpen')
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, 'Open with FileTree')
        winreg.SetValueEx(key, 'Icon', 0, winreg.REG_SZ, os.path.join(os.path.dirname(__file__), 'res', 'fticon.ico'))
        # HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell\FileTreeOpen\command
        key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell\FileTreeOpen\command')
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, 'ftree open "%1"')

        # HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell\FileTreeMake
        key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell\FileTreeMake')
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, 'Create a new fileTree with selected files')
        winreg.SetValueEx(key, 'Icon', 0, winreg.REG_SZ, os.path.join(os.path.dirname(__file__), 'res', 'fticon.ico'))
        # HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell\FileTreeMake\command
        key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell\FileTreeMake\command')
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, 'ftree new "%1\\..\\New FileTree.ft" -d %1')

        # HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell\FileTreeScattered
        key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell\FileTreeScattered')
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, 'Create a new fileTree with selected files')
        winreg.SetValueEx(key, 'Icon', 0, winreg.REG_SZ, os.path.join(os.path.dirname(__file__), 'res', 'fticon.ico'))
        # HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell\FileTreeScattered\command
        key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell\FileTreeScattered\command')
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, 'ftree new "%1\\..\\New FileTree.ft" --scattered %*')

        # HKEY_CLASSES_ROOT\.ft\
        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r'.ft')
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, 'fileTree.object')
        # HKEY_CLASSES_ROOT\.ft\OpenWithProgids
        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r'.ft\OpenWithProgids')
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, 'fileTree.object')

        # HKEY_CLASSES_ROOT\fileTree.object
        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r'fileTree.object')
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, 'FileTree File')
        
        # HKEY_CLASSES_ROOT\fileTree.object\defaultIcon
        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, r'fileTree.object\defaultIcon')
        winreg.SetValueEx(key, '', 0, winreg.REG_SZ, os.path.join(os.path.dirname(__file__), 'res', 'fticon.ico'))
        
        # 安装信息
        key = winreg.CreateKey(
            winreg.HKEY_LOCAL_MACHINE,
            r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\filetree'
        )
        winreg.SetValue(key, '', winreg.REG_SZ, os.path.join(os.path.dirname(__file__), 'ftree.exe'))
        winreg.SetValueEx(key, 'Path', 0, winreg.REG_SZ, os.path.dirname(__file__))
        winreg.CloseKey(key)

        key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\filetree')
        winreg.SetValueEx(key, 'DisplayName', 0, winreg.REG_SZ, 'FileTree')
        winreg.SetValueEx(key, 'Publisher', 0, winreg.REG_SZ, f'xystudio')
        winreg.SetValueEx(key, 'InstallLocation', 0, winreg.REG_SZ, os.path.dirname(__file__))
        winreg.SetValueEx(key, 'UninstallString', 0, winreg.REG_SZ, f'"{os.path.join(os.path.dirname(__file__), 'ftree.exe')}" reg --unregister')
        winreg.SetValueEx(key, 'RepairPath', 0, winreg.REG_SZ, f'"{os.path.join(os.path.dirname(__file__), 'ftree.exe')}" reg --unregister&&"{os.path.join(os.path.dirname(__file__), 'ftree.exe')}" reg --register')
        winreg.SetValueEx(key, 'DisplayVersion', 0, winreg.REG_SZ, __version__)

        winreg.SetValueEx(key, 'EstimatedSize', 0, winreg.REG_DWORD, int(get_dir_size_for_reg(os.path.dirname(__file__))))
        winreg.SetValueEx(key, 'URLInfoAbout', 0, winreg.REG_SZ, 'https://www.github.com/xystudiocode/filetree')
        winreg.SetValueEx(key, 'DisplayIcon', 0, winreg.REG_SZ, fr'{os.path.join(os.path.dirname(__file__))}\res\fticon.ico')
        
        winreg.SetValueEx(key, 'RegOwner', 0, winreg.REG_SZ, 'xystudio')
        winreg.SetValueEx(key, 'RegCompany', 0, winreg.REG_SZ, 'xystudio')
        winreg.SetValueEx(key, 'ProductID', 0, winreg.REG_SZ, '42')
    except Exception as e:
        print(f'{colorama.Fore.RED}Error: {e}')
    finally:
        winreg.CloseKey(key)
        
def unreg():
    '''
    删除配置和初始化完成文件
    '''
    remove_from_path_permanent(os.path.dirname(__file__))
    # 删除注册表
    winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'*\shell\FileTreeCommand')
    winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'Directory\shell\FileTreeCommand')
    winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'AllFilesystemObjects\shell\FileTreeCommand')
    winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'.ft\OpenWithProgids')
    winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'.ft')
    winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'fileTree.object\defaultIcon')
    winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, r'fileTree.object')
    winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\filetree')
    winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\filetree')
    winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell\FileTreeOpen\Command')
    winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell\FileTreeOpen')
    winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell\FileTreeMake\Command')
    winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell\FileTreeMake')
    winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell\FileTreeScattered\Command')
    winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell\FileTreeScattered')
    # 删除初始化完成文件
    os.remove('Initialized')
    
def remove_from_path_permanent(dir_to_remove):
    """
    从Windows PATH中永久删除指定目录。
    system_wide=True 操作系统PATH（需要管理员权限），False 操作用户PATH。
    """
    # 选择注册表路径
    key_path = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
    hive = winreg.HKEY_LOCAL_MACHINE

    with winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
        current_path, reg_type = winreg.QueryValueEx(key, "PATH")
        paths = current_path.split(os.pathsep)
        dir_to_remove = os.path.normpath(dir_to_remove)
        new_paths = [p for p in paths if os.path.normpath(p) != dir_to_remove]
        new_path = os.pathsep.join(new_paths)
        winreg.SetValueEx(key, "PATH", 0, reg_type, new_path)
    
def run_as_admin(code, exe, args=None):
    args_list = []
    in_dev = os.path.exists('in_dev')
    if in_dev:
        args_list.append(code)
    if args:
        args_list.extend(args)
    subprocess.Popen(f'powershell -Command "Start-Process \'{"python" if in_dev else exe}\' {f'-ArgumentList "{','.join(args_list)}"' if args_list else ''} -Verb RunAs"')

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if __name__ == '__main__':
    if not os.path.exists('Initialized'):
        if not is_admin():
            run_as_admin('ftree.py', 'ftree.exe')
            sys.exit(0)
        writekey()
        with open('Initialized', 'w') as f:
            pass
    main()