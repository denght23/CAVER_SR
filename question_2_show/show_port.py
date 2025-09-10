import re
import pandas as pd
import numpy as np
import random

def parse_log(filename):
    """
    解析 log 文件，返回 DataFrame：
    列包括 [time, switch, host, port, LQ, LCE, R, update_time, valid]
    """
    data = []
    with open(filename, "r") as f:
        for line in f:
            if "[PERHOP_CHOICE]" not in line:
                continue

            # 提取公共头部字段
            header_match = re.search(r"T:(\d+) S:(\d+) H:(\d+)", line)
            if not header_match:
                continue
            now_us, switch_id, host_id = map(int, header_match.groups())

            # 提取端口字段
            port_entries = re.findall(
                r"P:(\d+)\|LQ:(\d+)\|LCE:(\d+)\|R:(\d+)\|T:(\d+)\|V:(\d)",
                line
            )
            for entry in port_entries:
                port, lq, lce, rce, utime, valid = map(int, entry)
                data.append({
                    "time": now_us,
                    "switch": switch_id,
                    "host": host_id,
                    "port": port,
                    "LQ": lq,
                    "LCE": lce,
                    "R": rce,
                    "update_time": utime,
                    "valid": valid
                })

    return pd.DataFrame(data)


def choose_random_switch_host(df):
    """随机选择一个 (switch, host) 对"""
    pairs = df.groupby(["switch", "host"]).size().index.tolist()
    return random.choice(pairs)


def analyze_switch_host(df, switch_id, host_id, window=10):
    """
    在指定 switch + host 上进行分析
    """

    sub = df[(df["switch"] == switch_id) & (df["host"] == host_id)]
    if sub.empty:
        print(f"No data for switch {switch_id}, host {host_id}")
        return

    results = {}

    # (1) 平均 update_time
    valid_sub = sub[sub["valid"] == 1]
    results["avg_update_time"] = valid_sub["update_time"].mean()

    # (2) 最优端口 (LQ+R 最小) 的滑动窗口更新频率
    def best_port(group):
        g = group[group["valid"] == 1]
        if g.empty:
            return None
        return g.loc[(g["LQ"] + g["R"]).idxmin(), "port"]

    best_ports = sub.groupby("time").apply(best_port)
    best_ports = best_ports.dropna().astype(int).reset_index()

    # 滑动窗口变化统计
    changes = 0
    for i in range(1, len(best_ports)):
        if best_ports.loc[i, 0] != best_ports.loc[i-1, 0]:
            changes += 1
    results["best_port_changes"] = changes
    results["best_port_change_rate"] = changes / len(best_ports) if len(best_ports) > 0 else 0

    # (3) LQ+R vs LQ 最优端口一致性
    def best_port_LQ(group):
        g = group[group["valid"] == 1]
        if g.empty:
            return None
        return g.loc[g["LQ"].idxmin(), "port"]

    compare = []
    diff_values = []
    for t, g in sub.groupby("time"):
        g = g[g["valid"] == 1]
        if g.empty:
            continue
        best_lr = g.loc[(g["LQ"] + g["R"]).idxmin()]
        best_lq = g.loc[g["LQ"].idxmin()]

        compare.append(best_lr["port"] == best_lq["port"])
        if best_lr["port"] != best_lq["port"]:
            diff_values.append(best_lr["LQ"] + best_lr["R"] - (best_lq["LQ"] + best_lq["R"]))

    results["same_port_prob"] = np.mean(compare) if compare else None
    results["diff_distribution"] = diff_values

    return results


if __name__ == "__main__":
    name = "[282]-09-09-22:15:16-caver-48"
    log_file = f"../mix/output/{name}/config.log"
    df = parse_log(log_file)

    switch_id, host_id = choose_random_switch_host(df)
    print(f"Analyzing switch {switch_id}, host {host_id}")

    results = analyze_switch_host(df, switch_id, host_id)
    for k, v in results.items():
        if k == "diff_distribution":
            print(f"{k}: count={len(v)}, mean={np.mean(v) if v else None}")
        else:
            print(f"{k}: {v}")
