#!/bin/python3
# _*_ coding:utf-8 _*_
#
# sensitive-helper.py
# 本地文件敏感信息搜索工具

import base64
import binascii
import csv
import json
import pathlib
import re
import time
from typing import List, Dict, Any, Union, AnyStr

import pandas
import tqdm

import utils.configurator
from utils.process import ProcessPoolHelper


def log_run_times(func):
    def wrapper(*args, **kwargs):
        s_time = time.time()
        ret = func(*args, **kwargs)
        total_time = time.time() - s_time
        if total_time <= 1:
            return ret
        with open('run_times.log', 'a') as _f:
            _f.write('total time(s): {}, args: {}\n'.format(time.time() - s_time, args[0][:127]))
        return ret

    return wrapper


def string_to_reg_flags(flags: str):
    flags_int = 0
    for flag in flags.split('|'):
        flags_int |= getattr(re, flag)
    return flags_int


def is_filter_base64(result: AnyStr):
    if len(result) % 4 != 0:
        return True, ''
    try:
        # 编码错误的全都丢掉，不丢掉也看不懂
        ret_extend = base64.b64decode(result).decode('utf-8')
        if not re.search(r'^[\u0020-\u007F\u2010-\u202f\u3000-\u301f\u4e00-\u9fa5\uff00-\uffef]+$', ret_extend):
            return True, ''
        # \u0020-\u007F：英文可视字符集
        # \u2010-\u202f：中文部分符号集
        # \u3000-\u301f：中文部分符号集
        # \u4e00-\u9fa5：中文常见文字集
        # \u2e80-\u9fff：中文文字及中文异形文字集
        # \uff00-\uffef：中文部分符号集
    except UnicodeDecodeError:
        return True, ''
    except binascii.Error:
        return True, ''
    return False, ret_extend


def is_filter_jwt(result: AnyStr):
    times = 0
    res_split = result.split(b'.')
    while times < 2:
        if len(res_split[times]) % 4 != 0:
            return True, ''
        times += 1
    return False, ''


def is_filter_result(result: AnyStr, filters: List[AnyStr], flags: int):
    if not filters:
        return False, ''
    for fil in filters:
        if re.search(fil, result, flags):
            return True, ''
    return False, ''


# @log_run_times
def search_content(file_object: Union[pathlib.Path, bytes], rules: Dict[str, List[str]],
                   split: bytes = b'[\x00-\x1F\x7F]+',
                   is_re_all: bool = False) -> List[
    Dict[str, str]]:
    ret = []
    row_contents = [file_object]
    if isinstance(file_object, pathlib.Path):
        row_contents = re.split(split, file_object.read_bytes())
    for row_one in row_contents:
        # 按控制字符进行分割行
        if len(row_one) < 12:
            # 单行内容少于8个字符，丢掉
            continue
        for rule_name in rules:
            rule = rules[rule_name]
            flags = 0
            filters = None
            if isinstance(rule, Dict):
                if 'flags' in rule:
                    flags = string_to_reg_flags(rule['flags'])
                if 're_filters' in rule:
                    filters = rule['re_filters']
                rule = rule['regexp']
            for regexp in rule:
                r_result = re.search(regexp, row_one, flags)
                if not r_result:
                    continue
                try:
                    result_byte = r_result.group()
                    result_text = result_byte.decode('utf-8')
                except UnicodeDecodeError:
                    continue
                is_filter, extend = is_filter_result(result_byte, filters, flags)
                if rule_name == 'BASE64':
                    is_filter, extend = is_filter_base64(result_byte)
                if rule_name == 'JSON WEB TOKEN(JWT)':
                    is_filter, extend = is_filter_jwt(result_byte)
                if is_filter:
                    continue

                ret.append({
                    'file': file_object.__str__(), 'group': rule_name, 'regexp': regexp.decode('utf-8'),
                    'match': result_text,
                    'extend': extend})
                if not is_re_all:
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
    if not filelist:
        print('[!] the file path is empty. please check whether the path is correct.\n')
        return
    filelist = sorted(filelist, key=lambda x: x.stat().st_size, reverse=True)
    ret = []
    result_filter_list = []
    groups = cfg.get('rules')
    total = 0
    print('[*] file loading...')
    for filepath in filelist:
        pool.submit_super(search_content, filepath, groups, cfg.get('row_split'), cfg.get('is_re_all'))

    print('[*] analyzing...\n')
    result_gen = pool.result_yield()
    if cfg.get('is_silent'):
        result_gen = tqdm.tqdm(
            pool.result_yield(), total=len(filelist), mininterval=1, ncols=80,
            bar_format='{n_fmt}/{total_fmt} [{bar}] {elapsed}<{remaining},{rate_fmt}{postfix}')
    for results in result_gen:
        if not results:
            continue
        for result in results:
            union_data = [result['file'], result['match']]
            # 相同文件，相同匹配字符串去重
            if union_data in result_filter_list:
                continue
            result_filter_list.append([result['file'], result['match']])
            ret.append(result)
            if not cfg.get('is_silent'):
                print('[+] group: {}, match: {}, file: {}'.format(result['group'], result['match'], result['file']))
    output_format = cfg.get('output_format')
    filename = 'results.csv'
    if output_format == 'json':
        filename = 'results.json'
        with open(filename, 'w', encoding='utf-8') as _f:
            _f.write(json.dumps(ret))
    else:
        to_csv(ret, filename)

    print('[*] total file number:', len(filelist))
    print('[+] output to:', pathlib.Path(filename).absolute())
    return ret


