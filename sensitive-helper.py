#!/bin/python3
# _*_ coding:utf-8 _*_
#
"""
sensitive-helper.py

本地文件敏感信息搜索工具：
- 遍历目标目录或文件，必要时对常见办公与压缩文件进行解析/解压；
- 使用多进程并发扫描，根据规则匹配可能的敏感信息；
- 输出命中结果为 CSV 或 JSON。

主要模块:
- utils.compress: 识别与解压多种压缩格式
- utils.office: 解析 .docx/.xlsx 内容为可扫描文本
- utils.process: 进程池辅助工具
- utils.configurator: 简易配置加载与合并
"""

import base64
import binascii
import csv
import json
import pathlib
import re
import time
from typing import Any, AnyStr, Dict, List, Union

import pandas
import tqdm

from utils import compress, configurator, office, process


def log_run_times(func):
    """装饰器：记录执行耗时超过 1 秒的函数调用。调试专用函数，用于检测哪些步骤消耗大量计算时间，正式使用可不理会。

    记录内容写入 `run_times.log`，包括耗时与首个参数的前 127 字符。
    """

    def wrapper(*args, **kwargs):
        s_time = time.time()
        ret = func(*args, **kwargs)
        total_time = time.time() - s_time
        if total_time <= 1:
            return ret
        with open("run_times.log", "a") as _f:
            _f.write("total time(s): {}, args: {}\n".format(time.time() - s_time, args[0][:127]))
        return ret

    return wrapper


def string_to_reg_flags(flags: str):
    """将形如 "I|M|S" 的正则标志字符串转换为 re 标志位整型。"""
    flags_int = 0
    for flag in flags.split("|"):
        flags_int |= getattr(re, flag)
    return flags_int


def is_filter_base64(result: AnyStr):
    """校验并尝试解码 Base64 片段。

    返回 (is_filter, extend_text)：
    - is_filter 为 True 表示应过滤（无效/不可读/不合规）；
    - extend_text 为解码出的可读文本（当不过滤时）。
    """
    if len(result) % 4 != 0:
        return True, ""
    try:
        # 编码错误的全都丢掉，不丢掉也看不懂
        ret_extend = base64.b64decode(result).decode("utf-8")
        if not re.search(
            r"^[\u0020-\u007F\u2010-\u202f\u3000-\u301f\u4e00-\u9fa5\uff00-\uffef]+$",
            ret_extend,
        ):
            return True, ""
        # \u0020-\u007F：英文可视字符集
        # \u2010-\u202f：中文部分符号集
        # \u3000-\u301f：中文部分符号集
        # \u4e00-\u9fa5：中文常见文字集
        # \u2e80-\u9fff：中文文字及中文异形文字集
        # \uff00-\uffef：中文部分符号集
    except UnicodeDecodeError:
        return True, ""
    except binascii.Error:
        return True, ""
    return False, ret_extend


def is_filter_jwt(result: AnyStr):
    """快速校验 JWT 结构是否符合 Base64 块长度要求（粗筛）。"""
    times = 0
    res_split = result.split(b".")  # type: ignore
    while times < 2:
        if len(res_split[times]) % 4 != 0:
            return True, ""
        times += 1
    return False, ""


def is_filter_result(result: AnyStr, filters: List[AnyStr], flags: int):
    """基于 `re_filters` 做二次过滤，命中即过滤。"""
    if not filters:
        return False, ""
    for fil in filters:
        if re.search(fil, result, flags):  # type: ignore
            return True, ""
    return False, ""


