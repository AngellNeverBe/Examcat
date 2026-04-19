#!/usr/bin/env python3
"""
处理CSV文件：删除难度列，在题型列后插入次要题型列（默认值：无）。

用法：
    python3 migrate.py input.csv output.csv
    python3 migrate.py input.csv > output.csv   # 输出到标准输出
    python3 migrate.py < input.csv > output.csv # 从标准输入读取
"""

import csv
import sys
import argparse

def process_csv(input_file, output_file, delimiter=','):
    """
    处理CSV文件，删除难度列，在题型列后插入次要题型列。

    :param input_file: 输入文件对象（支持迭代），例如sys.stdin或open()返回的文件对象
    :param output_file: 输出文件对象，例如sys.stdout或open()返回的文件对象
    :param delimiter: CSV分隔符，默认为逗号
    """
    reader = csv.reader(input_file, delimiter=delimiter)
    writer = csv.writer(output_file, delimiter=delimiter)

    # 读取表头
    try:
        headers = next(reader)
    except StopIteration:
        return  # 空文件

    # 找到题型列的索引
    try:
        type_idx = headers.index('题型')
    except ValueError:
        print("错误：CSV文件中没有找到'题型'列。", file=sys.stderr)
        sys.exit(1)

    # 找到难度列的索引（如果存在）
    try:
        difficulty_idx = headers.index('难度')
        # 从表头中移除难度列
        headers.pop(difficulty_idx)
        # 如果难度列在题型列之前，删除后题型列索引会减1
        if difficulty_idx < type_idx:
            type_idx -= 1
    except ValueError:
        # 没有难度列，继续
        pass

    # 在题型列后插入新列
    headers.insert(type_idx + 1, '次要题型')
    writer.writerow(headers)

    # 处理数据行
    for row in reader:
        # 如果原行有难度列，删除对应值
        if 'difficulty_idx' in locals():
            row.pop(difficulty_idx)
        # 插入默认值
        row.insert(type_idx + 1, '无')
        writer.writerow(row)

def main():
    parser = argparse.ArgumentParser( description='处理CSV：删除难度列，插入次要题型列。')
    parser.add_argument('input', nargs='?', help='输入CSV文件路径（不指定则从标准输入读取）')
    parser.add_argument('output', nargs='?', help='输出CSV文件路径（不指定则输出到标准输出）')
    parser.add_argument('-d', '--delimiter', default=',', help='CSV分隔符（默认逗号）')
    args = parser.parse_args()

    # 打开输入文件
    if args.input:
        input_f = open(args.input, 'r', encoding='utf-8', newline='')
    else:
        input_f = sys.stdin

    # 打开输出文件
    if args.output:
        output_f = open(args.output, 'w', encoding='utf-8', newline='')
    else:
        output_f = sys.stdout

    try:
        process_csv(input_f, output_f, delimiter=args.delimiter)
    finally:
        if args.input:
            input_f.close()
        if args.output:
            output_f.close()

if __name__ == '__main__':
    main()