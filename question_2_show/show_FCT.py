import matplotlib.pyplot as plt
import numpy as np
import os

def get_LB_mode(file_path):
    """
    从config_log中读取 LB_MODE 和 PACKET_LB_MODE 的值。

    Args:
        file_path (str): config_log的路径。

    Returns:
        lb_mode:逐流路由的流量的路由算法；
        packet_lb_mode:逐包路由的流量的路由算法。
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
            elif line.startswith("PACKET_LB_MODE"):
                packet_lb_mode = int(line.split()[-1])
    return lb_mode, packet_lb_mode


def read_fct_slowdowns(file_path, time_start, time_end):
    """
    读取符合时间范围要求的流完成时间 (FCT) slowdown 和 FCT 绝对值，并计算平均值。

    :param file_path: 文件路径
    :param time_start: 起始时间（纳秒）
    :param time_end: 结束时间（纳秒）
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

    try:
        with open(file_path, 'r') as file:
            for line in file:
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

        return (flow_avg_slowdown, packet_avg_slowdown, total_avg_slowdown, 
                flow_count, packet_count, total_count,
                flow_avg_fct, packet_avg_fct, total_avg_fct,
                flow_slowdown_data, packet_slowdown_data, total_slowdown_data,
                [x/1000 for x in flow_fct_data], [x/1000 for x in packet_fct_data], [x/1000 for x in total_fct_data])
    
    except IOError as e:
        print("Error reading file:", e)
        return (0.0, 0.0, 0.0, 0, 0, 0, 0.0, 0.0, 0.0, [], [], [], [], [], [])                    


def plot_cdf(data, title, xlabel, filename, color='blue'):
    """
    绘制 CDF 图并保存为 PNG
    
    :param data: 数据列表
    :param title: 图标题
    :param xlabel: x轴标签
    :param filename: 保存的文件名
    :param color: 曲线颜色
    """
    if len(data) == 0:
        print(f"Warning: No data to plot for {title}")
        return
    
    # 排序数据
    sorted_data = np.sort(data)
    # 计算 CDF
    y = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
    
    plt.figure(figsize=(10, 6))
    plt.plot(sorted_data, y, color=color, linewidth=2)
    plt.xlabel(xlabel)
    plt.ylabel('CDF')
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.xlim(left=0)
    plt.ylim(0, 1)
    
    # 添加统计信息
    mean_val = np.mean(data)
    median_val = np.median(data)
    p95_val = np.percentile(data, 95)
    p99_val = np.percentile(data, 99)
    
    info_text = f'Mean: {mean_val:.2f}\nMedian: {median_val:.2f}\n95th: {p95_val:.2f}\n99th: {p99_val:.2f}\nCount: {len(data)}'
    plt.text(0.7, 0.2, info_text, transform=plt.gca().transAxes, 
             bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
    
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"CDF plot saved to: {filename}")

# def read_fct_slowdowns(file_path, time_start, time_end):
#     """
#     读取符合时间范围要求的流完成时间 (FCT) slowdown，并计算平均值。

#     :param file_path: 文件路径
#     :param time_start: 起始时间（纳秒）
#     :param time_end: 结束时间（纳秒）
#     :return: flow_avg_slowdown, packet_avg_slowdown
#     """
#     flow_slowdown_data = []
#     packet_slowdown_data = []
#     total_slowdown_data = []

#     try:
#         with open(file_path, 'r') as file:
#             for line in file:
#                 fields = line.split()
#                 if len(fields) < 8:
#                     continue

#                 start_time = int(fields[5])
#                 duration = int(fields[6])
#                 ideal_duration = int(fields[7])
#                 is_flow = int(fields[8])  # 假设第9列是流量类型，0表示逐流，1表示逐包
#                 if start_time > time_start and start_time + duration < time_end:
#                     slowdown = duration / ideal_duration
#                     if is_flow == 0:
#                         flow_slowdown_data.append(max(slowdown, 1.0))
#                     else:
#                         packet_slowdown_data.append(max(slowdown, 1.0))
#                     total_slowdown_data.append(max(slowdown, 1.0))

#         # 计算平均值
#         if flow_slowdown_data:
#             flow_avg_slowdown = sum(flow_slowdown_data) / len(flow_slowdown_data)
#         else:
#             flow_avg_slowdown = 0.0  # 如果没有数据，返回 0.0

#         if packet_slowdown_data:
#             packet_avg_slowdown = sum(packet_slowdown_data) / len(packet_slowdown_data)
#         else:
#             packet_avg_slowdown = 0.0  # 如果没有数据，返回 0.0
#         if total_slowdown_data:
#             total_avg_slowdown = sum(total_slowdown_data) / len(total_slowdown_data)
#         else:
#             total_avg_slowdown = 0.0

#         return flow_avg_slowdown, packet_avg_slowdown, total_avg_slowdown
    
#     except IOError as e:
#         print("Error reading file:", e)
#         return 0.0, 0.0

