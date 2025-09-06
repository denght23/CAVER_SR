#include "switch-mmu.h"

#include <fstream>
#include <iostream>

#include "ns3/assert.h"
#include "ns3/boolean.h"
#include "ns3/double.h"
#include "ns3/global-value.h"
#include "ns3/log.h"
#include "ns3/object-vector.h"
#include "ns3/packet.h"
#include "ns3/random-variable.h"
#include "ns3/simulator.h"
#include "ns3/uinteger.h"

NS_LOG_COMPONENT_DEFINE("SwitchMmu");

namespace ns3 {

TypeId SwitchMmu::GetTypeId(void) {
    static TypeId tid = TypeId("ns3::SwitchMmu")
                            .SetParent<Object>()
                            .AddConstructor<SwitchMmu>();
    return tid;
}

SwitchMmu::SwitchMmu(void) {
    // HPCC 版本的初始化
    buffer_size = 12 * 1024 * 1024;  // 12MB buffer
    reserve = 4 * 1024;              // 4KB reserved
    resume_offset = 3 * 1024;        // 3KB resume offset

    // 初始化 pfc_a_shift 数组
    for (uint32_t i = 0; i < pCnt; i++) {
        pfc_a_shift[i] = 3;  // 默认值，可配置
    }

    // 初始化运行时状态
    shared_used_bytes = 0;
    total_hdrm = 0;
    total_rsrv = 0;
    
    // 清零所有数组
    memset(hdrm_bytes, 0, sizeof(hdrm_bytes));
    memset(ingress_bytes, 0, sizeof(ingress_bytes));
    memset(paused, 0, sizeof(paused));
    memset(egress_bytes, 0, sizeof(egress_bytes));
    memset(headroom, 0, sizeof(headroom));
    memset(kmin, 0, sizeof(kmin));
    memset(kmax, 0, sizeof(kmax));
    memset(pmax, 0, sizeof(pmax));
    
    // 初始化兼容性变量
    memset(m_pause_remote, 0, sizeof(m_pause_remote));
    
    m_PFCenabled = true;

    // 初始化 PFC 死锁检测变量
    memset(pfcPauseStartTime, 0, sizeof(pfcPauseStartTime));
    memset(pfcDeadlockCheckCount, 0, sizeof(pfcDeadlockCheckCount));
}

// ==================== HPCC 版本的缓冲区管理接口 ====================

bool SwitchMmu::CheckIngressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize) {
    // HPCC 版本的入口准入控制逻辑
    if (psize + hdrm_bytes[port][qIndex] > headroom[port] && 
        psize + GetSharedUsed(port, qIndex) > GetPfcThreshold(port)) {
        if (m_drop_log) {
            bool peer_paused = m_pause_remote[port][qIndex];
            std::cout << "[MMU-INGRESS-DROP] time=" << Simulator::Now().GetMicroSeconds() 
                      << "us port=" << port << " qIndex=" << qIndex 
                      << " psize=" << psize 
                      << " current_hdrm=" << hdrm_bytes[port][qIndex]
                      << " current_shared=" << GetSharedUsed(port, qIndex)
                      << " headroom=" << headroom[port]
                      << " pfc_threshold=" << GetPfcThreshold(port)
                      << " peer_paused=" << (peer_paused ? "YES" : "NO")
                      << std::endl;
        }
        return false;
    }
    return true;
}

bool SwitchMmu::CheckEgressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize) {
    // HPCC 版本的出口准入控制逻辑（简化版本）
    return true;
}