# @log_run_times
def search_content(
    file_object: Union[pathlib.Path, bytes],
    rules: Dict[str, List[str]],
    split: bytes = b"[\x00-\x1f\x7f]+",
    re_filter_content: bytes = rb"",
    is_re_all: bool = False,
    is_silent: bool = False,
) -> List[Dict[str, str]]:
    """扫描单个文件对象的内容并返回命中结果列表。

    参数:
    - file_object: `Path` 或 bytes；Path 时按控制字符切分字节行；
    - rules: 规则字典，值可以是字符串列表或带 flags/re_filters/regexp 的字典；
    - split: 行分割正则（bytes）；
    - re_filter_content: 跳过匹配过滤，碰到指定字符直接跳过匹配；
    - is_re_all: 命中一条是否继续匹配该文件的其它规则。

    返回:
    - 列表项包含 file/group/regexp/match/extend 字段。
    """
    ret = []
    row_contents = [file_object]
    if isinstance(file_object, pathlib.Path):
        row_contents = re.split(split, file_object.read_bytes())

    # 创建文件行扫描进度条
    file_name = str(file_object) if isinstance(file_object, pathlib.Path) else "bytes"
    result_gen = enumerate(row_contents, start=1)
    if is_silent:
        result_gen = tqdm.tqdm(
            enumerate(row_contents, start=1),
            total=len(row_contents),
            desc=f"file: {file_name.split('/')[-1][:16]}..",
            leave=False,  # 不保留进度条，避免与主进度条冲突
            ncols=100,
            bar_format="{desc}:{percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
        )

    for index, row_one in result_gen:
        # 按控制字符进行分割行
        if len(row_one) < 12:
            # 单行内容少于8个字符，丢掉
            continue
        if re_filter_content and re.search(re_filter_content, row_one):
            continue
        for rule_name in rules:
            rule = rules[rule_name]
            flags = 0
            filters = None
            if isinstance(rule, Dict):
                if "flags" in rule:
                    flags = string_to_reg_flags(rule["flags"])  # type: ignore
                if "re_filters" in rule:
                    filters = rule["re_filters"]  # type: ignore
                rule = rule["regexp"]  # type: ignore
            for regexp in rule:
                r_result = re.search(regexp, row_one, flags)  # type: ignore
                if not r_result:
                    continue
                try:
                    result_byte = r_result.group()
                    result_text = result_byte.decode("utf-8")
                except UnicodeDecodeError:
                    continue
                is_filter, extend = is_filter_result(result_byte, filters, flags)  # type: ignore
                if rule_name == "BASE64":
                    is_filter, extend = is_filter_base64(result_byte)
                if rule_name == "JSON WEB TOKEN(JWT)":
                    is_filter, extend = is_filter_jwt(result_byte)
                if is_filter:
                    continue

                ret.append(
                    {
                        "file": f"{file_object.__str__()}:{index}",
                        "group": rule_name,
                        "regexp": regexp.decode("utf-8"),  # type: ignore
                        "match": result_text,
                        "extend": extend,
                    }
                )
                if not is_re_all:
                    # 如果关闭了匹配所有正则组数据且已发现有用数据，则退出循环
                    if hasattr(result_gen, 'close'):
                        result_gen.close()  # type: ignore # 关闭进度条
                    return ret

    if hasattr(result_gen, 'close'):
        result_gen.close()  # type: ignore # 关闭进度条
    return ret


def gen_file_list(src_path: str, exclude_files: List[str]) -> List[pathlib.Path]:
    """生成需扫描的文件列表，并对特定类型进行预处理。

    - 对 `.docx`/`.xlsx`：解析内容到同名 `_resolved.txt`，便于后续扫描；
    - 其它文件：尝试递归解压缩，以发现嵌套内容。
    """
    tar_path = pathlib.Path(src_path)
    ret = []
    if tar_path.is_file():
        ret.append(tar_path)
    else:
        for filepath in tar_path.glob("**/*"):
            is_skip = False
            if filepath.is_dir():
                continue
            filename = filepath.name
            for r_exclude in exclude_files:
                # 文件名正则匹配，在排除名单中则排除文件
                if re.match(r_exclude, filename):
                    is_skip = True
                    break
            if is_skip:
                continue
            if filename.endswith(".docx") and not filename.startswith("~$"):
                office.docx_handler(filepath)
            elif filename.endswith(".xlsx") and not filename.startswith("~$"):
                office.xlsx_handler(filepath)
            else:
                compress.uncompress(filepath, is_error=False, is_recursive=True)
            ret.append(filepath)
    return ret


