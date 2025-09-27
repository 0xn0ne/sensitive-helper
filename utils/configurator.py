"""
configurator.py

通用配置加载与访问工具：支持 JSON/YAML/TOML 的加载、合并、保存与友好打印。

组件：
- BaseConfigurator: 基础配置容器，提供 get/set/loads/dumps/gen_pretty 等方法；
- FileConfigurator: 在 BaseConfigurator 基础上增加从文件加载与保存；
- new: 简易单例工厂，按 name 复用配置实例。
"""

import copy
import json
import os
import pathlib
from typing import Any, AnyStr, Dict, Iterable, List, Union

import toml
import yaml

_G_CFG = {}


def maps_merge(*maps: Dict) -> Dict:
    """深合并多个字典，返回新副本。后者覆盖前者。"""
    ret = copy.deepcopy(maps[0])
    for src in maps:
        map_merge(ret, src)
    return ret


def map_merge(dst: Dict, src: Dict):
    """原地深合并 `src` 到 `dst`。嵌套字典递归合并，其它类型直接覆盖。"""
    for key, val in src.items():
        if isinstance(val, Dict):
            if not (key in dst and isinstance(dst[key], Dict)):
                dst[key] = {}
            map_merge(dst[key], val)
            continue
        dst[key] = val


class BaseConfigurator:
    """基础配置容器，封装常用读写与序列化能力。"""

    def __init__(self, template: Dict = None):
        self.raw: Union[Dict, Any] = template or {}

    def get(self, keys: AnyStr, _defult: Any = None, sep: AnyStr = '.') -> Any:
        """按分隔符路径获取值，不存在则返回 `_defult`。"""
        keys = keys.split(sep)
        point = self.raw
        is_found = True
        for key in keys:
            if not isinstance(point, Dict) or key not in point:
                is_found = False
                break
            point = point[key]
        return point if is_found else _defult

    def set(self, keys: AnyStr, value: Any, sep: AnyStr = '.'):
        """按分隔符路径设置值，必要时自动创建中间层级。"""
        keys = keys.split(sep)
        point = self.raw
        for key in keys[:-1]:
            if key not in point:
                point[key] = {}
            point = point[key]
        point[keys[-1]] = value

    def loads(self, content: str, fmt: str = 'json', reload: bool = False):
        """从文本加载配置，支持 json/yaml/toml；`reload=True` 时覆盖原始内容。"""
        if fmt == 'toml':
            object_config = toml.loads(content)
        elif fmt == 'yaml':
            object_config = yaml.safe_load(content)
        else:
            object_config = json.loads(content)
        if not object_config:
            return self.raw

        if reload:
            self.raw = object_config
        else:
            self.raw.update(object_config)
        return self.raw

    def dumps(self, fmt: str = 'json'):
        """将配置序列化为文本，支持 json/yaml/toml。"""
        if fmt == 'toml':
            content = toml.dumps(self.raw)
        elif fmt == 'yaml':
            content = yaml.safe_dump(self.raw)
        else:
            content = json.dumps(self.raw)
        return content

    def exists(self, key: AnyStr):
        """键是否存在。存在返回 True，否则 False。"""
        return self.get(key) is not None

    def gen_pretty(self, objs: Iterable = None, depth: int = 3, filters: List[str] = None):
        """生成简短可读的层次化预览字符串。

        - depth: 控制递归深度；
        - filters: 过滤掉特定路径（如 'rules'）。
        """

        def gen_value(value, depth_next, parent_next):
            if isinstance(value, Dict):
                value = '{{{}}}'.format(recursion_pretty(value, depth_next, parent_next))
            if isinstance(value, List):
                value = '[{}]'.format(recursion_pretty(value, depth_next, parent_next))
            return value

        def recursion_pretty(obj_data, depth_curr, parent: str = ''):
            if depth_curr < 1:
                return '...'

            print_list = []
            if isinstance(obj_data, Dict):
                for key in obj_data:
                    if not obj_data[key]:
                        continue
                    parent_next = '{}.{}'.format(parent, key) if parent else key
                    if filters and parent_next in filters:
                        continue
                    print_list.append('{}: {}'.format(key, gen_value(obj_data[key], depth_curr - 1, parent_next)))
            if isinstance(obj_data, List):
                for index, val in enumerate(obj_data):
                    if not val:
                        continue
                    parent_next = '{}.{}'.format(parent, index) if parent else str(index)
                    if filters and parent_next in filters:
                        continue
                    print_list.append(gen_value(val, depth_curr - 1, parent_next))
            if depth == depth_curr and isinstance(obj_data, Dict):
                return ' | '.join(print_list)
            return ', '.join(print_list)

        objs = objs if objs else self.raw
        return recursion_pretty(objs, depth)

    def __str__(self):
        return '{}, {}>'.format(super().__str__()[:-1], self.raw)


