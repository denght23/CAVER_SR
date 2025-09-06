

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
    读取符合时间范围要求的流完成时间 (FCT) slowdown，并计算平均值。

    :param file_path: 文件路径
    :param time_start: 起始时间（纳秒）
    :param time_end: 结束时间（纳秒）
    :return: flow_avg_slowdown, packet_avg_slowdown
    """
    flow_slowdown_data = []
    packet_slowdown_data = []
    total_slowdown_data = []

    try:
        with open(file_path, 'r') as file:
            for line in file:
                fields = line.split()
                if len(fields) < 8:
                    continue

                start_time = int(fields[5])
                duration = int(fields[6])
                ideal_duration = int(fields[7])
                is_flow = int(fields[8])  # 假设第9列是流量类型，0表示逐流，1表示逐包
                if start_time > time_start and start_time + duration < time_end:
                    slowdown = duration / ideal_duration
                    if is_flow == 0:
                        flow_slowdown_data.append(max(slowdown, 1.0))
                    else:
                        packet_slowdown_data.append(max(slowdown, 1.0))
                    total_slowdown_data.append(max(slowdown, 1.0))

        # 计算平均值
        if flow_slowdown_data:
            flow_avg_slowdown = sum(flow_slowdown_data) / len(flow_slowdown_data)
        else:
            flow_avg_slowdown = 0.0  # 如果没有数据，返回 0.0

        if packet_slowdown_data:
            packet_avg_slowdown = sum(packet_slowdown_data) / len(packet_slowdown_data)
        else:
            packet_avg_slowdown = 0.0  # 如果没有数据，返回 0.0
        if total_slowdown_data:
            total_avg_slowdown = sum(total_slowdown_data) / len(total_slowdown_data)
        else:
            total_avg_slowdown = 0.0

        return flow_avg_slowdown, packet_avg_slowdown, total_avg_slowdown
    
    except IOError as e:
        print("Error reading file:", e)
        return 0.0, 0.0

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
name_list = ["[172]-09-03-20:28:11-fecmp-48", "[173]-09-03-20:28:21-fecmp-48", "[174]-09-03-20:28:31-caver-48", "[175]-09-03-20:28:41-fecmp-48", "[176]-09-03-20:28:51-caver-48", "[177]-09-03-20:35:25-fecmp-48", "[178]-09-03-20:45:48-fecmp-48"]
folder = "/home/denghaotian/research/Out_of_Order/ns-allinone-3.19/ns-3.19/mix/output"

for name in name_list:
    fct_path = folder + f"/{name}/{name}_out_fct.txt"
    config_path = folder + f"/{name}/config.txt"
    flow_LB_mode, packet_LB_mode = get_LB_mode(config_path)
    flow_level_ratio = 0.7 ###这个与/traffic_gen/traffic_gen.py 中的134行一致
    load = int(name.split("-")[-1])
    time_start = int(2.000 * 1e9)  # 起始时间（纳秒）
    time_end = int(2.003 * 1e9)      # 结束时间（纳秒）


    flow_avg_slowdown, packet_avg_slowdown, total_avg_slowdown = read_fct_slowdowns(fct_path, time_start, time_end)
    print(f"Flow LB Mode: {LB_mode[flow_LB_mode]}, Packet LB Mode: {LB_mode[packet_LB_mode]}")
    print(f"Flow Average Slowdown: {flow_avg_slowdown}, Packet Average Slowdown: {packet_avg_slowdown}, Total Average Slowdown: {total_avg_slowdown}")
