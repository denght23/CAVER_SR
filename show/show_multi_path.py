import json
import os
import math
import re

def read_fct_slowdowns(file_path, time_start, time_end, max_lines=float('inf')):
    """
    读取符合时间范围要求的流完成时间 (FCT) slowdown 和 FCT 绝对值，并计算平均值。

    :param file_path: 文件路径
    :param time_start: 起始时间（纳秒）
    :param time_end: 结束时间（纳秒）
    :param max_lines: 最大读取行数，默认为无限大
    :return: flow_avg_slowdown, packet_avg_slowdown, total_avg_slowdown, flow_count, packet_count, total_count,
             flow_avg_fct, packet_avg_fct, total_avg_fct, flow_slowdowns, packet_slowdowns, total_slowdowns,
             flow_fcts, packet_fcts, total_fcts
    """
    flow_slowdown_data = []
    packet_slowdown_data = []
    total_slowdown_data = []
    
    flow_fct_data = []
    packet_fct_data = []
    total_fct_data = []
    
    lines_read = 0

    try:
        with open(file_path, 'r') as file:
            for line in file:
                # 检查是否达到最大行数限制
                if lines_read >= max_lines:
                    print(f"Reached maximum line limit ({max_lines}), stopping read.")
                    break
                    
                lines_read += 1
                
                # 显示进度（每10000行）
                # if lines_read % 10000 == 0:
                #     print(f"Read {lines_read} lines...")
                
                fields = line.split()
                if len(fields) < 8:
                    continue

                start_time = int(fields[5])
                duration = int(fields[6])  # FCT 绝对值（纳秒）
                ideal_duration = int(fields[7])
                is_flow = int(fields[8])  # 假设第9列是流量类型，0表示逐流，1表示逐包
                
                if start_time > time_start and start_time + duration < time_end:
                    slowdown = duration / ideal_duration
                    slowdown = max(slowdown, 1.0)  # slowdown 至少为 1.0
                    
                    if is_flow == 0:
                        flow_slowdown_data.append(slowdown)
                        flow_fct_data.append(duration)
                    else:
                        packet_slowdown_data.append(slowdown)
                        packet_fct_data.append(duration)
                    
                    total_slowdown_data.append(slowdown)
                    total_fct_data.append(duration)

        # 计算平均值和统计数量
        flow_count = len(flow_slowdown_data)
        packet_count = len(packet_slowdown_data)
        total_count = len(total_slowdown_data)
        
        # Slowdown 平均值
        flow_avg_slowdown = sum(flow_slowdown_data) / flow_count if flow_count > 0 else 0.0
        packet_avg_slowdown = sum(packet_slowdown_data) / packet_count if packet_count > 0 else 0.0
        total_avg_slowdown = sum(total_slowdown_data) / total_count if total_count > 0 else 0.0
        
        # FCT 绝对值平均值（转换为微秒）
        flow_avg_fct = sum(flow_fct_data) / flow_count / 1000 if flow_count > 0 else 0.0  # 转换为微秒
        packet_avg_fct = sum(packet_fct_data) / packet_count / 1000 if packet_count > 0 else 0.0
        total_avg_fct = sum(total_fct_data) / total_count / 1000 if total_count > 0 else 0.0

        # 输出读取信息
        print(f"Successfully read {lines_read} lines from {file_path}")
        if lines_read == max_lines:
            print(f"Stopped at maximum line limit ({max_lines})")

        return (flow_avg_slowdown, packet_avg_slowdown, total_avg_slowdown, 
                flow_count, packet_count, total_count,
                flow_avg_fct, packet_avg_fct, total_avg_fct,
                flow_slowdown_data, packet_slowdown_data, total_slowdown_data,
                [x/1000 for x in flow_fct_data], [x/1000 for x in packet_fct_data], [x/1000 for x in total_fct_data])
    
    except IOError as e:
        print("Error reading file:", e)
        return (0.0, 0.0, 0.0, 0, 0, 0, 0.0, 0.0, 0.0, [], [], [], [], [], [])   

