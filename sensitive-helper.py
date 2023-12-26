#!/bin/python3
# _*_ coding:utf-8 _*_
#
# sensitive-helper.py
# 本地文件敏感信息搜索工具

import base64
import binascii
import json
import pathlib
import re
import time
from typing import List, Dict

import utils.configurator
from utils.process import ProcessPoolHelper


def string_to_reg_flags(flags: str):
    flags_int = 0
    for flag in flags.split('|'):
        flags_int |= getattr(re, flag)
    return flags_int


def search_content(filepath: pathlib.Path, re_groups: Dict[str, List[str]], is_re_all_group: bool = False) -> List[
    Dict[str, str]]:
    ret = []
    byte_content = filepath.read_bytes()
    for row_content in byte_content.split(b'\n'):
        for group_name in re_groups:
            groups = re_groups[group_name]
            flags = 0
            if isinstance(groups, Dict):
                flags = string_to_reg_flags(groups['flags'])
                groups = groups['regexp']
            for r_str in groups:
                r_result = re.search(r_str.encode(), row_content, flags)
                if not r_result:
                    continue
                result = r_result.group()
                if group_name == 'BASE64':
                    try:
                        # 编码错误的全都丢掉，不丢掉也看不懂
                        base64.b64decode(result).decode('utf-8')
                    except UnicodeDecodeError:
                        continue
                    except binascii.Error:
                        continue
                    ret.append({'file': filepath.__str__(), 'group': group_name, 'regexp': r_str,
                                'match': result.decode('utf-8'),
                                'extend': base64.b64decode(result).decode('utf-8')})
                else:
                    try:
                        ret.append(
                            {'file': filepath.__str__(), 'group': group_name, 'regexp': r_str,
                             'match': result.decode('utf-8'), 'extend': ''})
                    except UnicodeDecodeError:
                        continue
                if not is_re_all_group:
                    # 如果关闭了匹配所有正则组数据且已发现有用数据，则退出循环
                    return ret
    return ret


def gen_file_list(src_path: str, exclude_files: List[str]) -> List[pathlib.Path]:
    tar_path = pathlib.Path(src_path)
    ret = []
    if tar_path.is_file():
        ret.append(tar_path)
    else:
        for filepath in tar_path.glob('**/*'):
            is_skip = False
            if filepath.is_dir():
                continue
            for r_exclude in exclude_files:
                # 文件名正则匹配，在排除名单中则排除文件
                if not re.match(r_exclude, filepath.name):
                    continue
                is_skip = True
                break
            if is_skip:
                continue
            ret.append(filepath)
    return ret


def run():
    pool = ProcessPoolHelper(max_workers=cfg.get('process_number'))
    filelist = gen_file_list(cfg.get('target_path'), cfg.get('exclude_files'))
    ret = []
    groups = cfg.get('re_groups')
    for filepath in filelist:
        pool.submit_super(search_content, filepath, groups, cfg.get('is_re_all_group'))

    for results in pool.result_yield():
        if not results:
            continue
        for result in results:
            print('[+]', result)
        ret.extend(results)
    output = cfg.get('output')
    if output:
        with open('results.json', 'w', encoding='utf-8') as _f:
            _f.write(json.dumps(ret))

    print('total file number:', len(filelist))
    return ret


__DEFAULT_CONFIG = {
    'target_path': '',
    'config_path': 'config.yaml',
    'output_path': './',
    'process_number': 20,
    'exclude_files': ['\.DS_Store'],
    're_groups': {
        'ALI AKSK': ['LTAI\w+'],
        'JWT': ['ey[\w/+-]*={,2}(\.[\w/+-]*={,2}){2}'],
        'BASE64': ['[0-9a-zA-Z/+-]{6,}={,2}'],
        'FUZZY MATCH': {
            'flags': 'I|X',
            'regexp': [
                'SECRET.{,20}[=:(]\s*.{,128}', 'APP[-_]?KEY.{,20}[=:(]\s*.{,128}',
                'ACCESS[-_]?KEY.{,20}[=:(]\s*.{,128}',
                'USER.{,20}[=:(]\s*.{,128}', 'PASS.{,20}[=:(]\s*.{,128}', 'USR.{,20}[=:(]\s*.{,128}',
                'PWD.{,20}[=:(]\s*.{,128}']},
        'URL': ['(ftp|https?):\/\/[\w\-_]+(\.[\w\-_]+)+([\w\-\.,@?^=%&amp;:/~\+#]*[\w\-\@?^=%&amp;/~\+#])?']
    },
    'is_re_all_group': True
}
cfg = {}

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description='''
███████╗███████╗███╗   ██╗███████╗██╗████████╗██╗██╗   ██╗███████╗
██╔════╝██╔════╝████╗  ██║██╔════╝██║╚══██╔══╝██║██║   ██║██╔════╝
███████╗█████╗  ██╔██╗ ██║███████╗██║   ██║   ██║██║   ██║█████╗  
╚════██║██╔══╝  ██║╚██╗██║╚════██║██║   ██║   ██║╚██╗ ██╔╝██╔══╝  
███████║███████╗██║ ╚████║███████║██║   ██║   ██║ ╚████╔╝ ███████╗
╚══════╝╚══════╝╚═╝  ╚═══╝╚══════╝╚═╝   ╚═╝   ╚═╝  ╚═══╝  ╚══════╝
    v0.1.1
    by 0xn0ne, https://github.com/0xn0ne/sensitive-helper
''')
    parser.add_argument(
        '-t', '--target-path', required=True,
        help='search for file paths or folder paths for sensitive data(eg. ~/download/folder).')
    parser.add_argument(
        '-p', '--process-number', default=8,
        help='number of program processes(default number 8).')
    parser.add_argument(
        '-c', '--config', default='configs.yaml',
        help='path to the yaml configuration file(default configs.yaml).')
    parser.add_argument(
        '-o', '--output',
        help='path to json output(default without output).')
    parser.add_argument(
        '-e', '--exclude-files', nargs='+',
        help='excluded files, using regular matching(eg. \\.DS_Store .*bin .*doc).')
    parser.add_argument(
        '-a', '--is-re-all-group', action='store_true',
        help='hit a single regular expression per line or match all regular expressions to exit the match loop.')
    args = parser.parse_args()

    print(parser.description)

    s_time = time.time()
    nargs = dict(args.__dict__)
    for key in args.__dict__:
        if nargs[key] is None:
            del nargs[key]

    cfg = utils.configurator.new(filepath=args.config)
    cfg.raw = __DEFAULT_CONFIG
    cfg.raw.update(nargs)
    # cfg.save()

    run()
    print('total time(s):', time.time() - s_time)
