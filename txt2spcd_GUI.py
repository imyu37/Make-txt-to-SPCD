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

"""

import argparse
import os
import sys
from typing import List, Optional, Tuple

try:
    import FreeSimpleGUI as sg

    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    print(
        "警告: FreeSimpleGUI未安装，图形界面将不可用。请使用 'pip install FreeSimpleGUI' 安装。"
    )

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    # 设置matplotlib支持中文的字体
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
    plt.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print(
        "警告: matplotlib未安装，光谱曲线绘制功能将不可用。请使用 'pip install matplotlib' 安装。"
    )

import datetime


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
            f.write(f"{header}\n")
        for wl, intensity in data:
            # 使用科学计数法或十进制？使用默认字符串表示。
            # 确保足够的精度。
            f.write(f"{wl:.3f} {intensity:.6f}\n")


def main():
    parser = argparse.ArgumentParser(
        description="光谱文本文件转换为 OpticStudio SPCD 格式"
    )
    parser.add_argument("input", help="包含光谱数据的输入文本文件。")
    parser.add_argument(
        "-o",
        "--output",
        help="输出 SPCD 文件路径。若未指定，则从输入文件名派生。",
    )
    parser.add_argument(
        "--unit",
        default="nm",
        choices=["nm", "μm"],
        help="输入文件中波长的单位（默认：nm）。",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=200,
        help="输出中的最大行数（默认：200）。",
    )
    parser.add_argument(
        "--normalize", action="store_true", help="将强度归一化到 [0,1] 范围。"
    )
    parser.add_argument(
        "--no-normalize",
        dest="normalize",
        action="store_false",
        help="不归一化强度（默认）。",
    )
    parser.add_argument(
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


def draw_spectrum_graph(window, window_key, data):
    """绘制光谱曲线"""
    if not MATPLOTLIB_AVAILABLE:
        raise RuntimeError("matplotlib未安装，无法绘制光谱曲线。")

    # 创建matplotlib图形
    fig, ax = plt.subplots(figsize=(6, 4))

    wavelengths, intensities = zip(*data)
    ax.plot(
        wavelengths, intensities, marker="o", linestyle="-", linewidth=1, markersize=4
    )
    ax.set_xlabel("波长 (μm)")
    ax.set_ylabel("强度")
    ax.set_title("光谱曲线")
    ax.grid(True)

    # 在GUI中嵌入图表
    canvas_elem = window[window_key]
    if not hasattr(canvas_elem, "Widget") or canvas_elem.Widget is None:
        raise RuntimeError("GUI画布控件未正确初始化，请重启程序后重试。")

    figure_canvas_agg = FigureCanvasTkAgg(fig, canvas_elem.Widget)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side="top", fill="both", expand=1)

    return figure_canvas_agg


def gui_main():
    """图形用户界面主函数"""
    if not GUI_AVAILABLE:
        print("错误: FreeSimpleGUI未安装，无法启动图形界面。")
        return

    # 使用支持中英文的字体
    global_font = ("Microsoft YaHei", 10)

    sg.theme("LightGreen")
    sg.set_options(font=global_font)

    # 定义布局
    layout = [
        [
            sg.Push(),
            sg.Text(
                "光谱TXT文件转换为OpticStudio SPCD文件",
                font=("Microsoft YaHei", 16, "bold"),
                justification="center",
            ),
            sg.Push(),
        ],
        [
            sg.Text("选择输入文件:", size=(15, 1)),
            sg.Input(key="-INPUT-", size=(55, 1)),
            sg.FileBrowse(file_types=(("文本文件", "*.txt"),), button_text="浏览"),
        ],
        [
            sg.Text("输出文件路径:", size=(15, 1)),
            sg.Input(key="-OUTPUT-", size=(55, 1)),
            sg.FileSaveAs(file_types=(("SPCD文件", "*.spcd"),), button_text="保存"),
        ],
        [
            sg.Text("输入波长单位:", size=(15, 1)),
            sg.Combo(["nm", "μm"], default_value="nm", key="-UNIT-", readonly=True),
        ],
        [
            sg.Text("输出数据行数:", size=(15, 1)),
            sg.Combo(
                ["10", "20", "50", "100", "200"],
                default_value="50",
                key="-ROWS-",
                readonly=True,
            ),
        ],
        [sg.Checkbox("归一化强度", key="-NORMALIZE-", default=False)],
        [
            sg.Text("标题注释:", size=(15, 1)),
            sg.Multiline(
                key="-HEADER-",
                default_text="",
                size=(50, 4),
            ),
        ],
        [sg.Button("转换", size=(10, 1)), sg.Button("退出", size=(10, 1))],
        [
            sg.Frame(
                layout=[[sg.Canvas(key="-GRAPH-", size=(600, 300))]],
                title="光谱曲线",
                visible=False,
                key="-GRAPH_FRAME-",
            )
        ],
        [sg.Text("", key="-STATUS-", size=(50, 1), text_color="red")],
    ]

    window = sg.Window("", layout, finalize=True)

    while True:
        event, values = window.read()

        if event in (sg.WINDOW_CLOSED, "退出"):
            break

        if event == "转换":
            input_file = values["-INPUT-"]
            output_file = values["-OUTPUT-"]

            # 验证输入
            if not input_file:
                window["-STATUS-"].update("错误：请选择输入文件")
                continue

            if not output_file:
                # 如果没有指定输出文件，从输入文件名派生
                base, _ = os.path.splitext(input_file)
                output_file = base + ".spcd"

            try:
                # 读取数据
                data = read_spectral_data(input_file, unit=values["-UNIT-"])
                window["-STATUS-"].update(
                    f"从 '{input_file}' 读取了 {len(data)} 个数据点。"
                )

                # 将波长转换为微米
                data = convert_wavelength(
                    data, from_unit=values["-UNIT-"], to_unit="μm"
                )

                # 如果需要则归一化
                if values["-NORMALIZE-"]:
                    data = normalize_intensity(data)

                # 限制行数
                max_rows = int(values["-ROWS-"])
                if len(data) > max_rows:
                    data = limit_rows(data, max_rows)

                # 更新标题注释，包含原文件名称和日期
                current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                filename = os.path.basename(input_file)
                header_text = f"#由txt2spcd.py转换SPCD文件\n#原文件: {filename}\n#日期: {current_date}"
                window["-HEADER-"].update(header_text)

                # 写入 SPCD 文件
                write_spcd(output_file, data, header=header_text)
                window["-STATUS-"].update(f"已成功转换SPCD 文件！", text_color="green")

                # 绘制光谱曲线
                if MATPLOTLIB_AVAILABLE:
                    try:
                        # 清除之前的图表
                        canvas_elem = window["-GRAPH-"]
                        if (
                            hasattr(canvas_elem, "Widget")
                            and canvas_elem.Widget is not None
                        ):
                            for widget in canvas_elem.Widget.winfo_children():
                                widget.destroy()

                        # 绘制新的光谱曲线
                        draw_spectrum_graph(window, "-GRAPH-", data)

                        # 显示图表框架
                        window["-GRAPH_FRAME-"].update(visible=True)
                    except Exception as graph_err:
                        window["-STATUS-"].update(
                            f"警告：光谱曲线绘制失败（{graph_err}），但文件已成功转换。",
                            text_color="orange",
                        )
                else:
                    window["-STATUS-"].update(
                        "警告：matplotlib未安装，无法显示光谱曲线。",
                        text_color="orange",
                    )

            except Exception as e:
                import traceback

                error_msg = f"错误：{e}\n\n详细信息：\n{traceback.format_exc()}"
                window["-STATUS-"].update(f"错误：{e}", text_color="red")
                sg.popup_error(error_msg, title="转换错误")
                # 如果出错，隐藏图表框架
                try:
                    window["-GRAPH_FRAME-"].update(visible=False)
                except Exception:
                    pass

    window.close()


if __name__ == "__main__":
    # 如果有命令行参数，使用命令行模式
    if len(sys.argv) > 1:
        main()
    else:
        # 否则启动图形界面
        gui_main()
