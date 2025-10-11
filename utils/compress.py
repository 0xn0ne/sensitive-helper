#!/bin/python3
# _*_ coding:utf-8 _*_
#
"""
compress.py

压缩文件处理工具：识别并解压常见压缩/打包格式（zip/tar/gz/7z/rar）。

功能要点：
- zip_info: 读取 zip 本地文件头判断是否 zip 以及压缩方式；
- uncompress_*: 各格式的解压实现，输出到指定目录；
- uncompress: 统一入口，自动识别并（可选）递归解压嵌套文件。

依赖：
- 7z: 需要 `py7zr`
- rar: 需要安装系统工具（Windows: WinRAR 并在 PATH 中；Linux: unrar）

参考：`https://segmentfault.com/a/1190000007495352`
"""

import gzip
import pathlib
import tarfile
import zipfile
from typing import Any, Dict, Union

import py7zr
import rarfile


def get_zip_info(file_path: pathlib.Path) -> Dict[str, Any]:
    """读取 zip 文件头信息，返回是否为 zip 及压缩方式。"""
    ret = {'is_zip': False, 'compression': -1}
    with open(file_path, 'rb') as _f:
        byte_info = _f.read(30)
        ret['is_zip'] = byte_info[:4] == b'PK\x03\x04'
        ret['compression'] = int.from_bytes(byte_info[8:10], 'little')
    return ret


def uncompress_zip(
    file_path: Union[pathlib.Path, str], extract_dir: Union[pathlib.Path, str] = '', compression: int = 0
) -> Union[pathlib.Path, Any]:
    """解压 zip 文件到 `extract_dir`。自动使用本地头中的压缩方式。"""
    if isinstance(file_path, str):
        file_path = pathlib.Path(file_path)
    if not extract_dir:
        extract_dir = file_path.parent.joinpath('un_' + file_path.name)
    if isinstance(extract_dir, str):
        extract_dir = pathlib.Path(extract_dir)

    # extract_dir = extract_dir.joinpath(file_path.name)
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(file_path, 'r', compression=compression) as _f:
        for extr_name in _f.namelist():
            _f.extract(extr_name, extract_dir.__str__())
            extract_dir.joinpath(extr_name).rename(extract_dir.joinpath(extr_name.encode('cp437').decode('gbk')))
    return extract_dir


def is_tar(file_path: pathlib.Path):
    """通过魔数判断是否为 tar 文件。"""
    with open(file_path, 'rb') as _f:
        if _f.read(262)[-5:] == b'ustar':
            return True
    return False


def uncompress_tar(
    file_path: Union[pathlib.Path, str], extract_dir: Union[pathlib.Path, str] = ''
) -> Union[pathlib.Path, Any]:
    """解包 tar/tar.* 文件到 `extract_dir`。"""
    if isinstance(file_path, str):
        file_path = pathlib.Path(file_path)
    if not extract_dir:
        extract_dir = file_path.parent.joinpath('un_' + file_path.name)
    if isinstance(extract_dir, str):
        extract_dir = pathlib.Path(extract_dir)

    # extract_dir = extract_dir.joinpath(file_path.name)
    extract_dir.mkdir(parents=True, exist_ok=True)

    # tarfile.ReadError: file could not be opened successfully
    with tarfile.open(file_path) as _f:
        for extr_name in _f.getnames():
            _f.extract(extr_name, extract_dir)
        return extract_dir


def is_gz(file_path: pathlib.Path):
    """通过魔数判断是否为 gzip 文件。"""
    with open(file_path, 'rb') as _f:
        if _f.read(2) == b'\x1f\x8b':
            return True
    return False


def uncompress_gz(
    file_path: Union[pathlib.Path, str], extract_dir: Union[pathlib.Path, str] = ''
) -> Union[pathlib.Path, Any]:
    """解压 gzip 文件；若内部为 tar 则继续调用 tar 解包。"""
    if isinstance(file_path, str):
        file_path = pathlib.Path(file_path)
    if not extract_dir:
        extract_dir = file_path.parent.joinpath('un_' + file_path.name)
    if isinstance(extract_dir, str):
        extract_dir = pathlib.Path(extract_dir)

    # extract_dir = extract_dir.joinpath(file_path.name)
    extract_dir.mkdir(parents=True, exist_ok=True)
    extract_file = extract_dir.joinpath(file_path.name)

    with gzip.open(file_path, 'rb') as gz_f:
        with open(extract_file, 'wb+') as _f:
            _f.write(gz_f.read())
    if is_tar(extract_file):
        return uncompress_tar(extract_file, extract_dir)
    return extract_dir


def is_7z(file_path: pathlib.Path):
    """通过魔数判断是否为 7z 文件。"""
    with open(file_path, 'rb') as _f:
        if _f.read(6) == b'7z\xbc\xaf\x27\x1c':
            return True
    return False


