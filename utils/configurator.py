#!/bin/python3
# _*_ coding:utf-8 _*_
#
# configurator.py
# 依赖安装：pip install toml yaml
# toml 文档：https://github.com/uiri/toml
# yaml 文档：https://pyyaml.org/wiki/PyYAMLDocumentation

import argparse
import json
import pathlib
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

try:
    import toml
except ImportError:
    toml = None

try:
    import yaml
except ImportError:
    yaml = None

# 全局配置字典，用于存储所有配置实例
_G_CFG = {}


class Mode:
    merge = 10
    update = 20
    replace = 30


class BaseConfigurator:
    def __init__(self, template: Dict[str, Any] = {}):
        """
        初始化配置基类

        Args:
            template (Dict, optional): 默认配置模板。默认为空字典。
        """
        self.raw = template or {}
        # 保存原始模板
        self.template = template

    def loads(self, content: str, fmt: str = "json", mode: int = Mode.update) -> "BaseConfigurator":
        """
        从字符串加载配置

        Args:
            content (str): 配置内容字符串
            fmt (str, optional): 配置格式，支持 'json', 'yaml', 'toml'。默认为 'json'。

        Returns:
            BaseConfigurator: 返回自身实例
        """
        if not content:
            return self
        if fmt == "toml" and toml:
            config_dict = toml.loads(content)
        elif fmt == "yaml" and yaml:
            config_dict = yaml.safe_load(content)
        else:
            config_dict = json.loads(content)
        if mode == Mode.merge:
            self.raw = self._merge_dicts(self.raw, config_dict)
        elif mode == Mode.replace:
            self.raw = config_dict
        else:
            self.raw.update(config_dict)
        return self

    def dumps(self, fmt: str = "json") -> str:
        """
        将配置转换为字符串

        Args:
            fmt (str, optional): 配置格式，支持 'json', 'yaml', 'toml'。默认为 'json'。

        Returns:
            str: 配置内容字符串
        """
        if fmt == "toml" and toml:
            return toml.dumps(self.raw)
        elif fmt == "yaml" and yaml:
            return yaml.safe_dump(self.raw)
        else:
            return json.dumps(self.raw)

    def get(self, keys: str, default: Any = None, sep: str = ".") -> Any:
        """
        获取配置值

        Args:
            keys (str): 多级键字符串
            default (Any, optional): 默认值。默认为 None。
            sep (str, optional): 键分隔符。默认为 '.'。

        Returns:
            Any: 配置值
        """
        keys_list = keys.split(sep)
        value = self.raw
        for key in keys_list:
            if isinstance(value, dict) and key in value:
                value = value[key]
            elif default is None:
                raise KeyError(f'key "{keys}" not found in configuration.')
            else:
                return default
        return value

    def set(self, keys: str, value: Any, sep: str = "."):
        """
        设置配置值

        Args:
            keys (str): 多级键字符串
            value (Any): 配置值
            sep (str, optional): 键分隔符。默认为 '.'。
        """
        keys_list = keys.split(sep)
        d = self.raw
        for key in keys_list[:-1]:
            if key not in d or not isinstance(d[key], dict):
                d[key] = {}
            d = d[key]
        d[keys_list[-1]] = value

    def exists(self, key: str) -> bool:
        """
        判断配置键是否存在

        Args:
            key (str): 配置键

        Returns:
            bool: 是否存在
        """
        return self.get(key) is not None

    def clear(self):
        """
        清空配置
        """
        self.raw = {}

    def gen_detail(self, depth: int = 3, sep: str = "; ", filters: List[str] = []) -> str:
        """
        生成配置简要预览

        Args:
            depth (int, optional): 最大遍历深度，负数的情况下输出所有内容。默认为 3。
            sep (str, optional): 首级键分隔符。默认为 ';'。

        Returns:
            str: 配置简要预览字符串
        """

        def _gen_detail(parent_dict, current_depth: int, parent_key: str = ""):
            if not current_depth:
                return "..."
            if isinstance(parent_dict, dict):
                d_detail = {}
                for k, v in parent_dict.items():
                    next_key = "{}.{}".format(parent_key, k) if parent_key else k
                    if filters and next_key in filters:
                        continue
                    d_detail[k] = _gen_detail(v, current_depth - 1, next_key)

                return d_detail
            return parent_dict

        detail = _gen_detail(self.raw, depth)
        l_detail = []
        for k, v in detail.items():  # type: ignore
            l_detail.append(f"{k}: {v}")

        return sep.join(l_detail)

    def _merge_dicts(self, d1, d2):
        """
        合并两个字典

        Args:
            d1 (dict): 字典1
            d2 (dict): 字典2

        Returns:
            dict: 合并后的字典
        """
        for k, v in d2.items():
            if k in d1 and isinstance(d1[k], dict) and isinstance(v, dict):
                self._merge_dicts(d1[k], v)
            else:
                d1[k] = v
        return d1