def run():
    """主流程：构建任务队列、并发扫描、汇总去重并输出结果。"""
    pool = process.ProcessPoolHelper(max_workers=CFG.get("process_number"))
    print("[*] file loading...")
    filelist = gen_file_list(CFG.get("target_path"), CFG.get("exclude_files"))  # type: ignore
    if not filelist:
        print("[!] the file path is empty. please check whether the path is correct.\n")
        return
    filelist = sorted(filelist, key=lambda x: x.stat().st_size, reverse=True)
    ret = []
    result_filter_list = []
    print(f"[*] found {len(filelist)} files.")
    groups = CFG.get("rules")
    for filepath in filelist:
        pool.submit_super(
            search_content,
            filepath,
            groups,
            CFG.get("row_split"),
            CFG.get("re_filter_content"),
            CFG.get("is_re_all"),
            CFG.get("is_silent"),
        )

    print("[*] analyzing...\n")
    result_gen = pool.result_yield()
    if CFG.get("is_silent"):
        result_gen = tqdm.tqdm(
            pool.result_yield(),
            total=len(filelist),
            mininterval=1,
            ncols=100,
            bar_format="{n_fmt}/{total_fmt} [{bar}] {elapsed}<{remaining},{rate_fmt}{postfix}",
        )
    for results in result_gen:
        if not results:
            continue
        for result in results:
            union_data = [result["file"], result["match"]]
            # 相同文件，相同匹配字符串去重
            if union_data in result_filter_list:
                continue
            result_filter_list.append([result["file"], result["match"]])
            ret.append(result)
            if not CFG.get("is_silent"):
                print("[+] group: {}, match: {}, file: {}".format(result["group"], result["match"], result["file"]))
    output_format = CFG.get("output_format")
    filename = "results_{}.csv".format(time.strftime("%H%M%S", time.localtime()))
    if output_format == "json":
        filename = "results.json"
        with open(filename, "w", encoding="utf-8") as _f:
            _f.write(json.dumps(ret))
    else:
        to_csv(ret, filename)

    print("[*] total file number:", len(filelist))
    print("[+] output to:", pathlib.Path(filename).absolute())
    return ret


def to_csv(data: Union[Dict[str, Any], List[Dict[str, Any]]], filename: str = "output.csv"):
    """将结果列表输出为 CSV 文件。"""
    dataframe = pandas.DataFrame(data)
    dataframe.to_csv(filename, quoting=csv.QUOTE_MINIMAL)


# 考虑字典数据、列表数据、函数数据
FUZZY_UNIVERSAL_STRING = r'["\'`]?\s*[=:(\{\[]\s*["\'`][\x20-\x7F]{,128}?[\'"`]'
#
PATH_COMMON_STRING = r"users?|windows?|program files(\(x\d{2,3}\))?|s?bin|etc|usr|boot|dev|home|proc|opt|sys|srv|var"