LB_mode = {
    0: "ECMP",
    2: "Drill",
    20: "CAVER",
    32: "Greedy",
    33: "Oblivious",
}



# name_list = ["[125]-07-25-16:14:55-fecmp-70", "[122]-07-25-14:46:25-fecmp-70", "[123]-07-25-14:46:35-fecmp-70", "[124]-07-25-14:46:45-caver-70"]
####逐流：逐包 = 0。7：0。3
# name_list = ["[156]-09-03-17:52:26-fecmp-50", "[157]-09-03-17:52:36-fecmp-50", "[159]-09-03-17:52:56-fecmp-50", "[155]-09-03-17:50:36-fecmp-50", "[161]-09-03-17:53:16-fecmp-50", "[160]-09-03-17:53:06-fecmp-50", "[158]-09-03-17:52:46-fecmp-50", "[162]-09-03-17:53:26-fecmp-50", "[163]-09-03-19:18:13-fecmp-50", "[164]-09-03-19:30:15-caver-50", "[165]-09-03-19:45:07-fecmp-50"]
####逐流：逐包 = 0。15：0。85
# name_list = ["[172]-09-03-20:28:11-fecmp-48", "[173]-09-03-20:28:21-fecmp-48", "[174]-09-03-20:28:31-caver-48", "[175]-09-03-20:28:41-fecmp-48", "[176]-09-03-20:28:51-caver-48", "[177]-09-03-20:35:25-fecmp-48", "[178]-09-03-20:45:48-fecmp-48"]
####逐流：逐包 = 0。15：0。85（解决了PFC，SR启用的bug）
# name_list = ["[175]-09-03-20:28:41-fecmp-48", "[208]-09-05-18:10:47-fecmp-48", "[209]-09-05-18:11:06-fecmp-48"]
####逐流：逐包 = 0。15：0。85（解决了PFC，SR启用的bug）
# name_list = ["[245]-09-06-22:29:56-fecmp-48", "[244]-09-06-22:29:11-fecmp-48", "[239]-09-06-22:26:31-fecmp-48", "[240]-09-06-22:26:58-fecmp-48", "[241]-09-06-22:27:14-fecmp-48", "[242]-09-06-22:28:15-fecmp-48", "[243]-09-06-22:28:30-fecmp-48"]
####逐流：逐包 = 0。15：0。85（关闭DCQCN）
# name_list = ["[249]-09-08-11:50:05-fecmp-48", "[250]-09-08-11:52:33-fecmp-48", "[252]-09-08-12:52:53-fecmp-48", "[253]-09-08-13:58:07-fecmp-48", "[254]-09-08-13:59:06-fecmp-48", "[256]-09-08-20:15:05-caver-48"]


#####逐流：逐包 = 0。15：0。85（开启DCQCN，正确PFC）
# name_list = ["[319]-09-10-15:42:51-caver-48", "[318]-09-10-15:42:16-caver-48",  "[315]-09-10-15:41:03-caver-48", "[317]-09-10-15:41:47-caver-48", "[316]-09-10-15:41:30-caver-48", "[249]-09-08-11:50:05-fecmp-48", "[245]-09-06-22:29:56-fecmp-48", "[254]-09-08-13:59:06-fecmp-48"]

######全部逐包 load 48：
# name_list = ["[323]-09-10-22:09:54-caver-48","[324]-09-10-22:10:16-caver-48","[325]-09-10-22:10:36-caver-48","[326]-09-10-22:10:53-caver-48", "[327]-09-10-22:21:15-caver-48", "[328]-09-10-22:24:48-caver-48", "[320]-09-10-15:45:30-caver-48", "[321]-09-10-15:46:02-caver-48", "[322]-09-10-15:46:16-caver-48", "[280]-09-09-16:35:20-fecmp-48", "[281]-09-09-16:35:59-fecmp-48","[254]-09-08-13:59:06-fecmp-48"]
######全部逐包 load 80:
# name_list = ["[344]-09-12-09:00:23-fecmp-80", "[341]-09-12-08:58:44-caver-80", "[343]-09-12-08:59:42-fecmp-80", "[342]-09-12-08:59:11-fecmp-80"]
######全部逐包 load 80 OS1 topo:
name_list = ["[353]-09-12-12:57:45-caver-80", "[354]-09-12-13:05:01-fecmp-80","[345]-09-12-09:40:26-caver-80", "[346]-09-12-09:42:10-greedy-80", "[349]-09-12-09:43:45-fecmp-80", "[350]-09-12-09:44:13-fecmp-80"]
###### 全部逐包 ununiform load 48
# name_list = ["[333]-09-10-23:26:29-caver-48", "[334]-09-10-23:27:57-fecmp-48", "[335]-09-10-23:28:21-fecmp-48", "[336]-09-10-23:28:47-fecmp-48"]

output_dir = "cdf_plots"
if not os.path.exists(output_dir):
    os.makedirs(output_dir, exist_ok=True)

