#!/bin/python3
# _*_ coding:utf-8 _*_
#
# compress.py
# 压缩文件处理工具
# 参考链接：https://segmentfault.com/a/1190000007495352
# pip install py7zr

import gzip
import pathlib
import tarfile
import zipfile
from typing import Any, Dict, Union

import py7zr
import rarfile


def zip_info(file_path: pathlib.Path) -> Dict[str, Any]:
    ret = {'is_magic': False, 'compression': -1}
    with open(file_path, 'rb') as _f:
        byte_info = _f.read(30)
        ret['is_magic'] = byte_info[:4] == b'PK\x03\x04'
        ret['compression'] = int.from_bytes(byte_info[8:10], 'little')
    return ret


def uncompress_zip(
    file_path: Union[pathlib.Path, str], extract_dir: Union[pathlib.Path, str] = None, is_error: bool = True
) -> Union[pathlib.Path, Any]:
    if isinstance(file_path, str):
        file_path = pathlib.Path(file_path)
    if not extract_dir:
        extract_dir = file_path.parent.joinpath('un_' + file_path.name)
    if isinstance(extract_dir, str):
        extract_dir = pathlib.Path(extract_dir)

    file_info = zip_info(file_path)
    # extract_dir = extract_dir.joinpath(file_path.name)
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(file_path, 'r', compression=file_info['compression']) as _f:
        for extr_name in _f.namelist():
            _f.extract(extr_name, extract_dir.__str__())
            extract_dir.joinpath(extr_name).rename(extract_dir.joinpath(extr_name.encode('cp437').decode('gbk')))
    return extract_dir


def is_tar(file_path: pathlib.Path):
    with open(file_path, 'rb') as _f:
        if _f.read(262)[-5:] == b'ustar':
            return True
    return False


def uncompress_tar(
    file_path: Union[pathlib.Path, str], extract_dir: Union[pathlib.Path, str] = None
) -> Union[pathlib.Path, Any]:
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
    with open(file_path, 'rb') as _f:
        if _f.read(2) == b'\x1F\x8B':
            return True
    return False


def uncompress_gz(
    file_path: Union[pathlib.Path, str], extract_dir: Union[pathlib.Path, str] = None
) -> Union[pathlib.Path, Any]:
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
    with open(file_path, 'rb') as _f:
        if _f.read(6) == b'7z\xBC\xAF\x27\x1C':
            return True
    return False


def uncompress_7z(
    file_path: Union[pathlib.Path, str], extract_dir: Union[pathlib.Path, str] = None
) -> Union[pathlib.Path, Any]:
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
    with open(file_path, 'rb') as _f:
        if _f.read(4) == b'\x52\x61\x72\x21':
            return True
    return False


def uncompress_rar(
    file_path: Union[pathlib.Path, str], extract_dir: Union[pathlib.Path, str] = None
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
    with open(file_path, 'rb') as _f:
        if _f.read(2) == b'\x42\x5A\x68':
            return True
    return False


def uncompress(
    file_path: Union[pathlib.Path, str],
    extract_dir: Union[pathlib.Path, str] = None,
    is_error: bool = True,
    is_recursive: bool = False,
    max_level=64,
) -> Union[pathlib.Path, Any]:
    """
    支持 gz/tar/7z/zip/rar
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
    file_info = zip_info(file_path)
    if file_info['is_magic']:
        ret = uncompress_zip(file_path, extract_dir)
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
        for file_path in ret.glob('**/*'):
            uncompress(file_path, ret.joinpath('un_' + file_path.name), is_error, is_recursive, max_level - 1)
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
