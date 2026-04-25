#!/usr/bin/env python3
"""根据电机 CAN 协议读取 16 位寄存器并按电机打印结果。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:
    import can  # type: ignore
except ImportError:
    can = None

# 依据用户给出的示例：
# 读 id=11 电机时，请求 can id = 0x60B，回复 can id = 0x600
# 请求数据: 00 0A 01 70
# 回复数据: 00 0B 01 70 AA AA  (AA AA 为16位寄存器值)
TX_ID_BASE = 0x600
RX_ID = 0x600
READ_CMD = 0x01


def load_id_list(path: Path) -> List[int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "id" not in data or not isinstance(data["id"], list):
        raise ValueError(f"{path} 缺少 id 列表，例如 {{\"id\":[1,2,3]}}")
    return [int(v) for v in data["id"]]


def load_addr_list(path: Path) -> List[int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "addr" not in data or not isinstance(data["addr"], list):
        raise ValueError(f"{path} 缺少 addr 列表，例如 {{\"addr\":[\"0x170\",\"0x171\"]}}")

    out: List[int] = []
    for raw in data["addr"]:
        out.append(int(raw, 0) if isinstance(raw, str) else int(raw))
    return out


def build_read_request(target_id: int, reg_addr: int, source_id: int = 0x0A, cmd: int = READ_CMD) -> List[int]:
    """构造读取 16 位寄存器请求 DATA。格式: [0x00, source_id, cmd, addr_low]"""
    _ = target_id
    return [
        0x00,
        source_id & 0xFF,
        cmd & 0xFF,
        reg_addr & 0xFF,
    ]


def parse_read_response(data: Iterable[int]) -> Dict[str, int]:
    """解析应答 DATA。期望格式: [0x00, motor_id, cmd, addr_low, value_lo, value_hi]。"""
    b = list(data)
    if len(b) < 6:
        raise ValueError(f"应答长度过短: {len(b)}")

    motor_id = b[1]
    cmd = b[2]
    addr_low = b[3]
    reg_val = b[4] | (b[5] << 8)

    return {
        "motor_id": motor_id,
        "cmd": cmd,
        "addr_low": addr_low,
        "value": reg_val,
    }


def can_read_register(
    bus: "can.BusABC",
    motor_id: int,
    reg_addr: int,
    source_id: int = 0x0A,
    tx_base_id: int = TX_ID_BASE,
    rx_id: int = RX_ID,
    cmd: int = READ_CMD,
    timeout: float = 0.2,
) -> Optional[Dict[str, int]]:
    """发送单次读寄存器请求并等待应答。"""
    request_data = build_read_request(motor_id, reg_addr, source_id=source_id, cmd=cmd)
    tx = can.Message(arbitration_id=(tx_base_id + (motor_id & 0xFF)), is_extended_id=False, data=request_data)
    bus.send(tx)

    while True:
        rx = bus.recv(timeout=timeout)
        if rx is None:
            return None

        if rx.arbitration_id != rx_id:
            continue

        parsed = parse_read_response(rx.data)
        if parsed["motor_id"] != (motor_id & 0xFF):
            continue
        if parsed["cmd"] != (cmd & 0xFF):
            continue
        if parsed["addr_low"] != (reg_addr & 0xFF):
            continue
        return parsed


def run_print_only(ids: List[int], addrs: List[int]) -> None:
    for mid in ids:
        print(f"电机 ID {mid}:")
        for addr in addrs:
            print(f"  - 寄存器 0x{addr:04X}")


def run_can_read(
    ids: List[int],
    addrs: List[int],
    channel: str,
    bustype: str,
    bitrate: int,
    source_id: int,
    tx_base_id: int,
    rx_id: int,
    cmd: int,
    timeout: float,
) -> None:
    if can is None:
        raise RuntimeError("未安装 python-can。请先执行: pip install python-can")

    with can.Bus(interface=bustype, channel=channel, bitrate=bitrate) as bus:
        for mid in ids:
            print(f"电机 ID {mid}:")
            for addr in addrs:
                result = can_read_register(
                    bus=bus,
                    motor_id=mid,
                    reg_addr=addr,
                    source_id=source_id,
                    tx_base_id=tx_base_id,
                    rx_id=rx_id,
                    cmd=cmd,
                    timeout=timeout,
                )
                if result is None:
                    print(f"  - 0x{addr:04X}: 超时无应答")
                    continue

                print(f"  - 0x{addr:04X}: 0x{result['value']:04X} ({result['value']})")


def main() -> None:
    parser = argparse.ArgumentParser(description="按 JSON 列表读取电机 16 位寄存器")
    parser.add_argument("--ids", required=True, type=Path, help="电机ID列表JSON，如 {'id':[11,12]}")
    parser.add_argument("--addrs", required=True, type=Path, help="寄存器地址JSON，如 {'addr':['0x170','0x171']}")

    parser.add_argument("--read", action="store_true", help="启用真实 CAN 读取；默认仅打印分组")
    parser.add_argument("--channel", default="can0", help="CAN 通道，默认 can0")
    parser.add_argument("--bustype", default="socketcan", help="python-can interface，默认 socketcan")
    parser.add_argument("--bitrate", default=500000, type=int, help="波特率，默认 500000")
    parser.add_argument("--source-id", default=0x0A, type=lambda x: int(x, 0), help="主站ID，默认 0x0A")
    parser.add_argument("--tx-base-id", default=0x600, type=lambda x: int(x, 0), help="发送 CAN ID 基值，默认 0x600")
    parser.add_argument("--rx-id", default=0x600, type=lambda x: int(x, 0), help="接收应答 CAN ID，默认 0x600")
    parser.add_argument("--cmd", default=0x01, type=lambda x: int(x, 0), help="读取命令字节，默认 0x01")
    parser.add_argument("--timeout", default=0.2, type=float, help="每个寄存器应答超时秒")

    args = parser.parse_args()

    ids = load_id_list(args.ids)
    addrs = load_addr_list(args.addrs)

    if args.read:
        run_can_read(
            ids=ids,
            addrs=addrs,
            channel=args.channel,
            bustype=args.bustype,
            bitrate=args.bitrate,
            source_id=args.source_id,
            tx_base_id=args.tx_base_id,
            rx_id=args.rx_id,
            cmd=args.cmd,
            timeout=args.timeout,
        )
    else:
        run_print_only(ids, addrs)


if __name__ == "__main__":
    main()