folder = "/home/denghaotian/research/Out_of_Order/ns-allinone-3.19/ns-3.19/mix/output"

# for name in name_list:
#     fct_path = folder + f"/{name}/{name}_out_fct.txt"
#     config_path = folder + f"/{name}/config.txt"
#     flow_LB_mode, packet_LB_mode = get_LB_mode(config_path)
#     flow_level_ratio = 0.15 ###这个与/traffic_gen/traffic_gen.py 中的134行一致
#     load = int(name.split("-")[-1])
#     time_start = int(2.000 * 1e9)  # 起始时间（纳秒）
#     time_end = int(2.003 * 1e9)      # 结束时间（纳秒）


#     flow_avg_slowdown, packet_avg_slowdown, total_avg_slowdown = read_fct_slowdowns(fct_path, time_start, time_end)
#     print(f"Flow LB Mode: {LB_mode[flow_LB_mode]}, Packet LB Mode: {LB_mode[packet_LB_mode]}")
#     print(f"Flow Average Slowdown: {flow_avg_slowdown}, Packet Average Slowdown: {packet_avg_slowdown}, Total Average Slowdown: {total_avg_slowdown}")



for name in name_list:
    fct_path = folder + f"/{name}/{name}_out_fct.txt"
    config_path = folder + f"/{name}/config.txt"
    flow_LB_mode, packet_LB_mode = get_LB_mode(config_path)
    flow_level_ratio = 0.15 ###这个与/traffic_gen/traffic_gen.py 中的134行一致
    load = int(name.split("-")[-1])
    time_start = int(2.000 * 1e9)  # 起始时间（纳秒）
    time_end = int(3.003 * 1e9)      # 结束时间（纳秒）

    (flow_avg_slowdown, packet_avg_slowdown, total_avg_slowdown, 
     flow_count, packet_count, total_count,
     flow_avg_fct, packet_avg_fct, total_avg_fct,
     flow_slowdowns, packet_slowdowns, total_slowdowns,
     flow_fcts, packet_fcts, total_fcts) = read_fct_slowdowns(fct_path, time_start, time_end)
    
    print(f"\n=== {name} ===")
    print(f"Flow LB Mode: {LB_mode[flow_LB_mode]}, Packet LB Mode: {LB_mode[packet_LB_mode]}")
    print(f"Flow Count: {flow_count}, Packet Count: {packet_count}, Total Count: {total_count}")
    print(f"Flow Average Slowdown: {flow_avg_slowdown:.3f}, Packet Average Slowdown: {packet_avg_slowdown:.3f}, Total Average Slowdown: {total_avg_slowdown:.3f}")
    print(f"Flow Average FCT: {flow_avg_fct:.2f}μs, Packet Average FCT: {packet_avg_fct:.2f}μs, Total Average FCT: {total_avg_fct:.2f}μs")
    
    # 绘制 FCT Slowdown CDF
    if len(flow_slowdowns) > 0:
        plot_cdf(flow_slowdowns, 
                f'Flow FCT Slowdown CDF - {name}\n{LB_mode[flow_LB_mode]}', 
                'FCT Slowdown', 
                f'{output_dir}/{name}_flow_slowdown_cdf.png', 
                'blue')
    if len(packet_slowdowns) > 0:
        plot_cdf(packet_slowdowns, 
                f'Packet FCT Slowdown CDF - {name}\n{LB_mode[packet_LB_mode]}', 
                'FCT Slowdown', 
                f'{output_dir}/{name}_packet_slowdown_cdf.png', 
                'red')
    
    if len(total_slowdowns) > 0:
        plot_cdf(total_slowdowns, 
                f'Total FCT Slowdown CDF - {name}\nFlow:{LB_mode[flow_LB_mode]}, Packet:{LB_mode[packet_LB_mode]}', 
                'FCT Slowdown', 
                f'{output_dir}/{name}_total_slowdown_cdf.png', 
                'green')
    
    # 绘制 FCT 绝对值 CDF
    if len(flow_fcts) > 0:
        plot_cdf(flow_fcts, 
                f'Flow FCT CDF - {name}\n{LB_mode[flow_LB_mode]}', 
                'FCT (μs)', 
                f'{output_dir}/{name}_flow_fct_cdf.png', 
                'blue')
    
    if len(packet_fcts) > 0:
        plot_cdf(packet_fcts, 
                f'Packet FCT CDF - {name}\n{LB_mode[packet_LB_mode]}', 
                'FCT (μs)', 
                f'{output_dir}/{name}_packet_fct_cdf.png', 
                'red')
    
    if len(total_fcts) > 0:
        plot_cdf(total_fcts, 
                f'Total FCT CDF - {name}\nFlow:{LB_mode[flow_LB_mode]}, Packet:{LB_mode[packet_LB_mode]}', 
                'FCT (μs)', 
                f'{output_dir}/{name}_total_fct_cdf.png', 
                'green')

print(f"\nAll CDF plots have been saved to: {output_dir}")