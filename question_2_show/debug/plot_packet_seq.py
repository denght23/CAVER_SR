import re
import matplotlib.pyplot as plt

def parse_log(filename):
    new_snd_nxt_list = []
    sr_nack_list = []

    with open(filename, "r") as f:
        for line in f:
            if line.startswith("SR_GetNxtPacket:"):
                match = re.search(r"new_snd_nxt=(\d+)", line)
                if match:
                    new_snd_nxt_list.append(int(match.group(1)))
            elif line.startswith("SR_ReceiveACK BEFORE:"):
                match = re.search(r"srNack=(\d+)", line)
                if match:
                    sr_nack_list.append(int(match.group(1)))

    return new_snd_nxt_list, sr_nack_list


def plot_lists(new_snd_nxt_list, sr_nack_list):
    plt.figure(figsize=(10, 8))

    plt.subplot(2, 1, 1)
    plt.plot(range(len(new_snd_nxt_list)), new_snd_nxt_list, label="packet_seq=", marker="o")
    plt.xlabel("Index (event order)")
    plt.ylabel("new_snd_nxt")
    plt.title("SR_GetNxtPacket")
    plt.legend()
    plt.grid(True)

    plt.subplot(2, 1, 2)
    plt.plot(range(len(sr_nack_list)), sr_nack_list, label="srNack", marker="x", color="orange")
    plt.xlabel("Index (event order)")
    plt.ylabel("srNack")
    plt.title("SR_ReceiveACK")
    plt.legend()
    plt.grid(True)

    # plt.xlabel("Index (event order)")
    # plt.ylabel("Value")
    # plt.title("SR_GetNxtPacket vs SR_ReceiveACK")
    # plt.legend()
    # plt.grid(True)
    plt.tight_layout()
    plt.savefig("output.png")


if __name__ == "__main__":
    # 日志文件名
    filename = "/home/denghaotian/research/Out_of_Order/ns-allinone-3.19/ns-3.19/mix/output/[149]-09-03-13:12:45-fecmp-66/config.log"

    new_snd_nxt_list, sr_nack_list = parse_log(filename)

    # print("new_snd_nxt_list:", new_snd_nxt_list)
    # print("sr_nack_list:", sr_nack_list)

    plot_lists(new_snd_nxt_list, sr_nack_list)