class FileConfigurator(BaseConfigurator):
    """带持久化能力的配置器，从文件加载/保存。"""

    def __init__(self, filepath: str = 'configs.json', template: Dict = None):
        self.filepath = filepath
        self.ext = self.filepath.split('.')[-1]
        super().__init__(template)
        self.load()

    def load(self, strict: bool = False, quiet: bool = False) -> Union[Exception, Any]:
        """从文件加载配置；找不到时返回异常对象或抛出异常（strict）。"""
        if not os.path.isfile(self.filepath):
            notice = 'could not find the file "{}", or is not a file.'.format(self.filepath)
            error = ValueError(notice)
            if strict:
                raise ValueError(notice)
            if not quiet:
                print(notice)
            return error
        with open(self.filepath, encoding='utf-8') as _f:
            self.loads(_f.read(), self.ext)
        return None

    def save(self, exist_ok: bool = True):
        """将当前配置写回文件，必要时创建目录。"""
        dirspath = self.filepath.split(os.sep)[:-1]
        if dirspath:
            os.makedirs(os.sep.join(dirspath), exist_ok=exist_ok)
        with open(self.filepath, 'w', encoding='utf-8') as _f:
            text = self.dumps(self.ext)
            _f.write(text)
        return True


def new(
    name: str = '__DEFAULT__', base_class: Union[Any, FileConfigurator] = FileConfigurator, *args, **kwargs
) -> FileConfigurator:
    """获取（或创建）名为 `name` 的配置单例实例。"""
    if name not in _G_CFG:
        _G_CFG[name] = base_class(*args, **kwargs)
    return _G_CFG[name]


if __name__ == '__main__':
    cfg = new()
    cfg.set('keya', 1024)
    cfg.set('keyb', {})
    cfg.set('keyc', ['a', 'b'])
    cfg.set('keys.b', {'user': 'lee', 'password': 'pass'})
    cfg.set('keys.c.info', {'name': 'lilei', 'age': 20, 'female': True, 'like': ['basketball', 'swim']})
    assert cfg.get('keya', 996) == 1024
    assert cfg.get('keyb', 1024) == {}
    assert cfg.get('keyc.a', 1024) == 1024
    try:
        assert cfg.get('keys.b.c.d') == 'this is error test.'
        raise SystemError('assert failure.')
    except AssertionError as e:
        pass

    # cfg.load_from_url('https://httpbin.org/get')
    # assert cfg.get('url') == 'https://httpbin.org/get'

    cfg.loads(
        '''aaaa:
    user: lee
testa: 1024
testb: {}
testc:
- a
- b''',
        fmt='yaml',
    )

    assert cfg.gen_pretty() == (
        'keya: 1024 | keyc: [a, b] | keys: {b: {user: lee, password: pass}, c: {info: {...}}} '
        '| aaaa: {user: lee} | testa: 1024 | testc: [a, b]'
    )
    assert cfg.gen_pretty(depth=2) == (
        'keya: 1024 | keyc: [a, b] | keys: {b: {...}, c: {...}} | aaaa: {user: lee} | ' 'testa: 1024 | testc: [a, b]'
    )
    assert cfg.gen_pretty(filters=['aaaa', 'keys.c.info']) == (
        'keya: 1024 | keyc: [a, b] | keys: {b: {user: lee, ' 'password: pass}, c: {}} | testa: 1024 | testc: [a, b]'
    )