def read_flow_mapping(mapping_file_path):
    """
    从映射文件中读取流映射信息
    
    Parameters:
    - mapping_file_path: 映射文件路径
    
    Returns:
    - new_to_old: {新流编号: 旧流编号}
    - old_to_new: {旧流编号: [新流编号列表]}
    """
    new_to_old = {}
    old_to_new = {}
    
    try:
        with open(mapping_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split()
                    if len(parts) >= 2:
                        new_id = int(parts[0])
                        old_id = int(parts[1])
                        
                        new_to_old[new_id] = old_id
                        
                        if old_id not in old_to_new:
                            old_to_new[old_id] = []
                        old_to_new[old_id].append(new_id)
        
        print(f"Loaded mapping: {len(new_to_old)} new flows from {len(old_to_new)} original flows")
        
        return new_to_old, old_to_new
        
    except FileNotFoundError:
        print(f"Error: Mapping file {mapping_file_path} not found")
        return {}, {}
    except Exception as e:
        print(f"Error reading mapping file {mapping_file_path}: {e}")
        return {}, {}

def analyze_split_flows_fct(fct_file_path, mapping_file_path, time_start, time_end, original_traffic_file=None):
    """
    分析切分后的流量FCT，计算原始流的FCT（取子流中最大的结束时间）
    只有当原始流的所有子流都完成时，才计算相应的FCT
    
    Parameters:
    - fct_file_path: FCT结果文件路径
    - mapping_file_path: 映射文件路径
    - time_start: 起始时间（纳秒）
    - time_end: 结束时间（纳秒）
    - original_traffic_file: 原始流量文件路径（可选，用于获取原始流大小）
    
    Returns:
    - original_flow_results: {原流编号: FCT信息}
    """
    # 读取映射信息
    new_to_old, old_to_new = read_flow_mapping(mapping_file_path)
    
    if not new_to_old:
        print("No mapping information found")
        return {}
    
    # 读取原始流量文件信息（如果提供）
    original_sizes = {}
    if original_traffic_file:
        try:
            with open(original_traffic_file, 'r') as f:
                lines = f.readlines()
                for old_id, line in enumerate(lines[1:]):
                    fields = line.strip().split()
                    if len(fields) >= 4:
                        original_sizes[old_id] = int(fields[3])
        except Exception as e:
            print(f"Error reading original traffic file: {e}")
    
    # 读取FCT数据
    sub_flow_fcts = {}  # {新流编号: FCT信息}
    
    try:
        with open(fct_file_path, 'r') as file:
            print(f"Reading FCT file...: {fct_file_path}")
            for line_num, line in enumerate(file):
                fields = line.split()
                if len(fields) < 9:
                    continue
                
                new_flow_id = int(fields[8])
                start_time = int(fields[5])
                duration = int(fields[6])
                end_time = start_time + duration
                standard_fct = int(fields[7])
                size = int(fields[4])
                
                if start_time > time_start and end_time < time_end:
                    sub_flow_fcts[new_flow_id] = {
                        'start_time': start_time,
                        'duration': duration,
                        'end_time': end_time,
                        'standalone_fct': standard_fct ,
                        'size': size
                    }
    
    except IOError as e:
        print(f"Error reading FCT file: {e}")
        return {}
    
    # 计算原始流的FCT - 只有当所有子流都完成时才计算
    original_flow_results = {}
    completed_flows = 0
    incomplete_flows = 0
    
    for old_id, new_ids in old_to_new.items():
        # 检查这个原始流的所有子流是否都完成了
        sub_flow_data = []
        missing_sub_flows = []
        
        for new_id in new_ids:
            if new_id in sub_flow_fcts:
                sub_flow_data.append(sub_flow_fcts[new_id])
            else:
                missing_sub_flows.append(new_id)
        
        # 只有当所有子流都完成时，才计算原始流的FCT
        if len(missing_sub_flows) == 0 and len(sub_flow_data) == len(new_ids):
            # 所有子流都完成了
            # 计算最早开始时间和最晚结束时间
            min_start_time = min(data['start_time'] for data in sub_flow_data)
            max_end_time = max(data['end_time'] for data in sub_flow_data)
            total_fct = max_end_time - min_start_time
            
            original_flow_results[old_id] = {
                'start_time': min_start_time,
                'end_time': max_end_time,
                'total_fct': total_fct,
                'sub_flow_count': len(sub_flow_data),
                'sub_flows': sub_flow_data,
                'original_size': original_sizes.get(old_id, 0),
                'all_sub_flows_completed': True
            }
            completed_flows += 1
        else:
            # 有子流未完成，不计算这个原始流的FCT
            incomplete_flows += 1
            if len(sub_flow_data) > 0:
                # 记录调试信息，但不加入结果
                print(f"Warning: Original flow {old_id} incomplete - "
                      f"completed sub-flows: {len(sub_flow_data)}/{len(new_ids)}, "
                      f"missing sub-flows: {missing_sub_flows}")
    
    print(f"Analyzed {completed_flows} complete original flows from split data")
    print(f"Skipped {incomplete_flows} incomplete original flows")
    print(f"Total original flows in mapping: {len(old_to_new)}")
    
    return original_flow_results


def calculate_standalone_fct(flow_size, sub_flow_info=None, packet_payload_size=1000, default_bandwidth=100e9):
    """
    计算standalone FCT
    对于切分流：用每个子流的标准fct-子流大小/100Gbps得到传播时间，然后用旧流大小/100Gbps+传播时间
    对于普通流：使用传统计算方法
    
    Parameters:
    - flow_size: 原始流大小（字节）
    - sub_flow_info: 子流信息 {'sub_flows': [sub_flow_data], 'sub_flow_count': count}，如果为None则是普通流
    - packet_payload_size: 数据包负载大小，默认1000字节
    - default_bandwidth: 默认带宽，100Gbps
    
    Returns:
    - standalone_fct: standalone FCT（纳秒）
    """
    bandwidth_100g = 100e9  # 100Gbps
    
    # 如果有子流信息，使用新的计算方法
    if sub_flow_info and 'sub_flows' in sub_flow_info and len(sub_flow_info['sub_flows']) > 0:
        # 取第一个子流计算传播时间（所有子流传播时间相同）
        first_sub_flow = sub_flow_info['sub_flows'][0]
        # 从子流数据中获取子流大小（第5列，索引4）和标准FCT（倒数第二列，索引7）
        sub_flow_size = first_sub_flow['size']  # 子流大小（字节）
        sub_flow_standard_fct = first_sub_flow['standalone_fct']  # 从FCT文件的倒数第二列获取标准FCT
        
        # 计算子流的传输时间
        sub_flow_transmission_time = int(sub_flow_size * 8 * 1000000000 / bandwidth_100g)  # 纳秒
        
        # 传播时间 = 子流标准FCT - 子流大小/100Gbps
        propagation_time = sub_flow_standard_fct - sub_flow_transmission_time
        
        # 原始流标准FCT = 原始流大小/100Gbps + 传播时间
        original_flow_transmission_time = int(flow_size * 8 * 1000000000 / bandwidth_100g)  # 纳秒
        standalone_fct = original_flow_transmission_time + propagation_time
    else:
        # 传统计算方法（用于非切分流）
        base_rtt = 12480  # 纳秒，假设值
        transmission_time = int(flow_size * 8 * 1000000000 / bandwidth_100g)
        standalone_fct = base_rtt + transmission_time
    
    return standalone_fct

def analyze_fct_with_standalone(fct_file_path, pair_rtt_file, mapping_file_path=None, 
                               time_start=None, time_end=None, original_traffic_file=None):
    """
    分析FCT文件，计算FCT slowdown
    
    Parameters:
    - fct_file_path: FCT文件路径
    - pair_rtt_file: pairRTT文件路径
    - mapping_file_path: 映射文件路径（如果有切分流量）
    - time_start: 开始时间（纳秒）
    - time_end: 结束时间（纳秒）
    - original_traffic_file: 原始流量文件路径
    
    Returns:
    - analysis_results: 分析结果字典
    """
    
    analysis_results = {
        'flows': [],
        'avg_slowdown': 0,
        'p99_slowdown': 0,
        'total_flows': 0
    }
    
    # 如果有映射文件，说明是切分后的流量
    if mapping_file_path:
        # 使用已有的函数处理切分流量
        original_flow_results = analyze_split_flows_fct(
            fct_file_path, mapping_file_path, time_start, time_end, original_traffic_file
        )
        
        # 读取映射信息获取原始流大小
        new_to_old, old_to_new = read_flow_mapping(mapping_file_path)
        
        # 读取原始流量文件获取节点信息
        original_flow_info = {}
        if original_traffic_file:
            try:
                with open(original_traffic_file, 'r') as f:
                    lines = f.readlines()
                    for old_id, line in enumerate(lines[1:]):
                        fields = line.strip().split()
                        if len(fields) >= 6:
                            original_flow_info[old_id] = {
                                'src': int(fields[0]),
                                'dst': int(fields[1]),
                                'size': int(fields[3])
                            }
            except Exception as e:
                print(f"Error reading original traffic file: {e}")
        
        # 计算每个原始流的slowdown
        slowdowns = []
        for old_id, fct_data in original_flow_results.items():
            if old_id in original_flow_info:
                src_id = original_flow_info[old_id]['src']
                dst_id = original_flow_info[old_id]['dst']
                flow_size = original_flow_info[old_id]['size']
                actual_fct = fct_data['total_fct']
                
                # 传递子流信息给 calculate_standalone_fct
                sub_flow_info = {
                    'sub_flows': fct_data['sub_flows'],
                    'sub_flow_count': fct_data['sub_flow_count']
                }
                standalone_fct = calculate_standalone_fct(flow_size, sub_flow_info)
                slowdown = actual_fct / standalone_fct if standalone_fct > 0 else float('inf')
                
                slowdowns.append(slowdown)
                analysis_results['flows'].append({
                    'flow_id': old_id,
                    'src': src_id,
                    'dst': dst_id,
                    'size': flow_size,
                    'actual_fct': actual_fct,
                    'standalone_fct': standalone_fct,
                    'slowdown': slowdown,
                    'sub_flow_count': fct_data['sub_flow_count']
                })
    
    else:
        # 直接处理FCT文件
        slowdowns = []
        try:
            with open(fct_file_path, 'r') as f:
                for line_id, line in enumerate(f):
                    fields = line.strip().split()
                    if len(fields) >= 8:
                        src_id = int(fields[0])
                        dst_id = int(fields[1])
                        sport = int(fields[2])
                        dport = int(fields[3])
                        flow_size = int(fields[4])
                        start_time = int(fields[5])
                        duration = int(fields[6])
                        standalone_fct_from_file = int(fields[7])
                        reorderable = int(fields[8]) if len(fields) > 8 else 0
                        
                        # 过滤时间范围
                        if time_start and start_time <= time_start:
                            continue
                        if time_end and start_time + duration >= time_end:
                            continue
                        
                        # 重新计算standalone FCT以验证
                        calculated_standalone_fct = calculate_standalone_fct(flow_size, None)
                        
                        actual_fct = duration
                        slowdown = actual_fct / calculated_standalone_fct if calculated_standalone_fct > 0 else float('inf')
                        
                        slowdowns.append(slowdown)
                        analysis_results['flows'].append({
                            'flow_id': line_id,
                            'src': src_id,
                            'dst': dst_id,
                            'sport': sport,
                            'dport': dport,
                            'size': flow_size,
                            'actual_fct': actual_fct,
                            'standalone_fct_from_file': standalone_fct_from_file,
                            'calculated_standalone_fct': calculated_standalone_fct,
                            'slowdown': slowdown,
                            'reorderable': reorderable
                        })
        
        except Exception as e:
            print(f"Error reading FCT file: {e}")
            return analysis_results
    
    # 计算统计信息
    if slowdowns:
        analysis_results['avg_slowdown'] = sum(slowdowns) / len(slowdowns)
        analysis_results['p99_slowdown'] = sorted(slowdowns)[int(len(slowdowns) * 0.99)]
        analysis_results['total_flows'] = len(slowdowns)
        
        print(f"Analysis complete:")
        print(f"  Total flows: {analysis_results['total_flows']}")
        print(f"  Average slowdown: {analysis_results['avg_slowdown']:.3f}")
        print(f"  P99 slowdown: {analysis_results['p99_slowdown']:.3f}")
    
    return analysis_results

def find_experiment_names_by_numbers(numbers, base_folder="/home/denghaotian/research/CAVER_muti_path/ns-allinone-3.19/ns-3.19/mix/output"):
    """
    根据数字编号列表在指定文件夹中找到对应的实验名称
    
    :param numbers: 数字编号列表，例如 [444, 445, 446, 447]
    :param base_folder: 基础文件夹路径
    :return: 对应的实验名称列表
    """
    name_list = []
    
    if not os.path.exists(base_folder):
        print(f"Error: Base folder {base_folder} does not exist!")
        return name_list
    
    # 获取文件夹中所有的目录名
    all_folders = [f for f in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, f))]
    
    # 为每个数字编号查找对应的文件夹
    for number in numbers:
        found = False
        pattern = rf'^\[{number}\]-.*'  # 匹配 [数字]- 开头的文件夹名
        
        for folder_name in all_folders:
            if re.match(pattern, folder_name):
                name_list.append(folder_name)
                print(f"Found experiment {number}: {folder_name}")
                found = True
                break
        
        if not found:
            print(f"Warning: No experiment found for number {number}")
    
    return name_list

