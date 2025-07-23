import subprocess

def read_fct_slowdowns(file_path, time_start, time_end):
    """
    读取符合时间范围要求的流完成时间 (FCT) slowdown，并计算平均值。

    :param file_path: 文件路径
    :param time_start: 起始时间（纳秒）
    :param time_end: 结束时间（纳秒）
    :return: 平均 slowdown 和所有 slowdown 的列表
    """
    slowdown_data = []

    try:
        with open(file_path, 'r') as file:
            for line in file:
                fields = line.split()
                if len(fields) < 8:
                    continue

                start_time = int(fields[5])
                duration = int(fields[6])
                ideal_duration = int(fields[7])

                if start_time > time_start and start_time + duration < time_end:
                    slowdown = duration / ideal_duration
                    slowdown_data.append(max(slowdown, 1.0))

        # 计算平均值
        if slowdown_data:
            avg_slowdown = sum(slowdown_data) / len(slowdown_data)
        else:
            avg_slowdown = 0.0  # 如果没有数据，返回 0.0

        return avg_slowdown, slowdown_data
    except IOError as e:
        print("Error reading file:", e)
        return 0.0, []


file_path = "/home/denghaotian/research/Out_of_Order/ns-allinone-3.19/ns-3.19/mix/output/[118]-07-23-22:20:26-fecmp-70/[118]-07-23-22:20:26-fecmp-70_out_fct.txt"