void SwitchMmu::UpdateIngressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize) {
    // HPCC 版本的入口缓冲区更新逻辑
    if (m_mmuLog) {
        std::cout << "[MMU-INGRESS-UPDATE-START] time=" << Simulator::Now().GetMicroSeconds() 
                  << "us port=" << port << " qIndex=" << qIndex << " psize=" << psize
                  << " current_ingress=" << ingress_bytes[port][qIndex]
                  << " current_hdrm=" << hdrm_bytes[port][qIndex]
                  << " current_shared=" << shared_used_bytes
                  << " reserve=" << reserve << std::endl;
    }
    uint32_t new_bytes = ingress_bytes[port][qIndex] + psize;
    if (new_bytes <= reserve) {
        // 在保留区域内
        ingress_bytes[port][qIndex] += psize;
        if (m_mmuLog) {
            std::cout << "[MMU-INGRESS-RESERVE] time=" << Simulator::Now().GetMicroSeconds() 
                      << "us using reserved buffer, new_ingress=" << ingress_bytes[port][qIndex] << std::endl;
        }
    } else {
        uint32_t thresh = GetPfcThreshold(port);
        if (new_bytes - reserve > thresh) {
            // 超过阈值，使用 headroom
            hdrm_bytes[port][qIndex] += psize;
            if (m_mmuLog) {
                std::cout << "[MMU-INGRESS-HEADROOM] time=" << Simulator::Now().GetMicroSeconds() 
                          << "us using headroom, threshold=" << thresh
                          << " new_hdrm=" << hdrm_bytes[port][qIndex] << std::endl;
            }
        } else {
            // 使用共享缓冲区
            ingress_bytes[port][qIndex] += psize;
            shared_used_bytes += std::min(psize, new_bytes - reserve);
            if (m_mmuLog) {
                uint32_t shared_increase = std::min(psize, new_bytes - reserve);
                std::cout << "[MMU-INGRESS-SHARED] time=" << Simulator::Now().GetMicroSeconds() 
                          << "us using shared buffer, shared_increase=" << shared_increase
                          << " new_shared_used=" << shared_used_bytes
                          << " new_ingress=" << ingress_bytes[port][qIndex] << std::endl;
            }
        }
    }
}

void SwitchMmu::UpdateEgressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize) {
    // HPCC 版本的出口缓冲区更新逻辑
    egress_bytes[port][qIndex] += psize;
}

void SwitchMmu::RemoveFromIngressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize) {
    // HPCC 版本的入口缓冲区释放逻辑
    uint32_t from_hdrm = std::min(hdrm_bytes[port][qIndex], psize);
    uint32_t from_shared = std::min(psize - from_hdrm, 
                                   ingress_bytes[port][qIndex] > reserve ? 
                                   ingress_bytes[port][qIndex] - reserve : 0);
    
    hdrm_bytes[port][qIndex] -= from_hdrm;
    ingress_bytes[port][qIndex] -= (psize - from_hdrm);
    shared_used_bytes = (shared_used_bytes > from_shared) ? shared_used_bytes - from_shared : 0;
}

void SwitchMmu::RemoveFromEgressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize) {
    // HPCC 版本的出口缓冲区释放逻辑
    egress_bytes[port][qIndex] = (egress_bytes[port][qIndex] > psize) ? 
                                 egress_bytes[port][qIndex] - psize : 0;
}

// ==================== HPCC 版本的 PFC 接口 ====================

bool SwitchMmu::CheckShouldPause(uint32_t port, uint32_t qIndex) {
    // HPCC 版本的 PFC 暂停检查逻辑
    if (m_mmuLog) {
        std::cout << "[MMU-PFC-CHECK-PAUSE] time=" << Simulator::Now().GetMicroSeconds() 
                  << "us port=" << port << " qIndex=" << qIndex
                  << " already_paused=" << paused[port][qIndex]
                  << " hdrm_used=" << hdrm_bytes[port][qIndex]
                  << " shared_used=" << GetSharedUsed(port, qIndex)
                  << " pfc_threshold=" << GetPfcThreshold(port)
                  << " should_pause=" << (hdrm_bytes[port][qIndex] > 0 || GetSharedUsed(port, qIndex) >= GetPfcThreshold(port));
    }
    if (paused[port][qIndex]) return false;  // 已经暂停了
    
    // 检查是否需要暂停：headroom 使用或共享缓冲区超过阈值

    return (hdrm_bytes[port][qIndex] > 0 || 
            GetSharedUsed(port, qIndex) >= GetPfcThreshold(port));
}

bool SwitchMmu::CheckShouldResume(uint32_t port, uint32_t qIndex) {
    bool currently_paused = paused[port][qIndex];
    if (!currently_paused) {
        if (m_mmuLog) {
            std::cout << "[MMU-PFC-CHECK-RESUME] time=" << Simulator::Now().GetMicroSeconds() 
                      << "us port=" << port << " qIndex=" << qIndex
                      << " not_paused=true should_resume=false" << std::endl;
        }
        return false;
    }
    
    uint32_t hdrm_used = hdrm_bytes[port][qIndex];
    uint32_t shared_used = GetSharedUsed(port, qIndex);
    uint32_t pfc_thresh = GetPfcThreshold(port);
    
    bool should_resume = (hdrm_used == 0 && 
                         (shared_used == 0 || shared_used + resume_offset <= pfc_thresh));
    
    if (m_mmuLog) {
        std::cout << "[MMU-PFC-CHECK-RESUME] time=" << Simulator::Now().GetMicroSeconds() 
                  << "us port=" << port << " qIndex=" << qIndex
                  << " currently_paused=" << currently_paused
                  << " hdrm_used=" << hdrm_used
                  << " shared_used=" << shared_used
                  << " pfc_threshold=" << pfc_thresh
                  << " resume_offset=" << resume_offset
                  << " should_resume=" << should_resume << std::endl;
    }
    
    return should_resume;
}