def get_flow_file_from_config_log(config_log_path):
    """
    从config_log文件中读取FLOW_FILE配置信息，返回流量文件名
    
    Parameters:
    - config_log_path: config_log文件路径
    
    Returns:
    - flow_file: 流量文件名（不包含路径），如果没找到则返回None
    """
    try:
        with open(config_log_path, 'r') as f:
            for line in f:
                line = line.strip()
                # 查找包含FLOW_FILE的行
                if line.startswith('FLOW_FILE') and 'config/' in line:
                    # 提取文件路径部分
                    parts = line.split()
                    if len(parts) >= 2:
                        file_path = parts[1]  # 获取文件路径部分
                        # 提取文件名（去掉路径前缀）
                        if 'config/' in file_path:
                            flow_file = file_path.split('config/')[-1]
                            print(f"Found FLOW_FILE: {flow_file}")
                            return flow_file
        
        print(f"Warning: No FLOW_FILE found in {config_log_path}")
        return None
        
    except FileNotFoundError:
        print(f"Error: Config log file {config_log_path} not found")
        return None
    except Exception as e:
        print(f"Error reading config log file {config_log_path}: {e}")
        return None

def extract_original_traffic_name(flow_file):
    """
    从切分后的流量文件名中提取原始流量文件名
    
    Parameters:
    - flow_file: 切分后的流量文件名，如 "L_29.00_CDF_AliStorage2019_N_256_T_30ms_B_100_SR_1.0_flow_split.txt"
    
    Returns:
    - original_file: 原始流量文件名，如 "L_29.00_CDF_AliStorage2019_N_256_T_30ms_B_100_SR_1.0_flow.txt"
    """
    if flow_file and flow_file.endswith('_split.txt'):
        # 移除 "_split" 部分
        original_file = flow_file.replace('_split.txt', '.txt')
        return original_file
    elif flow_file and flow_file.endswith('.txt'):
        # 如果已经是原始文件名，直接返回
        return flow_file
    else:
        print(f"Warning: Unexpected flow file format: {flow_file}")
        return flow_file

