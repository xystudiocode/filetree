import sys
import argparse
import json
import os
import base64
from uuid import uuid4
from tempfile import gettempdir
from shutil import rmtree
import colorama

colorama.init(autoreset=True)

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
    parser_new.add_argument('--dir', '-d', default='', type=str, help='Create a new file with directory structure')
    
    # 无参数，显示文档退出
    if len(sys.argv) == 1 or sys.argv[1] in ['-h', '--help']:
        parser.print_help()
        sys.exit(0)
        
    # 如果第一个参数不是子命令 'open' 或 'new'，则自动插入 'open' 作为默认子命令
    if len(sys.argv) == 1:
        sys.argv.insert(1, 'open')

    args = parser.parse_args()

    if args.command == 'open':
        controller(args.file_path)

    elif args.command == 'new':
        path = args.file_path if args.file_path.endswith('.ft') else args.file_path + '.ft'
        # 创建文件（若已存在则清空）
        try:
            with open(path, 'x') as f:
                f.write(json.dumps({}))
        except FileExistsError:
            print(f'{colorama.Fore.RED}Error: file "{path}" already exists.')
            sys.exit(1)

        # 决定是否打开：未指定 --no-open 时均打开（包括默认和 --open）
        print(f'{colorama.Fore.GREEN}File "{path}" created successfully.')
        if args.dir:
            save_file(args.dir, path)
        if not args.no_open:
            controller(path)
                
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
        return
    if not os.path.isdir(dir_path):
        print(f'{colorama.Fore.RED}Error: "{dir_path}" is not a directory.')
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
                    rmtree(ft_path)
                except Exception as e:
                    print(f'{colorama.Fore.RED}Error: {e}')
                    print(f'{colorama.Fore.RED}File saved successfully but temporary directory could not be removed completely.Please close all applications and manually remove the directory "{ft_path}"')
                print(f'{colorama.Fore.GREEN}Exit.')
                exit(0)
            except Exception as e:
                print(f'{colorama.Fore.RED}Error:', e)
                print(f'{colorama.Fore.RED}Failed to save file. Please close all applications try again.')
                main_range()
            
    main_range()

if __name__ == '__main__':
    main()