__DEFAULT_CONFIG = {
    "target_path": {
        "__help": "search for file paths or folder paths for sensitive cache (eg. ~/download/folder).",
    },
    "process_number": {
        "__type": int,
        '__default': 12,
        '__help': "number of program processes (default: 12).",
    },
    "config_path": {
        "__default": "config.yaml",
        '__help': "path to the yaml configuration file (default: configs.yaml).",
    },
    "output_format": {
        "__default": "csv",
        '__help': "output file format, available formats json, csv (default: csv).",
    },
    "exclude_files": {
        "__default": [r"\.DS_Store"],
        "__nargs": "+",
        '__help': "excluded files, using regular matching (eg. \\.DS_Store .*bin .*doc).",
    },
    "is_re_all": {
        "__flags": ['-a', '--is-re-all'],
        "__action": "store_true",
        '__help': "hit a single regular expression per file or match all regular expressions to exit the match loop.",
    },
    "is_silent": {
        "__flags": ['-s', '--is-silent'],
        "__action": "store_true",
        '__help': "silent mode: when turned on, no hit data will be output on the console. use a progress bar instead.",
    },
    "re_filter_content": {
        '__help': "filter regular expression. if a regular expression is hit during the string matching process of each line, skip the matching of that line directly",
    },
    "row_split": "[\x00-\x1f\x7f]+",
    "rules": {
        "AKSK": [
            r"[\s\n\'\"`=:#]LTAI\w{12,20}[\s\n\'\"`=:#]",
            r"[\s\n\'\"`=:#](A3T[A-Z0-9]|ABIA|ACCA|AGPA|AIDA|AIPA|AKIA|ANPA|ANVA|APKA|AROA|ASCA|ASIA)[0-9A-Z]{16}[\s\n\'\"`=:#]",
            r"[\s\n\'\"`=:#]GOOG\w{10,30}[\s\n\'\"`=:#]",
            r"[\s\n\'\"`=:#]AZ[A-Za-z0-9]{34,40}[\s\n\'\"`=:#]",
            r"[\s\n\'\"`=:#]IBM[A-Za-z0-9]{10,40}[\s\n\'\"`=:#]",
            r"[\s\n\'\"`=:#][a-zA-Z0-9]{8}(-[a-zA-Z0-9]{4}){3}-[a-zA-Z0-9]{12}[\s\n\'\"`=:#]",
            r"[\s\n\'\"`=:#]OCID[A-Za-z0-9]{10,40}[\s\n\'\"`=:#]",
            r"[\s\n\'\"`=:#]LTAI[A-Za-z0-9]{12,20}[\s\n\'\"`=:#]",
            r"[\s\n\'\"`=:#]AKID[A-Za-z0-9]{13,20}[\s\n\'\"`=:#]",
            r"[\s\n\'\"`=:#]AK[A-Za-z0-9]{10,40}[\s\n\'\"`=:#]",
            r"[\s\n\'\"`=:#]JDC_[A-Z0-9]{28,32}[\s\n\'\"`=:#]",
            r"[\s\n\'\"`=:#]AKLT[a-zA-Z0-9-_]{0,252}[\s\n\'\"`=:#]",
            r"[\s\n\'\"`=:#]UC[A-Za-z0-9]{10,40}[\s\n\'\"`=:#]",
            r"[\s\n\'\"`=:#]QY[A-Za-z0-9]{10,40}[\s\n\'\"`=:#]",
            r"[\s\n\'\"`=:#]AKLT[a-zA-Z0-9-_]{16,28}[\s\n\'\"`=:#]",
            r"[\s\n\'\"`=:#]LTC[A-Za-z0-9]{10,60}[\s\n\'\"`=:#]",
            r"[\s\n\'\"`=:#]YD[A-Za-z0-9]{10,60}[\s\n\'\"`=:#]",
            r"[\s\n\'\"`=:#]CTC[A-Za-z0-9]{10,60}[\s\n\'\"`=:#]",
            r"[\s\n\'\"`=:#]YYT[A-Za-z0-9]{10,60}[\s\n\'\"`=:#]",
            r"[\s\n\'\"`=:#]YY[A-Za-z0-9]{10,40}[\s\n\'\"`=:#]",
            r"[\s\n\'\"`=:#]CI[A-Za-z0-9]{10,40}[\s\n\'\"`=:#]",
            r"[\s\n\'\"`=:#]gcore[A-Za-z0-9]{10,30}[\s\n\'\"`=:#]",
        ],
        "JSON WEB TOKEN(JWT)": [r"ey[0-9a-zA-Z/+]{4,}={,2}\.[0-9a-zA-Z/+]{6,}={,2}\.[A-Za-z0-9-_]+"],
        "FUZZY MATCH": {
            "flags": "I",
            "regexp": [
                r"(APP|ACCESS|USER|PASS|OSS|ECS|CVM|AWS)[\w]{,8}(NAME|ID|KEY|NUM|ENC|CODE|SEC|WORD)[\w]{,16}%s"
                % FUZZY_UNIVERSAL_STRING,
                # 考虑驼峰写法，下划线写法，MAP键值下面单词后必须接大写字母、下划线、中划线，否侧可能出现如：
                r"(USR|PWD|COOKIE)[_\-A-Z][\w]{,16}%s" % FUZZY_UNIVERSAL_STRING,
                r"(SECRET|SIGN|TOKEN)[\w]{,16}%s" % FUZZY_UNIVERSAL_STRING,
            ],
        },
        "BASE64": [r"[0-9a-zA-Z/+]{8,}={,2}"],
        "URL": {
            "regexp": [r"(ftp|https?):\/\/[%.\w\-]+([\w\-\.,@?^=%&amp;:/~\+#]*[\w\-\@?^=%&amp;/~\+#])?"],
            "re_filters": [
                r"(adobe|amap|android|apache|bing|digicert|eclipse|freecodecamp|github|githubusercontent|gnu|godaddy|google|googlesource|youtube|youtu|jd"
                r"|npmjs|microsoft|openxmlformats|outlook|mozilla|openssl|oracle|qq|spring|sun|umang|w3|wikipedia|xml)\.("
                r"org|com|cn|net|edu|io|be)",
                r"(ali|baidu|cdn|example|ssh|ssl)[\w-]*\.(org|com|cn|net|edu|io)",
            ],
        },
        "EMAIL": [r"[a-zA-Z0-9][-+.\w]{1,127}@([a-zA-Z0-9][-a-zA-Z0-9]{0,63}.){,3}(org|com|cn|net|edu|mail)"],
        "PHONE": [r"(13[0-9]|14[5-9]|15[0-3,5-9]|16[6]|17[0-8]|18[0-9]|19[8,9])\d{8}"],
        "FILE PATH": {
            "flags": "I|X",
            "regexp": [
                r"([a-z]:\\)?([\\/])(users?|windows?|program files(\(x\d{2,3}\))?|s?bin|etc|usr|boot|dev|home|proc|opt"
                r"|sys|srv|var)(\2[.\w!#\(~\[\{][.\w!#&\(\)+=~\[\]\{\}\s]{2,63}){1,16}"
            ],
            "re_filters": [
                # r'[\\/].*sdk.*',
                # r'[\\/](alibaba|aliyun|annotation|apache|chromium|collections|eclipse|facebook|functions|github|google'
                # r'|internal|jetbrains|oppo|reactnative|reflect|sdklib|sequences|taobao|tencent|unionpay|view|vivo'
                # r'|webkit|xiaomi)',
            ],
        },
    },
}