void SwitchMmu::SetPause(uint32_t port, uint32_t qIndex) {
    // HPCC 版本的 PFC 暂停设置
    paused[port][qIndex] = 1;
    m_pause_remote[port][qIndex] = true;
    
    // 启动 PFC 死锁检测定时器
    StartPfcDeadlockTimer(port, qIndex);
    
    if (m_drop_log) {
        std::cout << "[PFC-PAUSE-SET] time=" << Simulator::Now().GetMicroSeconds()
                  << "us switch_id=" << node_id
                  << " port=" << port << " qIndex=" << qIndex
                  << " action=SET_PAUSE"
                  << " hdrm_used=" << hdrm_bytes[port][qIndex]
                  << " shared_used=" << GetSharedUsed(port, qIndex)
                  << " pfc_threshold=" << GetPfcThreshold(port) << std::endl;
    }
}

void SwitchMmu::SetResume(uint32_t port, uint32_t qIndex) {
    // HPCC 版本的 PFC 恢复设置
    paused[port][qIndex] = 0;
    m_pause_remote[port][qIndex] = false;
    
    // 停止 PFC 死锁检测定时器
    StopPfcDeadlockTimer(port, qIndex);
    
    if (m_drop_log) {
        uint64_t pause_duration = 0;
        if (pfcPauseStartTime[port][qIndex] > 0) {
            pause_duration = Simulator::Now().GetMicroSeconds() - pfcPauseStartTime[port][qIndex];
        }
        
        std::cout << "[PFC-RESUME-SET] time=" << Simulator::Now().GetMicroSeconds()
                  << "us switch_id=" << node_id
                  << " port=" << port << " qIndex=" << qIndex
                  << " action=SET_RESUME"
                  << " pause_duration=" << pause_duration << "us"
                  << " deadlock_checks=" << pfcDeadlockCheckCount[port][qIndex]
                  << " hdrm_used=" << hdrm_bytes[port][qIndex]
                  << " shared_used=" << GetSharedUsed(port, qIndex) << std::endl;
    }
}

// 启动 PFC 死锁检测定时器
void SwitchMmu::StartPfcDeadlockTimer(uint32_t port, uint32_t qIndex) {
    // 记录暂停开始时间
    pfcPauseStartTime[port][qIndex] = Simulator::Now().GetMicroSeconds();
    pfcDeadlockCheckCount[port][qIndex] = 0;
    
    // 取消之前的定时器（如果存在）
    Simulator::Cancel(pfcDeadlockTimer[port][qIndex]);
    
    // 启动新的定时器，每 1ms 触发一次
    pfcDeadlockTimer[port][qIndex] = Simulator::Schedule(
        MilliSeconds(1), 
        &SwitchMmu::PfcDeadlockCheck, 
        this, 
        port, 
        qIndex
    );
    
    if (m_drop_log) {
        std::cout << "[PFC-DEADLOCK-TIMER-START] time=" << Simulator::Now().GetMicroSeconds()
                  << "us switch_id=" << node_id
                  << " port=" << port << " qIndex=" << qIndex
                  << " timer_started=true" << std::endl;
    }
}

// 停止 PFC 死锁检测定时器
void SwitchMmu::StopPfcDeadlockTimer(uint32_t port, uint32_t qIndex) {
    // 取消定时器
    Simulator::Cancel(pfcDeadlockTimer[port][qIndex]);
    
    if (m_drop_log) {
        uint64_t total_pause_time = 0;
        if (pfcPauseStartTime[port][qIndex] > 0) {
            total_pause_time = Simulator::Now().GetMicroSeconds() - pfcPauseStartTime[port][qIndex];
        }
        
        std::cout << "[PFC-DEADLOCK-TIMER-STOP] time=" << Simulator::Now().GetMicroSeconds()
                  << "us switch_id=" << node_id
                  << " port=" << port << " qIndex=" << qIndex
                  << " timer_stopped=true"
                  << " total_pause_time=" << total_pause_time << "us"
                  << " total_checks=" << pfcDeadlockCheckCount[port][qIndex] << std::endl;
    }
    
    // 重置计数器
    pfcPauseStartTime[port][qIndex] = 0;
    pfcDeadlockCheckCount[port][qIndex] = 0;
}

