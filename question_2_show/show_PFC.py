import pandas as pd
import os

def load_pfc_data(pfc_file):
    """读取PFC文件"""
    df = pd.read_csv(
        pfc_file,
        comment="#",
        delim_whitespace=True,
        names=["timestamp", "sender_node", "receiver_node", "qIndex", "type", "reason"]
    )
    return df

def count_pause_events(pfc_file):
    """统计pause事件的数量"""
    df = load_pfc_data(pfc_file)
    
    # 统计总的pause事件数量 (type = 1)
    total_pause = len(df[df["type"] == 1])
    
    # 统计总的resume事件数量 (type = 0)
    total_resume = len(df[df["type"] == 0])
    
    print(f"总的PAUSE事件数量: {total_pause}")
    print(f"总的RESUME事件数量: {total_resume}")
    print(f"总事件数量: {len(df)}")
    
    return total_pause, total_resume

def detailed_pause_statistics(pfc_file):
    """详细的pause统计信息"""
    df = load_pfc_data(pfc_file)
    
    print("=== PFC事件详细统计 ===")
    
    # 总体统计
    total_pause = len(df[df["type"] == 1])
    total_resume = len(df[df["type"] == 0])
    print(f"总PAUSE事件: {total_pause}")
    print(f"总RESUME事件: {total_resume}")
    
    # 按节点对统计
    print("\n=== 按节点对统计PAUSE事件 ===")
    pause_df = df[df["type"] == 1]
    node_pair_stats = pause_df.groupby(["sender_node", "receiver_node"]).size().reset_index(name="pause_count")
    node_pair_stats = node_pair_stats.sort_values("pause_count", ascending=False)
    
    print("节点对 (发送者 -> 接收者) 的PAUSE次数:")
    for _, row in node_pair_stats.head(10).iterrows():  # 显示前10个
        print(f"  {row['sender_node']} -> {row['receiver_node']}: {row['pause_count']} 次")
    
    
    # 按发送节点统计
    print(f"\n=== 按发送节点统计PAUSE事件 ===")
    sender_stats = pause_df.groupby("sender_node").size().reset_index(name="pause_count")
    sender_stats = sender_stats.sort_values("pause_count", ascending=False)
    
    print("各发送节点的PAUSE次数 (前10个):")
    for _, row in sender_stats.head(10).iterrows():
        print(f"  节点 {row['sender_node']}: {row['pause_count']} 次")
    
    # 按接收节点统计
    print(f"\n=== 按接收节点统计PAUSE事件 ===")
    receiver_stats = pause_df.groupby("receiver_node").size().reset_index(name="pause_count")
    receiver_stats = receiver_stats.sort_values("pause_count", ascending=False)
    
    print("各接收节点的PAUSE次数 (前10个):")
    for _, row in receiver_stats.head(10).iterrows():
        print(f"  节点 {row['receiver_node']}: {row['pause_count']} 次")
    
    return {
        "total_pause": total_pause,
        "total_resume": total_resume,
        "node_pair_stats": node_pair_stats,
        "sender_stats": sender_stats,
        "receiver_stats": receiver_stats
    }

def analyze_pause_duration(pfc_file):
    """分析pause持续时间"""
    df = load_pfc_data(pfc_file)
    
    # 按节点对和队列分组，计算pause-resume对
    grouped = df.groupby(["sender_node", "receiver_node", "qIndex"])
    
    pause_durations = []
    
    for name, group in grouped:
        group = group.sort_values("timestamp")
        
        i = 0
        while i < len(group):
            if group.iloc[i]["type"] == 1:  # PAUSE
                pause_time = group.iloc[i]["timestamp"]
                # 寻找对应的RESUME
                j = i + 1
                while j < len(group) and group.iloc[j]["type"] != 0:
                    j += 1
                
                if j < len(group):  # 找到了对应的RESUME
                    resume_time = group.iloc[j]["timestamp"]
                    duration = resume_time - pause_time
                    pause_durations.append({
                        "sender": name[0],
                        "receiver": name[1], 
                        "queue": name[2],
                        "pause_time": pause_time,
                        "resume_time": resume_time,
                        "duration": duration
                    })
                    i = j + 1
                else:
                    i += 1
            else:
                i += 1
    
    if pause_durations:
        duration_df = pd.DataFrame(pause_durations)
        print(f"\n=== PAUSE持续时间分析 ===")
        print(f"完整的PAUSE-RESUME对数量: {len(duration_df)}")
        print(f"平均持续时间: {duration_df['duration'].mean():.2f} ns")
        print(f"最短持续时间: {duration_df['duration'].min()} ns")
        print(f"最长持续时间: {duration_df['duration'].max()} ns")
        print(f"持续时间中位数: {duration_df['duration'].median():.2f} ns")
        
        return duration_df
    else:
        print("没有找到完整的PAUSE-RESUME对")
        return pd.DataFrame()

# 使用示例
if __name__ == "__main__":
    # 设置文件路径
    name = "[254]-09-08-13:59:06-fecmp-48"
    pfc_file = f"../mix/output/{name}/{name}_out_pfc.txt"
    
    # 检查文件是否存在
    if not os.path.exists(pfc_file):
        print(f"文件不存在: {pfc_file}")
    else:
        print(f"分析文件: {pfc_file}")
        
        # 简单统计
        pause_count, resume_count = count_pause_events(pfc_file)
        
        print("\n" + "="*50)
        
        # 详细统计
        stats = detailed_pause_statistics(pfc_file)
        
        print("\n" + "="*50)
        
        # 持续时间分析
        duration_df = analyze_pause_duration(pfc_file)