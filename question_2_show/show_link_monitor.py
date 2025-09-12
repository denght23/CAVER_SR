import re
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def parse_link_states_to_dict(filepath):
    """
    解析 link_states 文件并重建为嵌套字典的数据结构。
    格式: {timestamp: {src_id: {dst_id: [qlen, utilization]}}}
    """
    link_states_data = {}
    current_timestamp = None
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # 匹配 "Link state at [timestamp]:" 行
                timestamp_match = re.match(r"Link state at (\d+):", line)
                if timestamp_match:
                    current_timestamp = int(timestamp_match.group(1))
                    link_states_data[current_timestamp] = {}
                    continue
                # 匹配 "Src:[ID], [dst] [qlen] [util], ..." 行
                src_match = re.match(r"Src:(\d+)", line)
                if src_match and current_timestamp is not None:
                    src_id = int(src_match.group(1))
                    link_states_data[current_timestamp].setdefault(src_id, {})
                    link_info_str = line[src_match.end(0):]
                    link_details = re.findall(r",\s*(\d+)\s+(\d+)\s+([\d.]+)", link_info_str)
                    for dst_id_str, qlen_str, util_str in link_details:
                        dst_id = int(dst_id_str)
                        qlen = int(qlen_str)
                        utilization = float(util_str)
                        link_states_data[current_timestamp][src_id][dst_id] = [qlen, utilization]
    except FileNotFoundError:
        print(f"错误：文件 '{filepath}' 未找到。请检查文件名和路径。")
        return None
    except Exception as e:
        print(f"解析文件时发生错误: {e}")
        return None
    return link_states_data

def draw_heatmap(parsed_data, timestamp, name, metric='util'):
    """
    根据解析的数据为指定的时问戳绘制链路利用率热力图。
    此版本经过优化，可以自适应处理拥挤的X轴刻度。
    """
    # 检查时间戳是否存在
    if timestamp not in parsed_data:
        print(f"错误：时间戳 {timestamp} 在数据中未找到。可用时间戳为: {list(parsed_data.keys())}")
        return

    link_data_at_timestamp = parsed_data[timestamp]
    
    # 1. 自适应识别所有唯一的节点ID
    all_node_ids = set()
    for src_id, destinations in link_data_at_timestamp.items():
        all_node_ids.add(src_id)
        for dst_id in destinations.keys():
            all_node_ids.add(dst_id)

    if not all_node_ids:
        print(f"警告：在时间戳 {timestamp} 没有找到任何节点数据。")
        return

    # 2. 对节点ID排序，并建立从ID到矩阵索引的映射
    sorted_nodes = sorted(list(all_node_ids))
    node_to_idx = {node_id: i for i, node_id in enumerate(sorted_nodes)}
    num_nodes = len(sorted_nodes)

    # 3. 初始化矩阵
    heatmap_matrix = np.full((num_nodes, num_nodes), np.nan)

    # 4. 填充矩阵
    for src_id, destinations in link_data_at_timestamp.items():
        for dst_id, (qlen, util) in destinations.items():
            src_idx = node_to_idx.get(src_id)
            dst_idx = node_to_idx.get(dst_id)
            if src_idx is not None and dst_idx is not None:
                value = util if metric == 'util' else qlen / 150000.0
                heatmap_matrix[src_idx, dst_idx] = value

    # --- 开始绘图 (已优化) ---
    # 适当增加图像宽度以容纳更多标签
    plt.figure(figsize=(16, 14))
    
    ax = sns.heatmap(
        heatmap_matrix,
        annot=False,
        cmap="viridis",
        linewidths=.1,
        vmin=0.0,
        vmax=1.0,
        cbar_kws={'label': f'{metric}'},
        xticklabels=sorted_nodes,
        yticklabels=sorted_nodes
    )

    #ax.xaxis.set_major_locator(MaxNLocator(nbins=40, integer=True))
    #ax.yaxis.set_major_locator(MaxNLocator(nbins=40, integer=True))

    # 设置标题和坐标轴标签
    plt.title(f'{metric} Heatmap at Timestamp {timestamp}', fontsize=16)
    plt.xlabel('Destination Node ID', fontsize=12)
    plt.ylabel('Source Node ID', fontsize=12)


    # 调整布局以确保所有标签都可见
    plt.tight_layout()

    # 显示图像
    plt.savefig(f"{name}_heatmap_{metric}_{timestamp}.png", dpi=300)

# --- 主程序入口 ---
if __name__ == '__main__':
    # ==================== 用户配置 ====================
    # 1. 请将这里的文件名修改为您自己的 link_states 文件名
    name = "[355]-09-12-16:35:12-fecmp-80"
    FILENAME = f"../mix/output/{name}/{name}_out_link_monitor.txt"
    
    # 2. 定义网络拓扑的尺寸 (8x8 矩阵)
    # ================================================

    print(f"正在从 '{FILENAME}' 文件中解析数据...")
    parsed_data = parse_link_states_to_dict(FILENAME)

    if not parsed_data:
        print("数据解析失败或文件为空，程序退出。")
    else:
        print("数据解析成功！")
        # 获取文件中所有可用时间戳
        available_timestamps = list(parsed_data.keys())
        print(f"在文件中找到以下时间戳: {available_timestamps}")
        
        # 默认绘制第一个找到的时间戳的热力图
        timestamp_to_draw = available_timestamps[50]
        
        # 如果您想绘制特定的时间戳，可以取消下面这行的注释并修改
        # timestamp_to_draw = 1234567890 # <--- 在这里指定你想看的时间戳

        print(f"\n正在为时间戳 {timestamp_to_draw} 绘制热力图...")
        draw_heatmap(parsed_data, timestamp_to_draw, name, metric='util')