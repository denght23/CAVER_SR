import json
import os
import math

def split_flows_by_chunks(input_file, output_file, k=4, chunk_size=1000, mapping_file=None):
    """
    将流量文件中最后一列为1的流量使用轮转方法分成最多k个子流，
    按开始时间排序后重新分配ID，并生成新旧ID映射
    
    Parameters:
    - input_file: 输入流量文件路径
    - output_file: 输出流量文件路径
    - k: 最多分成k个子流
    - chunk_size: 每次分配的chunk大小，默认1000字节
    - mapping_file: 映射文件路径，如果为None则自动生成
    
    Returns:
    - mapping_file: 映射文件的路径
    """
    if mapping_file is None:
        # 自动生成映射文件名
        base_name = os.path.splitext(output_file)[0]
        mapping_file = f"{base_name}_mapping.txt"
    
    with open(input_file, 'r') as fin:
        lines = fin.readlines()
    
    # 存储所有生成的流（包含原始流ID信息）
    all_flows = []
    
    # 处理每个流
    for old_flow_id, line in enumerate(lines[1:]):
        fields = line.strip().split()
        if len(fields) < 6:
            continue
            
        src = int(fields[0])
        dst = int(fields[1])
        protocol = int(fields[2])
        size = int(fields[3])
        start_time = float(fields[4])
        reorder = int(fields[5])
        
        if reorder == 1:
            # 需要切分的流 - 使用轮转分配
            sub_flow_sizes = distribute_flow_size_round_robin(size, k, chunk_size)
            
            # 100Gbps = 100 * 1e9 bits/s = 12.5 * 1e9 Bytes/s
            bandwidth_Bps = 12.5e9
            cur_start_time = start_time
            for idx, sub_size in enumerate(sub_flow_sizes):
                flow_info = {
                    'src': src,
                    'dst': dst,
                    'protocol': protocol,
                    'size': sub_size,
                    'start_time': cur_start_time,
                    'reorder': 0,
                    'original_flow_id': old_flow_id
                }
                all_flows.append(flow_info)
                # 下一个子流的开始时间递增
                cur_start_time += sub_size / bandwidth_Bps
        else:
            # 不需要切分的流，直接添加
            flow_info = {
                'src': src,
                'dst': dst,
                'protocol': protocol,
                'size': size,
                'start_time': start_time,
                'reorder': reorder,
                'original_flow_id': old_flow_id
            }
            all_flows.append(flow_info)
    
    # 按开始时间排序
    all_flows.sort(key=lambda x: x['start_time'])
    
    # 生成新的流量文件
    new_lines = [str(len(all_flows))]  # 总流量数
    
    # 生成映射关系 (新ID -> 旧ID)
    id_mapping = []
    
    for new_flow_id, flow_info in enumerate(all_flows):
        new_fields = [
            str(flow_info['src']),
            str(flow_info['dst']),
            str(flow_info['protocol']),
            str(flow_info['size']),
            f"{flow_info['start_time']:.9f}",
            str(flow_info['reorder'])
        ]
        new_line = ' '.join(new_fields)
        new_lines.append(new_line)
        
        # 记录映射关系
        id_mapping.append((new_flow_id, flow_info['original_flow_id']))
    
    # 写入新的流量文件
    with open(output_file, 'w') as fout:
        fout.write('\n'.join(new_lines) + '\n')
    
    # 写入映射文件
    with open(mapping_file, 'w') as fout:
        for new_id, old_id in id_mapping:
            fout.write(f"{new_id} {old_id}\n")
    
    # 统计信息
    original_flow_count = len(lines) - 1
    split_count = sum(1 for line in lines[1:] if len(line.strip().split()) >= 6 and int(line.strip().split()[5]) == 1)
    
    print(f"Original flows: {original_flow_count}")
    print(f"Split {split_count} flows (reorder=1) into sub-flows using round-robin with max {k} sub-flows each")
    print(f"Total new flows: {len(all_flows)}")
    print(f"Flows sorted by start time")
    print(f"Flow mapping saved to: {mapping_file}")
    
    return mapping_file

def distribute_flow_size_round_robin(total_size, k, chunk_size):
    """
    使用轮转分配方法将总大小分配给最多k个子流
    
    Parameters:
    - total_size: 总大小
    - k: 最多k个子流
    - chunk_size: 每次分配的chunk大小
    
    Returns:
    - sub_flow_sizes: 各个子流的大小列表（只包含大小>0的子流）
    """
    sub_flow_sizes = [0] * k  # 初始化k个子流，大小都为0
    remaining_size = total_size
    current_sub_flow = 0
    
    while remaining_size > 0:
        # 计算当前分配的大小
        if remaining_size >= chunk_size:
            allocation = chunk_size
        else:
            allocation = remaining_size  # 剩余不足chunk_size时，分配全部剩余
        
        # 分配给当前子流
        sub_flow_sizes[current_sub_flow] += allocation
        remaining_size -= allocation
        
        # 轮转到下一个子流
        current_sub_flow = (current_sub_flow + 1) % k
    
    # 只返回大小大于0的子流
    return [size for size in sub_flow_sizes if size > 0]

name = 'L_29.00_CDF_AliStorage2019_N_256_T_30ms_B_100_SR_1.0_flow'
input_file = f'{name}.txt'
output_file = f'{name}_split.txt'
mapping_file = split_flows_by_chunks(
    input_file=input_file,
    output_file=output_file
)
name = 'L_29.00_CDF_AliStorage2019_N_256_T_30ms_B_100_SR_0.9_flow'
input_file = f'{name}.txt'
output_file = f'{name}_split.txt'
mapping_file = split_flows_by_chunks(
    input_file=input_file,
    output_file=output_file
)
name = 'L_29.00_CDF_AliStorage2019_N_256_T_30ms_B_100_SR_0.8_flow'
input_file = f'{name}.txt'
output_file = f'{name}_split.txt'
mapping_file = split_flows_by_chunks(
    input_file=input_file,
    output_file=output_file
)
name = 'L_29.00_CDF_AliStorage2019_N_256_T_30ms_B_100_SR_0.7_flow'
input_file = f'{name}.txt'
output_file = f'{name}_split.txt'
mapping_file = split_flows_by_chunks(
    input_file=input_file,
    output_file=output_file
)
name = 'L_29.00_CDF_AliStorage2019_N_256_T_30ms_B_100_SR_0.6_flow'
input_file = f'{name}.txt'
output_file = f'{name}_split.txt'
mapping_file = split_flows_by_chunks(
    input_file=input_file,
    output_file=output_file
)