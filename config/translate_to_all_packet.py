# 修改 txt 文件中从第二行开始的最后一列为 1

def modify_file(input_file, output_file):
    with open(input_file, "r") as f:
        lines = f.readlines()

    new_lines = []
    for i, line in enumerate(lines):
        if i == 0:  # 第一行不变
            new_lines.append(line)
        else:
            parts = line.strip().split()
            parts[-1] = "1"   # 修改最后一列
            new_lines.append(" ".join(parts) + "\n")

    with open(output_file, "w") as f:
        f.writelines(new_lines)

def write_range_line(k, output_file):
    with open(output_file, "w") as f:
        # pass
        line = " ".join(str(i) for i in range(k + 1))
        f.write(line + "\n")

if __name__ == "__main__":
    input_path = "L_24.00_CDF_AliStorage2019_N_256_T_30ms_B_100_flow.txt"
    output_path = "L_24.00_CDF_AliStorage2019_N_256_T_30ms_B_100_flow_all_packet.txt"
    SR_output_path = "L_24.00_CDF_AliStorage2019_N_256_T_30ms_B_100_flow_all_packet_SR_host.txt"
    modify_file(input_path, output_path)
    write_range_line(255, SR_output_path)
