#!/usr/bin/env python3
"""按 JSON 列表读取电机 16 位寄存器（支持打印模式与真实 CAN 读取）。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:
    import can  # type: ignore
except ImportError:
    can = None

# 固定协议（按用户给出的最新帧）
# 请求: can0 10B [4] 00 0A 01 70   (电机ID=0x0B)
# 应答: can0 700 [6] 0B 0C 01 70 00 02
TX_ID_BASE = 0x100           # 发送ID = 0x100 + motor_id
RX_ID_FIXED = 0x700          # 应答ID固定
MASTER_ID = 0x1E             # 请求 Byte1 固定
READ_CMD = 0x00              # 请求/应答 Byte2 固定
w_data = 500              # 请求/应答 Byte2 固定


def load_id_list(path: Path) -> List[int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "id" not in data or not isinstance(data["id"], list):
        raise ValueError(f"{path} 缺少 id 列表，例如 {{\"id\":[11,12]}}")
    return [int(v) for v in data["id"]]



def build_read_request(reg_addr: int) -> List[int]:
    """请求数据固定为: [00, 0A, 01, addr_low]。"""
    return [0x00, MASTER_ID, (reg_addr >> 8) & 0xFF, reg_addr & 0xFF, (w_data >> 8) & 0xFF, w_data & 0xFF]


def parse_read_response(data: Iterable[int]) -> Dict[str, int]:
    """应答数据格式: [motor_id, host_id, cmd, addr_low, value_hi, value_lo]。"""
    b = list(data)
    if len(b) < 6:
        raise ValueError(f"应答长度过短: {len(b)}")

    motor_id = b[0]
    host_id = b[2]
    cmd = b[1]
    addr_low = b[3]
    value = (b[4] << 8) | b[5]  # 按 00 02 => 2 解析

    return {
        "motor_id": motor_id,
        "host_id": host_id,
        "cmd": cmd,
        "addr_low": addr_low,
        "value": value,
    }


def can_read_register(
    bus: "can.BusABC",
    motor_id: int,
    reg_addr: int,
    timeout: float = 0.2,
) -> Optional[Dict[str, int]]:
    """发送单次读寄存器请求并等待匹配应答。"""
    tx_id = TX_ID_BASE + (motor_id & 0xFF)
    tx_data = build_read_request(reg_addr)
    tx = can.Message(arbitration_id=tx_id, is_extended_id=False, data=tx_data)
    bus.send(tx)
    return None


def run_can_read(
    ids: List[int],
    addrs: List[int],
    channel: str,
    bustype: str,
    bitrate: int,
    timeout: float,
) -> None:
    if can is None:
        raise RuntimeError("未安装 python-can。请先执行: pip install python-can")

    with can.Bus(interface=bustype, channel=channel, bitrate=bitrate) as bus:
        for mid in ids:
            print(f"电机 ID {mid}:")
            for addr in addrs:
                result = can_read_register(bus=bus, motor_id=mid, reg_addr=addr, timeout=timeout)
                if result is None:
                    print(f"  - 0x{addr:04X}: 超时无应答")
                    continue
                print(f"  - 0x{addr:04X}: 0x{result['value']:04X} ({result['value']})")

def main() -> None:
    parser = argparse.ArgumentParser(description="按 JSON 列表读取电机 16 位寄存器")
    parser.add_argument("--ids", required=True, type=Path, help="电机ID列表JSON，如 {'id':[11,12]}")
    parser.add_argument("--addrs", required=True, type=Path, help="寄存器地址JSON，如 {'addr':['0x170','0x171']}")

    parser.add_argument("--read", action="store_true", help="启用真实 CAN 读取；默认仅打印将发送的报文")
    parser.add_argument("--channel", default="can0", help="CAN 通道，默认 can0")
    parser.add_argument("--bustype", default="socketcan", help="python-can interface，默认 socketcan")
    parser.add_argument("--bitrate", default=500000, type=int, help="波特率，默认 500000")
    parser.add_argument("--timeout", default=0.2, type=float, help="每个寄存器应答超时秒")

    args = parser.parse_args()

    ids = load_id_list(args.ids)

    addrs = [0x00dd]

    run_can_read(
        ids=ids,
        addrs=addrs,
        channel=args.channel,
        bustype=args.bustype,
        bitrate=args.bitrate,
        timeout=args.timeout,
    )

if __name__ == "__main__":
    main()
