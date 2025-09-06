import random

def generate_flows(num_flows, output_file):
    flows = []
    for _ in range(num_flows):
        src = random.randint(1, 254)
        dst = random.randint(1, 254)
        while dst == src:  # 避免源和目的相同
            dst = random.randint(1, 254)
        flows.append(f"{src} {dst} 3 2000000 2.000000061 0")

    with open(output_file, "w") as f:
        # 第一行：流的数量
        f.write(str(num_flows + 1) + "\n")
        # 写入流
        for line in flows:
            f.write(line + "\n")
        # 附加最后一行
        f.write("0 255 3 2000000 2.000000161 1\n")


if __name__ == "__main__":
    # 例如生成 10 个流
    generate_flows(50, "my_flow_2.txt")
    print("my_flow_2.txt 已生成")