def uncompress_7z(
    file_path: Union[pathlib.Path, str], extract_dir: Union[pathlib.Path, str] = ''
) -> Union[pathlib.Path, Any]:
    """解压 7z 文件到 `extract_dir`。"""
    if isinstance(file_path, str):
        file_path = pathlib.Path(file_path)
    if not extract_dir:
        extract_dir = file_path.parent.joinpath('un_' + file_path.name)
    if isinstance(extract_dir, str):
        extract_dir = pathlib.Path(extract_dir)

    extract_dir.mkdir(parents=True, exist_ok=True)

    with py7zr.SevenZipFile(file_path, mode='r') as _f:
        _f.extractall(extract_dir)
    return extract_dir


def is_rar(file_path: pathlib.Path):
    """通过魔数判断是否为 RAR 文件。"""
    with open(file_path, 'rb') as _f:
        if _f.read(4) == b'\x52\x61\x72\x21':
            return True
    return False


def uncompress_rar(
    file_path: Union[pathlib.Path, str], extract_dir: Union[pathlib.Path, str] = ''
) -> Union[pathlib.Path, Any]:
    """
    解压 rar 文件在 windows 上需要安装 winrar，并配置好环境变量；linux 上需要安装 unrar，并配置好环境变量
    否则会报出 rarfile.RarCannotExec: Cannot find working tool 错误
    """
    if isinstance(file_path, str):
        file_path = pathlib.Path(file_path)
    if not extract_dir:
        extract_dir = file_path.parent.joinpath('un_' + file_path.name)
    if isinstance(extract_dir, str):
        extract_dir = pathlib.Path(extract_dir)

    extract_dir.mkdir(parents=True, exist_ok=True)

    with rarfile.RarFile(file_path) as _f:
        # _f.extractall(extract_dir)
        for extr_name in _f.namelist():
            _f.extract(extr_name, extract_dir)
    return extract_dir


def is_bz(file_path: pathlib.Path):
    """通过魔数判断是否为 bzip2 文件。"""
    with open(file_path, 'rb') as _f:
        if _f.read(2) == b'\x42\x5a\x68':
            return True
    return False


def uncompress(
    file_path: Union[pathlib.Path, str],
    extract_dir: Union[pathlib.Path, str] = '',
    is_error: bool = True,
    is_recursive: bool = False,
    max_level=64,
) -> Union[pathlib.Path, Any]:
    """统一解压入口，自动识别并可递归解压。

    支持格式：gz/tar/7z/zip/rar。
    当 `is_recursive=True` 时，将在 `max_level` 限制内递归处理嵌套压缩。
    """
    if not isinstance(file_path, pathlib.Path):
        file_path = pathlib.Path(file_path)
    if not extract_dir:
        extract_dir = file_path.parent.joinpath('un_' + file_path.name)
    if not isinstance(extract_dir, pathlib.Path):
        extract_dir = pathlib.Path(extract_dir)

    if not file_path.is_file():
        if is_error:
            raise ValueError('{} is not a file.'.format(file_path))
        return

    ret = None
    file_info = get_zip_info(file_path)
    if file_info['is_zip']:
        ret = uncompress_zip(file_path, extract_dir, file_info['compression'])
    elif is_gz(file_path):
        ret = uncompress_gz(file_path, extract_dir)
    elif is_tar(file_path):
        ret = uncompress_tar(file_path, extract_dir)
    elif is_7z(file_path):
        ret = uncompress_7z(file_path, extract_dir)
    elif is_rar(file_path):
        ret = uncompress_rar(file_path, extract_dir)
    elif is_error:
        raise ValueError('{} is not a compressed file.'.format(file_path))

    if is_recursive and ret and max_level > 0:
        for it in ret.glob('**/*'):
            uncompress(it, ret.joinpath('un_' + it.name), is_error, is_recursive, max_level - 1)
    return ret


if __name__ == '__main__':
    # print(zip_info(pathlib.Path('cache/utils.zip')))
    # print(uncompress_zip('cache/utils.zip'))
    # print(is_tar(pathlib.Path('cache/utils.tar')))
    # print(uncompress_tar('cache/utils.tar'))
    # print(is_gz(pathlib.Path('cache/utils.tgz')))
    # print(uncompress_gz('cache/utils.tgz'))
    # print(is_7z(pathlib.Path('cache/utils.7z')))
    # print(uncompress_7z('cache/utils.7z'))
    # print(is_rar(pathlib.Path('cache/utils.rar')))
    # print(uncompress_rar('cache/utils.rar'))
    print(uncompress('cache/utils.xlsx', is_error=False, is_recursive=True))
    pass