// PFC 死锁检测函数
void SwitchMmu::PfcDeadlockCheck(uint32_t port, uint32_t qIndex) {
    // 检查是否仍处于暂停状态
    if (!paused[port][qIndex] || !m_pause_remote[port][qIndex]) {
        // 已经恢复，停止检测
        if (m_drop_log) {
            std::cout << "[PFC-DEADLOCK-CHECK-ENDED] time=" << Simulator::Now().GetMicroSeconds()
                      << "us switch_id=" << node_id
                      << " port=" << port << " qIndex=" << qIndex
                      << " reason=already_resumed" << std::endl;
        }
        return;
    }
    
    // 增加检测次数
    pfcDeadlockCheckCount[port][qIndex]++;
    
    // 计算暂停持续时间
    uint64_t pause_duration = Simulator::Now().GetMicroSeconds() - pfcPauseStartTime[port][qIndex];
    
    // 获取对端交换机 ID（这里需要根据实际拓扑结构来获取）
    uint32_t peer_switch_id = GetPeerSwitchId(port); // 需要实现这个函数
    
    if (m_drop_log) {
        std::cout << "[PFC-DEADLOCK-CHECK] time=" << Simulator::Now().GetMicroSeconds()
                  << "us local_switch=" << node_id
                  << " peer_switch=" << peer_switch_id
                  << " port=" << port << " qIndex=" << qIndex
                  << " pause_duration=" << pause_duration << "us"
                  << " check_count=" << pfcDeadlockCheckCount[port][qIndex]
                  << " local_hdrm=" << hdrm_bytes[port][qIndex]
                  << " local_shared=" << GetSharedUsed(port, qIndex)
                  << " local_pfc_threshold=" << GetPfcThreshold(port)
                  << " should_resume=" << (CheckShouldResume(port, qIndex) ? "YES" : "NO");
        
        // 如果暂停时间超过阈值，标记为可能的死锁
        if (pause_duration > 10000) { // 10ms
            std::cout << " POTENTIAL_DEADLOCK=true";
        }
        
        std::cout << std::endl;
    }
    
    // 继续下一次检测
    pfcDeadlockTimer[port][qIndex] = Simulator::Schedule(
        MilliSeconds(1), 
        &SwitchMmu::PfcDeadlockCheck, 
        this, 
        port, 
        qIndex
    );
}

// 获取对端交换机 ID 的辅助函数（需要根据实际拓扑实现）
uint32_t SwitchMmu::GetPeerSwitchId(uint32_t port) {
    // 方法1：使用 Settings::m_nodeInterfaceMap 获取对端节点ID
    if (Settings::m_nodeInterfaceMap.find(node_id) != Settings::m_nodeInterfaceMap.end()) {
        auto& interfaceMap = Settings::m_nodeInterfaceMap[node_id];
        if (interfaceMap.find(port) != interfaceMap.end()) {
            uint32_t peer_node_id = interfaceMap[port];
            
            if (m_drop_log) {
                std::cout << "[MMU-PEER-LOOKUP] time=" << Simulator::Now().GetMicroSeconds()
                          << "us local_switch=" << node_id
                          << " port=" << port
                          << " peer_node=" << peer_node_id << std::endl;
            }
            
            return peer_node_id;
        }
    }
    
    // 方法2：如果方法1失败，尝试通过 Settings::if2id 查找
    // 这需要我们有对应的 Node 指针，但在 MMU 中可能没有直接访问
    
    if (m_drop_log) {
        std::cout << "[MMU-PEER-LOOKUP-FAILED] time=" << Simulator::Now().GetMicroSeconds()
                  << "us local_switch=" << node_id
                  << " port=" << port
                  << " reason=port_not_found_in_interface_map" << std::endl;
    }
    
    return 999; // 未知对端
}



// ==================== 兼容性包装函数 ====================