CFG = configurator.CliConfigurator({})

if __name__ == "__main__":
    import argparse

    CFG = configurator.new(
        configurator.CliConfigurator,
        template=__DEFAULT_CONFIG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
    ███████╗███████╗███╗   ██╗███████╗██╗████████╗██╗██╗   ██╗███████╗
    ██╔════╝██╔════╝████╗  ██║██╔════╝██║╚══██╔══╝██║██║   ██║██╔════╝
    ███████╗█████╗  ██╔██╗ ██║███████╗██║   ██║   ██║██║   ██║█████╗
    ╚════██║██╔══╝  ██║╚██╗██║╚════██║██║   ██║   ██║╚██╗ ██╔╝██╔══╝
    ███████║███████╗██║ ╚████║███████║██║   ██║   ██║ ╚████╔╝ ███████╗
    ╚══════╝╚══════╝╚═╝  ╚═══╝╚══════╝╚═╝   ╚═╝   ╚═╝  ╚═══╝  ╚══════╝
    v0.1.6
    by 0xn0ne, https://github.com/0xn0ne/sensitive-helper
""",
    )
    CFG.parse_args('config_path')  # type: ignore
    print("[*] config:", CFG.gen_detail(depth=2, filters=["rules"]))
    rules = CFG.get("rules")
    for rule in rules.values():
        if isinstance(rule, Dict):
            if "re_filters" in rule:
                for index, value in enumerate(rule["re_filters"]):
                    rule["re_filters"][index] = value.encode()
            rule = rule["regexp"]
        for index, value in enumerate(rule):
            rule[index] = value.encode()
    CFG.raw["row_split"] = CFG.raw["row_split"].encode()
    CFG.raw["re_filter_content"] = CFG.raw["re_filter_content"].encode()
    run()
