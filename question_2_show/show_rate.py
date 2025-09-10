import pandas as pd
import os
import matplotlib.pyplot as plt

def load_rate_trace(rate_file):
    """读取速率变化文件"""
    df = pd.read_csv(
        rate_file,
        comment="#",
        delim_whitespace=True,
        names=["flow_id", "rate_bps", "target_rate_bps", "timestamp", "reason"]
    )
    return df
def load_flow_info(flow_file):
    """读取流信息文件"""
    df = pd.read_csv(
        flow_file,
        comment="#",
        delim_whitespace=True,
        names=[
            "flow_id", "src_id", "dst_id", "sport", "dport",
            "original_size", "actual_data_bytes", "actual_total_bytes",
            "packet_count", "start_time", "end_time", "duration"
        ]
    )
    return df

def compute_avg_rate(rate_file, flow_file):
    """计算每个流的平均速率"""
    rate_df = load_rate_trace(rate_file)
    flow_df = load_flow_info(flow_file)

    avg_rates = {}
    for flow_id in flow_df["flow_id"].unique():
        # 获取该流的开始/结束时间
        flow_info = flow_df[flow_df["flow_id"] == flow_id].iloc[0]
        start_time, end_time = flow_info["start_time"], flow_info["end_time"]

        # 取该流的速率变化
        flow_rates = rate_df[rate_df["flow_id"] == flow_id]
        if flow_rates.empty:
            continue

        # 按速率区间计算时间加权平均
        total_time, weighted_sum = 0, 0
        times = list(flow_rates["timestamp"]) + [end_time]
        rates = list(flow_rates["rate_bps"])

        for i in range(len(rates)):
            t1, t2 = times[i], times[i+1]
            duration = t2 - t1
            weighted_sum += rates[i] * duration
            total_time += duration

        avg_rates[flow_id] = weighted_sum / total_time if total_time > 0 else 0

    return avg_rates

def get_flow_id_direct(src_id, dst_id, sport, dport, flow_file):
    """
    直接从文件查找flow_id（不使用缓存查找表）
    
    Args:
        src_id: 源节点ID
        dst_id: 目标节点ID
        sport: 源端口
        dport: 目标端口
        flow_file: 流信息文件路径
    
    Returns:
        int: flow_id，如果找不到则返回None
    """
    df = pd.read_csv(
        flow_file,
        comment="#",
        delim_whitespace=True,
        names=[
            "flow_id", "src_id", "dst_id", "sport", "dport",
            "original_size", "actual_data_bytes", "actual_total_bytes",
            "packet_count", "start_time", "end_time", "duration"
        ]
    )
    
    # 查找匹配的行
    result = df[(df["src_id"] == src_id) & 
                (df["dst_id"] == dst_id) & 
                (df["sport"] == sport) & 
                (df["dport"] == dport)]
    
    if not result.empty:
        return result.iloc[0]["flow_id"]
    else:
        return None

def get_flow_rate_trace(flow_id, rate_file, flow_file):
    """获取单个流的速率随时间变化情况"""
    rate_df = load_rate_trace(rate_file)
    flow_df = load_flow_info(flow_file)

    flow_info = flow_df[flow_df["flow_id"] == flow_id].iloc[0]
    end_time = flow_info["end_time"]

    flow_rates = rate_df[rate_df["flow_id"] == flow_id].copy()
    if flow_rates.empty:
        return []

    # 添加最后一个点，保持速率到end_time
    last_rate = flow_rates.iloc[-1]["rate_bps"]
    last_target_rate = flow_rates.iloc[-1]["target_rate_bps"]
    
    # 返回包含timestamp, rate_bps, target_rate_bps的数据
    flow_rates = flow_rates[["timestamp", "rate_bps", "target_rate_bps"]].values.tolist()
    flow_rates.append([end_time, last_rate, last_target_rate])

    return flow_rates

def plot_flow_rate(name, flow_id, rate_file, flow_file):
    """绘制某个流的速率-时间图"""
    trace = get_flow_rate_trace(flow_id, rate_file, flow_file)
    if not trace:
        print(f"No rate data for flow {flow_id}")
        return

    times, rates, target_rates = zip(*trace)
    
    # 绘制两条线
    plt.step(times, rates, where="post", label=f"Flow {flow_id} - Actual Rate", linewidth=2)
    plt.step(times, target_rates, where="post", label=f"Flow {flow_id} - Target Rate", 
             linewidth=2, linestyle='--', alpha=0.8)
    
    plt.xlabel("Time (ns)")
    plt.ylabel("Rate (bps)")
    plt.title(f"Rate-Time Curve of Flow {flow_id}")
    
    plt.xlim(2.02*1e9, 2.04*1e9)
    
    # 格式化y轴显示
    plt.ticklabel_format(style='scientific', axis='y', scilimits=(0,0))
    plt.ticklabel_format(style='scientific', axis='x', scilimits=(0,0))
    
    plt.legend()
    plt.grid(True, alpha=0.3)
    output_dir = "cdf_rate"
    os.makedirs(output_dir, exist_ok=True)
    plt.savefig(os.path.join(output_dir, f"{name}_flow_{flow_id}_rate_time.png"), dpi=300, bbox_inches='tight')
    plt.close()


name = "[249]-09-08-11:50:05-fecmp-48"
rate_file = f"../mix/output/{name}/{name}_out_rate_change.txt"
flow_file = f"../mix/output/{name}/{name}_out_qp_stat.txt"

####两种方式决定看哪个流
# flow_id = 50
flow_info = [51, 151, 11757, 1773]  # flow_id, src_id, dst_id, sport, dport
flow_id = get_flow_id_direct(flow_info[0], flow_info[1], flow_info[2], flow_info[3], flow_file)
print(flow_id)


# 计算平均速率
# avg = compute_avg_rate(rate_file, flow_file)
# print(avg)

# 获取某个流的速率变化
trace = get_flow_rate_trace(flow_id, rate_file, flow_file)
print(trace[:10])  # 前10个点

# 绘制图像
plot_flow_rate(name, flow_id, rate_file, flow_file)