def to_csv(data: Union[Dict[str, Any], List[Dict[str, Any]]], filename: str = 'output.csv'):
    """
    输入数据应为：cache = {'a': [1, 0, 9], 'b': [3, 7, 6]}
    """
    dataframe = pandas.DataFrame(data)
    dataframe.to_csv(filename, quoting=csv.QUOTE_MINIMAL)


# 考虑字典数据、列表数据、函数数据
FUZZY_UNIVERSAL_STRING = r'["\'`]?\s*[=:(\{\[]\s*["\'`][\x20-\x7F]{,128}?[\'"`]'
#
PATH_COMMON_STRING = r'users?|windows?|program files(\(x\d{2,3}\))?|s?bin|etc|usr|boot|dev|home|proc|opt|sys|srv|var'

__DEFAULT_CONFIG = {
    'target_path': '',
    'config_path': 'config.yaml',
    'output_format': 'csv',
    'process_number': 5,
    'exclude_files': [r'\.DS_Store'],
    'row_split': '[\x00-\x1F\x7F]+',
    'rules': {
        'AKSK': [r'LTAI\w+'],
        'JSON WEB TOKEN(JWT)': [r'ey[0-9a-zA-Z/+]{4,}={,2}\.[0-9a-zA-Z/+]{6,}={,2}\.[A-Za-z0-9-_]+'],
        'FUZZY MATCH': {
            'flags': 'I',
            'regexp': [
                r'(APP|ACCESS|USER|PASS|OSS|ECS|CVM|AWS)[\w]{,8}(ID|KEY|NUM|ENC|CODE|SEC|WORD)[\w]{,16}%s' % FUZZY_UNIVERSAL_STRING,
                # 考虑驼峰写法，下划线写法，MAP键值下面单词后必须接大写字母、下划线、中划线，否侧可能出现如：
                r'(USR|PWD|COOKIE)[_\-A-Z][\w]{,16}%s' % FUZZY_UNIVERSAL_STRING,
                r'(SECRET|SIGN|TOKEN)[\w]{,16}%s' % FUZZY_UNIVERSAL_STRING,
            ]},
        'BASE64': [r'[0-9a-zA-Z/+]{8,}={,2}'],
        'URL': {
            'regexp': [r'(ftp|https?):\/\/[%.\w\-]+([\w\-\.,@?^=%&amp;:/~\+#]*[\w\-\@?^=%&amp;/~\+#])?'],
            're_filters': [
                r'(adobe|amap|android|apache|bing|digicert|eclipse|github|gnu|godaddy|google|googlesource|jd'
                r'|microsoft|openxmlformats|outlook|mozilla|openssl|oracle|qq|spring|sun|umang|w3|xml)\.('
                r'org|com|cn|net|edu|io)',
                r'(ali|baidu|cdn|example|ssh|ssl)[\w-]*\.(org|com|cn|net|edu|io)',
            ]},
        'EMAIL': [r'[a-zA-Z0-9][-+.\w]{1,127}@([a-zA-Z0-9][-a-zA-Z0-9]{0,63}.){,3}(org|com|cn|net|edu|mail)'],
        'PHONE': [r'(13[0-9]|14[5-9]|15[0-3,5-9]|16[6]|17[0-8]|18[0-9]|19[8,9])\d{8}'],
        'FILE PATH': {
            'flags': 'I|X',
            'regexp': [
                r'([a-z]:\\)?([\\/])(users?|windows?|program files(\(x\d{2,3}\))?|s?bin|etc|usr|boot|dev|home|proc|opt'
                r'|sys|srv|var)(\2[.\w!#\(~\[\{][.\w!#&\(\)+=~\[\]\{\}\s]{2,63}){1,16}'],
            're_filters': [
                # r'[\\/].*sdk.*',
                # r'[\\/](alibaba|aliyun|annotation|apache|chromium|collections|eclipse|facebook|functions|github|google'
                # r'|internal|jetbrains|oppo|reactnative|reflect|sdklib|sequences|taobao|tencent|unionpay|view|vivo'
                # r'|webkit|xiaomi)',
            ]},
    },
    'is_re_all': False,
    'is_silent': False
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
    v0.1.3
    by 0xn0ne, https://github.com/0xn0ne/sensitive-helper
''')
    parser.add_argument(
        '-t', '--target-path', required=True,
        help='search for file paths or folder paths for sensitive cache (eg. ~/download/folder).')
    parser.add_argument(
        '-p', '--process-number', default=5, type=int,
        help='number of program processes (default: 5).')
    parser.add_argument(
        '-c', '--config-path', default='configs.yaml',
        help='path to the yaml configuration file (default: configs.yaml).')
    parser.add_argument(
        '-o', '--output-format',
        help='output file format, available formats json, csv (default: csv).')
    parser.add_argument(
        '-e', '--exclude-files', nargs='+',
        help='excluded files, using regular matching (eg. \\.DS_Store .*bin .*doc).')
    parser.add_argument(
        '-a', '--is-re-all', action='store_true',
        help='hit a single regular expression per file or match all regular expressions to exit the match loop.')
    parser.add_argument(
        '-s', '--is-silent', action='store_true',
        help='silent mode: when turned on, no hit data will be output on the console. use a progress bar instead.')
    args = parser.parse_args()

    print(parser.description)

    nargs = dict(args.__dict__)
    for key in args.__dict__:
        if nargs[key] is None:
            del nargs[key]

    cfg = utils.configurator.new(filepath=args.config_path, template=__DEFAULT_CONFIG)
    # cfg.save()
    cfg.raw.update(nargs)
    print('[*] config:', cfg.gen_pretty(depth=2, filters=['rules']))

    rules = cfg.get('rules')
    for rule in rules.values():
        if isinstance(rule, Dict):
            if 're_filters' in rule:
                for index, value in enumerate(rule['re_filters']):
                    rule['re_filters'][index] = value.encode()
            rule = rule['regexp']
        for index, value in enumerate(rule):
            rule[index] = value.encode()
    cfg.raw['row_split'] = cfg.raw['row_split'].encode()

    run()

    # TODO: 添加docx、xlsx、pptx处理逻辑
    # TODO: 添加zip、rar、gz等压缩格式处理逻辑
