#ifndef SWITCH_MMU_H
#define SWITCH_MMU_H

#include <ns3/node.h>
#include <ns3/random-variable-stream.h>
#include <ns3/simulator.h>
#include <ns3/event-id.h>

#include <list>
#include <unordered_map>

// 保留原有的路由模块引用
#include "ns3/conga-routing.h"
#include "ns3/conweave-routing.h"
#include "ns3/letflow-routing.h"
#include "ns3/settings.h"
#include "ns3/dv-routing.h"
#include "ns3/caver-routing.h"
#include "ns3/hula-routing.h"
#include "ns3/noshare-routing.h"

namespace ns3 {

class Packet;

class SwitchMmu : public Object {
   public:
    // 使用 HPCC 版本的常量定义
    static const uint32_t pCnt = 257;  // Number of ports used
    static const uint32_t qCnt = 8;    // Number of queues/priorities used
    static const uint32_t MTU = 1048;  // MTU size

    static TypeId GetTypeId(void);

    SwitchMmu(void);

    // ==================== HPCC 版本的核心接口 ====================
    bool CheckIngressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize);
    bool CheckEgressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize);
    void UpdateIngressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize);
    void UpdateEgressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize);
    void RemoveFromIngressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize);
    void RemoveFromEgressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize);

    // ==================== HPCC 版本的 PFC 接口 ====================
    bool CheckShouldPause(uint32_t port, uint32_t qIndex);
    bool CheckShouldResume(uint32_t port, uint32_t qIndex);
    void SetPause(uint32_t port, uint32_t qIndex);
    void SetResume(uint32_t port, uint32_t qIndex);

    // ==================== PFC 死锁检测相关函数 ====================
    void PfcDeadlockCheck(uint32_t port, uint32_t qIndex);
    void StartPfcDeadlockTimer(uint32_t port, uint32_t qIndex);
    void StopPfcDeadlockTimer(uint32_t port, uint32_t qIndex);

    // ==================== 兼容性包装函数 ====================
    // 为了兼容原有代码而添加的包装函数
    void GetPauseClasses(uint32_t port, uint32_t qIndex, bool pClasses[]);
    bool GetResumeClasses(uint32_t port, uint32_t qIndex);
    void SetPause(uint32_t port, uint32_t qIndex, uint32_t pause_time);

    // ==================== HPCC 版本的配置接口 ====================
    void ConfigEcn(uint32_t port, uint32_t _kmin, uint32_t _kmax, double _pmax);
    void ConfigHdrm(uint32_t port, uint32_t size);
    void ConfigNPort(uint32_t n_port);
    void ConfigBufferSize(uint32_t size);

    // ==================== HPCC 版本的查询接口 ====================
    uint32_t GetPfcThreshold(uint32_t port);
    uint32_t GetSharedUsed(uint32_t port, uint32_t qIndex);
    bool ShouldSendCN(uint32_t ifindex, uint32_t qIndex);

    // ==================== 兼容性查询函数 ====================
    uint32_t GetUsedBufferTotal();
    void SetDynamicThreshold(bool value);
    bool GetDynamicThreshold(void) const { return false; } // HPCC 不支持动态阈值

    // 兼容性函数 - 映射到 HPCC 版本
    uint32_t GetusedIngressPortBytes(uint32_t port);
    uint32_t GetusedIngressSPBytes();
    uint32_t Getport_max_shared_cell(void) const;
    uint32_t GetusedEgressQSharedBytes(uint32_t port, uint32_t qIndex);
    uint32_t Getop_uc_port_config1_cell(void) const;

    // ==================== 原有代码需要的特殊函数 ====================
    void SetBroadcomParams(uint32_t buffer_cell_limit_sp,
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
                           uint32_t pg_qcn_threshold);

    void SetMarkingThreshold(uint32_t kmin, uint32_t kmax, double pmax);
    uint32_t GetIngressSP(uint32_t port, uint32_t pgIndex);
    uint32_t GetEgressSP(uint32_t port, uint32_t qIndex);
    void InitSwitch(void);

    // ==================== HPCC 版本的配置参数 ====================
    uint32_t node_id;
    uint32_t buffer_size;
    uint32_t pfc_a_shift[pCnt];
    uint32_t reserve;
    uint32_t headroom[pCnt];
    uint32_t resume_offset;
    uint32_t kmin[pCnt], kmax[pCnt];
    double pmax[pCnt];
    uint32_t total_hdrm;
    uint32_t total_rsrv;

    // ==================== HPCC 版本的运行时状态 ====================
    uint32_t shared_used_bytes;
    uint32_t hdrm_bytes[pCnt][qCnt];
    uint32_t ingress_bytes[pCnt][qCnt];
    uint32_t paused[pCnt][qCnt];
    uint32_t egress_bytes[pCnt][qCnt];

    /*------------ Conga Objects-------------*/
    CongaRouting m_congaRouting;

    /*------------ Letflow Objects-------------*/
    LetflowRouting m_letflowRouting;

    /*------------ ConWeave Objects-------------*/
    ConWeaveRouting m_conweaveRouting;

    /*------------ DVObjects-------------*/
    DVRouting m_dvRouting;

    /*------------ CaverObjects-------------*/
    CaverRouting m_caverRouting;

    /*------------ HulaObjects-------------*/
    HulaRouting m_hulaRouting;

    /*------------ NoshareObjects-------------*/
    NoshareRouting m_noshareRouting;

    // ==================== 兼容性变量 ====================
    // 为兼容原有代码添加的变量，用于 pause_remote 状态
    bool m_pause_remote[pCnt][qCnt];
    EventId resumeEvt[pCnt][qCnt];

    // ==================== PFC 死锁检测变量 ====================
    EventId pfcDeadlockTimer[pCnt][qCnt];  // PFC 死锁检测定时器
    uint64_t pfcPauseStartTime[pCnt][qCnt]; // PFC 暂停开始时间
    uint32_t pfcDeadlockCheckCount[pCnt][qCnt]; // PFC 死锁检测次数
    uint32_t m_switch_id; // 本交换机 ID，需要在初始化时设置

    bool m_mmuLog = false;
    bool m_drop_log = false;
    uint32_t GetPeerSwitchId(uint32_t port);

   private:
    bool m_PFCenabled = true;
};

} /* namespace ns3 */

#endif /* SWITCH_MMU_H */