class FileConfigurator(BaseConfigurator):
    def __init__(
        self,
        filepath: str = "configs.json",
        template: Dict = {},
        is_auto_make: bool = False,
    ):
        """
        初始化文件配置子类

        Args:
            filepath (str, optional): 配置文件路径。默认为 'configs.json'。
            template (Dict, optional): 默认配置模板。默认为空字典。
        """
        super().__init__(template)
        self.filepath = pathlib.Path(filepath)
        if is_auto_make:
            self.filepath.touch()
        self.load(Mode.merge)

    def load(self, mode: int = Mode.update):
        """
        从文件加载配置
        """
        if self.filepath.is_file():
            self.loads(self.filepath.read_text(encoding='utf-8'), self.filepath.suffix[1:], mode)

    def save(self, fmt: str = "json"):
        """
        将配置保存到文件

        Args:
            fmt (str, optional): 配置格式，支持 'json', 'yaml', 'toml'。默认为 'json'。
        """
        if fmt not in ["json", "yaml", "toml"]:
            raise NotImplementedError(f'the file format "{fmt}" is not supported.')
        self.filepath = self.filepath.with_suffix(f".{fmt}")
        self.filepath.write_text(self.dumps(fmt))

    def delete(self, fmts: Union[str, List[str]] = []):
        """
        删除配置文件

        Args:
            fmt (Union[str, List[str]], optional): 配置格式，支持 'json', 'yaml', 'toml'。默认为空列表。
        """
        if isinstance(fmts, str):
            fmts = [fmts]
        for ext in fmts:
            if ext not in ["json", "yaml", "toml"]:
                raise NotImplementedError(f'the file format "{ext}" is not supported.')
        if not fmts:
            fmts = ["json", "yaml", "toml"]
        for ext in fmts:
            self.filepath.with_suffix(f".{ext}").unlink(missing_ok=True)


