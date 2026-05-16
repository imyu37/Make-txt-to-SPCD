# Make-txt-to-SPCD

光谱 TXT → OpticStudio SPCD 格式转换工具，提供 CLI 与 GUI 双模式。

## 项目结构

- `txt2spcd_GUI.py` — 唯一源文件，同时包含 CLI 和 GUI 两套入口（有命令行参数走 CLI，无参数走 GUI）

## 依赖

- Python ≥ 3.8
- FreeSimpleGUI — GUI 框架（无此库则 GUI 不可用但 CLI 仍可运行）
- matplotlib — 光谱曲线预览（无此库则 GUI 无图表但转换功能正常）

```bash
pip install FreeSimpleGUI matplotlib
```

## 运行

```bash
python txt2spcd_GUI.py              # GUI 模式
python txt2spcd_GUI.py input.txt    # CLI 模式
```

## SPCD 格式约束

- 波长单位必须为微米（μm），代码自动从 nm 转换
- 最多 200 行，超出则等间距下采样
- 输出格式：`波长(3位小数) 强度(6位小数)`，空格分隔
- 注释行以 `#` 开头

## 深入文档

- [README.md](readme.md) — 使用说明、输入输出格式示例
