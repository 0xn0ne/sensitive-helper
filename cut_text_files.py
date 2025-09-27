#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本文件切割工具
支持按行数切割文本文件，可自定义输入文件/文件夹和输出目录
"""

import argparse
import glob
import math
import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Union


class TextFileSplitter:
    """文本文件切割器"""

    def __init__(self, output_lines_number: int = 10000, output_dir: str = "output"):
        """
        初始化切割器

        Args:
            output_lines_number: 每个输出文件的行数
            output_dir: 输出目录
        """
        self.output_lines_number = output_lines_number
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def split_files(self, input_file: Union[str, Path]):
        """
        切割单个文件

        Args:
            input_file: 输入文件路径

        Returns:
            生成的文件路径列表
        """
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"文件或文件夹不存在: {input_path}")

        if input_path.is_file():
            input_path = [input_path]
        else:
            input_path = input_path.iterdir()

        for path in input_path:
            if path.is_dir():
                continue

            print(f"正在处理文件: {path}")

            # 创建输出文件名模板
            base_name = path.stem
            extension = path.suffix

            content = path.read_bytes()
            content_list = re.split(rb'\n', content)
            content_list_len = len(content_list)
            times = math.ceil(content_list_len / self.output_lines_number)
            for index in range(times):
                self._write_chunk(
                    content_list[index * self.output_lines_number : (index + 1) * self.output_lines_number],
                    base_name,
                    extension,
                    index,
                )

            print(f"文件 {input_path} 已切割为 {times} 个文件")

    def _write_chunk(self, lines: List[bytes], base_name: str, extension: str, file_id: int) -> str:
        """
        写入文件块

        Args:
            lines: 要写入的行列表
            base_name: 基础文件名
            extension: 文件扩展名
            file_count: 文件编号

        Returns:
            输出文件路径
        """
        output_filename = f"{base_name}_part_{file_id:06d}{extension}"
        output_path = self.output_dir / output_filename
        output_path.write_bytes(b'\n'.join(lines))

        return str(output_path)

    def get_file_info(self, file_path: Union[str, Path]) -> dict:
        """
        获取文件信息

        Args:
            file_path: 文件路径

        Returns:
            文件信息字典
        """
        path = Path(file_path)
        if not path.exists():
            return {"error": "文件不存在"}

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                line_count = sum(1 for _ in f)

            return {
                "file_name": path.name,
                "file_size": path.stat().st_size,
                "line_count": line_count,
                "estimated_parts": (line_count + self.output_lines_number - 1) // self.output_lines_number,
            }
        except Exception as e:
            return {"error": str(e)}


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="文本文件切割工具 - 按行数切割文本文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python cut_text_files.py -f input_or_folder.txt -l 1000
  python cut_text_files.py -f input.txt --info
        """,
    )

    # 输入参数组
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("-f", "--files", type=str, help="要切割的单个文件路径")

    # 其他参数
    parser.add_argument("-l", "--lines", type=int, default=10000, help="每个输出文件的行数 (默认: 10000)")
    parser.add_argument("-o", "--output", type=str, default="output", help="输出目录 (默认: output)")
    parser.add_argument(
        "-p",
        "--pattern",
        type=str,
        default="*.txt",
        help="文件匹配模式，仅用于目录模式 (默认: *.txt)",
    )
    parser.add_argument("--info", action="store_true", help="显示文件信息而不进行切割")

    args = parser.parse_args()

    # 创建切割器
    splitter = TextFileSplitter(output_lines_number=args.lines, output_dir=args.output)

    if args.files:
        # 处理单个文件
        if args.info:
            # 显示文件信息
            info = splitter.get_file_info(args.files)
            if "error" in info:
                print(f"错误: {info['error']}")
                return 1

            print(f"文件信息:")
            print(f"  文件名: {info['file_name']}")
            print(f"  文件大小: {info['file_size']:,} 字节")
            print(f"  行数: {info['line_count']:,}")
            print(f"  预计切割为: {info['estimated_parts']} 个文件")
            print(f"  每个文件行数: {args.lines}")
        else:
            # 切割文件
            splitter.split_files(args.files)
            print(f"输出目录: {args.output}")


if __name__ == "__main__":
    sys.exit(main())