void SwitchMmu::GetPauseClasses(uint32_t port, uint32_t qIndex, bool pClasses[]) {
    // 兼容原有代码的 PFC 暂停检查包装函数
    for (uint32_t i = 0; i < qCnt; i++) {
        pClasses[i] = CheckShouldPause(port, i);
    }
}

bool SwitchMmu::GetResumeClasses(uint32_t port, uint32_t qIndex) {
    // 兼容原有代码的 PFC 恢复检查包装函数
    return CheckShouldResume(port, qIndex);
}

void SwitchMmu::SetPause(uint32_t port, uint32_t qIndex, uint32_t pause_time) {
    // 兼容原有代码的带超时时间的 PFC 暂停设置
    SetPause(port, qIndex);
    Simulator::Cancel(resumeEvt[port][qIndex]);
    resumeEvt[port][qIndex] = Simulator::Schedule(MicroSeconds(pause_time), 
                                                  &SwitchMmu::SetResume, this, port, qIndex);
}

// ==================== HPCC 版本的配置接口 ====================

uint32_t SwitchMmu::GetPfcThreshold(uint32_t port) {
    // HPCC 版本的 PFC 阈值计算
    uint32_t threshold = (buffer_size - total_hdrm - total_rsrv - shared_used_bytes) >> pfc_a_shift[port];
    
    if (m_mmuLog) {
        std::cout << "[MMU-PFC-THRESHOLD] time=" << Simulator::Now().GetMicroSeconds() 
                  << "us port=" << port 
                  << " buffer_size=" << buffer_size
                  << " total_hdrm=" << total_hdrm
                  << " total_rsrv=" << total_rsrv
                  << " shared_used=" << shared_used_bytes
                  << " pfc_a_shift=" << pfc_a_shift[port]
                  << " threshold=" << threshold << std::endl;
    }
    
    return threshold;
}

uint32_t SwitchMmu::GetSharedUsed(uint32_t port, uint32_t qIndex) {
    // HPCC 版本的共享缓冲区使用量查询
    uint32_t used = ingress_bytes[port][qIndex];
    return used > reserve ? used - reserve : 0;
}

bool SwitchMmu::ShouldSendCN(uint32_t ifindex, uint32_t qIndex) {
    // HPCC 版本的 ECN 标记逻辑
    if (qIndex == 0)  // 最高优先级不标记
        return false;
        
    if (egress_bytes[ifindex][qIndex] > kmax[ifindex]) {
        return true;
    }
    
    if (egress_bytes[ifindex][qIndex] > kmin[ifindex]) {
        double p = pmax[ifindex] * 
                   double(egress_bytes[ifindex][qIndex] - kmin[ifindex]) / 
                   (kmax[ifindex] - kmin[ifindex]);
        if (UniformVariable(0, 1).GetValue() < p)
            return true;
    }
    
    return false;
}

void SwitchMmu::ConfigEcn(uint32_t port, uint32_t _kmin, uint32_t _kmax, double _pmax) {
    // HPCC 版本的 ECN 配置
    kmin[port] = _kmin * 1000;  // 转换为字节
    kmax[port] = _kmax * 1000;  // 转换为字节
    pmax[port] = _pmax;
    if (m_mmuLog) {
        std::cout << "[MMU-CONFIG-ECN] time=" << Simulator::Now().GetMicroSeconds() 
                  << "us port=" << port 
                  << " kmin_input=" << _kmin << " kmin_bytes=" << kmin[port]
                  << " kmax_input=" << _kmax << " kmax_bytes=" << kmax[port]
                  << " pmax=" << pmax[port] << std::endl;
    }
}

void SwitchMmu::ConfigHdrm(uint32_t port, uint32_t size) {
    // HPCC 版本的 headroom 配置
    headroom[port] = size;
    if (m_mmuLog) {
        std::cout << "[MMU-CONFIG-HDRM] time=" << Simulator::Now().GetMicroSeconds() 
                  << "us port=" << port << " headroom_size=" << size << std::endl;
    }
}

void SwitchMmu::ConfigNPort(uint32_t n_port) {
    uint32_t old_total_hdrm = total_hdrm;
    uint32_t old_total_rsrv = total_rsrv;
    // HPCC 版本的端口数配置
    total_hdrm = 0;
    total_rsrv = 0;
    for (uint32_t i = 1; i <= n_port; i++) {
        total_hdrm += headroom[i];
        total_rsrv += reserve;
    }
    if (m_mmuLog) {
        std::cout << "[MMU-CONFIG-NPORT] time=" << Simulator::Now().GetMicroSeconds() 
                  << "us n_port=" << n_port
                  << " old_total_hdrm=" << old_total_hdrm << " new_total_hdrm=" << total_hdrm
                  << " old_total_rsrv=" << old_total_rsrv << " new_total_rsrv=" << total_rsrv
                  << " reserve_per_port=" << reserve << std::endl;
    }
}

