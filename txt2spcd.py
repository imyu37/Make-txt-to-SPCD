#!/usr/bin/env python3
"""
txt2spcd.py - 将包含光谱数据的文本文件转换为 OpticStudio SPCD 格式。

SPCD 格式要求：
- 波长以微米（micrometers）为单位
- 数据行数最多200行
- 两列：波长（浮点数）、相对强度（浮点数）
- 可选强度归一化（0-1）

输入文本文件格式：假设为两列，以空格或制表符分隔。
波长单位：默认为纳米（nm），将转换为微米。
也可以通过 --unit 选项处理其他单位。

使用方法：
    python txt2spcd.py input.txt --output output.spcd
    python txt2spcd.py input.txt --output output.spcd --max-rows 200 --normalize
"""

import argparse
import math
import os
import sys
from typing import List, Optional, Tuple


def read_spectral_data(filepath: str, unit: str = "nm") -> List[Tuple[float, float]]:
    """
    从文本文件读取光谱数据。

    参数
    ----------
    filepath : str
        输入文本文件路径。
    unit : str
        文件中波长的单位。'nm'（纳米）或 'μm'（微米）。

    返回
    -------
    data : list of tuples (wavelength, intensity)
        从文件读取的原始数据。
    """
    data = []
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        # 跳过空行以及以 # 开头的注释行
        if not line or line.startswith("#"):
            continue
        # 按空白字符（空格或制表符）分割
        parts = line.split()
        if len(parts) < 2:
            print(
                f"警告：第 {line_num} 行没有至少两列：'{line}'",
                file=sys.stderr,
            )
            continue
        try:
            wl = float(parts[0])
            intensity = float(parts[1])
        except ValueError:
            print(
                f"警告：第 {line_num} 行包含非数值数据：'{line}'",
                file=sys.stderr,
            )
            continue
        data.append((wl, intensity))

    if not data:
        raise ValueError("文件中未找到有效数据行。")

    return data


def convert_wavelength(
    data: List[Tuple[float, float]], from_unit: str, to_unit: str = "μm"
) -> List[Tuple[float, float]]:
    """
    转换波长单位。

    支持的单位：'nm'（纳米），'μm'（微米）。
    转换关系：1 μm = 1000 nm。
    """
    if from_unit == to_unit:
        return data

    factor = 1.0
    if from_unit == "nm" and to_unit == "μm":
        factor = 0.001
    elif from_unit == "μm" and to_unit == "nm":
        factor = 1000.0
    else:
        raise ValueError(f"不支持的单位转换：{from_unit} -> {to_unit}")

    return [(wl * factor, intensity) for wl, intensity in data]


def normalize_intensity(data: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """将强度归一化到 [0, 1] 范围。"""
    if not data:
        return data
    max_intensity = max(intensity for _, intensity in data)
    if max_intensity <= 0:
        # 全部为零或负数？保持原样
        return data
    return [(wl, intensity / max_intensity) for wl, intensity in data]


def limit_rows(
    data: List[Tuple[float, float]], max_rows: int
) -> List[Tuple[float, float]]:
    """通过等间距采样将行数限制为 max_rows。"""
    n = len(data)
    if n <= max_rows:
        return data

    # 等间距索引
    indices = [int(i * (n - 1) / (max_rows - 1)) for i in range(max_rows)]
    return [data[i] for i in indices]


def write_spcd(
    filepath: str, data: List[Tuple[float, float]], header: Optional[str] = None
):
    """
    将数据写入 SPCD 文件。

    SPCD 格式：简单的两列空格分隔值。
    可选择包含以 '#' 开头的标题行。
    """
    with open(filepath, "w", encoding="utf-8") as f:
        if header:
            f.write(f"# {header}\n")
        for wl, intensity in data:
            # 使用科学计数法或十进制？使用默认字符串表示。
            # 确保足够的精度。
            f.write(f"{wl:.6f} {intensity:.6f}\n")


def main():
    parser = argparse.ArgμmentParser(
        description="将光谱文本文件转换为 OpticStudio SPCD 格式。"
    )
    parser.add_argμment("input", help="包含光谱数据的输入文本文件。")
    parser.add_argμment(
        "-o",
        "--output",
        help="输出 SPCD 文件路径。若未指定，则从输入文件名派生。",
    )
    parser.add_argμment(
        "--unit",
        default="nm",
        choices=["nm", "μm"],
        help="输入文件中波长的单位（默认：nm）。",
    )
    parser.add_argμment(
        "--max-rows",
        type=int,
        default=200,
        help="输出中的最大行数（默认：200）。",
    )
    parser.add_argμment(
        "--normalize", action="store_true", help="将强度归一化到 [0,1] 范围。"
    )
    parser.add_argμment(
        "--no-normalize",
        dest="normalize",
        action="store_false",
        help="不归一化强度（默认）。",
    )
    parser.add_argμment(
        "--header",
        type=str,
        default="SPCD data converted by txt2spcd.py",
        help="输出文件中包含的标题注释。",
    )
    parser.set_defaults(normalize=False)

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"错误：输入文件 '{args.input}' 不存在。", file=sys.stderr)
        sys.exit(1)

    # 确定输出路径
    if args.output is None:
        base, _ = os.path.splitext(args.input)
        output = base + ".spcd"
    else:
        output = args.output

    try:
        # 读取数据
        data = read_spectral_data(args.input, unit=args.unit)
        print(f"从 '{args.input}' 读取了 {len(data)} 个数据点。")

        # 将波长转换为微米（OpticStudio 要求微米）
        data = convert_wavelength(data, from_unit=args.unit, to_unit="μm")
        print(f"波长已从 {args.unit} 转换为 μm。")

        # 如果需要则归一化
        if args.normalize:
            data = normalize_intensity(data)
            print("强度已归一化到 [0,1] 范围。")

        # 限制行数
        if len(data) > args.max_rows:
            data = limit_rows(data, args.max_rows)
            print(f"已下采样至 {len(data)} 行（最大行数 = {args.max_rows}）。")
        else:
            print(f"数据行数在限制内（{len(data)} <= {args.max_rows}）。")

        # 写入 SPCD 文件
        write_spcd(output, data, header=args.header)
        print(f"SPCD 文件已写入 '{output}'。")

    except Exception as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
