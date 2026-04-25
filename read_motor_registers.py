#!/usr/bin/env python3
"""根据电机 CAN 协议读取 16 位寄存器并按电机打印结果。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:
    import can  # type: ignore
except ImportError:  # 允许仅演示 JSON 与报文组包逻辑
    can = None

MODE_BYTE = 0x01
CMD_READ_16_REQ = 0x14  # 问者功能码 20 (0x14)
CMD_READ_16_ACK = 0x15  # 答者正常功能码 21 (0x15)
CMD_READ_16_ERR = 0x16  # 答者异常功能码 22 (0x16)


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
        if isinstance(raw, str):
            out.append(int(raw, 0))
        else:
            out.append(int(raw))
    return out


def build_read_request(target_id: int, reg_addr: int, source_id: int = 0x01) -> List[int]:
    """构造读取 16 位寄存器请求 DATA[0..7]。"""
    return [
        source_id & 0xFF,          # Byte0: 问者 ID（消息源）
        CMD_READ_16_REQ & 0xFF,    # Byte1: 功能码 0x14
        reg_addr & 0xFF,           # Byte2: 寄存器地址低字节
        (reg_addr >> 8) & 0xFF,    # Byte3: 寄存器地址高字节
        0x00,
        0x00,
        0x00,
        0x00,
    ]


def parse_read_response(data: Iterable[int]) -> Dict[str, int]:
    """解析应答帧 DATA，返回功能码、地址和值/错误码。"""
    b = list(data)
    if len(b) < 6:
        raise ValueError(f"应答长度过短: {len(b)}")

    cmd = b[1]
    reg_addr = b[2] | (b[3] << 8)

    if cmd == CMD_READ_16_ACK:
        reg_val = b[4] | (b[5] << 8)
        return {"cmd": cmd, "addr": reg_addr, "value": reg_val}
    if cmd == CMD_READ_16_ERR:
        err_code = b[4]
        return {"cmd": cmd, "addr": reg_addr, "error": err_code}

    return {"cmd": cmd, "addr": reg_addr}


def can_read_register(
    bus: "can.BusABC",
    motor_id: int,
    reg_addr: int,
    source_id: int = 0x01,
    arbitration_id: int = 0x000,
    timeout: float = 0.2,
) -> Optional[Dict[str, int]]:
    """发请求并等待应答。注意：ID 过滤规则按你的控制器再调整。"""
    request_data = build_read_request(motor_id, reg_addr, source_id)
    tx = can.Message(arbitration_id=arbitration_id, is_extended_id=False, data=request_data)
    bus.send(tx)

    deadline = timeout
    while True:
        rx = bus.recv(timeout=deadline)
        if rx is None:
            return None

        if len(rx.data) < 2:
            continue

        # 协议中 D7-D0 通常放答者ID，这里假设在 arbitration_id 的低8位
        responder_id = rx.arbitration_id & 0xFF
        if responder_id != (motor_id & 0xFF):
            continue

        parsed = parse_read_response(rx.data)
        return parsed


def run_print_only(ids: List[int], addrs: List[int]) -> None:
    """仅按电机打印要读取的寄存器列表。"""
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
    arbitration_id: int,
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
                    arbitration_id=arbitration_id,
                    timeout=timeout,
                )
                if result is None:
                    print(f"  - 0x{addr:04X}: 超时无应答")
                    continue

                cmd = result.get("cmd")
                if cmd == CMD_READ_16_ACK:
                    print(f"  - 0x{addr:04X}: 0x{result['value']:04X} ({result['value']})")
                elif cmd == CMD_READ_16_ERR:
                    print(f"  - 0x{addr:04X}: 错误码 {result['error']}")
                else:
                    print(f"  - 0x{addr:04X}: 未知应答 {result}")


def main() -> None:
    parser = argparse.ArgumentParser(description="按 JSON 列表读取电机 16 位寄存器")
    parser.add_argument("--ids", required=True, type=Path, help="电机ID列表JSON，如 {'id':[1,2,3]}")
    parser.add_argument("--addrs", required=True, type=Path, help="寄存器地址JSON，如 {'addr':['0x170','0x171']}")

    parser.add_argument("--read", action="store_true", help="启用真实 CAN 读取；默认仅打印分组")
    parser.add_argument("--channel", default="can0", help="CAN 通道，默认 can0")
    parser.add_argument("--bustype", default="socketcan", help="python-can interface，默认 socketcan")
    parser.add_argument("--bitrate", default=500000, type=int, help="波特率，默认 500000")
    parser.add_argument("--source-id", default=0x01, type=lambda x: int(x, 0), help="问者ID，默认 0x01")
    parser.add_argument("--arb-id", default=0x000, type=lambda x: int(x, 0), help="发送帧标识符ID，默认 0x000")
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
            arbitration_id=args.arb_id,
            timeout=args.timeout,
        )
    else:
        run_print_only(ids, addrs)


if __name__ == "__main__":
    main()