def get_mapping_file_name(flow_file):
    """
    根据流量文件名生成对应的映射文件名
    
    Parameters:
    - flow_file: 流量文件名
    
    Returns:
    - mapping_file: 映射文件名
    """
    if flow_file and flow_file.endswith('_split.txt'):
        # 替换 "_split.txt" 为 "_split_mapping.txt"
        mapping_file = flow_file.replace('_split.txt', '_split_mapping.txt')
        return mapping_file
    else:
        print(f"Warning: Flow file {flow_file} doesn't appear to be a split file")
        return None

def get_LB_mode(file_path):
    """
    从config_log中读取 LB_MODE的值。

    Args:
        file_path (str): config_log的路径。

    Returns:
        lb_mode:逐流路由的流量的路由算法；
    """
    with open(file_path, "r") as f:
        for line in f:
            # 去掉换行和首尾空格
            line = line.strip()
            # 跳过空行
            if not line:
                continue
            if line.startswith("LB_MODE"):
                # 取等号右边或空格后面的值
                lb_mode = int(line.split()[-1])
    return lb_mode

LB_mode = {
    0: "ECMP",
    2: "Drill",
    20: "CAVER",
    32: "Greedy",
    33: "Oblivious",
}


# 1. 定义文件路径

traffic_folder = "/home/denghaotian/research/CAVER_muti_path/ns-allinone-3.19/ns-3.19/config"
output_folder = "/home/denghaotian/research/CAVER_muti_path/ns-allinone-3.19/ns-3.19/mix/output"
###故障
experiment_numbers = [18,19,20,21,22,23]  # 替换为你想查找的实验编号列表
name_list = find_experiment_names_by_numbers(experiment_numbers)
###背景流
# experiment_numbers = [26, 27, 28, 29, 30, 31, 32, 33, 34, 35]
# name_list = find_experiment_names_by_numbers(experiment_numbers)