class CliConfigurator(FileConfigurator):
    def __init__(
        self,
        template: Dict[str, Union[Dict[str, str], Any]],
        filepath: str = "configs.json",
        prog: Optional[str] = None,
        usage: Optional[str] = None,
        description: Optional[str] = None,
        epilog: Optional[str] = None,
        **kwargs,
    ):
        """
        初始化命令行配置子类

        Args:
            template (Dict, optional): 默认命令行参数配置模板，该模版必须存在，不支持从配置文件中加载。
            filepath (str, optional): 配置文件路径。默认为 'configs.json'。
        """
        # 根据 template 配置，创建命令行
        self.exists_short_key: Set[str] = set()
        self.parser = argparse.ArgumentParser(prog, usage, description, epilog, **kwargs)
        self._add_args_from_template(template)

        # 循环遍历 self.raw，去除命令行参数所需要使用的默认值和描述信息
        del_keys = []
        for key, value in template.items():
            if not isinstance(value, dict):
                continue
            for sub_key in value:
                if sub_key == "__default":
                    template[key] = value["__default"]
                    continue
                if sub_key == '__description':
                    del value["__description"]
                    continue
                if sub_key.startswith('__'):
                    del_keys.append(key)
                    break
        # 因为中途删除key会导致字典变化，引发错误，检索完成后删除一轮
        for del_key in del_keys:
            del template[del_key]
        super().__init__(filepath, template)

    def _parse_add_argument_kwargs(
        self,
        value: Dict[str, Any],
        able_keys: List[str] = [
            'default',
            'type',
            'help',
            'required',
            'action',
            'nargs',
            'const',
            'choices',
            'metavar',
            'dest',
            'deprecated',
        ],
    ) -> Dict[str, Any]:
        """
        able_keys参考可用参数来源https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument

        Args:
            value (Dict[str, Any]): _description_
            able_keys (List[str], optional): _description_. Defaults to [ 'default', 'type', 'help', 'required', 'action', 'nargs', 'const', 'choices', 'metavar', 'dest', 'deprecated', ].

        Returns:
            Dict[str, Any]: _description_
        """
        kwargs = {}
        for key, val in value.items():
            if key.startswith('__') and key[2:] in able_keys:
                kwargs[key[2:]] = val
        return kwargs

    def _gen_flags(self, flag: str, is_initial_letter_mode: bool = False) -> List[str]:
        """创建短命令标志

        Args:
            flag (str): 常规长度的 flag 字符串
            is_initial_letter_mode (bool, optional): 启用首字母模式，将 flag 的每个首字母拼合成短命令标志，默认为：False.

        Returns:
            List[str]: 成功生成短命令标志的情况下就会返回命令标志字符串列表
        """
        r_flag = re.findall(r'[\da-zA-Z]+', flag)
        if not r_flag:
            raise ValueError('the flag does not conform to the specification and should be a character in "0-9a-zA-Z".')
        # 创建常规长度 flag
        flags = ['--' + '-'.join(r_flag)]
        new_short_flag = '-'
        if is_initial_letter_mode:
            # 如果短flag已存在，报错
            new_short_flag += ''.join([i[0] for i in r_flag])
            if new_short_flag in self.exists_short_key:
                raise ValueError(f'this "{new_short_flag}" short flag command already exists.')
            self.exists_short_key.add(new_short_flag)
            flags.reverse()
            return flags
        for iter in r_flag:
            new_short_flag += iter[0]
            # 防冲突，已存在就直接跳过
            if new_short_flag not in self.exists_short_key:
                self.exists_short_key.add(new_short_flag)
                flags.append(new_short_flag)
                break
        flags.reverse()
        return flags

    def _add_args_from_template(self, template: Dict, group: Optional[argparse.ArgumentParser] = None):
        """
        根据模板添加命令行参数

        Args:
            template (Dict): 配置模板，命令行参数解析仅支持解析深度为 2 的字典结构。如
        """
        if not group:
            group = self.parser

        for key, value in template.items():
            if not isinstance(value, dict):
                # 子键值为字典才会解析到命令行中
                continue
            kwargs = self._parse_add_argument_kwargs(value)
            if kwargs:
                if '__flags' in value:
                    flags = value['__flags']
                else:
                    flags = self._gen_flags(key)

                group.add_argument(  # type: ignore
                    *flags,
                    **kwargs,
                    # type=value["__type"],
                    # default=value["__default"],
                    # help=value.get("__help", ""),
                    # required=value.get("__required", False),
                )
                continue
            # 且没有扫描到 add_argument 函数所需的参数的情况下，添加为参数组
            # __description 为可选参数，有则添加描述说明，无则跳过
            group = self.parser.add_argument_group(key, description=value.get("__description", None))  # type: ignore
            self._add_args_from_template(value, group)

    def parse_args(self, config_file_flag: Optional[str] = None):
        """
        解析命令行参数并合并到配置中

        Args:
            config_file_flag (Optional[str]): 配置文件的命令标志. Defaults to None.
        """
        args = vars(self.parser.parse_args())
        if config_file_flag and args[config_file_flag]:
            self.filepath = pathlib.Path(args[config_file_flag])
            # 因为如果需要根据命令标志读取文件并对配置修改，需要在解析过程中重载命令标志对应的文件
            self.load(Mode.update)
        for key, value in args.items():
            if value is None:
                continue
            self.set(key, value)


def new(
    base_class: Callable = FileConfigurator,
    name: str = "__DEFAULT__",
    *args,
    **kwargs,
) -> Union[BaseConfigurator, FileConfigurator, CliConfigurator]:
    """
    创建具有指定名称和基类的配置对象的新实例。

    Args:
        name (str, optional): 配置对象的名称。Defaults to '__DEFAULT__'.
        base_class (Union[BaseConfigurator, FileConfigurator, CLIConfigurator], optional): 配置对象的基类。Defaults to FileConfigurator.
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.

    Returns:
        FileConfigurator: 新创建的配置对象。

    Raises:
        None

    Examples:
        >>> new('my_config_name', FileConfigurator, arg1='value1', arg2='value2')
        <FileConfigurator object at 0x7f9b0a0c6b80>
    """
    if name not in _G_CFG:
        _G_CFG[name] = base_class(*args, **kwargs)
    return _G_CFG[name]