void SwitchMmu::ConfigBufferSize(uint32_t size) {
    // HPCC 版本的缓冲区大小配置
    buffer_size = size;
    if (m_mmuLog) {
        std::cout << "[MMU-CONFIG-BUFFER-SIZE] time=" << Simulator::Now().GetMicroSeconds()
                  << "us new_buffer_size=" << buffer_size << std::endl;
    }
}

// ==================== 兼容性函数实现 ====================

uint32_t SwitchMmu::GetUsedBufferTotal() {
    return shared_used_bytes;
}

void SwitchMmu::SetDynamicThreshold(bool value) {
    // HPCC 版本不支持动态阈值，忽略此设置
}

uint32_t SwitchMmu::GetusedIngressPortBytes(uint32_t port) {
    uint32_t total = 0;
    for (uint32_t i = 0; i < qCnt; i++) {
        total += ingress_bytes[port][i] + hdrm_bytes[port][i];
    }
    return total;
}

uint32_t SwitchMmu::GetusedIngressSPBytes() {
    return shared_used_bytes;
}

uint32_t SwitchMmu::Getport_max_shared_cell(void) const {
    return buffer_size / 4;  // 简化实现
}

uint32_t SwitchMmu::GetusedEgressQSharedBytes(uint32_t port, uint32_t qIndex) {
    return egress_bytes[port][qIndex];
}

uint32_t SwitchMmu::Getop_uc_port_config1_cell(void) const {
    return buffer_size / 2;  // 简化实现
}

// ==================== 原有代码需要的特殊函数 ====================

void SwitchMmu::SetBroadcomParams(
    uint32_t buffer_cell_limit_sp,
    uint32_t buffer_cell_limit_sp_shared,
    uint32_t pg_min_cell,
    uint32_t port_min_cell,
    uint32_t pg_shared_limit_cell,
    uint32_t port_max_shared_cell,
    uint32_t pg_hdrm_limit,
    uint32_t port_max_pkt_size,
    uint32_t q_min_cell,
    uint32_t op_uc_port_config1_cell,
    uint32_t op_uc_port_config_cell,
    uint32_t op_buffer_shared_limit_cell,
    uint32_t q_shared_alpha_cell, 
    uint32_t port_share_alpha_cell,
    uint32_t pg_qcn_threshold) {
    
    // 将 Broadcom 参数映射到 HPCC 版本
    buffer_size = op_buffer_shared_limit_cell;
    reserve = q_min_cell;
    
    // 设置所有端口的 headroom
    for (uint32_t i = 0; i < pCnt; i++) {
        headroom[i] = pg_hdrm_limit;
        pfc_a_shift[i] = 3;  // 默认值，可以根据 q_shared_alpha_cell 调整
    }
    
    // 更新总量
    ConfigNPort(32);  // 假设32端口，可以根据实际情况调整
}

void SwitchMmu::SetMarkingThreshold(uint32_t _kmin, uint32_t _kmax, double _pmax) {
    // 为所有端口设置相同的 ECN 阈值
    for (uint32_t i = 0; i < pCnt; i++) {
        ConfigEcn(i, _kmin, _kmax, _pmax);
    }
}

uint32_t SwitchMmu::GetIngressSP(uint32_t port, uint32_t pgIndex) {
    // 简化的服务池映射
    return pgIndex == 1 ? 1 : 0;
}

uint32_t SwitchMmu::GetEgressSP(uint32_t port, uint32_t qIndex) {
    // 简化的服务池映射
    return qIndex == 0 ? 0 : 1;
}

void SwitchMmu::InitSwitch(void) {
    // HPCC 版本的交换机初始化
    // 重置所有运行时状态
    shared_used_bytes = 0;
    memset(hdrm_bytes, 0, sizeof(hdrm_bytes));
    memset(ingress_bytes, 0, sizeof(ingress_bytes));
    memset(paused, 0, sizeof(paused));
    memset(egress_bytes, 0, sizeof(egress_bytes));
    memset(m_pause_remote, 0, sizeof(m_pause_remote));
}

} // namespace ns3