# ##单路径实验：
# experiment_numbers = [36, 37]  # 替换为你想查找的实验编号列表
# name_list = find_experiment_names_by_numbers(experiment_numbers)


for name in name_list:
    print(f"\n=== {name} ===")
    fct_file = output_folder + f"/{name}/{name}_out_fct.txt"
    pair_rtt_file = output_folder + f"/{name}/pairRtt.txt"
    config_log_file = output_folder + f"/{name}/config.log"
    flow_file = traffic_folder + f"/{get_flow_file_from_config_log(config_log_file)}"
    original_traffic_file = extract_original_traffic_name(flow_file)
    mapping_file = get_mapping_file_name(flow_file)
    flow_LB_mode= get_LB_mode(config_log_file)
    print(f"Flow LB Mode: {LB_mode[flow_LB_mode]}")




    analysis_results = analyze_fct_with_standalone(
        fct_file_path=fct_file,
        pair_rtt_file=pair_rtt_file,
        mapping_file_path=mapping_file,
        time_start=int(2.000 * 1e9),  # 开始时间（纳秒）
        time_end=int(30.000 * 1e9),   # 结束时间（纳秒）
        original_traffic_file=original_traffic_file
    )


    if analysis_results and analysis_results['total_flows'] > 0:
        print(f"总共分析的流数量: {analysis_results['total_flows']}")
        print(f"平均FCT slowdown: {analysis_results['avg_slowdown']:.4f}")
        print(f"99%分位数FCT slowdown: {analysis_results['p99_slowdown']:.4f}")
    else:
        print("没有找到完成的流或分析失败")
    
    # (flow_avg_slowdown, packet_avg_slowdown, total_avg_slowdown, 
    #  flow_count, packet_count, total_count,
    #  flow_avg_fct, packet_avg_fct, total_avg_fct,
    #  flow_slowdowns, packet_slowdowns, total_slowdowns,
    #  flow_fcts, packet_fcts, total_fcts) = read_fct_slowdowns(fct_file, int(2.000 * 1e9), int(30.000 * 1e9))
    
    # print(f"Flow Average Slowdown: {flow_avg_slowdown:.3f}, Packet Average Slowdown: {packet_avg_slowdown:.3f}, Total Average Slowdown: {total_avg_slowdown:.3f}")
    # print(f"Flow Average FCT: {flow_avg_fct:.2f}μs, Packet Average FCT: {packet_avg_fct:.2f}μs, Total Average FCT: {total_avg_fct:.2f}μs")