# 示例用法
if __name__ == "__main__":

    cfg = new(is_auto_make=True)
    cfg.set("keyint", 16)
    cfg.set("keystr", "hello")
    cfg.set("keydic", {})
    cfg.set("keyarr", ["a", "b"])
    cfg.set("keys.a", {"id": 10, "role": "admin"})
    cfg.set(
        "keys.a.info",
        {"name": "lilei", "age": 20, "female": True, "like": ["ball", "swim"]},
    )
    cfg.set("keys.b", {"user": "lee", "pass": "lei"})
    assert cfg.get("keyint", 996) == 16
    cfg.set("keyint", 32)
    assert cfg.get("keyint", 996) == 32

    assert cfg.get("keys.b.user") == "lee"
    cfg.set("keys.b.user", "li")
    assert cfg.get("keys.b.user") == "li"

    assert cfg.get("keyc.a", 1024) == 1024
    try:
        assert cfg.get("keys.b.c.d") == "this is error test."
        raise SystemError("assert failure.")
    except KeyError:
        pass

    assert cfg.dumps() == (
        '{"keyint": 32, "keystr": "hello", "keydic": {}, "keyarr": ["a", "b"], "keys": {"a": {"id": 10, "role": "admin", "info": {"name": "lilei", "age": 20, "female": true, "like": ["ball", "swim"]}}, "b": {"user": "li", "pass": "lei"}}}'
    )
    assert cfg.gen_detail() == (
        "keyint: 32; keystr: hello; keydic: {}; keyarr: ['a', 'b']; keys: {'a': {'id': '...', 'role': '...', 'info': '...'}, 'b': {'user': '...', 'pass': '...'}}"
    )
    assert cfg.gen_detail(depth=2) == (
        "keyint: 32; keystr: hello; keydic: {}; keyarr: ['a', 'b']; keys: {'a': '...', 'b': '...'}"
    )
    assert cfg.gen_detail(filters=["notkey", "keyarr", "keys.a.info.name", "keys.b"]) == (
        "keyint: 32; keystr: hello; keydic: {}; keys: {'a': {'id': '...', 'role': '...', 'info': '...'}}"
    )
    # cfg.load_from_url('https://httpbin.org/get')
    # assert cfg.get('url') == 'https://httpbin.org/get'

    cfg.clear()
    cfg.loads(
        """za:
    user: lee
zb: 1024
zc: {}
zd:
- a
- b""",
        fmt="yaml",
    )

    assert cfg.gen_detail() == "za: {'user': 'lee'}; zb: 1024; zc: {}; zd: ['a', 'b']"

    cfg.save()  # type: ignore
    cfg.save("json")  # type: ignore
    cfg.save("yaml")  # type: ignore
    cfg.save("toml")  # type: ignore

    template = {
        "url": {
            "__type": str,
            "__default": "https://localhost/api/v2/user",
            "__help": "后端地址",
        },  # 一级命令行的情况
        # 'database.host': {'__type': str, '__default': 'www.eg.com', '__help': '样例地址'},  # 命令行重复冲突的情况
        "database": {
            "host": {"__type": str, "__default": "localhost", "__help": "数据库地址"},
            "port": {
                "__type": int,
                "__default": 3306,
            },  # 二级命令行没 __help 参数的情况
            "__description": "数据库组配置参数",  # 创建组有 __description 参数的情况
        },
        "logging": {
            "level": {"__type": str, "__default": "INFO", "__help": "日志级别"}
        },  # 创建组没 __description 参数的情况
        "rule": {
            "china": {"beijing": "北京地区规则"},  # 二级没__type、__default参数的情况
        },
    }

    cfg = CliConfigurator(template=template)
    cfg.parse_args()
    print(cfg.raw)
    cfg.save("yaml")
    cfg.parser.print_help()
    print(cfg.gen_detail())
    cfg.delete()
